# AGENTS.md

Instructions for an AI agent helping someone **use** this script. If you are changing the code instead, see the last section.

## What the user is trying to do

Upload a directory of files to an archive.org item, without re-uploading what is already there, and with proof that every file arrived intact. One run does all of it: scan the directory, upload what is missing, wait for archive.org to index it, compare MD5s, exit non-zero if anything failed.

## Before the first run

Check, in this order:

1. `python3 --version` is 3.10 or newer.
2. Credentials exist in `~/.config/internetarchive/ia.ini`. If not, the user runs `ia configure` once — **they** type their archive.org password, never you, and never in chat.
3. The identifier is valid: 5–101 characters, only `a-z A-Z 0-9 _ . -`, no spaces. The script offers a corrected suggestion if it is not.
4. They understand that the upload is **public** as soon as it lands, and that the script never deletes anything afterwards.

`vendor/` ships with the repository, so there is nothing to install.

## Running it

```bash
python3 bulk-upload.py                        # interactive: identifier, directory, options
python3 bulk-upload.py my-item /path/files    # skip the menus, still asks about the IA sync
python3 bulk-upload.py my-item /path --yes    # no questions at all (cron, unattended)
```

Interactive runs also offer to create a launcher (`<identifier>.py`), edit metadata, and force a re-upload.

When the user is at the keyboard, let them answer the prompts; use `--yes` only for unattended runs, and only after one supervised run has worked.

## Reading the output

- `Found N files (size)` — what the local scan saw.
- `Already on IA: N` / `To upload: M` — the resume decision. Skipping is by **size**; real verification comes at the end.
- `[2/11] Uploading 'x.zip'` then `Upload successful` — an S3 HTTP 200. **Not** proof the file is stored yet.
- `Waiting for IA to index N uploaded file(s)` — normal: archive.org indexes asynchronously. The script waits up to 15 minutes.
- `✅ OK` / `❌ MISMATCH` / `❌ MISSING` per file, then a summary.
- Exit code `0` only when every local file verified; `1` when anything failed.

## Failure modes and what to do

- **`Cannot import name 'get_item' from 'internetarchive'`** — `vendor/` is missing or a partial download emptied it. Re-clone, or `python3 -m pip install --target=vendor questionary internetarchive tqdm`.
- **`Please reduce your request rate - total_tasks_queued exceeds global_limit`** — archive.org is throttling globally, not the user's account. Wait and re-run; nothing is lost, the run resumes. Do not raise retries or hammer it.
- **`MISSING` right after `Upload successful`** — index lag. Re-run; if the files appear, nothing was wrong.
- **`MISMATCH`** — the local file differs from the remote one (edited after upload, or a truncated transfer). Re-run with the force option, or delete that file and upload it again.
- **401 / 403 during upload** — wrong or missing credentials, or the identifier belongs to another account. The user re-runs `ia configure`; never ask for the password in chat.
- **Interrupted with Ctrl+C** — safe. Re-running resumes from the SQLite log.
- **`No files found in '<dir>'`** — empty, wrong, or unreadable directory. Check the path and permissions.
- **Uploaded but the item looks empty on the website** — index lag again; confirm via `https://archive.org/metadata/<identifier>`.

## Things not to do

- Never type the user's password or an emailed code; never accept either in chat.
- Do not claim success from the `Upload successful` lines alone — wait for the verification summary and the exit code.
- Do not force-upload to "fix" a mismatch before ruling out index lag.
- Do not delete files or items unless the user asked. Item deletion is web-UI only (`My uploads → item → Delete`).
- Metadata is collected and sent **only in interactive runs**. If the item needs a title or description, the first upload must be interactive; `--yes` and argument-only runs send none.

## Wrapping up

Report the item URL (`https://archive.org/details/<identifier>`), how many files uploaded and how many were skipped, the verification result, and the exit code. Name any file that mismatched.

## Smoke test — only on the identifier the user actually wants

Never invent a throwaway identifier. An item cannot be deleted from the CLI, only from the website, so every test identifier stays behind as litter. Test against the real target instead, with one tiny file:

1. Put a few bytes in a temporary directory, e.g. `smoke-test.txt`.
2. Upload it to the identifier the user is going to use:
   ```bash
   python3 bulk-upload.py old-book-1220 /tmp/smoke-dir --yes; echo "exit=$?"
   ```
   A working setup ends with `✅ OK` and exit `0`.
3. Delete that one file — file deletion works with the S3 keys, item deletion does not:
   ```bash
   ia delete old-book-1220 smoke-test.txt
   ```
   Deletion is queued like everything else; confirm it is gone (expect `404`) before moving on:
   ```bash
   curl -sL -o /dev/null -w '%{http_code}\n' https://archive.org/download/old-book-1220/smoke-test.txt
   ```
4. Run the real upload against the same identifier.

That way the only item that exists is the one the user wanted, and it holds exactly the files they uploaded.

## If you are changing the script instead

- `bulk-upload.py` is the only source file; `vendor/` is generated — never edit it by hand.
- A PUT returns 200 before the file is listed, so anything that reads the item back must poll (`wait_for_ia_index`).
- Keep these: force upload skips the IA sync; verification decides the exit code; `--yes` stays prompt-free; the launcher stays a `runpy` wrapper.
- Check a change with `python3 -m py_compile bulk-upload.py` plus an offline harness that stubs `questionary` and `fetch_ia_files` (no credentials, no network).
