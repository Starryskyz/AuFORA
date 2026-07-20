# AuFORA: A Unified Full-Stack Framework for CGRA with Agile Deployment and Fast Verification

To be updated

## Hardware: AXI Plugin CGRA

env script

```
conda create -n aufora python=3.12
conda activate aufora
conda install -c conda-forge openjdk=8 --no-update-deps
conda install sbt --no-update-deps
pip install "cocotb~=1.9.2"
pip install cocotbext-axi
pip install numpy
```

run script

```
cd AuFORA-CGRA
bash ./aufora.sh  
```

get
- `verilog/AuFORAWithAXI.v`
- `verilog/aufora-spec/axilite_spec.json`
- `verilog/aufora-spec/aufora_spec.json`
- `verilog/aufora-spec/aufora_cgra_adg.json`
- `verilog/aufora-spec/operations.json`

## MLIR-based Compiler

To be updated

## Cocotb Verification

run script

```
export PYTHONPATH=$(pwd)/server:$PYTHONPATH
export PYTHONPATH=$(pwd)/workspace:$PYTHONPATH
make [-j8]
```
