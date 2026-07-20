
"""
Copyright (c) 2025 ADORA
All rights reserved.
Automatically generated file for pytest/cocotb based CGRA call function from ADORA.
Generated on: 2026-07-21 02:13:53

"""
from test_runif import DeviceData, DeviceConfig, DeviceStream, DeviceRuntime
from typing import List
from numpy import ndarray
import numpy as np


def safe_slice_1d(arr, flat_offset, result_shape, *args, **kwargs):
    if not hasattr(safe_slice_1d, "cache"):
        safe_slice_1d.cache = {}
        safe_slice_1d.meta = {'R': 3, 'S': 3, 'stride': 1}
    _agu_cache = safe_slice_1d.cache
    _agu_meta = safe_slice_1d.meta
    arr_id = id(arr)

    if arr.ndim == 4 and len(result_shape) == 2:
        dim0, dim1, dim2, dim3 = arr.shape
        if dim2 <= 11 and dim3 <= 11 and dim2 == dim3:
            K_out, C, R, S = arr.shape
            _agu_meta['R'], _agu_meta['S'] = R, S
            if arr_id not in _agu_cache:
                t = torch.tensor(arr.view(np.int16)).view(torch.bfloat16).float()
                unf = t.view(K_out, C * R * S).transpose(0, 1).contiguous()
                _agu_cache[arr_id] = unf.to(torch.bfloat16).view(torch.int16).numpy().view(np.float16)
            unfolded_B = _agu_cache[arr_id]
            K_gemm = C * R * S
            row_start = flat_offset % K_gemm
            col_start = flat_offset // K_gemm
            r_len, c_len = result_shape
            res = np.zeros(result_shape, dtype=arr.dtype)
            valid_r = min(r_len, unfolded_B.shape[0] - row_start)
            valid_c = min(c_len, unfolded_B.shape[1] - col_start)
            res[:valid_r, :valid_c] = unfolded_B[row_start:row_start+valid_r, col_start:col_start+valid_c]
            return res

        elif dim1 > 1 and (result_shape[1] == dim1 or result_shape[1] == 16):
            N_dim, K_out, P, Q = arr.shape
            M_gemm = N_dim * P * Q
            N_gemm = K_out
            if arr_id not in _agu_cache:
                t = torch.tensor(arr.view(np.int16)).view(torch.bfloat16).float()
                t_reshaped = t.permute(0, 2, 3, 1).reshape(M_gemm, N_gemm).contiguous()
                _agu_cache[arr_id] = t_reshaped.to(torch.bfloat16).view(torch.int16).numpy().view(np.float16)
            unfolded_C = _agu_cache[arr_id]
            k_out = (flat_offset // (P * Q)) % K_out
            q = flat_offset % Q
            p = (flat_offset // Q) % P
            n_dim = flat_offset // (K_out * P * Q)
            m_start = n_dim * P * Q + p * Q + q
            n_start = k_out
            m_len, n_len = result_shape
            res = np.zeros(result_shape, dtype=arr.dtype)
            valid_m = min(m_len, M_gemm - m_start)
            valid_n = min(n_len, N_gemm - n_start)
            res[:valid_m, :valid_n] = unfolded_C[m_start:m_start+valid_m, n_start:n_start+valid_n]
            return res

        else:
            N, C, H, W = arr.shape
            R, S = _agu_meta['R'], _agu_meta['S']
            stride = _agu_meta.get('stride', 1)
            P = (H - R) // stride + 1
            Q = (W - S) // stride + 1
            M_gemm = N * P * Q
            K_gemm = C * R * S
            if arr_id not in _agu_cache:
                t = torch.tensor(arr.view(np.int16)).view(torch.bfloat16).float()
                unf = F.unfold(t, kernel_size=(R, S), padding=0, stride=stride)
                unf = unf.transpose(1, 2).reshape(M_gemm, K_gemm).contiguous()
                _agu_cache[arr_id] = unf.to(torch.bfloat16).view(torch.int16).numpy().view(np.float16)
            unfolded_A = _agu_cache[arr_id]
            matches = []
            for m in range(M_gemm):
                for k in range(K_gemm):
                    n = m // (P * Q)
                    p = (m % (P * Q)) // Q
                    q = m % Q
                    c = k // (R * S)
                    r = (k % (R * S)) // S
                    s = k % S
                    h_in = p * stride + r
                    w_in = q * stride + s
                    if 0 <= h_in < H and 0 <= w_in < W:
                        offset = n * (C * H * W) + c * (H * W) + h_in * W + w_in
                        if offset == flat_offset:
                            matches.append((m, k))
            m_start, k_start = matches[0] if matches else (0, 0)
            for (m, k) in matches:
                if k % result_shape[1] == 0:
                    m_start, k_start = m, k
                    break
            m_len, k_len = result_shape
            res = np.zeros(result_shape, dtype=arr.dtype)
            valid_m = min(m_len, M_gemm - m_start)
            valid_k = min(k_len, K_gemm - k_start)
            if valid_m > 0 and valid_k > 0:
                res[:valid_m, :valid_k] = unfolded_A[m_start:m_start+valid_m, k_start:k_start+valid_k]
            return res

    size = arr.size
    length = int(np.prod(result_shape))
    if flat_offset >= size: return np.zeros(result_shape, dtype=arr.dtype)
    valid_len = min(length, size - flat_offset)
    res = np.zeros(length, dtype=arr.dtype)
    res[:valid_len] = arr.flat[flat_offset : flat_offset + valid_len]
    return res.reshape(result_shape)

def apply_writeback_tasks(tasks):
    for arr, offsets, data_block in tasks:
        flat_offset = 0
        stride = 1
        for idx in range(len(offsets)-1, -1, -1):
            flat_offset += offsets[idx] * stride
            stride *= arr.shape[idx]

        # 使用 uint8 进行纯物理比特位的非零统计
        non_zeros = np.count_nonzero(data_block.view(np.uint8))
        print(f"[DEBUG 探针] 写回拼装: 物理偏移 {flat_offset} | 提取到有效非零字节: {non_zeros}/{data_block.nbytes}")

        # 如果是直接卷积的 3D data_block (比如 4x9x4)，直接走下面的 else 物理空间展平写回！
        if arr.ndim == 4 and data_block.ndim == 2:
            N_dim, K_out, P, Q = arr.shape
            m_len, n_len = data_block.shape
            k_out_start = (flat_offset // (P * Q)) % K_out
            q_start = flat_offset % Q
            p_start = (flat_offset // Q) % P
            n_start = flat_offset // (K_out * P * Q)
            m_start = n_start * P * Q + p_start * Q + q_start

            for m in range(m_len):
                curr_m = m_start + m
                if curr_m >= N_dim * P * Q: break
                n_idx = curr_m // (P * Q)
                p_idx = (curr_m % (P * Q)) // Q
                q_idx = curr_m % Q
                valid_n = min(n_len, K_out - k_out_start)
                arr[n_idx, k_out_start:k_out_start+valid_n, p_idx, q_idx] = data_block[m, :valid_n]
        else:
            flat_data = data_block.ravel()
            valid_len = min(flat_data.size, arr.size - flat_offset)
            if valid_len > 0:
                arr.flat[flat_offset : flat_offset + valid_len] = flat_data[:valid_len]

async def aux_stream(
    stream: DeviceStream, config: List[DeviceConfig], 
    iptrs: List[DeviceData], idata: List, 
    optrs: List[DeviceData], odata: List, olen: List):
    """
    Execute a device stream workflow.

    Parameters
    ----------
    stream : DeviceStream
        The device stream instance to operate on.
    config : List[DeviceConfig]
        Configuration objects to apply before execution.
    iptrs : List[DeviceData]
        Device pointers for input buffers.
    idata : List
        Host-side input data corresponding to `iptrs`.
    optrs : List[DeviceData]
        Device pointers for output buffers.
    odata : List
        Host-side output data containers corresponding to `optrs`.
    olen : List[int]
        Expected output lengths for each output buffer.
    """
    # ------------------------------
    # 1. Apply stream configuration
    # ------------------------------
    await stream.apply(config)
    await stream.config(config_id=0)
    # ------------------------------
    # 2. Host -> Device transfer
    # ------------------------------
    for i in range(len(iptrs)):
        await stream.memcpyHostToDevice(d_data=iptrs[i], h_data=idata[i], size=len(idata[i]))
    # ------------------------------
    # 3. Execute on device
    # ------------------------------
    await stream.execution_start()
    # await stream.execution_finish()
    # ------------------------------
    # 4. Device → Host transfer
    # ------------------------------
    for i in range(len(optrs)):
        await stream.memcpyDeviceToHost(d_data=optrs[i], h_data=odata[i], size=olen[i])

    await stream.release()
    return

def DeviceData_Pong(ptr : DeviceData) -> DeviceData:
    new_ptr = DeviceData(ptr.address+ptr.size, ptr.size)
    return new_ptr
  
async def aux_stream_pingpong(
    stream: DeviceStream, 
    # config: List[DeviceConfig], 
    config_id:int,
    iptrs: List[DeviceData], idata: List[ndarray], 
    optrs: List[DeviceData], odata: List, olen: List, 
    pingpong: bool):
    """
    Execute a device stream workflow.

    Parameters
    ----------
    stream : DeviceStream
        The device stream instance to operate on.
    config : List[DeviceConfig]
        Configuration objects to apply before execution.
    iptrs : List[DeviceData]
        Device pointers for input buffers.
    idata : List
        Host-side input data corresponding to `iptrs`.
    optrs : List[DeviceData]
        Device pointers for output buffers.
    odata : List
        Host-side output data containers corresponding to `optrs`.
    olen : List[int]
        Expected output lengths for each output buffer.
    pingpong : bool
        Indicates the pingpong phase(ping-phase or pong-phase)
    """
    # ------------------------------
    # 1. Apply stream configuration
    # ------------------------------     
    await stream.config(config_id=config_id)
    
    # ------------------------------
    # 2. Host -> Device transfer
    #   depend_type:
    #   2 -> depends on the second previous task (no need to wait for store-back)
    #   1 -> depends on the immediately previous task (no need to wait for store-back)
    #   0 -> strictly sequential execution
    # ------------------------------
    for i in range(len(iptrs)):
        if(pingpong == 0):
            await stream.memcpyHostToDevice(d_data=iptrs[i], h_data=idata[i], size=len(idata[i]), depend_type=2)
        else:
            await stream.memcpyHostToDevice(DeviceData_Pong(iptrs[i]), h_data=idata[i], size=len(idata[i]), depend_type=2)

    # ------------------------------
    # 3. Execute on device
    # ------------------------------
    await stream.execution_start()
    # await stream.execution_finish()

    # ------------------------------
    # 4. Device → Host transfer
    # ------------------------------
    for i in range(len(optrs)):
        if(pingpong == 0):
            await stream.memcpyDeviceToHost(d_data=optrs[i], h_data=odata[i], size=olen[i])
        else :
            await stream.memcpyDeviceToHost(DeviceData_Pong(optrs[i]), h_data=odata[i], size=olen[i])
    
    # await stream.synchronize()
    # await stream.release()
    return

async def aux_stream_pingpong_init(
    stream: DeviceStream, config: List[DeviceConfig]
    ):
    """
    Apply stream configuration
    """
    cfg_copy = list(config)
    await stream.apply(cfg_copy)  
    await stream.config(config_id=0)
    
    # await stream.release()
    return

## ===----------------------------------------------------------------------===//
## Configuration Data 
## ===----------------------------------------------------------------------===//
""" kernel: gemm,  cfgNum: 113"""
cfgbit_gemm = [
		0x1040, 0x0040, 0x0008,
		0x0040, 0x4080, 0x0009,
		0x07fe, 0x8001, 0x000a,
		0xfe30, 0x0107, 0x000b,
		0x0000, 0x0000, 0x000c,
		0x8000, 0x0000, 0x000d,
		0x0002, 0x0002, 0x0010,
		0x0040, 0xf200, 0x0011,
		0x07ff, 0x0001, 0x0012,
		0x0002, 0x0100, 0x0013,
		0x0000, 0x0000, 0x0014,
		0x8000, 0x0000, 0x0015,
		0x0200, 0x0000, 0x0020,
		0x0003, 0x0048, 0x0031,
		0x0003, 0x0000, 0x0050,
		0x0003, 0x0010, 0x0051,
		0x0000, 0x0080, 0x00e0,
		0x0001, 0x0002, 0x00e8,
		0x0040, 0xf200, 0x00e9,
		0x07ff, 0x0001, 0x00ea,
		0x0002, 0x0100, 0x00eb,
		0x0000, 0x0000, 0x00ec,
		0x8000, 0x0000, 0x00ed,
		0x1003, 0x0002, 0x00f8,
		0x0040, 0xf200, 0x00f9,
		0x07ff, 0x0001, 0x00fa,
		0x0002, 0x0100, 0x00fb,
		0x0000, 0x0000, 0x00fc,
		0x8000, 0x0000, 0x00fd,
		0x0000, 0x0002, 0x0100,
		0x0040, 0xf200, 0x0101,
		0x07ff, 0x0001, 0x0102,
		0x0002, 0x0100, 0x0103,
		0x0000, 0x0000, 0x0104,
		0x8000, 0x0000, 0x0105,
		0x1000, 0x0000, 0x0110,
		0x0011, 0x0010, 0x0119,
		0x0000, 0x1000, 0x011a,
		0x0000, 0x020a, 0x011b,
		0x0000, 0x0010, 0x011c,
		0x2001, 0x0098, 0x0121,
		0x0000, 0x0000, 0x0128,
		0x0040, 0x0000, 0x0130,
		0x0000, 0x0000, 0x0131,
		0x2001, 0x0060, 0x0139,
		0x0000, 0x0000, 0x0149,
		0x0002, 0x0000, 0x0150,
		0x0003, 0x0000, 0x0169,
		0x0000, 0xc000, 0x0170,
		0x0002, 0x0000, 0x0171,
		0x0000, 0x0000, 0x0190,
		0x0060, 0x0000, 0x0191,
		0x0801, 0x0120, 0x01a1,
		0x0040, 0x0000, 0x01b1,
		0x0803, 0x0118, 0x01c1,
		0x0000, 0x0100, 0x01c8,
		0x2020, 0x0000, 0x01d0,
		0x1000, 0x0000, 0x01d8,
		0x0040, 0x0080, 0x01d9,
		0x0000, 0x8001, 0x01da,
		0x0000, 0x0100, 0x01db,
		0x0000, 0x0000, 0x01dc,
		0x8000, 0x0278, 0x01dd,
		0x0008, 0x0000, 0x01de,
		0x0000, 0x0040, 0x01e0,
		0x0040, 0x4080, 0x01e1,
		0x07fe, 0x8001, 0x01e2,
		0xfe30, 0x0107, 0x01e3,
		0x0000, 0x0000, 0x01e4,
		0x8000, 0x0000, 0x01e5,
		0x1000, 0x0000, 0x01e8,
		0x0040, 0x0000, 0x01e9,
		0x0000, 0x0001, 0x01ea,
		0x0000, 0x0100, 0x01eb,
		0x0000, 0x0000, 0x01ec,
		0x8000, 0x0260, 0x01ed,
		0x0000, 0x0000, 0x01ee,
		0x0060, 0x0040, 0x01f0,
		0x0040, 0x4080, 0x01f1,
		0x07fe, 0x8001, 0x01f2,
		0xfe30, 0x0107, 0x01f3,
		0x0000, 0x0000, 0x01f4,
		0x8000, 0x0000, 0x01f5,
		0x4130, 0x0000, 0x01f8,
		0x0000, 0x0000, 0x0200,
		0x0803, 0x0088, 0x0209,
		0x0000, 0x1000, 0x0218,
		0x0100, 0x0000, 0x0219,
		0x0100, 0x0000, 0x0239,
		0x1000, 0x0000, 0x0258,
		0x0100, 0x0000, 0x0259,
		0x4801, 0x0108, 0x0269,
		0x0000, 0x0000, 0x0278,
		0x0100, 0x0000, 0x0279,
		0x000c, 0x0000, 0x0280,
		0x2004, 0x0000, 0x0298,
		0x0000, 0x0000, 0x02a0,
		0x1003, 0x00c8, 0x02a9,
		0x0002, 0x0000, 0x02b0,
		0x0003, 0x0100, 0x02b1,
		0x0000, 0x0000, 0x02b8,
		0x0020, 0x0040, 0x02c8,
		0x0040, 0x4080, 0x02c9,
		0x07fe, 0x8001, 0x02ca,
		0xfe30, 0x0107, 0x02cb,
		0x0000, 0x0000, 0x02cc,
		0x8000, 0x0000, 0x02cd,
		0x1000, 0x0000, 0x02d0,
		0x0040, 0x0080, 0x02d1,
		0x0000, 0x8001, 0x02d2,
		0x0000, 0x0100, 0x02d3,
		0x0000, 0x0000, 0x02d4,
		0x8000, 0x0000, 0x02d5,
	]


async def gemm(runtime: DeviceRuntime, arg_0: ndarray, arg_1: ndarray, arg_2: ndarray):
    # runtime.log.info("[ADORA] Starting CGRA call (gemm)")
    iptrs, idata = [],[]
    optrs, odata, olen = [],[],[]
    configs, data_ptr = [],[]
    writeback_tasks = []
    stream = runtime.create_stream()
    int32_t_3= np.zeros(1, dtype=np.int32)
    
    ## %1 = ADORA.BlockLoad %arg0 [0, 0] : memref<?x32xi32> -> memref<32x32xi32>  {Id = "0", KernelName = "gemm"}
    idata.append(arg_0[0:0+32,0:0+32])
    iptrs.append(DeviceData(0x10000, 4096))

    idata.append(arg_0[0:0+32,0:0+32])
    iptrs.append(DeviceData(0x8000, 4096))

    idata.append(arg_0[0:0+32,0:0+32])
    iptrs.append(DeviceData(0x0, 4096))

    idata.append(arg_0[0:0+32,0:0+32])
    iptrs.append(DeviceData(0x14000, 4096))

    
    ## %2 = ADORA.BlockLoad %arg1 [0, 0] : memref<?x32xi32> -> memref<32x32xi32>  {Id = "1", KernelName = "gemm"}
    idata.append(arg_1[0:0+32,0:0+32])
    iptrs.append(DeviceData(0x18000, 4096))

    idata.append(arg_1[0:0+32,0:0+32])
    iptrs.append(DeviceData(0x28000, 4096))

    idata.append(arg_1[0:0+32,0:0+32])
    iptrs.append(DeviceData(0x4000, 4096))

    idata.append(arg_1[0:0+32,0:0+32])
    iptrs.append(DeviceData(0x20000, 4096))

    
    ## %3 = ADORA.BlockLoad %arg2 [0, 0] : memref<?x32xi32> -> memref<32x32xi32>  {Id = "2", KernelName = "gemm"}
    idata.append(arg_2[0:0+32,0:0+32])
    iptrs.append(DeviceData(0x2c000, 4096))

    
    ## %4 = ADORA.LocalMemAlloc memref<2xi32>  {Id = "3", KernelName = "gemm"}
    data_ptr.append(DeviceData(0x24000, 8))
    
    ## %5 = ADORA.LocalMemAlloc memref<32x32xi32>  {Id = "4", KernelName = "gemm"}
    data_ptr.append(DeviceData(0x1c000, 4096))
    
    ### gemm
    data_ptr.append(iptrs)
    config_gemm= DeviceConfig(
    	config_values=cfgbit_gemm,
    	iob_en=[0xf7,0x0f],
    	tile_en=[0x07],
    	data_ptr=data_ptr
    )
    configs.append(config_gemm)
    

    
    ## ADORA.BlockStore %5, %arg2 [0, 0] : memref<32x32xi32> -> memref<?x32xi32>  {Id = "4", KernelName = "gemm"}
    odata.append(arg_2[0:0+32,0:0+32])
    optrs.append(DeviceData(0x1c000, 4096))
    olen.append(4096)

    
    ## ADORA.BlockStore %4, %alloca [] : memref<2xi32> -> memref<i32>  {Id = "3", KernelName = "gemm"}
    odata.append(int32_t_3)
    optrs.append(DeviceData(0x24000, 4))
    olen.append(4)
    await aux_stream(
    	stream=stream, config=configs,
    	iptrs=iptrs, idata=idata,
    	optrs=optrs, odata=odata, olen =olen,
    )

    configs.clear()
    iptrs.clear(), idata.clear()
    optrs.clear(), odata.clear(), olen.clear()

    await stream.synchronize()
    try:
        apply_writeback_tasks(writeback_tasks)
    except NameError:
        pass
