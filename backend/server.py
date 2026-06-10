"""MergeForge backend - FastAPI app."""
import os, sys, asyncio, secrets, uuid, json, time, shutil, threading, subprocess, math, re
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient

import hardware, catalog

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
WORKSPACE_DIR = Path(os.environ["WORKSPACE_DIR"])
HF_CACHE_DIR = Path(os.environ["HF_CACHE_DIR"])
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
HF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
MERGES_DIR = WORKSPACE_DIR / "merges"
MERGES_DIR.mkdir(parents=True, exist_ok=True)

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Admin secret for tier mgmt
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "mergeforge-admin-secret-change-me")

# Tier daily merge limits
TIER_LIMITS = {"free": 3, "pro": 20, "enterprise": -1}  # -1 = unlimited

# llama.cpp dir (cloned on first use)
LLAMA_CPP_DIR = Path("/home/ubuntu/llm_fusion_studio/llama.cpp")

# Cache hardware profile once at startup
HW_PROFILE: Dict[str, Any] = {}

# ---- Word list for 30-word token generation ----
WORDLIST = (
    "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda sigma omega "
    "river forest mountain ocean desert valley canyon glacier volcano meadow "
    "phoenix dragon raven falcon tiger panther wolf otter falcon lynx "
    "ember frost spark cinder breeze quartz onyx amber jade ruby "
    "echo nova orbit comet aurora nebula pulsar quasar zenith eclipse "
    "ironclad copper bronze silver gold platinum titanium crystal marble obsidian "
    "thunder lightning storm rainbow horizon sunrise sunset twilight midnight dawn "
    "mystic ancient sacred hidden silent swift bold brave fierce calm "
    "compass anchor lantern beacon prism mirror feather arrow shield torch "
    "harbor summit gulf isle cove peak ridge cliff dune steppe"
).split()

def generate_token() -> str:
    """Generate human-friendly 30-word token."""
    return "-".join(secrets.choice(WORDLIST) for _ in range(30))

def now_utc():
    return datetime.now(timezone.utc)

def iso(dt):
    return dt.isoformat() if isinstance(dt, datetime) else dt

# ---- Models ----
class SignupReq(BaseModel):
    username: str = Field(min_length=2, max_length=40)

class SignupResp(BaseModel):
    user_id: str
    username: str
    token: str
    created_at: str

class LoginReq(BaseModel):
    token: str

