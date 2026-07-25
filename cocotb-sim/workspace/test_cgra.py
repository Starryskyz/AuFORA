"""
Copyright (c) 2025 CGRA
All rights reserved.

This module contains a cocotb testbench for running a CGRA kernel with pytest

"""

###########
## Import from cocotb
###########
import os
import logging
import numpy as np
import itertools
import logging
import random

import cocotb

# from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from cocotb.regression import TestFactory
from cocotb.utils import get_sim_time

# from cocotbext.axi import AxiBus, AxiMaster, AxiLiteBus, AxiLiteMaster, AxiRam

## set path for  cgra_test_pylib
from test_runif import (
    DeviceInfo,
    DeviceData,
    DeviceConfig,
    DeviceStream,
    DeviceRuntime,
    Axi4LiteTb,
)
import test_runif

## ================================
## Import from kernel function py
## ================================
# @zwzhong
# from IntVecAdd import IntVecAdd
from gemm import gemm
# from fir import fir
from aff import aff


tests_dir = os.path.dirname(__file__)


# ==============================
# Main cocotb coroutine
# ==============================
# def random_init_i16(shape, low=0, high=30):
#     return np.random.randint(low, high + 1, size=shape, dtype=np.int16)


# def zero_init_i16(shape):
#     return np.zeros(shape, dtype=np.int16)


def ri32(shape, low=0, high=1000):
    return np.random.randint(low, high + 1, size=shape, dtype=np.int32)


def zi32(shape):
    return np.zeros(shape, dtype=np.int32)

# ==============================
# Main cocotb coroutine
# ==============================
async def cgra_run_top_intvecadd(dut) -> None:
    """
    Run a CGRA kernel test.

    Args:
        dut: cocotb DUT object (Design Under Test).
    """
    # Reset DUT
    axibus = Axi4LiteTb(dut)
    await axibus.cycle_reset()
    axibus.log.info("[CGRA] Starting CGRA kernel test (intvecadd)")

    # set log level
    # axibus.log.setLevel(logging.WARNING)
    logging.getLogger("cocotb.test_cgra.axi").disabled = True
    logging.getLogger("cocotb.test_cgra.axil").disabled = True
    # logging.getLogger("test_runif").setLevel(logging.DEBUG)

    # Prepare test data
    x=ri32((32,32))
    y=ri32((32,32))
    o=zi32((32,32))
    oc=zi32((32,32))
    for i in range(0,32):
        for j in range(0,32):
            sum = 0 
            for k in range(0,32):
                sum += x[i][k]*y[k][j]
            o[i][j] = 3 *sum+2*o[i][j]

    # c1 = zi32(20)
    # c2 = zi32(20)
    # for i in range(0,20):
    #     if i>10:
    #         c1[i] = 6
    #     elif i>5:
    #         c1[i] = 8
    #     else:
    #         c1[i] = 2



    base_dir = os.path.dirname(os.path.abspath(__file__))
    reg_json_path = os.path.join(base_dir, "../circuits/axilite_spec.json")
    adg_json_path = os.path.join(base_dir, "../circuits/aufora_cgra_adg.json")
    device1 = test_runif.create_device_info_factory(
        reg_json_path=reg_json_path, adg_json_path=adg_json_path
    )

    runtime = DeviceRuntime(
        dut=dut,
        axi=axibus.axi,
        axil=axibus.axil,
        axi_size=axibus.axi.write_if.max_burst_size,
    )

    runtime.add_device(device1)

    # Start kernel execution
    start_time = get_sim_time(units="ns")
    # await IntVecAdd(runtime, a, b, c)
    await gemm(runtime, x, y, oc)
    # await aff(runtime, c2)

    await runtime.synchronize_all()
    await RisingEdge(dut.clk)

    # np.testing.assert_array_equal(
    #     c2,
    #     c1,
    #     err_msg=f"AFF result mismatch\nhardware: {c2}\nreference: {c1}",
    # )
    # axibus.log.info(f"AFF result check passed: {c2}")

    end_time = get_sim_time(units="ns")
    axibus.log.info(f"Sim time: {end_time - start_time} ns")

    for i in range(0,32):
        for j in range(0,32):
            if oc[i][j] != o[i][j]:
                print(f"Mismatch at ({i}, {j}): {oc[i][j]} != {o[i][j]}")
 #prin

# ==============================
# TestFactory registration
# ==============================
if cocotb.SIM_NAME:
    cgra_run_top = cgra_run_top_intvecadd
    factory = TestFactory(cgra_run_top)
    factory.generate_tests()

# if __name__ == "__main__":
#     cgra_run_top
