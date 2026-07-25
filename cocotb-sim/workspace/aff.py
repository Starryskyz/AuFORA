"""
Automatically generated pytest/cocotb helper for a mixed-grained DFG JSON mapping.
"""
from test_runif import DeviceConfig, DeviceData, DeviceRuntime
import numpy as np

cfgbit_aff = [
    0x8000, 0x0000, 0x0008,
    0x00a0, 0x0000, 0x0009,
    0x0000, 0x0000, 0x000a,
    0x0000, 0x0000, 0x000b,
    0x0000, 0x0000, 0x000c,
    0x8000, 0x9a28, 0x000d,
    0x0001, 0x0000, 0x000e,
    0x3000, 0x0000, 0x000f,
    0x9000, 0x0000, 0x0010,
    0x00a0, 0x0000, 0x0011,
    0x0000, 0x0000, 0x0012,
    0x0000, 0x0000, 0x0013,
    0x0000, 0x0000, 0x0014,
    0x8000, 0x1a30, 0x0015,
    0x0002, 0x0000, 0x0016,
    0x2000, 0x0000, 0x0017,
    0x0200, 0x0000, 0x0038,
    0x0000, 0x0800, 0x0040,
    0xd000, 0x0081, 0x004d,
    0x0005, 0x0000, 0x0050,
    0x000e, 0x0180, 0x0051,
    0x0000, 0x0000, 0x0055,
    0x0000, 0x0000, 0x0058,
    0x8100, 0x0000, 0x0060,
    0x0001, 0x0000, 0x0068,
    0x0021, 0x0000, 0x0069,
    0x0000, 0x2000, 0x006a,
    0x0000, 0x0a00, 0x006b,
    0x0800, 0x8000, 0x006c,
    0x0000, 0x0000, 0x006d,
    0x000a, 0x0000, 0x0070,
    0x000e, 0x0080, 0x0071,
    0x0000, 0x0000, 0x0075,
    0x2030, 0x0021, 0x0095,
    0x8000, 0x0000, 0x00f0,
    0x00a0, 0x0000, 0x00f1,
    0x0000, 0x0000, 0x00f2,
    0x0000, 0x0000, 0x00f3,
    0x0000, 0x0000, 0x00f4,
    0x8000, 0x9a48, 0x00f5,
    0x0000, 0x0000, 0x00f6,
    0x2000, 0x0000, 0x00f7,
    0x001d, 0x0400, 0x0318,
    0x0000, 0x0006, 0x0360,
    0x0000, 0x0010, 0x0379,
    0x0000, 0x0030, 0x0391,
    0x0a00, 0x0000, 0x03a8,
    0x0000, 0x0000, 0x0328,
    0x0000, 0x0400, 0x0330,
    0x0400, 0x0030, 0x0331,
    0x0000, 0x0000, 0x0338,
    0x0000, 0x0000, 0x0348,
    0x0000, 0x0030, 0x0349,
]

IO_METADATA = [
    {'tag': 'output_0', 'node': '$n2', 'ref_name': 'c', 'operation': 'COUTPUT', 'direction': 'output', 'iob_index': 0, 'address': 0x0, 'size_bytes': 80},
    {'tag': 'output_1', 'node': '$n4', 'ref_name': 'c', 'operation': 'COUTPUT', 'direction': 'output', 'iob_index': 1, 'address': 0x4000, 'size_bytes': 80},
    {'tag': 'output_2', 'node': '$n5', 'ref_name': 'c', 'operation': 'COUTPUT', 'direction': 'output', 'iob_index': 3, 'address': 0x8000, 'size_bytes': 80},
]

async def run_aff(runtime: DeviceRuntime, inputs=None):
    """Configure and run the mapped DFG; return output arrays by tag."""
    inputs = {} if inputs is None else inputs
    iptrs, idata = [], []
    optrs, outputs = [], {}
    all_ptrs = []
    for meta in IO_METADATA:
        ptr = DeviceData(meta['address'], meta['size_bytes'])
        all_ptrs.append(ptr)
        words = (meta['size_bytes'] + 3) // 4
        if meta['direction'] == 'input':
            value = inputs.get(meta['tag'], inputs.get(meta['ref_name']))
            if value is None:
                value = np.zeros(words, dtype=np.uint32)
            value = np.ascontiguousarray(value, dtype=np.uint32)
            if value.nbytes > meta['size_bytes']:
                raise ValueError(f"{meta['tag']} exceeds its mapped SPAD buffer")
            iptrs.append(ptr)
            idata.append(value)
        else:
            value = np.zeros(words, dtype=np.uint32)
            optrs.append(ptr)
            outputs[meta['tag']] = value

    config = DeviceConfig(
        config_values=cfgbit_aff,
        iob_en=[0x0b, 0x00],
        tile_en=[0x01],
        data_ptr=all_ptrs,
    )
    stream = runtime.create_stream()
    await stream.apply([config])
    await stream.config(config_id=0)
    for ptr, value in zip(iptrs, idata):
        await stream.memcpyHostToDevice(
            d_data=ptr, h_data=value, size=value.size, dtype='i')
    # Predicate-false COUTPUT locations are untouched by hardware.
    # Clear each output bank so multiport results can be merged safely.
    for ptr, value in zip(optrs, outputs.values()):
        await stream.memcpyHostToDevice(
            d_data=ptr, h_data=value, size=value.size, dtype='i')
    await stream.execution_start()
    for ptr, value in zip(optrs, outputs.values()):
        await stream.memcpyDeviceToHost(
            d_data=ptr, h_data=value, size=value.nbytes)
    await stream.synchronize()
    return outputs


async def aff(runtime: DeviceRuntime, c: np.ndarray):
    """GEMM-style entry point using arrays named by JSON ref_name."""
    input_values = {
    }
    raw_outputs = await run_aff(runtime, inputs=input_values)
    output_targets = {
        'c': c,
    }
    for ref_name, target_value in output_targets.items():
        target = np.asarray(target_value).reshape(-1)
        target.fill(0)
        for meta in IO_METADATA:
            if (meta['direction'] != 'output' or
                    meta['ref_name'] != ref_name):
                continue
            source = raw_outputs[meta['tag']].reshape(-1)
            count = min(target.size, source.size)
            active = source[:count] != 0
            target[:count][active] = source[:count][active]