class CreateMergeReq(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    method: str = Field(default="linear")  # linear, ties, dare_ties, slerp, passthrough
    models: List[Dict[str, Any]]   # [{"id": "...", "weight": 0.5}]
    compression: str = Field(default="auto")  # auto, fp16, int8, int4
    dtype: str = Field(default="float16")
    notes: Optional[str] = None

# ---- Auth dep ----
async def auth_user(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(401, "Missing Authorization header")
    token = authorization.replace("Bearer ", "").strip()
    user = await db.users.find_one({"token": token})
    if not user:
        raise HTTPException(401, "Invalid token")
    return user

# ---- App ----
app = FastAPI(title="MergeForge", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
async def startup():
    global HW_PROFILE
    HW_PROFILE = hardware.detect_hardware()
    await db.users.create_index("token", unique=True)
    await db.users.create_index("username", unique=True)
    await db.jobs.create_index("user_id")
    await db.jobs.create_index("status")
    # Insert/update single hardware doc
    await db.hardware.update_one({"_id": "current"},
                                  {"$set": {**HW_PROFILE, "detected_at": now_utc()}},
                                  upsert=True)
    # Spawn background worker
    asyncio.create_task(merge_worker())
    print(f"[startup] Hardware tier: {HW_PROFILE["tier"]} ({HW_PROFILE["tier_label"]})", flush=True)

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "mergeforge", "time": iso(now_utc())}

# ---- Hardware endpoints ----
@app.get("/api/hardware/profile")
async def get_hw_profile():
    return HW_PROFILE

@app.get("/api/hardware/live")
async def get_hw_live():
    return hardware.live_metrics()

# ---- Model catalog & filtering ----
def evaluate_compat(model: dict, profile: dict) -> dict:
    """Return compatibility dict for a model given the hardware profile."""
    tier = profile["tier"]
    ram_avail_gb = profile["ram"]["available_mb"] / 1024
    ram_total_gb = profile["ram"]["total_mb"] / 1024
    vram_total_gb = profile["gpu"]["vram_total_mb"] / 1024
    caps = profile["capabilities"]

    warnings = []
    blockers = []

    # Tier check
    tier_order = ["TIER_1", "TIER_2", "TIER_3", "TIER_4"]
    if tier_order.index(model["tier_min"]) > tier_order.index(tier):
        blockers.append(f"Requires {model["tier_min"]}, hardware is {tier}")

    # RAM check (use int4 if cpu-only and quantizable)
    cpu_only = not profile["gpu"]["available"]
    needed_ram = model["min_ram_gb_int4"] if (cpu_only and model["quantizable"]) else model["min_ram_gb_fp16"]
    if needed_ram > ram_total_gb:
        blockers.append(f"Needs {needed_ram:.1f}GB RAM, you have {ram_total_gb:.1f}GB total")
    elif needed_ram > ram_avail_gb:
        warnings.append(f"Tight on RAM: needs {needed_ram:.1f}GB, {ram_avail_gb:.1f}GB available")

    # GPU-required models on CPU-only hosts
    if model["gpu_required"] and not profile["gpu"]["available"]:
        blockers.append("Requires GPU (none detected)")

    # Param limit by tier
    if model["params_b"] > caps["max_params_b"]:
        blockers.append(f"Model is {model["params_b"]}B; tier max is {caps["max_params_b"]}B")

    # Merge time estimate (min) for 2-way merge
    base = 5.0  # minutes baseline on TIER_3 for a 7B
    est_min = base * (model["params_b"] / 7.0) * caps["merge_time_multiplier"]
    est_min = max(1.0, est_min)

    return {
        "can_use": len(blockers) == 0,
        "warnings": warnings,
        "blockers": blockers,
        "needed_ram_gb": needed_ram,
        "merge_time_min_estimate": round(est_min, 1),
        "cpu_only_mode": cpu_only,
        "quantization_recommended": cpu_only and model["quantizable"],
    }

@app.get("/api/models")
async def list_models(include_incompatible: bool = True, family: Optional[str] = None, search: Optional[str] = None):
    items = catalog.ALL
    if family:
        items = [m for m in items if m["family"].lower() == family.lower()]
    if search:
        s = search.lower()
        items = [m for m in items if s in m["id"].lower() or s in m["name"].lower() or s in m["family"].lower()]
    result, available, hidden = [], 0, 0
    for m_ in items:
        compat = evaluate_compat(m_, HW_PROFILE)
        if compat["can_use"]:
            available += 1
        else:
            hidden += 1
            if not include_incompatible:
                continue
        result.append({**m_, "compatibility": compat})
    return {
        "total": len(items),
        "available_count": available,
        "incompatible_count": hidden,
        "tier": HW_PROFILE["tier"],
        "tier_label": HW_PROFILE["tier_label"],
        "items": result,
    }

@app.get("/api/models/families")
async def model_families():
    fams = sorted({m["family"] for m in catalog.ALL})
    return {"families": fams}

# ---- Auth ----
@app.post("/api/auth/signup", response_model=SignupResp)
async def signup(req: SignupReq):
    existing = await db.users.find_one({"username": req.username})
    if existing:
        raise HTTPException(400, "Username already taken")
    token = generate_token()
    user_id = str(uuid.uuid4())
    doc = {
        "_id": user_id, "username": req.username, "token": token,
        "tier": "free",
        "created_at": now_utc(), "last_login": now_utc(),
    }
    await db.users.insert_one(doc)
    return SignupResp(user_id=user_id, username=req.username, token=token, created_at=iso(doc["created_at"]))

@app.post("/api/auth/login")
async def login(req: LoginReq):
    token = req.token.strip()
    user = await db.users.find_one({"token": token})
    if not user:
        raise HTTPException(401, "Invalid token")
    await db.users.update_one({"_id": user["_id"]}, {"$set": {"last_login": now_utc()}})
    return {"user_id": user["_id"], "username": user["username"], "token": token, "tier": user.get("tier", "free")}

@app.get("/api/auth/me")
async def me(user=Depends(auth_user)):
    return {"user_id": user["_id"], "username": user["username"],
            "tier": user.get("tier", "free"),
            "created_at": iso(user["created_at"])}

# ---- Usage / tier ----
async def _count_today_merges(user_id: str) -> int:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return await db.jobs.count_documents({"user_id": user_id, "created_at": {"$gte": start}})

@app.get("/api/usage/today")
async def usage_today(user=Depends(auth_user)):
    tier = user.get("tier", "free")
    used = await _count_today_merges(user["_id"])
    limit = TIER_LIMITS.get(tier, 3)
    return {"tier": tier, "used_today": used, "daily_limit": limit,
            "remaining": (limit - used) if limit >= 0 else -1}

# ---- Admin ----
@app.post("/api/admin/tier")
async def admin_set_tier(payload: Dict[str, str],
                        x_admin_secret: Optional[str] = Header(None)):
    if not x_admin_secret or x_admin_secret != ADMIN_SECRET:
        raise HTTPException(401, "Invalid admin secret")
    token = payload.get("token", "").strip()
    tier = payload.get("tier", "").strip()
    if tier not in TIER_LIMITS:
        raise HTTPException(400, f"Invalid tier (must be one of {list(TIER_LIMITS)})")
    res = await db.users.update_one({"token": token}, {"$set": {"tier": tier}})
    if res.matched_count == 0:
        raise HTTPException(404, "User token not found")
    return {"ok": True, "tier": tier}

# ---- Pre-merge validation ----
@app.post("/api/merge/validate")
async def validate_merge(req: CreateMergeReq, user=Depends(auth_user)):
    if len(req.models) < 2:
        raise HTTPException(400, "At least 2 models required")
    if len(req.models) > HW_PROFILE["capabilities"]["max_concurrent_models"]:
        raise HTTPException(400, f"Tier {HW_PROFILE["tier"]} supports max {HW_PROFILE["capabilities"]["max_concurrent_models"]} models per merge")
    id_to_model = {m["id"]: m for m in catalog.ALL}
    blockers, warnings = [], []
    total_size_gb = 0.0
    total_params_b = 0.0
    max_time = 0.0
    selected = []
    for sel in req.models:
        if sel["id"] not in id_to_model:
            blockers.append(f"Unknown model: {sel["id"]}")
            continue
        m_ = id_to_model[sel["id"]]
        compat = evaluate_compat(m_, HW_PROFILE)
        if not compat["can_use"]:
            blockers.extend(compat["blockers"])
        warnings.extend(compat["warnings"])
        size = m_["quantized_size_gb"] if compat["quantization_recommended"] else m_["size_gb_fp16"]
        total_size_gb += size
        total_params_b += m_["params_b"]
        max_time = max(max_time, compat["merge_time_min_estimate"])
        selected.append(m_)
    n = len(selected)
    if n == 0:
        return {
            "status": "IMPOSSIBLE",
            "warnings": warnings,
            "blockers": blockers or ["No valid models selected"],
            "resource_estimate": {"peak_ram_gb": 0, "peak_vram_gb": 0,
                                   "merge_time_min": 0, "output_size_gb": 0,
                                   "download_size_gb": 0},
            "verdict": {"is_possible": False, "headroom_ram_gb": 0},
            "tier": HW_PROFILE["tier"],
        }
    peak_ram_gb = total_size_gb * 2.0  # rough merge overhead 2x
    ram_total_gb = HW_PROFILE["ram"]["total_mb"] / 1024
    if peak_ram_gb > ram_total_gb * 0.85:
        blockers.append(f"Peak RAM needed ~{peak_ram_gb:.0f}GB > 85% of {ram_total_gb:.0f}GB")
    free_gb = HW_PROFILE["storage"]["free_mb"] / 1024
    needed_disk = total_size_gb * 2.5  # cache + output
    if needed_disk > free_gb:
        blockers.append(f"Disk too low: need {needed_disk:.0f}GB, have {free_gb:.0f}GB")
    merge_time_min = max_time * (1 + 0.3 * (n - 2))
    return {
        "status": "OK" if not blockers else "IMPOSSIBLE",
        "warnings": warnings,
        "blockers": blockers,
        "resource_estimate": {
            "peak_ram_gb": round(peak_ram_gb, 1),
            "peak_vram_gb": 0 if not HW_PROFILE["gpu"]["available"] else round(total_size_gb * 1.2, 1),
            "merge_time_min": round(merge_time_min, 1),
            "output_size_gb": round(total_size_gb / n * (0.6 if HW_PROFILE["capabilities"]["compression_required"] else 1.0), 1),
            "download_size_gb": round(total_size_gb, 1),
        },
        "verdict": {
            "is_possible": len(blockers) == 0,
            "headroom_ram_gb": round(ram_total_gb - peak_ram_gb, 1),
        },
        "tier": HW_PROFILE["tier"],
    }

# ---- Merge jobs ----
JOB_QUEUE: asyncio.Queue = asyncio.Queue()
# Track active subprocess PIDs per job_id so we can cancel.
ACTIVE_PROCS: Dict[str, "asyncio.subprocess.Process"] = {}

@app.post("/api/merge/create")
async def create_merge(req: CreateMergeReq, user=Depends(auth_user)):
    # ---- Tier-based daily rate limit ----
    tier = user.get("tier", "free")
    limit = TIER_LIMITS.get(tier, 3)
    if limit >= 0:
        used = await _count_today_merges(user["_id"])
        if used >= limit:
            raise HTTPException(429,
                f"Daily merge limit reached on '{tier}' tier ({used}/{limit}). "
                f"Upgrade to 'pro' for {TIER_LIMITS['pro']}/day or 'enterprise' for unlimited.")
    # Re-validate
    validation = await validate_merge(req, user=user)
    if validation["status"] != "OK":
        return JSONResponse({"error": "Validation failed", "validation": validation}, status_code=400)
    job_id = str(uuid.uuid4())
    job = {
        "_id": job_id, "user_id": user["_id"], "username": user["username"],
        "name": req.name, "method": req.method, "compression": req.compression,
        "dtype": req.dtype, "notes": req.notes,
        "models": req.models, "status": "queued", "progress": 0,
        "stage": "queued", "logs": [],
        "estimated_minutes": validation["resource_estimate"]["merge_time_min"],
        "output_size_gb": validation["resource_estimate"]["output_size_gb"],
        "created_at": now_utc(), "started_at": None, "completed_at": None,
        "output_path": None, "error": None,
        "is_public": False,
        "quality_score": None, "quality_summary": None,
        "gguf_path": None, "gguf_size_mb": None,
    }
    await db.jobs.insert_one(job)
    await JOB_QUEUE.put(job_id)
    return {"job_id": job_id, "status": "queued", "estimated_minutes": job["estimated_minutes"]}

def serialize_job(j):
    j = dict(j)
    j["id"] = j.pop("_id")
    for k in ("created_at", "started_at", "completed_at"):
        if j.get(k): j[k] = iso(j[k])
    return j

@app.get("/api/merge/jobs")
async def list_jobs(user=Depends(auth_user), limit: int = 50):
    cur = db.jobs.find({"user_id": user["_id"]}).sort("created_at", -1).limit(limit)
    return [serialize_job(j) async for j in cur]

@app.get("/api/merge/jobs/{job_id}")
async def get_job(job_id: str, user=Depends(auth_user)):
    j = await db.jobs.find_one({"_id": job_id, "user_id": user["_id"]})
    if not j: raise HTTPException(404, "Not found")
    return serialize_job(j)

@app.delete("/api/merge/jobs/{job_id}")
async def delete_job(job_id: str, user=Depends(auth_user)):
    j = await db.jobs.find_one({"_id": job_id, "user_id": user["_id"]})
    if not j: raise HTTPException(404, "Not found")
    # If job is running, kill its subprocess first
    proc = ACTIVE_PROCS.get(job_id)
    if proc is not None:
        await _terminate_proc(proc)
        ACTIVE_PROCS.pop(job_id, None)
    # Delete output if exists
    if j.get("output_path"):
        p = Path(j["output_path"])
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
        tar = p.with_suffix(".tar")
        if tar.exists():
            try: tar.unlink()
            except OSError: pass
    await db.jobs.delete_one({"_id": job_id})
    return {"ok": True}

@app.post("/api/merge/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, user=Depends(auth_user)):
    j = await db.jobs.find_one({"_id": job_id, "user_id": user["_id"]})
    if not j: raise HTTPException(404, "Not found")
    if j["status"] in ("completed", "failed", "cancelled"):
        return {"ok": True, "status": j["status"]}
    proc = ACTIVE_PROCS.get(job_id)
    if proc is not None:
        await _terminate_proc(proc)
        ACTIVE_PROCS.pop(job_id, None)
    await db.jobs.update_one(
        {"_id": job_id},
        {"$set": {"status": "cancelled", "error": "Cancelled by user",
                  "completed_at": now_utc()}})
    await append_log(job_id, "Job cancelled by user")
    return {"ok": True, "status": "cancelled"}

@app.get("/api/merge/jobs/{job_id}/download")
async def download_job(job_id: str, token: str):
    user = await db.users.find_one({"token": token})
    if not user: raise HTTPException(401)
    j = await db.jobs.find_one({"_id": job_id, "user_id": user["_id"]})
    if not j or not j.get("output_path"):
        raise HTTPException(404, "No output available")
    # Output is a tarball
    p = Path(j["output_path"])
    tar = p.with_suffix(".tar")
    if not tar.exists():
        subprocess.run(["tar", "-cf", str(tar), "-C", str(p.parent), p.name], check=False)
    return FileResponse(str(tar), filename=f"{j["name"]}.tar", media_type="application/x-tar")

@app.get("/api/merge/jobs/{job_id}/download/gguf")
async def download_gguf(job_id: str, token: str):
    user = await db.users.find_one({"token": token})
    if not user: raise HTTPException(401)
    j = await db.jobs.find_one({"_id": job_id, "user_id": user["_id"]})
    if not j or not j.get("gguf_path"):
        raise HTTPException(404, "No GGUF available")
    p = Path(j["gguf_path"])
    if not p.exists():
        raise HTTPException(404, "GGUF file missing")
    return FileResponse(str(p), filename=f"{j['name']}-Q4_K_M.gguf", media_type="application/octet-stream")

@app.patch("/api/merge/jobs/{job_id}/visibility")
async def set_visibility(job_id: str, payload: Dict[str, Any], user=Depends(auth_user)):
    j = await db.jobs.find_one({"_id": job_id, "user_id": user["_id"]})
    if not j: raise HTTPException(404, "Not found")
    is_public = bool(payload.get("is_public", False))
    await db.jobs.update_one({"_id": job_id}, {"$set": {"is_public": is_public}})
    return {"ok": True, "is_public": is_public}

# ---- Public leaderboard (no auth) ----
@app.get("/api/leaderboard")
async def leaderboard(limit: int = 10):
    cur = db.jobs.find({"is_public": True, "status": "completed",
                        "quality_score": {"$ne": None}}).sort("quality_score", -1).limit(limit)
    out = []
    async for j in cur:
        out.append({
            "id": j["_id"],
            "name": j["name"],
            "username": j.get("username", "anon"),
            "method": j["method"],
            "models": [m.get("id") for m in j.get("models", [])],
            "quality_score": j.get("quality_score"),
            "quality_summary": j.get("quality_summary"),
            "created_at": iso(j.get("created_at")),
        })
    return {"items": out}

# ---- Dashboard stats ----
@app.get("/api/dashboard/stats")
async def dashboard(user=Depends(auth_user)):
    total = await db.jobs.count_documents({"user_id": user["_id"]})
    done = await db.jobs.count_documents({"user_id": user["_id"], "status": "completed"})
    failed = await db.jobs.count_documents({"user_id": user["_id"], "status": "failed"})
    running = await db.jobs.count_documents({"user_id": user["_id"], "status": "running"})
    queued = await db.jobs.count_documents({"user_id": user["_id"], "status": "queued"})
    # disk usage of users merges
    used_mb = 0
    async for j in db.jobs.find({"user_id": user["_id"], "output_path": {"$ne": None}}):
        p = Path(j["output_path"])
        if p.exists():
            for f in p.rglob("*"):
                if f.is_file():
                    used_mb += f.stat().st_size // (1024*1024)
    return {
        "total_jobs": total, "completed": done, "failed": failed,
        "running": running, "queued": queued,
        "output_disk_used_mb": used_mb,
        "hardware": HW_PROFILE,
        "tier": user.get("tier", "free"),
        "daily_limit": TIER_LIMITS.get(user.get("tier", "free"), 3),
        "used_today": await _count_today_merges(user["_id"]),
    }

# ---- Background worker (async simulation of merge with realistic timing) ----
async def update_job(job_id, **fields):
    fields.setdefault("updated_at", now_utc())
    await db.jobs.update_one({"_id": job_id}, {"$set": fields})

async def append_log(job_id, line):
    await db.jobs.update_one({"_id": job_id},
                             {"$push": {"logs": f"[{now_utc().strftime("%H:%M:%S")}] {line}"}})

def _dir_size_mb(p: Path) -> int:
    total = 0
    if not p.exists(): return 0
    try:
        for root, _, files in os.walk(p):
            for f in files:
                fp = os.path.join(root, f)
                try: total += os.path.getsize(fp)
                except OSError: pass
    except OSError: pass
    return total // (1024 * 1024)

def _system_snapshot() -> Dict[str, Any]:
    """Cheap snapshot of RAM/swap/disk in GiB."""
    snap = {}
    try:
        with open("/proc/meminfo") as f:
            mi = {}
            for line in f:
                k, _, v = line.partition(":")
                v = v.strip().split()
                if v:
                    mi[k.strip()] = int(v[0])  # KiB
            # store as GiB (rounded down)
            snap["mem_avail_gb"] = mi.get("MemAvailable", 0) // (1024 * 1024)
            snap["swap_used_gb"] = (mi.get("SwapTotal", 0) - mi.get("SwapFree", 0)) // (1024 * 1024)
    except OSError: pass
    try:
        st = os.statvfs(str(WORKSPACE_DIR))
        snap["disk_free_gb"] = (st.f_bavail * st.f_frsize) // (1024 * 1024 * 1024)
    except OSError: pass
    return snap

async def _download_model(job_id, repo_id, attempt):
    """Download one HF model snapshot with stall watchdog and progress %.
    Returns True on success.
    """
    await append_log(job_id, f"[download] {repo_id} attempt={attempt}")
    repo_dir = HF_CACHE_DIR / "hub" / ("models--" + repo_id.replace("/", "--"))
    # Clean stale .incomplete files from PRIOR aborted runs of OTHER blobs.
    # huggingface_hub picks the largest .incomplete for the current blob and
    # resumes from it, but it does NOT clean orphans from prior runs of
    # different blob hashes. Keep only the largest one per blob.
    if attempt == 1 and repo_dir.exists():
        try:
            from collections import defaultdict
            groups = defaultdict(list)  # blob_hash -> [(size, path)]
            for p in repo_dir.rglob("*.incomplete"):
                # filename: <blobhash>.<suffix>.incomplete
                blob = p.name.split(".", 1)[0]
                try: groups[blob].append((p.stat().st_size, p))
                except OSError: pass
            removed_mb = 0
            for blob, files in groups.items():
                files.sort(reverse=True)  # largest first
                for size, p in files[1:]:
                    try:
                        p.unlink()
                        removed_mb += size // (1024*1024)
                    except OSError: pass
            if removed_mb > 0:
                await append_log(job_id,
                    f"[{repo_id}] cleaned {removed_mb}MB of stale .incomplete files")
        except Exception as e:
            await append_log(job_id, f"[{repo_id}] cache cleanup warning: {e}")

    env = {**os.environ,
           "HF_HOME": str(HF_CACHE_DIR),
           "TRANSFORMERS_CACHE": str(HF_CACHE_DIR),
           "HF_HUB_DISABLE_TELEMETRY": "1",
           "HF_HUB_ENABLE_HF_TRANSFER": "0",
           "PYTHONUNBUFFERED": "1",
           # cap thread RAM overhead for downloads
           "OMP_NUM_THREADS": "2",
           "MKL_NUM_THREADS": "2"}
    if os.environ.get("HF_TOKEN"):
        env["HF_TOKEN"] = os.environ["HF_TOKEN"]
        env["HUGGING_FACE_HUB_TOKEN"] = os.environ["HF_TOKEN"]

    # repo_dir already computed above for cleanup

    # start child in its own process group so we can kill the whole tree
    proc = await asyncio.create_subprocess_exec(
        "/home/ubuntu/llm_fusion_studio/venv/bin/python3", "-u",
        "/home/ubuntu/llm_fusion_studio/backend/hf_snapshot.py", repo_id,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        env=env, start_new_session=True)
    ACTIVE_PROCS[job_id] = proc

    last_size_mb = -1
    stall_seconds = 0
    STALL_LIMIT = 900            # 15 min with zero byte progress -> kill
    HARD_TIMEOUT = 60 * 60 * 3   # 3h absolute max per attempt
    start_ts = time.time()
    last_log_ts = 0.0

    while True:
        try:
            line = await asyncio.wait_for(proc.stdout.readline(), timeout=10.0)
        except asyncio.TimeoutError:
            line = b""
        if line:
            text = line.decode("utf-8", errors="ignore").rstrip()
            if text:
                # filter out spammy carriage-return tqdm refreshes
                if "\r" in text:
                    text = text.split("\r")[-1]
                if text:
                    await append_log(job_id, f"[{repo_id}] " + text[:220])
        if proc.returncode is not None:
            break

        cur_mb = _dir_size_mb(repo_dir)
        if cur_mb > last_size_mb:
            last_size_mb = cur_mb
            stall_seconds = 0
        else:
            stall_seconds += 10

        # periodic heartbeat every 60s
        now = time.time()
        if now - last_log_ts > 60:
            last_log_ts = now
            snap = _system_snapshot()
            await append_log(job_id,
                f"[{repo_id}] progress={cur_mb}MB elapsed={int(now-start_ts)}s "
                f"mem_avail={snap.get('mem_avail_gb',0)}GB disk_free={snap.get('disk_free_gb',0)}GB")

        if stall_seconds >= STALL_LIMIT:
            await append_log(job_id,
                f"[{repo_id}] STALLED {stall_seconds}s at {cur_mb}MB -> killing")
            await _terminate_proc(proc)
            ACTIVE_PROCS.pop(job_id, None)
            return False
        if (now - start_ts) > HARD_TIMEOUT:
            await append_log(job_id,
                f"[{repo_id}] HARD_TIMEOUT {int(now-start_ts)}s at {cur_mb}MB -> killing")
            await _terminate_proc(proc)
            ACTIVE_PROCS.pop(job_id, None)
            return False

    rc = await proc.wait()
    ACTIVE_PROCS.pop(job_id, None)
    if rc == 0:
        await append_log(job_id, f"[download] {repo_id} OK ({last_size_mb}MB)")
        return True
    # exit=-9 = SIGKILL, almost always OOM-killer or watchdog
    why = "OOM/SIGKILL" if rc == -9 else f"exit={rc}"
    await append_log(job_id, f"[download] {repo_id} failed ({why})")
    return False

async def _terminate_proc(proc):
    """Try graceful, then SIGKILL the whole process group."""
    import signal as _sig
    try:
        os.killpg(os.getpgid(proc.pid), _sig.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        try: proc.terminate()
        except Exception: pass
    try:
        await asyncio.wait_for(proc.wait(), timeout=10)
        return
    except asyncio.TimeoutError:
        pass
    try:
        os.killpg(os.getpgid(proc.pid), _sig.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try: proc.kill()
        except Exception: pass
    try: await asyncio.wait_for(proc.wait(), timeout=10)
    except asyncio.TimeoutError: pass


QUALITY_VAL_SENTENCES = [
    "The quick brown fox jumps over the lazy dog near the riverbank.",
    "Artificial intelligence has transformed how scientists analyze massive datasets.",
    "She walked into the library and chose a worn paperback about astronomy.",
    "The recipe calls for two cups of flour, a pinch of salt, and warm water.",
    "Despite the storm, the pilot landed the small aircraft safely on the gravel strip.",
    "Photosynthesis converts sunlight into chemical energy stored in plant tissues.",
    "He sketched the bridge from memory, charcoal smudging across the rough paper.",
    "The committee will reconvene next Tuesday to review the quarterly budget.",
    "Quantum entanglement remains one of the strangest predictions of modern physics.",
    "Children played in the meadow until the sun dipped behind the distant hills.",
]
QUALITY_PROMPTS = [
    "The future of renewable energy depends on",
    "A short definition of recursion in computer science:",
    "In one sentence, describe why ocean currents matter:",
]

def _run_quality_eval_subprocess(model_dir: str) -> Dict[str, Any]:
    """Spawn a separate Python process that loads the merged model on CPU,
    computes perplexity on validation sentences and runs short inferences."""
    script = f"""
import json, sys, math, os
os.environ['TRANSFORMERS_OFFLINE'] = '0'
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.set_num_threads(4)
    mdir = {model_dir!r}
    tok = AutoTokenizer.from_pretrained(mdir)
    if tok.pad_token is None: tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(mdir, torch_dtype=torch.float32, low_cpu_mem_usage=True)
    model.eval()
    sents = {QUALITY_VAL_SENTENCES!r}
    prompts = {QUALITY_PROMPTS!r}
    total_loss, total_tokens = 0.0, 0
    with torch.no_grad():
        for s in sents:
            ids = tok(s, return_tensors='pt').input_ids
            if ids.shape[1] < 2: continue
            out = model(input_ids=ids, labels=ids)
            n = ids.shape[1] - 1
            total_loss += float(out.loss.item()) * n
            total_tokens += n
    avg_loss = total_loss / max(1, total_tokens)
    ppl = math.exp(min(20.0, avg_loss))
    coherent = 0
    samples = []
    with torch.no_grad():
        for p in prompts:
            ids = tok(p, return_tensors='pt').input_ids
            gen = model.generate(ids, max_new_tokens=24, do_sample=False, pad_token_id=tok.pad_token_id)
            txt = tok.decode(gen[0][ids.shape[1]:], skip_special_tokens=True).strip()
            samples.append(txt)
            if len(txt) > 4 and any(c.isalpha() for c in txt):
                coherent += 1
    print(json.dumps({{'perplexity': ppl, 'coherent': coherent, 'total_prompts': len(prompts), 'samples': samples}}))
except Exception as e:
    print(json.dumps({{'error': str(e)}}))
    sys.exit(1)
"""
    try:
        r = subprocess.run(
            ["/home/ubuntu/llm_fusion_studio/venv/bin/python3", "-c", script],
            capture_output=True, text=True, timeout=900,
            env={**os.environ, "OMP_NUM_THREADS": "4", "MKL_NUM_THREADS": "4"})
        last = (r.stdout or "").strip().splitlines()[-1] if r.stdout else ""
        return json.loads(last) if last else {"error": "no output"}
    except Exception as e:
        return {"error": f"eval subprocess: {e}"}

async def _evaluate_merged_model(job_id: str, model_dir: Path):
    """Run quality eval and update job record with score + summary."""
    await append_log(job_id, "[quality] running perplexity + inference eval (CPU)")
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _run_quality_eval_subprocess, str(model_dir))
    if "error" in result:
        await append_log(job_id, f"[quality] eval error: {result['error']}")
        await update_job(job_id, quality_score=0,
                         quality_summary=f"Eval failed: {result['error'][:120]}")
        return
    ppl = float(result.get("perplexity", 999.0))
    coh = int(result.get("coherent", 0))
    total = int(result.get("total_prompts", len(QUALITY_PROMPTS)))
    # score: lower perplexity is better. Map ppl: 5->100, 20->80, 50->60, 100->40, 500+->10
    if ppl <= 5: ppl_score = 100
    elif ppl <= 20: ppl_score = 100 - (ppl - 5) * (20/15)   # 100..80
    elif ppl <= 50: ppl_score = 80 - (ppl - 20) * (20/30)   # 80..60
    elif ppl <= 100: ppl_score = 60 - (ppl - 50) * (20/50)  # 60..40
    elif ppl <= 500: ppl_score = 40 - (ppl - 100) * (30/400)# 40..10
    else: ppl_score = 5
    coh_score = (coh / max(1, total)) * 100
    score = round(0.7 * ppl_score + 0.3 * coh_score, 1)
    label = "Excellent" if score >= 85 else "Good" if score >= 70 else "Fair" if score >= 50 else "Poor"
    summary = f"{label} — perplexity {ppl:.2f}, {coh}/{total} inference tests passed"
    await update_job(job_id, quality_score=score, quality_summary=summary)
    await append_log(job_id, f"[quality] score={score} {summary}")

def _ensure_llama_cpp() -> Optional[Path]:
    """Clone llama.cpp if missing. Return convert script path."""
    convert = LLAMA_CPP_DIR / "convert_hf_to_gguf.py"
    if convert.exists():
        return convert
    try:
        LLAMA_CPP_DIR.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--depth", "1",
                        "https://github.com/ggerganov/llama.cpp.git", str(LLAMA_CPP_DIR)],
                       check=True, timeout=300)
    except Exception:
        return None
    return convert if convert.exists() else None

async def _convert_to_gguf(job_id: str, model_dir: Path) -> Optional[Path]:
    """Run llama.cpp convert + quantize to Q4_K_M. Returns path or None."""
    await append_log(job_id, "[gguf] converting to GGUF Q4_K_M")
    loop = asyncio.get_event_loop()
    convert_script = await loop.run_in_executor(None, _ensure_llama_cpp)
    if not convert_script:
        await append_log(job_id, "[gguf] llama.cpp not available; skipping GGUF")
        return None
    f16_path = model_dir / "model-f16.gguf"
    q4_path = model_dir / "model-Q4_K_M.gguf"
    try:
        # step 1: hf -> f16 gguf
        proc = await asyncio.create_subprocess_exec(
            "/home/ubuntu/llm_fusion_studio/venv/bin/python3", str(convert_script),
            str(model_dir), "--outfile", str(f16_path), "--outtype", "f16",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            env={**os.environ, "PYTHONUNBUFFERED": "1"})
        async for line in proc.stdout:
            t = line.decode("utf-8", errors="ignore").rstrip()
            if t: await append_log(job_id, f"[gguf-convert] {t[:200]}")
        rc = await proc.wait()
        if rc != 0 or not f16_path.exists():
            await append_log(job_id, f"[gguf] convert failed rc={rc}")
            return None
        # step 2: quantize to Q4_K_M (binary must exist; build if not)
        quant_bin = LLAMA_CPP_DIR / "llama-quantize"
        if not quant_bin.exists():
            quant_bin = LLAMA_CPP_DIR / "build" / "bin" / "llama-quantize"
        if not quant_bin.exists():
            await append_log(job_id, "[gguf] quantize binary missing; building llama.cpp...")
            build = await asyncio.create_subprocess_shell(
                f"cd {LLAMA_CPP_DIR} && cmake -B build -DLLAMA_NATIVE=OFF >/dev/null 2>&1 && cmake --build build --target llama-quantize -j2 >/dev/null 2>&1",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
            await build.wait()
            quant_bin = LLAMA_CPP_DIR / "build" / "bin" / "llama-quantize"
        if not quant_bin.exists():
            await append_log(job_id, "[gguf] failed to build llama-quantize; keeping f16 gguf only")
            try: f16_path.rename(q4_path)
            except OSError: return f16_path if f16_path.exists() else None
            return q4_path
        proc = await asyncio.create_subprocess_exec(
            str(quant_bin), str(f16_path), str(q4_path), "Q4_K_M",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        async for line in proc.stdout:
            t = line.decode("utf-8", errors="ignore").rstrip()
            if t: await append_log(job_id, f"[gguf-quant] {t[:200]}")
        rc = await proc.wait()
        if rc != 0 or not q4_path.exists():
            await append_log(job_id, f"[gguf] quantize failed rc={rc}")
            return f16_path if f16_path.exists() else None
        # clean up f16 intermediate
        try: f16_path.unlink()
        except OSError: pass
        await append_log(job_id, f"[gguf] OK -> {q4_path.name}")
        return q4_path
    except Exception as e:
        await append_log(job_id, f"[gguf] error: {e}")
        return None

async def _post_merge_pipeline(job_id: str, out_dir: Path):
    """Background: quality eval + GGUF. Must NEVER mark job failed."""
    try:
        await _evaluate_merged_model(job_id, out_dir)
    except Exception as e:
        await append_log(job_id, f"[quality] uncaught: {e}")
    try:
        gguf = await _convert_to_gguf(job_id, out_dir)
        if gguf and gguf.exists():
            size_mb = gguf.stat().st_size // (1024*1024)
            await update_job(job_id, gguf_path=str(gguf), gguf_size_mb=size_mb)
    except Exception as e:
        await append_log(job_id, f"[gguf] uncaught: {e}")

async def perform_merge(job_id):
    job = await db.jobs.find_one({"_id": job_id})
    if not job: return
    await update_job(job_id, status="running", started_at=now_utc(), stage="preparing", progress=2)
    await append_log(job_id, f"Starting merge: {job['name']}")
    await append_log(job_id, f"Method: {job['method']}, models: {len(job['models'])}")

    id_to_model = {m["id"]: m for m in catalog.ALL}
    sel_models = [id_to_model[sp["id"]] for sp in job["models"] if sp["id"] in id_to_model]
    archs = {tuple(m["architectures"]) for m in sel_models}
    if len(archs) > 1:
        await update_job(job_id, status="failed", error="Models have different architectures; cannot merge.", completed_at=now_utc())
        await append_log(job_id, "ERROR: mismatched architectures " + str(archs))
        return

    out_dir = MERGES_DIR / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = out_dir.parent / f"{job_id}.yml"
    base_model = sel_models[0]["id"]
    method = job["method"]
    lines = [f"merge_method: {method}"]
    if method != "passthrough":
        lines.append(f"base_model: {base_model}")
    lines.append("dtype: float16")
    lines.append("models:")
    for sp in job["models"]:
        w = sp.get("weight", 1.0/len(job["models"]))
        lines.append(f"  - model: {sp['id']}")
        if method in ("linear", "ties", "dare_ties", "slerp"):
            lines.append("    parameters: { weight: %.4f, density: 0.5 }" % w)
    yaml_cfg = chr(10).join(lines) + chr(10)
    cfg_path.write_text(yaml_cfg)
    await append_log(job_id, "mergekit config written")
    await append_log(job_id, yaml_cfg.strip())

    await update_job(job_id, stage="downloading", progress=10)
    unique_ids = list({sp["id"] for sp in job["models"]})

    # Pre-flight: aggressively clean orphan .incomplete files across the WHOLE
    # cache (not just current repo) so we don't waste disk on stragglers from
    # prior crashed merges. Keep largest .incomplete per blob inside repos we
    # are about to download (resume-friendly).
    keep_blobs = set()
    for repo_id in unique_ids:
        rd = HF_CACHE_DIR / "hub" / ("models--" + repo_id.replace("/", "--"))
        if rd.exists():
            from collections import defaultdict
            groups = defaultdict(list)
            for p in rd.rglob("*.incomplete"):
                blob = p.name.split(".", 1)[0]
                try: groups[blob].append((p.stat().st_size, p))
                except OSError: pass
            for blob, files in groups.items():
                files.sort(reverse=True)
                if files: keep_blobs.add(str(files[0][1]))
    swept_mb = 0
    for p in HF_CACHE_DIR.rglob("*.incomplete"):
        if str(p) in keep_blobs: continue
        try:
            sz = p.stat().st_size
            p.unlink()
            swept_mb += sz // (1024*1024)
        except OSError: pass
    if swept_mb > 0:
        await append_log(job_id, f"Pre-flight: swept {swept_mb}MB of stale .incomplete orphans")

    # Pre-flight: disk-space sanity. Need ~2x model size on disk (cache + output).
    est_disk_gb = max(5, int(job.get("output_size_gb", 1) * 3))
    snap = _system_snapshot()
    if snap.get("disk_free_gb", 999) < est_disk_gb:
        msg = (f"Insufficient disk: need ~{est_disk_gb}GB free, "
               f"have {snap.get('disk_free_gb',0)}GB. "
               f"Delete old jobs or clear HF cache and retry.")
        await update_job(job_id, status="failed", error=msg, completed_at=now_utc())
        await append_log(job_id, "ERROR: " + msg)
        return

    # Sequential download is intentional: keeps peak RAM low on a 30GB host.
    DOWNLOAD_MAX_ATTEMPTS = 4
    for i, repo_id in enumerate(unique_ids):
        ok = False
        for attempt in range(1, DOWNLOAD_MAX_ATTEMPTS + 1):
            ok = await _download_model(job_id, repo_id, attempt)
            if ok: break
            backoff = min(60, 10 + attempt * 10)
            await append_log(job_id, f"retrying {repo_id} in {backoff}s (attempt {attempt+1}/{DOWNLOAD_MAX_ATTEMPTS})")
            await asyncio.sleep(backoff)
        if not ok:
            await update_job(job_id, status="failed",
                             error=f"Failed to download {repo_id} after {DOWNLOAD_MAX_ATTEMPTS} attempts",
                             completed_at=now_utc())
            return
        pct = 10 + int(((i+1) / len(unique_ids)) * 45)
        await update_job(job_id, progress=pct)

    await update_job(job_id, stage="merging", progress=58)

    # Pre-flight: detect pickle-only (.bin) repos. mergekit's --lazy-unpickle
    # has a known bug with torch>=2.6 ('TypedStorage' has no 'execute') so we
    # MUST avoid --lazy-unpickle when any input is .bin-only (no safetensors).
    def _repo_has_safetensors(repo_id: str) -> bool:
        snap_dir = HF_CACHE_DIR / "hub" / ("models--" + repo_id.replace("/", "--")) / "snapshots"
        if not snap_dir.exists(): return False
        for sd in snap_dir.iterdir():
            if any(p.name.endswith(".safetensors") for p in sd.iterdir() if p.is_file() or p.is_symlink()):
                return True
        return False
    all_have_safetensors = all(_repo_has_safetensors(sp["id"]) for sp in job["models"])
    use_lazy = all_have_safetensors

    await append_log(job_id,
        f"Starting mergekit-yaml (lazy_unpickle={use_lazy}; safetensors_only={all_have_safetensors})")
    env = {**os.environ,
           "HF_HOME": str(HF_CACHE_DIR),
           "TRANSFORMERS_CACHE": str(HF_CACHE_DIR),
           "HF_HUB_DISABLE_TELEMETRY": "1",
           "TOKENIZERS_PARALLELISM": "false",
           # cap thread fan-out so mergekit doesn't oversubscribe RAM on a 30GB box
           "OMP_NUM_THREADS": "4",
           "MKL_NUM_THREADS": "4",
           "OPENBLAS_NUM_THREADS": "4",
           "PYTHONUNBUFFERED": "1"}
    if os.environ.get("HF_TOKEN"):
        env["HF_TOKEN"] = os.environ["HF_TOKEN"]
        env["HUGGING_FACE_HUB_TOKEN"] = os.environ["HF_TOKEN"]

    def _build_cmd(lazy: bool):
        c = ["/home/ubuntu/llm_fusion_studio/venv/bin/mergekit-yaml",
             str(cfg_path), str(out_dir),
             "--allow-crimes", "--copy-tokenizer", "--out-shard-size", "2B",
             "--low-cpu-memory"]
        if lazy: c.append("--lazy-unpickle")
        return c

    # Up to 2 attempts: if first fails non-OOM and we used --lazy-unpickle,
    # retry without it (covers transient mergekit bugs).
    MERGE_STALL_LIMIT = 1800       # 30 min no output growth -> kill
    MERGE_HARD_TIMEOUT = 60 * 120  # 2h absolute (7B+7B realistic worst case)
    rc = None
    for attempt in (1, 2):
        # clear output dir between attempts
        if attempt == 2 and out_dir.exists():
            for child in out_dir.iterdir():
                try:
                    if child.is_file() or child.is_symlink(): child.unlink()
                    else: shutil.rmtree(child, ignore_errors=True)
                except OSError: pass
            await append_log(job_id, "Cleared partial output, retrying without --lazy-unpickle")
            use_lazy = False

        cmd = _build_cmd(use_lazy)
        await append_log(job_id, f"cmd: {' '.join(cmd)}")
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            env=env, start_new_session=True)
        ACTIVE_PROCS[job_id] = proc

        last_pct = 58
        last_out_mb = 0
        stall_seconds = 0
        start_ts = time.time()
        last_hb = 0.0
        saw_typed_storage_bug = False

        while True:
            try:
                line = await asyncio.wait_for(proc.stdout.readline(), timeout=10.0)
            except asyncio.TimeoutError:
                line = b""
            if line:
                text = line.decode("utf-8", errors="ignore").rstrip()
                if "\r" in text:
                    text = text.split("\r")[-1]
                if text:
                    await append_log(job_id, text[:240])
                    low = text.lower()
                    if "typedstorage" in low and "execute" in low:
                        saw_typed_storage_bug = True
                    if "plan" in low: last_pct = max(last_pct, 65)
                    elif "execut" in low or "task" in low: last_pct = min(94, last_pct + 1)
                    elif "saving" in low or "writing" in low or "shard" in low: last_pct = max(last_pct, 92)
                    await update_job(job_id, progress=last_pct)
                stall_seconds = 0
            else:
                if proc.returncode is not None: break
                cur_mb = _dir_size_mb(out_dir)
                if cur_mb > last_out_mb:
                    last_out_mb = cur_mb
                    stall_seconds = 0
                else:
                    stall_seconds += 10

                now = time.time()
                if now - last_hb > 60:
                    last_hb = now
                    snap = _system_snapshot()
                    await append_log(job_id,
                        f"[merge] output={cur_mb}MB elapsed={int(now-start_ts)}s "
                        f"mem_avail={snap.get('mem_avail_gb',0)}GB "
                        f"swap_used={snap.get('swap_used_gb',0)}GB "
                        f"disk_free={snap.get('disk_free_gb',0)}GB")

                if stall_seconds >= MERGE_STALL_LIMIT:
                    await append_log(job_id, f"merge STALLED {stall_seconds}s -> killing")
                    await _terminate_proc(proc)
                    ACTIVE_PROCS.pop(job_id, None)
                    await update_job(job_id, status="failed",
                                     error=f"Merge stalled for {MERGE_STALL_LIMIT//60} min with no output growth",
                                     completed_at=now_utc())
                    return
                if (now - start_ts) > MERGE_HARD_TIMEOUT:
                    await append_log(job_id, f"merge HARD_TIMEOUT {int(now-start_ts)}s -> killing")
                    await _terminate_proc(proc)
                    ACTIVE_PROCS.pop(job_id, None)
                    await update_job(job_id, status="failed",
                                     error=f"Merge exceeded {MERGE_HARD_TIMEOUT//60} min hard limit",
                                     completed_at=now_utc())
                    return

        rc = await proc.wait()
        ACTIVE_PROCS.pop(job_id, None)
        if rc == 0:
            break
        # decide whether to retry
        # rc == -9 == SIGKILL (OOM) -> no point retrying same way
        if rc == -9:
            await update_job(job_id, status="failed",
                             error="mergekit-yaml killed (OOM). Try smaller models or enable more swap.",
                             completed_at=now_utc())
            await append_log(job_id, "FAILED (OOM/SIGKILL)")
            return
        if attempt == 1 and (saw_typed_storage_bug or use_lazy):
            await append_log(job_id,
                f"attempt 1 failed (rc={rc}), retrying without --lazy-unpickle")
            continue
        # give up
        await update_job(job_id, status="failed",
                         error=f"mergekit-yaml failed: exit code {rc}",
                         completed_at=now_utc())
        await append_log(job_id, f"FAILED (exit code {rc})")
        return

    manifest = {"name": job["name"], "method": job["method"], "compression": job["compression"],
                "models": job["models"], "created_at": iso(now_utc()),
                "architecture": sel_models[0]["architectures"][0] if sel_models else "unknown"}
    (out_dir / "mergeforge.json").write_text(json.dumps(manifest, indent=2))

    tar = out_dir.with_suffix(".tar")
    await append_log(job_id, "Packaging output artifact")
    await update_job(job_id, stage="packaging", progress=98)
    pp = await asyncio.create_subprocess_exec("tar", "-cf", str(tar), "-C", str(out_dir.parent), out_dir.name)
    await pp.wait()

    try:
        for sm in sel_models:
            repo_dir = HF_CACHE_DIR / "hub" / ("models--" + sm["id"].replace("/", "--"))
            if repo_dir.exists():
                shutil.rmtree(repo_dir, ignore_errors=True)
                await append_log(job_id, f"Cleaned HF cache for {sm['id']}")
    except Exception as ee:
        await append_log(job_id, f"Cache cleanup warning: {ee}")

    await update_job(job_id, status="completed", progress=100, stage="completed",
                     completed_at=now_utc(), output_path=str(out_dir))
    await append_log(job_id, "Merge complete.")
    # background: quality eval + GGUF (does not block worker for next job)
    asyncio.create_task(_post_merge_pipeline(job_id, out_dir))

async def merge_worker():
    while True:
        job_id = None
        try:
            job_id = await JOB_QUEUE.get()
            await perform_merge(job_id)
        except Exception as e:
            print(f"[worker] error on job {job_id}: {e}", flush=True)
            import traceback; traceback.print_exc()
            if job_id:
                try:
                    ACTIVE_PROCS.pop(job_id, None)
                    await db.jobs.update_one(
                        {"_id": job_id, "status": {"$in": ["running", "queued"]}},
                        {"$set": {"status": "failed",
                                  "error": f"Worker exception: {type(e).__name__}: {e}",
                                  "completed_at": now_utc()}})
                except Exception: pass

# Re-enqueue jobs that were queued before restart
@app.on_event("startup")
async def requeue_pending():
    await asyncio.sleep(0.3)
    async for j in db.jobs.find({"status": "queued"}):
        await JOB_QUEUE.put(j["_id"])
    # mark stale running as failed
    await db.jobs.update_many({"status": "running"}, {"$set": {"status": "failed", "error": "Server restarted"}})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=int(os.environ.get("BACKEND_PORT", 8001)), reload=False)
