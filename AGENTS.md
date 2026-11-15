# AGENTS.md

Guidance for coding agents working on this repository.

## What this is

One script — `bulk-upload.py` — that uploads a local directory to an archive.org item, tracks what is already uploaded in SQLite, and verifies MD5s afterwards. Python dependencies are committed under `vendor/`.

## Ground rules

- `bulk-upload.py` is the only source file. `vendor/` is generated: never edit it by hand.
- Python 3.10+ (the vendored `requests`/`urllib3` require it).
- Credentials and user state live in `~/.config/internetarchive/` (`ia.ini`, `identifiers.json`, `metadata.json`, `upload_log.db`). Never add any of them to the repo.
- Never commit `__pycache__/`, `*.pyc` or compiled `*.so`. `.gitignore` covers them on purpose: a CPython-3.13-only `charset_normalizer` `.so` once made the import fail for everyone else.

## archive.org is asynchronous — this is the main source of "bugs"

- A successful file PUT returns 200 **before** the file is listed in `item.files`. Anything that reads the item back (verification, sync) must poll; see `wait_for_ia_index()`.
- Indexing is routinely minutes behind, and the platform answers with `Please reduce your request rate - total_tasks_queued exceeds global_limit` under load. Both are platform behaviour, not script failures — do not retry-tighten or "fix" them.
- Do not trust the PUT status as proof of upload; verification compares size + MD5.

## Invariants worth keeping

- `force_upload` must skip the IA sync. The sync re-imports every remote file as `uploaded=True` and silently cancels the forced re-upload.
- Verification returns `False` on any mismatch and `main()` exits non-zero; unattended callers depend on that.
- Skipping is by size, verification is by MD5. Re-runs must stay resumable.
- `create_configured_script()` writes a small launcher (`runpy` + `--yes`), never a modified copy of this source.
- `-y/--yes` must stay prompt-free end to end.
- Identifiers: 5–101 chars, `a-z A-Z 0-9 _ . -`, no spaces.

## Checking a change

```bash
python3 -m py_compile bulk-upload.py
python3 -W error::UserWarning -c "import sys; sys.path.insert(0,'vendor'); import requests, questionary; from internetarchive import get_item; print('imports ok')"
```

Offline test, no credentials and no network:

```python
import importlib.util, pathlib, tempfile, hashlib
spec = importlib.util.spec_from_file_location("bu", "bulk-upload.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class Ans:
    def __init__(self, v): self.v = v
    def ask(self): return self.v
class Q:
    def confirm(self, *a, **k): return Ans(True)
    def select(self, *a, **k): return Ans(None)
    def text(self, *a, **k): return Ans("x")
m.questionary = Q()

d = pathlib.Path(tempfile.mkdtemp()); (d / "a.bin").write_bytes(b"x" * 10)
# Report the file as already on the item so the run skips upload and polling
m.fetch_ia_files = lambda ident: {"a.bin": {"size": 10, "md5": hashlib.md5(b"x" * 10).hexdigest()}}
assert m.process_upload("offline-test-item", str(d)) is True, "offline check failed"
print("OFFLINE CHECK OK")
```

A live smoke test costs a real upload; use a throwaway identifier and delete the files afterwards:

```bash
ID=agent-smoke-$(date +%s)
python3 bulk-upload.py "$ID" ./some-dir --yes; echo "exit=$?"
ia delete "$ID" --all
```

## Workflow

Branch → PR → merge to `main`; `main` is what users download. Rebuild `vendor/` only if a dependency must change:

```bash
python3 -m pip install --target=vendor questionary internetarchive tqdm
```
