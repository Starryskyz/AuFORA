package aufora.dsa

import chisel3._
import scala.collection.mutable
import scala.collection.mutable.{ArrayBuffer, ListBuffer}
import aufora.ir.IR
import aufora.common.MacroVar._

/**
  * One-bit GIB fabric for a single AuFORA tile.
  *
  * The fabric mirrors the corner-switchbox topology of the wide CG network,
  * but it is deliberately kept inside a tile.  This avoids changing the
  * existing cross-tile data network and lets FG routing be enabled per build.
  */
class FineGrainedTileNetwork(
  rows: Int,
  cols: Int,
  peFgInputs: Int,
  peFgOutputs: Int,
  iobFgInputs: Int,
  iobFgOutputs: Int,
  numTrack: Int,
  trackRegedMode: Int,
  diagIopinConnect: Boolean,
  connectFlexibility: List[Int],
  cfgDataWidth: Int,
  cfgAddrWidth: Int,
  cfgBlkOffset: Int,
  cfgBaseBlock: Int,
  tileId: Int
) extends Module with IR {
  require(peFgInputs > 0 && peFgInputs % 4 == 0,
    s"PE FG inputs must contain four directional candidates per operand, got $peFgInputs")
  require(peFgOutputs > 0)
  require(iobFgInputs == 2, s"top/bottom IOBs require two FG input candidates, got $iobFgInputs")
  require(iobFgOutputs == 1)

  private val peCount = rows * cols
  private val iobCount = 2 * cols
  private val peOperands = peFgInputs / 4
  private val gibRows = rows + 1
  private val gibCols = cols + 1

  val io = IO(new Bundle {
    val cfg_en = Input(Bool())
    val cfg_addr = Input(UInt(cfgAddrWidth.W))
    val cfg_data = Input(UInt(cfgDataWidth.W))
    val pe_in = Output(Vec(peCount, Vec(peFgInputs, UInt(1.W))))
    val pe_out = Input(Vec(peCount, Vec(peFgOutputs, UInt(1.W))))
    val iob_in = Output(Vec(iobCount, Vec(iobFgInputs, UInt(1.W))))
    val iob_out = Input(Vec(iobCount, Vec(iobFgOutputs, UInt(1.W))))
  })

  apply("type", "FineGrainedGIBNetwork")
  apply("tile", tileId)
  apply("data_width", 1)
  apply("num_track", numTrack)
  apply("num_pe", peCount)
  apply("num_iob", iobCount)
  apply("cfg_base_block", cfgBaseBlock)

  private def peInputsAt(valid: Boolean): Int = if(valid) peOperands else 0
  private def peOutputsAt(valid: Boolean): Int = if(valid) peFgOutputs else 0
  private def iobInputsAt(valid: Boolean): Int = if(valid) 1 else 0
  private def iobOutputsAt(valid: Boolean): Int = if(valid) iobFgOutputs else 0

  val gibs = new ArrayBuffer[GIB]()
  for(r <- 0 until gibRows; c <- 0 until gibCols) {
    val nwPe = r > 0 && c > 0
    val nePe = r > 0 && c < cols
    val sePe = r < rows && c < cols
    val swPe = r < rows && c > 0
    val topNwIob = r == 0 && c > 0
    val topNeIob = r == 0 && c < cols
    val bottomSeIob = r == rows && c < cols
    val bottomSwIob = r == rows && c > 0

    val pinMap = mutable.Map[String, Int](
      "ipin_nw" -> (peInputsAt(nwPe) + iobInputsAt(topNwIob)),
      "opin_nw" -> (peOutputsAt(nwPe) + iobOutputsAt(topNwIob)),
      "ipin_ne" -> (peInputsAt(nePe) + iobInputsAt(topNeIob)),
      "opin_ne" -> (peOutputsAt(nePe) + iobOutputsAt(topNeIob)),
      "ipin_se" -> (peInputsAt(sePe) + iobInputsAt(bottomSeIob)),
      "opin_se" -> (peOutputsAt(sePe) + iobOutputsAt(bottomSeIob)),
      "ipin_sw" -> (peInputsAt(swPe) + iobInputsAt(bottomSwIob)),
      "opin_sw" -> (peOutputsAt(swPe) + iobOutputsAt(bottomSwIob))
    )

    val directions = ListBuffer[Int]()
    if(c > 0) directions += WEST
    if(r > 0) directions += NORTH
    if(c < cols) directions += EAST
    if(r < rows) directions += SOUTH
    val reged = trackRegedMode match {
      case 0 => false
      case 2 => true
      case _ => ((r + c) & 1) == 1
    }
    val local = r * gibCols + c
    val gibAttrs = mutable.Map[String, Any](
      "data_width" -> 1,
      "cfg_data_width" -> cfgDataWidth,
      "cfg_addr_width" -> cfgAddrWidth,
      "cfg_blk_index" -> (cfgBaseBlock + local),
      "cfg_blk_offset" -> cfgBlkOffset,
      "x" -> (2 * r + 1),
      "y" -> (2 * c + 1),
      "tile" -> tileId,
      "num_track" -> numTrack,
      "diag_iopin_connect" -> diagIopinConnect,
      "num_iopin_list" -> pinMap,
      "connect_flexibility" -> connectFlexibility,
      "track_reged" -> reged,
      "track_directions" -> directions
    )
    val gib = Module(new GIB(gibAttrs)).suggestName(s"fg_gib_t${tileId}_r${r}_c${c}")
    gib.io.cfg_en := io.cfg_en
    gib.io.cfg_addr := io.cfg_addr
    gib.io.cfg_data := io.cfg_data
    gibs += gib
  }

  private def gib(r: Int, c: Int): GIB = gibs(r * gibCols + c)
  private def gibId(r: Int, c: Int): Int = r * gibCols + c

  // Explicit architectural edges are exported for the mapper.  Node IDs are
  // local to the tile and are disambiguated by the source/destination type.
  // Format: src_type, src_local_id, src_port, dst_type, dst_local_id,
  // dst_port, bit_width.
  val connections = ListBuffer[(String, Int, Int, String, Int, Int, Int)]()

  // Bidirectional routing tracks between neighboring fine-grained GIBs.
  for(r <- 0 until gibRows; c <- 0 until gibCols; t <- 0 until numTrack) {
    gib(r,c).io.itrackW(t) := (if(c > 0) gib(r,c-1).io.otrackE(t) else 0.U)
    gib(r,c).io.itrackE(t) := (if(c < cols) gib(r,c+1).io.otrackW(t) else 0.U)
    gib(r,c).io.itrackN(t) := (if(r > 0) gib(r-1,c).io.otrackS(t) else 0.U)
    gib(r,c).io.itrackS(t) := (if(r < rows) gib(r+1,c).io.otrackN(t) else 0.U)
    if(c > 0) connections += (("FGGIB", gibId(r,c-1), gib(r,c-1).oPortMap(s"otrackE$t"),
      "FGGIB", gibId(r,c), gib(r,c).iPortMap(s"itrackW$t"), 1))
    if(c < cols) connections += (("FGGIB", gibId(r,c+1), gib(r,c+1).oPortMap(s"otrackW$t"),
      "FGGIB", gibId(r,c), gib(r,c).iPortMap(s"itrackE$t"), 1))
    if(r > 0) connections += (("FGGIB", gibId(r-1,c), gib(r-1,c).oPortMap(s"otrackS$t"),
      "FGGIB", gibId(r,c), gib(r,c).iPortMap(s"itrackN$t"), 1))
    if(r < rows) connections += (("FGGIB", gibId(r+1,c), gib(r+1,c).oPortMap(s"otrackN$t"),
      "FGGIB", gibId(r,c), gib(r,c).iPortMap(s"itrackS$t"), 1))
  }

  // PE pins.  Input ordering follows AuFORA's default direction order:
  // NORTHWEST, NORTHEAST, SOUTHWEST, SOUTHEAST for every FG operand.
  for(r <- 0 until rows; c <- 0 until cols) {
    val p = r * cols + c
    for(op <- 0 until peOperands) {
      io.pe_in(p)(op*4 + 0) := gib(r, c).io.ipinSE(op)
      io.pe_in(p)(op*4 + 1) := gib(r, c+1).io.ipinSW(op)
      io.pe_in(p)(op*4 + 2) := gib(r+1, c).io.ipinNE(op)
      io.pe_in(p)(op*4 + 3) := gib(r+1, c+1).io.ipinNW(op)
      connections += (("FGGIB", gibId(r,c), gib(r,c).oPortMap(s"ipinSE$op"),
        "GPE", p, op*4 + 0, 1))
      connections += (("FGGIB", gibId(r,c+1), gib(r,c+1).oPortMap(s"ipinSW$op"),
        "GPE", p, op*4 + 1, 1))
      connections += (("FGGIB", gibId(r+1,c), gib(r+1,c).oPortMap(s"ipinNE$op"),
        "GPE", p, op*4 + 2, 1))
      connections += (("FGGIB", gibId(r+1,c+1), gib(r+1,c+1).oPortMap(s"ipinNW$op"),
        "GPE", p, op*4 + 3, 1))
    }
    for(o <- 0 until peFgOutputs) {
      gib(r, c).io.opinSE(o) := io.pe_out(p)(o)
      gib(r, c+1).io.opinSW(o) := io.pe_out(p)(o)
      gib(r+1, c).io.opinNE(o) := io.pe_out(p)(o)
      gib(r+1, c+1).io.opinNW(o) := io.pe_out(p)(o)
      connections += (("GPE", p, o, "FGGIB", gibId(r,c),
        gib(r,c).iPortMap(s"opinSE$o"), 1))
      connections += (("GPE", p, o, "FGGIB", gibId(r,c+1),
        gib(r,c+1).iPortMap(s"opinSW$o"), 1))
      connections += (("GPE", p, o, "FGGIB", gibId(r+1,c),
        gib(r+1,c).iPortMap(s"opinNE$o"), 1))
      connections += (("GPE", p, o, "FGGIB", gibId(r+1,c+1),
        gib(r+1,c+1).iPortMap(s"opinNW$o"), 1))
    }
  }

  // Top and bottom IOB pins.
  for(c <- 0 until cols) {
    val top = c
    io.iob_in(top)(0) := gib(0, c).io.ipinNE(0)
    io.iob_in(top)(1) := gib(0, c+1).io.ipinNW(0)
    gib(0, c).io.opinNE(0) := io.iob_out(top)(0)
    gib(0, c+1).io.opinNW(0) := io.iob_out(top)(0)
    connections += (("FGGIB", gibId(0,c), gib(0,c).oPortMap("ipinNE0"), "IOB", top, 0, 1))
    connections += (("FGGIB", gibId(0,c+1), gib(0,c+1).oPortMap("ipinNW0"), "IOB", top, 1, 1))
    connections += (("IOB", top, 0, "FGGIB", gibId(0,c), gib(0,c).iPortMap("opinNE0"), 1))
    connections += (("IOB", top, 0, "FGGIB", gibId(0,c+1), gib(0,c+1).iPortMap("opinNW0"), 1))

    val bottom = cols + c
    io.iob_in(bottom)(0) := gib(rows, c).io.ipinSE(0)
    io.iob_in(bottom)(1) := gib(rows, c+1).io.ipinSW(0)
    gib(rows, c).io.opinSE(0) := io.iob_out(bottom)(0)
    gib(rows, c+1).io.opinSW(0) := io.iob_out(bottom)(0)
    connections += (("FGGIB", gibId(rows,c), gib(rows,c).oPortMap("ipinSE0"), "IOB", bottom, 0, 1))
    connections += (("FGGIB", gibId(rows,c+1), gib(rows,c+1).oPortMap("ipinSW0"), "IOB", bottom, 1, 1))
    connections += (("IOB", bottom, 0, "FGGIB", gibId(rows,c), gib(rows,c).iPortMap("opinSE0"), 1))
    connections += (("IOB", bottom, 0, "FGGIB", gibId(rows,c+1), gib(rows,c+1).iPortMap("opinSW0"), 1))
  }

  val totalCfgBits: Int = gibs.map(_.cfgsBit).sum
  apply("sum_cfg_bits", totalCfgBits)
  apply("gibs", gibs.zipWithIndex.map { case (g, i) =>
    i -> g.getAttrs
  }.toMap)
  apply("connections", connections.zipWithIndex.map { case (c, i) => i -> c }.toMap)
}
