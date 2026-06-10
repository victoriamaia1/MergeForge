"""Resilient HF snapshot downloader with internal retries.
Keeps calling snapshot_download (which resumes from .incomplete) until success.
"""
import sys, os, time, traceback
from huggingface_hub import snapshot_download
from huggingface_hub.utils import HfHubHTTPError

if __name__ == "__main__":
    repo = sys.argv[1]
    cache = os.environ["HF_HOME"]
    tok = os.environ.get("HF_TOKEN") or None
    last_err = None
    for attempt in range(1, 31):
        try:
            print(f"[hf_snapshot] attempt {attempt} for {repo}", flush=True)
            p = snapshot_download(
                repo_id=repo,
                cache_dir=cache + "/hub",
                token=tok,
                max_workers=2,
                etag_timeout=30,
                allow_patterns=["*.json", "*.safetensors", "*.bin", "*.model", "*.txt", "tokenizer.*", "*.md"],
            )
            print("SNAPSHOT_OK", p, flush=True)
            sys.exit(0)
        except Exception as e:
            last_err = e
            print(f"[hf_snapshot] attempt {attempt} failed: {type(e).__name__}: {e}", flush=True)
            traceback.print_exc()
            time.sleep(min(30, 5 + attempt * 2))
    print(f"[hf_snapshot] all retries exhausted: {last_err}", flush=True)
    sys.exit(2)
