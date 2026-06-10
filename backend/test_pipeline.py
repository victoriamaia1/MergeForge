#!/usr/bin/env python3
"""MergeForge pipeline smoke test.

Tests the full pipeline end-to-end:
  1. Create a user token via API
  2. Start a merge of two small (<500M) models
  3. Poll job status until complete (or fail) with 5 min timeout
  4. Verify output safetensors tar exists and is > 1MB
  5. Verify download endpoint returns a valid file
  6. Verify quality_score is computed and stored

Run inside the project venv:
   /home/ubuntu/llm_fusion_studio/venv/bin/python3 backend/test_pipeline.py

Exit code 0 = all pass; 1 = any step failed.
"""
import sys, os, time, uuid, json
import urllib.request, urllib.error

BASE = os.environ.get("MERGEFORGE_URL", "http://127.0.0.1:8001")
TIMEOUT = int(os.environ.get("MERGEFORGE_TEST_TIMEOUT", "300"))  # 5 min
MODEL_A = os.environ.get("TEST_MODEL_A", "HuggingFaceTB/SmolLM-135M")
MODEL_B = os.environ.get("TEST_MODEL_B", "HuggingFaceTB/SmolLM-135M-Instruct")

PASSED, FAILED = [], []

def step(name, ok, extra=""):
    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] {name}{(' :: ' + extra) if extra else ''}", flush=True)
    (PASSED if ok else FAILED).append(name)

def req(method, path, body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Content-Type": "application/json"}
    if headers: h.update(headers)
    r = urllib.request.Request(BASE + path, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read() or b"{}")
        except Exception: return e.code, {}

def main():
    # 1. signup
    uname = f"smoke-{uuid.uuid4().hex[:8]}"
    code, body = req("POST", "/api/auth/signup", {"username": uname})
    step("signup creates token", code == 200 and "token" in body, f"code={code}")
    if code != 200: return 1
    token = body["token"]
    auth = {"Authorization": "Bearer " + token}

    # 1b. bump tier to enterprise so we are not blocked by limit during repeated runs
    admin_secret = os.environ.get("ADMIN_SECRET", "mergeforge-admin-secret-change-me")
    req("POST", "/api/admin/tier", {"token": token, "tier": "enterprise"},
        headers={"X-Admin-Secret": admin_secret})

    # 2. create merge
    code, body = req("POST", "/api/merge/create",
        {"name": f"smoke-{uname}", "method": "linear",
         "models": [{"id": MODEL_A, "weight": 0.5},
                    {"id": MODEL_B, "weight": 0.5}],
         "compression": "auto", "dtype": "float16"},
        headers=auth)
    step("create merge accepts request", code == 200 and "job_id" in body, f"code={code} body={body}")
    if code != 200: return 1
    job_id = body["job_id"]

    # 3. poll
    deadline = time.time() + TIMEOUT
    status = "queued"; job = None
    while time.time() < deadline:
        code, job = req("GET", f"/api/merge/jobs/{job_id}", headers=auth)
        if code != 200: break
        status = job.get("status")
        print(f"  ... status={status} stage={job.get('stage')} progress={job.get('progress')}%", flush=True)
        if status in ("completed", "failed", "cancelled"): break
        time.sleep(5)
    step("merge job reaches terminal state in time", status in ("completed","failed","cancelled"),
         f"final={status}")
    step("merge job completed successfully", status == "completed",
         f"err={job.get('error') if job else 'no job'}")
    if status != "completed": return 1

    # 4. verify output tar exists
    out_path = job.get("output_path")
    ok_dir = bool(out_path) and os.path.isdir(out_path)
    step("output directory exists", ok_dir, f"path={out_path}")

    # 5. download endpoint returns file > 1MB
    try:
        url = f"{BASE}/api/merge/jobs/{job_id}/download?token={token}"
        with urllib.request.urlopen(url, timeout=60) as resp:
            n = 0
            while True:
                chunk = resp.read(65536)
                if not chunk: break
                n += len(chunk)
        step("download endpoint returns >1MB file", n > 1024*1024, f"bytes={n}")
    except Exception as e:
        step("download endpoint returns >1MB file", False, f"err={e}")

    # 6. wait for quality_score (post-merge async) up to 4 more minutes
    deadline2 = time.time() + 240
    qscore = job.get("quality_score")
    while qscore is None and time.time() < deadline2:
        time.sleep(5)
        _, job = req("GET", f"/api/merge/jobs/{job_id}", headers=auth)
        qscore = job.get("quality_score")
    step("quality_score is computed", qscore is not None,
         f"score={qscore} summary={job.get('quality_summary')}")

    print(f"\n=== {len(PASSED)} passed, {len(FAILED)} failed ===")
    return 0 if not FAILED else 1

if __name__ == "__main__":
    sys.exit(main())
