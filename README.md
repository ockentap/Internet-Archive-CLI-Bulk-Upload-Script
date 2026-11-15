# Internet Archive CLI Bulk-Upload Script

![Internet Archive bulk-upload banner](assets/banner.png)

Interactive bulk uploader for archive.org: pick a directory, the script uploads what is not on the item yet, then verifies every file by MD5.

## Requirements

- Python 3.10+
- archive.org credentials in `~/.config/internetarchive/ia.ini` (`ia configure`, once)

Dependencies are vendored in `vendor/` — nothing to install.

## Usage

```bash
python3 bulk-upload.py                       # interactive: pick identifier + directory
python3 bulk-upload.py my-item /path/files   # start from a given identifier/directory
python3 bulk-upload.py my-item /path --yes   # no prompts (cron, unattended)
```

![Terminal output](assets/terminal.png)

State lives next to the `ia` CLI config in `~/.config/internetarchive/`: `identifiers.json`, `metadata.json`, `upload_log.db`.

## Behaviour

- **Resumable** — re-running skips files already on the item.
- **Verification** — size + MD5 per file, after archive.org finishes indexing (waits up to 15 min).
- **Metadata** — title, description, creator, date, subject, language.
- **Pre-configured launcher** — optionally writes `<identifier>.py`, which runs that identifier/directory with `--yes`.
- **Force upload** — interactive option; clears the local log and skips the IA sync so everything is really re-uploaded.
- **Exit codes** — non-zero when upload or verification fails.

## Notes

- Identifiers: 5–101 characters, `a-z A-Z 0-9 _ . -`, no spaces.
- Missing `vendor/`: `python3 -m pip install --target=vendor questionary internetarchive tqdm`

Provided as-is, no warranty.
