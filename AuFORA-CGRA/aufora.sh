#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"
mkdir -p ./verilog/aufora-spec
export AUFORA_OUTPUT_DIR=./verilog
sbt -mem 4096 "runMain aufora.VerilogGen -td ./verilog"

sed 's/\/\/[[:space:]]*@.*$//' ./verilog/AuFORAWithAXI.v > ./verilog/clean.v