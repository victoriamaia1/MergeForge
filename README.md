<div align="center">

# 🔥 MergeForge v2

### **Self-hosted, hardware-aware LLM model merging — entirely from your browser.**

Merge open-weight large language models without writing a single line of code.
Profile your hardware, pick your models, click merge, download the result.
No GPU? No problem. CPU-only mode is a first-class citizen.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![React 18](https://img.shields.io/badge/react-18.3-61DAFB.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-7.0-47A248.svg)](https://www.mongodb.com/)

</div>

---

## 📖 Table of Contents

- [What is MergeForge?](#-what-is-mergeforge)
- [Why MergeForge?](#-why-mergeforge)
- [Purpose & Importance](#-purpose--importance)
- [Features](#-features)
- [Comparison with Other Tools](#-comparison-with-other-tools)
- [Architecture](#-architecture)
- [Installation](#-installation)
  - [Ubuntu / Debian](#ubuntu--debian-2004)
  - [macOS](#macos-1314)
  - [Kali Linux](#kali-linux)
  - [Arch / Manjaro](#arch--manjaro)
  - [Docker (any OS)](#docker-any-os)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [API Reference](#-api-reference)
- [Smoke Tests](#-smoke-tests)
- [Troubleshooting](#-troubleshooting)
- [Roadmap](#-roadmap)
- [License](#-license)

---

## 🌟 What is MergeForge?

**MergeForge** is a production-grade, self-hosted web application that turns the dark art of **LLM model merging** into a one-click experience.

Want to combine a coding model with a chat-tuned model? Want to blend an instruction-following model with a reasoning model? With MergeForge you do it in your browser — no Python notebooks, no YAML hand-editing, no command-line incantations.

Under the hood it wraps the excellent [`mergekit`](https://github.com/cg123/mergekit) library, adds hardware profiling, real-time progress, automatic quality evaluation, GGUF compression, and a multi-tier rate-limited REST API ready to be exposed to a team.

> _"Forge merged language models without surprises."_

---

## 💡 Why MergeForge?

| Pain | What other tools do | What MergeForge does |
|---|---|---|
| “Does my hardware have enough RAM?” | You find out 30 minutes into a crashed merge. | **Hardware profiled at boot** — impossible merges are hidden BEFORE you start. |
| “Will this take 5 minutes or 5 hours?” | Vague README guesses. | **Honest ETA per tier** based on detected CPU/GPU/RAM. |
| 7B model merges silently hanging | The process freezes; you SSH in to diagnose. | **Stall watchdog + auto retry + cache cleanup** — fails loud with a real error message, never hangs. |
| “Is the merged model any good?” | Eyeball test prompts manually. | **Automatic perplexity score (0–100)** + 3 built-in inference probes on every completed merge. |
| Sharing a merge weighs 14 GB | You upload safetensors and hope. | **Built-in llama.cpp GGUF Q4_K_M export** — typically 3× smaller, ready for `llama.cpp` / `ollama` / `LM Studio`. |
| Multi-user, no abuse control | Single-user notebook. | **Tier-based daily rate limits** (free / pro / enterprise) with admin escape hatch. |

---

## 🎯 Purpose & Importance

LLM merging is one of the most overlooked engineering moves of the last two years. The top open-weight models on HuggingFace leaderboards are **merges of merges of merges**. But the tooling lives at the Python-power-user level. That gatekeeps a generation of model creators.

**MergeForge exists to democratise that workflow.**

- 🧑‍🔬 **For researchers** — Run reproducible merges with quality scoring baked in. No more "I think this one feels better."
- 🏢 **For teams** — Multi-user, token-based access, rate-limited, audited via MongoDB. Drop it on an internal VPS and let the org experiment.
- 🎓 **For learners** — Visualise what `linear` vs `slerp` vs `ties` vs `dare_ties` actually do, by clicking instead of reading papers.
- 💸 **For the GPU-poor** — CPU-only Tier 1 is a fully supported execution path. A 24 GB machine can merge 7B models.

The bigger picture: **every team that fine-tunes today will be merging tomorrow.** MergeForge is the UI layer for that future.

---

## ✨ Features

### 🧠 Smart Merging Engine
- Wraps **mergekit** (the de-facto open-source merging library)
- Methods supported: `linear`, `slerp`, `ties`, `dare_ties`, `passthrough`
- Arbitrary weighting + density configuration per source model
- **Hard timeouts** (per-attempt stall watchdog + 2 h absolute cap)
- **Auto-retry** on transient failures (lazy_unpickle bug, OOM detection, partial downloads)
- **HF cache hygiene** — orphan `.incomplete` files swept before/after every job

### 📊 Post-Merge Quality Evaluation
- Computes **perplexity** on a built-in validation corpus
- Runs **3 inference probes** for coherence checks
- Stores a `quality_score` (0–100) with human-readable summary on every job
- Colour-coded UI: green > 80, amber > 60, red < 60

### 📦 GGUF Compression
- Automatic post-merge **GGUF Q4_K_M** export via `llama.cpp` convert + quantize
- Both formats downloadable from one page
- Fall-back safe — GGUF failure never blocks the merge

### 🪙 Tier-Based Access Control
| Tier | Daily merges | Use case |
|---|---|---|
| `free` | 3 / day | Hobbyist, evaluation |
| `pro` | 20 / day | Power user, small team |
| `enterprise` | unlimited | Organisation-wide |

- Token-based auth (30-word mnemonic — no passwords, no email)
- Admin endpoint to elevate tier via `X-Admin-Secret` header
- Daily counter resets at UTC midnight

### 🏆 Public Leaderboard
- Top 10 merges ranked by automated quality score
- Per-job `is_public` toggle (default private)
- Public endpoint — **no auth required** (perfect for community discovery & inbound users)

### 🖥️ Hardware Awareness
- Auto-detects CPU cores, RAM, swap, GPU (nvidia-smi), free disk
- Maps machine to one of four tiers (CPU-only → Ultra-scale)
- Disables incompatible models in the catalog with a clear blocker explanation
- Live resource monitor on the dashboard

### 🔒 Production Concerns Handled
- All long-running subprocesses run in their own process group → cancellable
- Background async worker → API stays responsive while merge runs
- Restart-resilient: queued jobs re-enqueued on boot; stale "running" → "failed"
- CORS, environment-variable-driven config, MongoDB indexes on hot paths

### 🧪 Built-in Smoke Tests
- `test_pipeline.py` exercises signup → merge → quality eval → download in < 5 min
- Exit 0/1 for CI integration

---

## ⚖️ Comparison with Other Tools

| Capability | **MergeForge** | mergekit CLI | LM Studio | Axolotl | HuggingFace AutoTrain |
|---|---|---|---|---|---|
| Browser UI for merging | ✅ | ❌ | ❌ (inference only) | ❌ | ⚠️ (paid, training) |
| Hardware-aware model filtering | ✅ | ❌ | ⚠️ | ❌ | ❌ |
| Real-time progress + stall watchdog | ✅ | ❌ | n/a | ❌ | ⚠️ |
| Auto perplexity scoring after merge | ✅ | ❌ | ❌ | ❌ | ❌ |
| Auto GGUF Q4_K_M export | ✅ | ❌ | ❌ (load only) | ❌ | ❌ |
| Multi-user with rate limits | ✅ | ❌ | ❌ | ❌ | ✅ (cloud) |
| Public leaderboard | ✅ | ❌ | ❌ | ❌ | ⚠️ |
| Self-hosted, MIT licensed | ✅ | ✅ | ❌ (closed) | ✅ | ❌ |
| CPU-only first-class | ✅ | ✅ | ✅ | ❌ | ❌ |
| Cancellable jobs from UI | ✅ | ❌ | n/a | ❌ | ✅ |

**TL;DR** — mergekit is the engine. MergeForge is the everything-else: UI, multi-tenancy, quality scoring, compression, deployment.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                       BROWSER (React 18)                     │
│  Landing · Auth · Dashboard · Models · Create · Jobs ·       │
│  JobDetail · Hardware · Leaderboard                          │
└────────────────────────┬─────────────────────────────────────┘
                         │ REST (Bearer token)
┌────────────────────────▼─────────────────────────────────────┐
│                  FASTAPI BACKEND (port 8001)                 │
│  Auth · Catalog · Validation · Job Queue · Rate Limit ·      │
│  Worker · Quality Eval · GGUF Export · Admin · Leaderboard   │
└──────┬───────────────────────────┬──────────────────┬────────┘
       │                           │                  │
       ▼                           ▼                  ▼
  ┌─────────┐              ┌──────────────┐   ┌─────────────┐
  │ MongoDB │              │   mergekit   │   │  llama.cpp  │
  │ (users, │              │ (subprocess) │   │ (convert +  │
  │  jobs)  │              │              │   │  quantize)  │
  └─────────┘              └──────┬───────┘   └─────────────┘
                                  │
                           ┌──────▼──────┐
                           │  HF Cache   │
                           │ (workspace) │
                           └─────────────┘
```

**Process flow for a merge:**
1. `POST /api/merge/create` → validate + enqueue
2. Async worker picks job → writes mergekit YAML
3. Sequentially downloads each HF model with stall watchdog
4. Spawns `mergekit-yaml` subprocess (real-time stdout streaming → MongoDB logs)
5. On success → background task: perplexity eval → GGUF convert + quantize
6. HF cache wiped, output tar packaged, downloads available

---

## 🚀 Installation

### Ubuntu / Debian 20.04+

```bash
# 1. System packages
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip git \
                        build-essential cmake nodejs \
                        mongodb-org curl

# 2. Yarn (frontend package manager)
sudo npm install -g yarn

# 3. Clone the repo
git clone https://github.com/vikrant-project/MergeForge.git
cd MergeForge

# 4. Backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# 5. Frontend
cd frontend
yarn install
yarn build
cd ..

# 6. MongoDB
sudo systemctl enable --now mongod

# 7. Environment
cp backend/.env.example backend/.env
# edit backend/.env with your paths and admin secret

# 8. Run
# Backend (in one terminal):
cd backend && ../venv/bin/python -m uvicorn server:app --host 0.0.0.0 --port 8001

# Frontend (in another terminal):
cd frontend && yarn preview --host 0.0.0.0 --port 7070
```

Open `http://localhost:7070` 🎉

---

### macOS (13/14)

```bash
# 1. Homebrew prerequisites
brew install python@3.11 node yarn mongodb-community cmake git

# 2. Start MongoDB as a service
brew services start mongodb-community

# 3. Clone & set up
git clone https://github.com/vikrant-project/MergeForge.git
cd MergeForge

python3.11 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

cd frontend && yarn install && yarn build && cd ..

cp backend/.env.example backend/.env

# 4. Launch
cd backend && ../venv/bin/python -m uvicorn server:app --host 0.0.0.0 --port 8001 &
cd frontend && yarn preview --host 0.0.0.0 --port 7070
```

> **Apple Silicon note:** mergekit uses PyTorch which has full MPS support. On an M-series Mac, the hardware profiler will classify you as Tier 2 and unlock 30B merges with reasonable speed.

---

### Kali Linux

Kali is Debian-based, so the Ubuntu instructions apply with one extra step (Kali doesn't ship `mongodb` in the default repos):

```bash
# MongoDB on Kali (add the official MongoDB apt repo)
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | \
  sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor
echo "deb [signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg] \
  https://repo.mongodb.org/apt/debian bookworm/mongodb-org/7.0 main" | \
  sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

sudo apt-get update
sudo apt-get install -y mongodb-org python3.11 python3.11-venv \
                        nodejs yarn build-essential cmake git

sudo systemctl enable --now mongod

# Then follow Ubuntu steps 3–8 above.
```

---

### Arch / Manjaro

```bash
sudo pacman -Syu --needed python python-pip nodejs yarn \
                          mongodb-bin cmake base-devel git

sudo systemctl enable --now mongodb

git clone https://github.com/vikrant-project/MergeForge.git
cd MergeForge

python -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt

cd frontend && yarn install && yarn build && cd ..
cp backend/.env.example backend/.env

# Launch (see Ubuntu step 8).
```

---

### Docker (any OS)

A multi-stage `Dockerfile` and `docker-compose.yml` are shipped in `/deploy`:

```bash
git clone https://github.com/vikrant-project/MergeForge.git
cd MergeForge
docker compose up -d
```

This will spin up three containers: `mongo`, `mergeforge-backend` (port 8001) and `mergeforge-frontend` (port 7070). Persistent volumes for the HF cache and the merges output directory are configured by default.

> The merging workload runs **inside the backend container** — so give it as much CPU/RAM as you can. 8 GB minimum for 1B-scale merges, 24 GB+ recommended for 7B-scale.

---

## ⚡ Quick Start

Once the services are running:

1. Visit `http://localhost:7070`
2. Click **Generate signup token** → save the 30-word phrase somewhere safe
3. Sidebar → **Model Catalog** → pick two models flagged compatible with your hardware
4. Sidebar → **New Merge** → choose method (start with `linear`), set weights, hit `Create`
5. Watch real-time logs in **Merge Jobs → [your job]**
6. On completion you'll see a **quality score**, the **SafeTensors** download, and (after ~30 s) the **GGUF Q4_K_M** download
7. Optionally toggle **Public** → your merge enters the leaderboard at `/leaderboard`

---

## ⚙️ Configuration

`backend/.env`:

```bash
MONGO_URL=mongodb://127.0.0.1:27017
DB_NAME=mergeforge
BACKEND_PORT=8001

# Where downloaded models + outputs live (can be huge — point to a big disk)
WORKSPACE_DIR=/var/lib/mergeforge/workspace
HF_CACHE_DIR=/var/lib/mergeforge/workspace/hf_cache

# Public-facing URL of the frontend (for CORS / share links)
PUBLIC_BASE_URL=http://localhost:7070

# Secret for the admin tier-change endpoint. CHANGE THIS.
ADMIN_SECRET=please-generate-a-random-string

# Optional: HuggingFace token if you want gated models
# HF_TOKEN=hf_xxx
```

`frontend/.env`:

```bash
VITE_BACKEND_URL=http://localhost:8001
```

---

## 🔌 API Reference

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/auth/signup` | – | Create user, receive 30-word token |
| `POST` | `/api/auth/login` | – | Login with token |
| `GET`  | `/api/auth/me` | Bearer | Current user (incl. tier) |
| `GET`  | `/api/usage/today` | Bearer | Daily merge usage / limit |
| `GET`  | `/api/models` | – | Catalog filtered by host hardware |
| `POST` | `/api/merge/validate` | Bearer | Dry-run validation + ETA |
| `POST` | `/api/merge/create` | Bearer | Enqueue a merge (rate-limited) |
| `GET`  | `/api/merge/jobs` | Bearer | List your jobs |
| `GET`  | `/api/merge/jobs/{id}` | Bearer | Job detail incl. quality + GGUF status |
| `POST` | `/api/merge/jobs/{id}/cancel` | Bearer | Kill running merge |
| `PATCH`| `/api/merge/jobs/{id}/visibility` | Bearer | Toggle public/private |
| `GET`  | `/api/merge/jobs/{id}/download?token=` | Token-in-query | Stream SafeTensors tar |
| `GET`  | `/api/merge/jobs/{id}/download/gguf?token=` | Token-in-query | Stream GGUF Q4_K_M |
| `GET`  | `/api/leaderboard` | – | Top 10 public merges (no auth) |
| `POST` | `/api/admin/tier` | `X-Admin-Secret` | Set a user's tier |
| `GET`  | `/api/hardware/profile` | – | Static hardware tier |
| `GET`  | `/api/hardware/live` | – | Live CPU/RAM/disk |
| `GET`  | `/api/dashboard/stats` | Bearer | All-in-one dashboard payload |

---

## 🧪 Smoke Tests

The repo ships with a self-contained pipeline test that exercises the full happy path against two tiny < 200 MB models:

```bash
cd MergeForge
venv/bin/python backend/test_pipeline.py
```

Expected output:

```
[PASS] signup creates token
[PASS] create merge accepts request
[PASS] merge job reaches terminal state in time :: final=completed
[PASS] merge job completed successfully
[PASS] output directory exists
[PASS] download endpoint returns >1MB file :: bytes=271656960
[PASS] quality_score is computed :: score=79.5 summary=Good — perplexity 33.86, 3/3 inference tests passed

=== 7 passed, 0 failed ===
```

Exit code 0 on full pass — drop it into CI directly.

---

## 🩺 Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Backend won't start, `ModuleNotFoundError` | Venv not activated | `source venv/bin/activate` first |
| Frontend shows blank page | `VITE_BACKEND_URL` wrong / CORS | Check `frontend/.env`, rebuild with `yarn build` |
| Merge stuck at 30% on 7B models | Disk pressure / OOM | Free disk space, increase swap, retry — the watchdog now logs the cause |
| GGUF column shows "converting…" forever | `llama.cpp` build failed | Install `cmake` + `build-essential`, re-run merge |
| Quality score never appears | Eval subprocess OOM | Use a 4 GB+ machine, or set `quality_score=null` defaults to "Eval failed" |
| `401 Invalid token` on every call | Token expired / cleared | Re-login at `/auth` |
| Daily limit error on first merge | UTC midnight rollover | Counter is UTC-based, not local |

For anything else, check `logs/backend.err.log` — every subprocess line is mirrored there.

---

## 🗺️ Roadmap

- [ ] WebSocket-based live log streaming (replace polling)
- [ ] More merge methods (`dare_linear`, `model_stock`, `breadcrumbs`)
- [ ] Direct push of merged model back to HuggingFace Hub
- [ ] Multi-host distributed merging (split layers across nodes)
- [ ] Built-in chat playground to test merged models in-browser
- [ ] Stripe-backed paid tiers (replacing the admin-set tier system)
- [ ] Leaderboard ratings + comments (community quality signal)

---

## 🤝 Contributing

PRs welcome! Please:
1. Run `backend/test_pipeline.py` before submitting
2. Keep components small & readable
3. Don't break the CPU-only Tier 1 path — it's the whole point

---

## 📄 License

[MIT](LICENSE) — do whatever you want with it.

---

<div align="center">

**Built with 🔥 for the open-weight model community.**

If MergeForge helped you merge a banger, [drop us a star](https://github.com/vikrant-project/MergeForge) ⭐

</div>
