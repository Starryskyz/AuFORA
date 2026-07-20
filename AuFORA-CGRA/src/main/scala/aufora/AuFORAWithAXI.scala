package aufora

import aufora._
import aufora.axi.{AXI4Bundle, AXI4BundleParameters, AXI4Scratchpad, AXILiteBundle}
import aufora.spec._


import chisel3._
import chisel3.util._
import firrtl.Utils.True
import firrtl.stage.FirrtlStage


import java.io.File

object AuFORAParam {
  val dumpSpec : Boolean = true
  val loadSpec : Boolean = false
  val dumpOperationSet : Boolean = true
  val dumpADG : Boolean = true
  val rootDirPath = (new File("")).getAbsolutePath()
  // val aufora_spec_filename = rootDirPath + "/generators/aufora/AuFORA/src/main/aufora_spec/aufora_spec.json"
  // val operation_set_filename = rootDirPath + "/generators/aufora/AuFORA/src/main/aufora_spec/operations.json"
  // val cgra_adg_filename = rootDirPath + "/generators/aufora/AuFORA/src/main/aufora_spec/aufora_cgra_adg.json"
  // val axil_reg_spec_filename = rootDirPath + "/generators/aufora/AuFORA/src/main/aufora_spec/axilite_spec.json"
  val FPGAImp = true
  val outputDir = sys.env.getOrElse("AUFORA_OUTPUT_DIR", "verilog")
  val spec_dir = new File(outputDir, "aufora-spec").getPath
  new File(spec_dir).mkdirs()

  val aufora_spec_filename = spec_dir + "/aufora_spec.json"
  val operation_set_filename = spec_dir + "/operations.json"
  val cgra_adg_filename = spec_dir + "/aufora_cgra_adg.json"
  val axil_reg_spec_filename = spec_dir + "/axilite_spec.json"

}

class AuFORAWithAXI(/*opcodes: OpcodeSet*/)/*(implicit p: Parameters)*/ extends Module  {
  override def desiredName = "AuFORAWithAXI"
  // override def desiredName = "aufora"
  import AuFORAParam._
  // println(aufora_spec_filename)
  if(dumpSpec){ AuFORASpec.dumpSpec(aufora_spec_filename) }
  if(loadSpec){ AuFORASpec.loadSpec(aufora_spec_filename) }
  AuFORASpec.attrs("dumpOperationSet") = dumpOperationSet
  if(dumpOperationSet){ AuFORASpec.attrs("operation_set_filename") = operation_set_filename }
  AuFORASpec.attrs("dumpOperationSet") = dumpADG
  if(dumpADG){ AuFORASpec.attrs("cgra_adg_filename") = cgra_adg_filename }
  println(s"adg path: $cgra_adg_filename")
  // scratchpad banks used for IOB
  val lgSizeSpadBank = AuFORASpec.attrs("spad_bank_lg_size").asInstanceOf[Int]
  val nSpadBanksEachTile = AuFORASpec.attrs("tile_spad_num_banks").asInstanceOf[Int]
  val nTiles = AuFORASpec.attrs("cgra_tile_num").asInstanceOf[Int]
  val nSpadBanksTotal = nSpadBanksEachTile * nTiles

  // scratchpad block used for Config
  val spadDataWidth = AuFORASpec.attrs("spad_data_width").asInstanceOf[Int]
  val cgraDataWidth = AuFORASpec.attrs("cgra_data_width").asInstanceOf[Int]
  val lgSizeSpadCfg = AuFORASpec.attrs("spad_cfg_lg_size").asInstanceOf[Int]
  val cfgSpadBanks = {
    if(lgSizeSpadCfg <= lgSizeSpadBank) 1
    else 1 << (lgSizeSpadCfg - lgSizeSpadBank)
  }
  val spadAddrWidth = lgSizeSpadBank + log2Ceil(nSpadBanksTotal+cfgSpadBanks) // in bus width bytes
  // println("lgSizeSpadBank, nSpadBanksTotal, cfgSpadBanks", lgSizeSpadBank, nSpadBanksTotal, cfgSpadBanks)
  // println("spadAddrWidth", spadAddrWidth)

  val lgMaxDataLen = spadAddrWidth
  val spadAddrNum = AuFORASpec.attrs("spad_addr_num").asInstanceOf[Int]
  val hasMask = AuFORASpec.attrs("cgra_iob_sram_has_mask").asInstanceOf[Boolean] //true // spadDataWidth != cgraDataWidth

  val idWidth = AuFORASpec.attrs("id_width").asInstanceOf[Int]
  val nReqInflight = AuFORASpec.attrs("dma_num_req_in_flight").asInstanceOf[Int]
  val maxLgSizeTL = AuFORASpec.attrs("dma_lg_max_burst_size").asInstanceOf[Int]
  val nWaysOfTLB = AuFORASpec.attrs("tlb_num_ways").asInstanceOf[Int]
  val useSharedTLB = AuFORASpec.attrs("tlb_is_shared").asInstanceOf[Boolean]


  ///// AXI LITE Parameters
  val AxiLiteAddrSpace = AuFORASpec.attrs("axilite_addrspace").asInstanceOf[Int] // Bytes
  val AxiLiteDataWidth = AuFORASpec.attrs("axilite_datawidth").asInstanceOf[Int]   // Byte
  val AxiLiteAddrWidth = log2Ceil(AxiLiteAddrSpace)

//  val cmdQueDepth = AuFORASpec.attrs("rs_cmd_queue_depth").asInstanceOf[Int]
//   val loadQueDepth = AuFORASpec.attrs("rs_load_queue_depth").asInstanceOf[Int]
//   val storeQueDepth = AuFORASpec.attrs("rs_store_queue_depth").asInstanceOf[Int]
//   val exeQueDepth = AuFORASpec.attrs("rs_exe_queue_depth").asInstanceOf[Int]
//   val streamQueDepth = AuFORASpec.attrs("ls_stream_queue_depth").asInstanceOf[Int]
  
