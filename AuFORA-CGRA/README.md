# AuFORA

AuFORA 是一个独立的 Chisel CGRA 工程，顶层提供 AXI4 scratchpad 数据接口和 AXI-Lite 控制接口。

## 环境

- JDK 8 或更新版本
- sbt 1.8.2
- 首次构建需能够解析 Maven 依赖

## 生成 RTL

Linux、macOS 或 Git Bash：

```sh
./aufora.sh
```

Windows PowerShell：

```powershell
.\aufora.ps1
```

也可以直接运行：

```sh
sbt "runMain aufora.VerilogGen -td ./verilog"
```

主要输出：

- `verilog/AuFORAWithAXI.v`
- `verilog/AuFORAWithAXI.fir`
- `verilog/AuFORAWithAXI.anno.json`
- `verilog/aufora-spec/*.json`

