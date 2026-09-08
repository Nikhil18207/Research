"""GPU temperature/clock sampling — thermal confound control for all RQs.

Laptop GPUs throttle under sustained load; this is a real confound for RQ1's
"is the latency gap caused by residency, not heat" claim, not a formality.
"""
import pynvml


class GPUMonitor:
    def __init__(self, device_index=0):
        pynvml.nvmlInit()
        self.handle = pynvml.nvmlDeviceGetHandleByIndex(device_index)

    def sample(self):
        temp = pynvml.nvmlDeviceGetTemperature(self.handle, pynvml.NVML_TEMPERATURE_GPU)
        clock_sm = pynvml.nvmlDeviceGetClockInfo(self.handle, pynvml.NVML_CLOCK_SM)
        clock_mem = pynvml.nvmlDeviceGetClockInfo(self.handle, pynvml.NVML_CLOCK_MEM)
        util = pynvml.nvmlDeviceGetUtilizationRates(self.handle)
        mem = pynvml.nvmlDeviceGetMemoryInfo(self.handle)
        power = pynvml.nvmlDeviceGetPowerUsage(self.handle) / 1000.0  # mW -> W
        return {
            "gpu_temp_c": temp,
            "clock_sm_mhz": clock_sm,
            "clock_mem_mhz": clock_mem,
            "gpu_util_pct": util.gpu,
            "mem_util_pct": util.memory,
            "mem_used_mib": mem.used / (1024 * 1024),
            "power_w": power,
        }

    def close(self):
        pynvml.nvmlShutdown()