  // val module = Module(new AuFORAModuleWithAxiImp(this))
  // val dma_node = LazyModule(new DMAController(lgMaxDataLen, spadDataWidth, hasMask, idWidth, nReqInflight, maxLgSizeTL, nWaysOfTLB, useSharedTLB))
  // override val tlNode = dma_node.id_node
  //  tlNode := dma_node.id_node
  // val axiAddrWidth = log2Ceil(nSpadBanksTotal * (1 << lgSizeSpadBank) - 1) - log2Ceil(spadDataWidth / 8)
  // val axiAddrWidth = log2Ceil(nSpadBanksTotal * (1 << lgSizeSpadBank) + lgSizeSpadCfg - 1) - log2Ceil(spadDataWidth / 8) // in bus width bytes
  val axiAddrWidth = log2Ceil(nSpadBanksTotal * (1 << lgSizeSpadBank) + lgSizeSpadCfg - 1) // in bus width bytes

  // println("axiAddrWidth", axiAddrWidth)
  val axi4Param = new AXI4BundleParameters(
                      addrBits = axiAddrWidth,
                      dataBits = spadDataWidth,
                      idBits   = idWidth) 
  
  println("lgSizeSpadCfg", lgSizeSpadCfg)
  println("AxiLiteAddrWidth", AxiLiteAddrWidth)
  // require(AxiLiteAddrWidth >= lgSizeSpadCfg - 3)
  val axiliteParam = new AXI4BundleParameters(
                      addrBits = AxiLiteAddrWidth,
                      dataBits = AxiLiteDataWidth,
                      idBits   = 1/* No id in axi lite*/) 

  val io = IO( new Bundle{
    // AXI4 Interface
    val s_axi = Flipped(new AXI4Bundle(axi4Param))

    // AXI4 Interface
    val s_axilite = Flipped(new AXILiteBundle(axiliteParam))
  })

  val spad = Module(new AXI4Scratchpad(
    idWidth       = idWidth,
    baseAddr      = 0,
    spadBanksNum  = nSpadBanksTotal,
    lgSizeSpadBank= lgSizeSpadBank,
    lgSizeLastBlock= lgSizeSpadCfg,
    axiBeatBytes  = spadDataWidth / 8,

    bPortBytes    = cgraDataWidth / 8,
    hasMask       = hasMask
  ))

  val cgra = Module(new AuFORACGRAController(AuFORASpec.attrs))

  io.s_axi          <> spad.io.s_axi
  io.s_axilite      <> cgra.io.s_axilite

  spad.io.aclk      := clock     
  spad.io.aresetn   := !reset.asBool 
  spad.io.srams     <> cgra.io.srams_iob
  spad.io.sram_last <> cgra.io.sram_cfg
  // Broadcast side-band signals
  spad.io.bcast_en        := cgra.io.bcast_en
  spad.io.bcast_bank_mask := cgra.io.bcast_bank_mask
  spad.io.bcast_base_addr := cgra.io.bcast_base_addr
}

// object SplitVerilogGen extends App {
//   (new chisel3.stage.ChiselStage).emitSystemVerilog(
//     new AuFORAWithAXI(),
//     Array(
//       "--split-verilog",
//       "--disable-all-randomization", // 可选
//       "--strip-debug-info"           // 可选
//     )
//   )
// }

import chisel3.stage.ChiselStage

object FirGen extends App {
  (new ChiselStage).emitFirrtl(
    new AuFORAWithAXI(),
    Array("--target-dir", "build_ir")
  )
}

// object SplitVerilogGen extends App {
//   // val chiselArgs =
//   //   Array(
//   //     "--target",
//   //     "systemverilog"
//   //   )
//   // (new chisel3.stage.ChiselStage).execute(
//   //   chiselArgs,
//   //   Seq(
//   //     chisel3.stage.ChiselGeneratorAnnotation(() => new AuFORAWithAXI()),
//   //     firrtl.EmitAllModulesAnnotation(classOf[firrtl.SystemVerilogEmitter])
//   //   ),
//   // )

//   (new chisel3.stage.ChiselStage).emitSystemVerilogFile(
//     new AuFORAWithAXI(),
//     Array("--split-verilog",
//       "--target",
//       "systemverilog",
//       "--disable-all-randomization", 
//       "--strip-debug-info", 
//       "-lower-memories"),
//   )
// }



object VerilogGen extends App {
 (new chisel3.stage.ChiselStage).emitVerilog(new AuFORAWithAXI(), args)
}


import firrtl.stage.RunFirrtlTransformAnnotation
import firrtl.transforms.{DeadCodeElimination, ConstantPropagation}

object VerilogGenFir extends App {
  (new chisel3.stage.ChiselStage).execute(
    Array(
      "-X", "verilog",
      // "--disable-all-randomization",
       "--strip-debug-info"
      // "--remove-unused-modules"
    ),
    Seq(
      chisel3.stage.ChiselGeneratorAnnotation(() => new AuFORAWithAXI()),
      RunFirrtlTransformAnnotation(new DeadCodeElimination),
      RunFirrtlTransformAnnotation(new ConstantPropagation)
    )
  )
}
