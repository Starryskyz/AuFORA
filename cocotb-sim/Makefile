COCOTB_RESOLVE_X ?= ZEROS
export COCOTB_RESOLVE_X
TOPLEVEL_LANG = verilog

# SIM ?= icarus
SIM ?= verilator

WAVES ?= 0

COCOTB_HDL_TIMEUNIT = 1ns
COCOTB_HDL_TIMEPRECISION = 1ns

DUT      = test_cgra
CGRA     = AuFORAWithAXI
TOPLEVEL = $(DUT)
SERVER   = cgra_server

MODULE   = $(DUT)
# MODULE = $(SERVER)

VERILOG_SOURCES += $(PWD)/circuits/$(DUT).v $(PWD)/circuits/$(CGRA).v
# VERILOG_SOURCES += $(DUT).v $(CGRA).v


# axi4 module parameters
export PARAM_DATA_WIDTH := 128
export PARAM_ADDR_WIDTH := 19
#18
export PARAM_STRB_WIDTH := $(shell expr $(PARAM_DATA_WIDTH) / 8 )
export PARAM_ID_WIDTH := 6

export PARAM_AWUSER_WIDTH := 1
export PARAM_WUSER_WIDTH := 1
export PARAM_BUSER_WIDTH := 1
export PARAM_ARUSER_WIDTH := 1
export PARAM_RUSER_WIDTH := 1

#axil parameters
export PARAM_AXIL_DATA_WIDTH := 32
export PARAM_AXIL_ADDR_WIDTH := 10
export PARAM_AXIL_STRB_WIDTH := $(shell expr $(PARAM_AXIL_DATA_WIDTH) / 8 )

ifeq ($(SIM), icarus)
	PLUSARGS += -fst

	COMPILE_ARGS += $(foreach v,$(filter PARAM_%,$(.VARIABLES)),-P $(TOPLEVEL).$(subst PARAM_,,$(v))=$($(v)))

	ifeq ($(WAVES), 1)
		VERILOG_SOURCES += vcd_dump.v
		COMPILE_ARGS += -s vcd_dump
	endif

else ifeq ($(SIM), verilator)
	COMPILE_ARGS += -Wno-SELRANGE -Wno-WIDTH -Wno-CASEINCOMPLETE

	COMPILE_ARGS += $(foreach v,$(filter PARAM_%,$(.VARIABLES)),-G$(subst PARAM_,,$(v))=$($(v)))

	COMPILE_ARGS += --threads 16
	COMPILE_ARGS += --build-jobs 16

	ifeq ($(WAVES), 1)
		COMPILE_ARGS += --trace-fst
	endif
endif

include $(shell cocotb-config --makefiles)/Makefile.sim

clean::
	@rm -rf sim_build