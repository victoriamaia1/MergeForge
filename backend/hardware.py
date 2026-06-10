"""Hardware detection and tier classification."""
import os, shutil, subprocess, psutil, cpuinfo

def detect_gpu():
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=4)
        if out.returncode == 0 and out.stdout.strip():
            gpus = []
            for line in out.stdout.strip().split("\n"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) == 2:
                    gpus.append({"name": parts[0], "vram_mb": int(parts[1])})
            return {"available": True, "type": "NVIDIA", "count": len(gpus),
                    "gpus": gpus, "vram_total_mb": sum(g["vram_mb"] for g in gpus)}
    except Exception:
        pass
    return {"available": False, "type": None, "count": 0, "gpus": [], "vram_total_mb": 0}

def classify_tier(ram_mb, vram_mb, gpu_count):
    if gpu_count >= 4 and vram_mb >= 200000 and ram_mb >= 400000:
        return ("TIER_4", "Ultra-Scale (Multi-A100)")
    if gpu_count >= 1 and vram_mb >= 40000 and ram_mb >= 128000:
        return ("TIER_3", "High-End GPU")
    if gpu_count >= 1 and vram_mb >= 8000:
        return ("TIER_2", "Modest GPU")
    return ("TIER_1", "CPU-Only")

def detect_hardware():
    gpu = detect_gpu()
    vm = psutil.virtual_memory()
    disk = shutil.disk_usage("/")
    try:
        info = cpuinfo.get_cpu_info()
        cpu_brand = info.get("brand_raw", "Unknown CPU")
        cpu_flags = info.get("flags", [])
    except Exception:
        cpu_brand, cpu_flags = "Unknown CPU", []
    cores_logical = psutil.cpu_count(logical=True) or 1
    cores_physical = psutil.cpu_count(logical=False) or cores_logical
    try:
        freq = psutil.cpu_freq()
        cpu_freq_mhz = int(freq.max or freq.current or 0) if freq else 0
    except Exception:
        cpu_freq_mhz = 0
    ram_mb = vm.total // (1024*1024)
    ram_avail_mb = vm.available // (1024*1024)
    tier, tier_label = classify_tier(ram_mb, gpu["vram_total_mb"], gpu["count"])

    # Capabilities derived from tier
    caps = {
        "TIER_1": {"max_params_b": 13, "max_concurrent_models": 2, "compression_required": True,
                   "merge_time_multiplier": 14.0, "supports_batch": False, "supports_no_compression": False,
                   "supports_moe_merge": False, "supports_parallel_gpu": False},
        "TIER_2": {"max_params_b": 30, "max_concurrent_models": 3, "compression_required": False,
                   "merge_time_multiplier": 2.5, "supports_batch": True, "supports_no_compression": True,
                   "supports_moe_merge": False, "supports_parallel_gpu": False},
        "TIER_3": {"max_params_b": 70, "max_concurrent_models": 4, "compression_required": False,
                   "merge_time_multiplier": 1.0, "supports_batch": True, "supports_no_compression": True,
                   "supports_moe_merge": False, "supports_parallel_gpu": True},
        "TIER_4": {"max_params_b": 405, "max_concurrent_models": 8, "compression_required": False,
                   "merge_time_multiplier": 0.4, "supports_batch": True, "supports_no_compression": True,
                   "supports_moe_merge": True, "supports_parallel_gpu": True},
    }[tier]

    return {
        "gpu": gpu,
        "cpu": {"brand": cpu_brand, "cores_physical": cores_physical, "cores_logical": cores_logical,
                "freq_mhz": cpu_freq_mhz, "has_avx": "avx" in cpu_flags, "has_avx512": any(f.startswith("avx512") for f in cpu_flags)},
        "ram": {"total_mb": ram_mb, "available_mb": ram_avail_mb,
                "used_pct": vm.percent},
        "storage": {"total_mb": disk.total // (1024*1024), "free_mb": disk.free // (1024*1024)},
        "tier": tier, "tier_label": tier_label,
        "capabilities": caps,
    }

def live_metrics():
    vm = psutil.virtual_memory()
    disk = shutil.disk_usage("/")
    cpu_pct = psutil.cpu_percent(interval=0.1)
    gpu = detect_gpu()
    return {
        "cpu_pct": cpu_pct,
        "ram_used_pct": vm.percent,
        "ram_available_mb": vm.available // (1024*1024),
        "ram_total_mb": vm.total // (1024*1024),
        "disk_free_mb": disk.free // (1024*1024),
        "gpu": gpu,
    }
