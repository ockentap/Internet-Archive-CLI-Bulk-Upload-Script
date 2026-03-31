# 📚 Internet Archive CLI Bulk-Upload Script

🚀 A powerful and interactive script to simplify and automate bulk uploads to the Internet Archive. Features a beautiful terminal UI with colors, emojis, and an intuitive directory browser.

**All dependencies are bundled** - just run and upload! 📦

---

## 🚀 Quick Start

```bash
# All dependencies are bundled - just run!
python3 bulk-upload.py
```

That's it! The script includes everything needed:
- 📦 Bundled dependencies in `vendor/` folder
- 🎨 Interactive UI with colors and emojis
- 📁 Directory browser with arrow key navigation
- 🔤 Identifier validation with auto-fix
- 📝 Metadata management
- 🔄 Automatic IA sync

---

## 🌟 Features

### ✨ New Interactive UI (v3.3+)
- 🎨 **Colorful terminal interface** with emoji support
- 📁 **Interactive directory browser** - navigate your filesystem with arrow keys
- 🏷️ **Smart identifier management** - saves and recalls your upload locations
- 🗑️ **Delete identifiers** - remove saved identifiers (not IA files)
- 📊 **Live upload progress** with file counters and transfer speeds
- ✅ **Verification with detailed reporting**
- 💾 **SQLite-based tracking** for resumable uploads
- 🔤 **Identifier validation** - auto-suggests valid identifiers
- 🔄 **Force upload option** - re-upload files when needed
- 📝 **Metadata management** - add title, description, tags, etc.

### 🔧 Core Features
- Automates the bulk upload process
- Uses your `ia` configuration stored at `~/.config/internetarchive`
- Tracks uploaded files in a SQLite database to avoid re-uploading
- Creates standalone scripts for unattended uploads
- Verifies file integrity via MD5 hash comparison
- Graceful interrupt handling (Ctrl+C)
- Follows symbolic links (with loop protection)
- Validates Internet Archive identifier format
- Uploads metadata (title, description, creator, tags) with files

---

## 🛠️ Requirements

### What You Need

| Dependency | Bundled? | Required? | Notes |
|------------|----------|-----------|-------|
| **Python 3** | ❌ | ✅ Yes | Version 3.8 or newer required |
| **internetarchive** (Python lib) | ✅ | ✅ Yes | Bundled in `vendor/` |
| **questionary** | ✅ | ✅ Yes | Bundled in `vendor/` |
| **tqdm** | ✅ | ✅ Yes | Bundled in `vendor/` |
| **ia CLI** | ❌ | ⚠️ One-time | Only needed for `ia configure` |

### Summary

**Required (not bundled):**
- Python 3.8+
- `ia` CLI (for initial setup only)

**Bundled in `vendor/` (~11MB):**
- All Python libraries needed to run the script

### What's Bundled

The `vendor/` directory includes all Python dependencies (~11MB):
- `internetarchive` - IA API client
- `questionary` + `prompt_toolkit` - Interactive menus
- `tqdm` - Progress bars
- `requests` + `urllib3` - HTTP client
- Plus all sub-dependencies

**No need to install Python packages!** Just run the script.

---

## 🚀 Quick Start

### 1️⃣ One-Time Setup

Configure Internet Archive credentials (requires `ia` CLI):

```bash
# Install ia CLI if you don't have it
# Arch Linux:
sudo pacman -S python-internetarchive

# Debian/Ubuntu:
sudo apt install python3-internetarchive

# macOS (Homebrew):
brew install python-internetarchive

# Configure with your credentials
ia configure
```

Enter your Internet Archive email and password when prompted.

**Note:** You only need `ia` for the initial `ia configure` step. After that, the script uses your saved credentials directly.

---

### 2️⃣ Run the Script

```bash
# That's it! All dependencies are bundled.
python3 bulk-upload.py
```

Or make it executable:

```bash
chmod +x bulk-upload.py
./bulk-upload.py
```

---

### 3️⃣ Command-Line Mode (Optional)

```bash
# Provide identifier and directory as arguments
python3 bulk-upload.py my-collection /path/to/files
```

---

## 📖 Step-by-Step Guide

### 1️⃣ Select an Identifier

The script shows a colorful menu with your saved identifiers:

```
📦  Internet Archive Bulk Upload
============================================================

🔖  Select an identifier:
  🏷️  my-first-collection
     📁 /home/user/uploads/collection1

  🏷️  another-project
     📁 /data/projects/project2

  ➕  Custom identifier
  🗑️  Delete identifier
  ❌  Exit
```

- Use **arrow keys** to navigate
- Press **Enter** to select
- Choose **Custom identifier** to enter a new one
- Choose **Delete identifier** to remove a saved identifier

#### 🗑️ Delete Identifier

Select "Delete identifier" to remove a saved identifier:

```
⚠️  Select identifier to delete:
  🏷️  my-first-collection
  🏷️  another-project
  ❌  Cancel

⚠️  Delete 'my-first-collection' from saved identifiers?
    (This will NOT delete files from Internet Archive) (y/N)

✅ Deleted 'my-first-collection' from saved identifiers.
```

**Note:** This only removes the identifier from your local saved list. It does **NOT** delete files from Internet Archive - that must be done via the IA web interface.

#### 🔤 Identifier Validation

When entering a custom identifier, the script validates it against Internet Archive rules:

**Rules:**
- Must be 5-101 characters long
- Must start with a letter or number
- Can only contain: `a-z`, `A-Z`, `0-9`, `_`, `.`, `-`
- **No spaces allowed**

**Invalid identifier example:**
```
❌ Identifier contains invalid characters
   Your input: '64MB SD-Card'
💡 Use suggested identifier '64MB_SD-Card' instead? (Y/n)
```

The script automatically suggests valid alternatives by replacing invalid characters!

---

### 2️⃣ Browse and Select Directory

After selecting an identifier, you'll be asked if you want to use the stored path:

```
✅ 📁 Use stored path: /home/user/uploads/collection1? (Y/n)
```

- **Yes (default)**: Uses the stored path directly and proceeds to upload
- **No**: Opens the interactive directory browser

**If you choose No**, the interactive directory browser lets you navigate:

```
🔍  📁  Browsing: /home/user
============================================================

  📁  ..              Parent directory
  📁  Documents       Directory
  📁  Downloads       Directory
  📁  Pictures        Directory
  📄  file1.txt       File (1.2 KB)
  📄  file2.pdf       File (3.4 MB)
  ...

  ✅  SELECT THIS DIRECTORY
  🏠  Go to Home
  ❌  Cancel
```

**Features:**
- 🗂️ Navigate with arrow keys
- 📊 See file sizes at a glance
- 🏠 Quick jump to home directory
- ✅ Select current directory for upload

---

### 3️⃣ Upload Progress

Watch live progress during upload:

```
📂 Scanning local files...
   Found 150 files (2.3 GB)

📤 45 files to upload

📤 [1/45] Uploading 'folder/document.pdf'...
(1/45) Uploading folder/document.pdf  ████████████░░░░░░░░  45.2%  1.2 MB/s

   ✅ Upload successful

📤 [2/45] Uploading 'folder/image.jpg'...
...
```

---

### 4️⃣ Verification

After upload, the script verifies files:

```
🔍 Verifying files on IA...
🔍 [1/150] folder/document.pdf... ✅ OK
🔍 [2/150] folder/image.jpg... ✅ OK
🔍 [3/150] folder/missing.dat... ❌ MISSING

============================================================
⚠️  Verification complete - 1 file(s) have issues:
   • folder/missing.dat
```

---

### 5️⃣ Create Pre-configured Script (Optional)

After selecting identifier and directory, you can create a standalone script:

```
📝  Create a pre-configured script for quick future uploads? (y/N)
```

This creates `<identifier>.py` that runs with pre-set values - perfect for:
- ✅ Automated cron jobs
- ✅ Repeated uploads to the same collection
- ✅ Sharing with team members

---

### 6️⃣ Force Upload (Optional)

If you're unsure whether files were uploaded successfully, you can force a re-upload:

```
⚠️  Force upload all files (ignore upload log and re-upload everything)? (y/N)
```

**When to use force upload:**
- Not sure if files were uploaded correctly
- Want to re-upload files with better quality
- Recover from interrupted uploads
- Reset upload state for testing

**What it does:**
- Clears the upload log for the current identifier
- All files will be marked as "not uploaded"
- Script will re-upload everything

---

### 7️⃣ Add Metadata (Optional)

The script can store and upload metadata with your files:

```
📝 Add metadata (title, description, tags, etc.) for this upload? (Y/n)

============================================================
📝  Metadata for Internet Archive Upload
============================================================

✏️  📌 Title: My Photo Collection
✏️  📄 Description: Photos from my summer vacation
✏️  👤 Creator/Author: John Doe
✏️  📅 Date (YYYY-MM-DD): 2026-03-31
✏️  🏷️  Subjects/Tags (semicolon-separated): photos;vacation;summer
✏️  🌐 Language (3-letter code, e.g., 'eng'): eng
```

**Metadata fields:**
- **Title** - Display name for your collection
- **Description** - Detailed description of the content
- **Creator/Author** - Who created the content
- **Date** - Publication/upload date
- **Subjects/Tags** - Keywords (semicolon-separated)
- **Language** - 3-letter ISO language code

**On subsequent runs:**
```
📝 Metadata already exists for this identifier. Edit it? (y/N)
```

Metadata is stored in `~/.config/internetarchive/metadata.json` and reused for future uploads to the same identifier.

---

## 📁 Project Structure

```
Internet-Archive-CLI-Bulk-Upload-Script/
├── bulk-upload.py          # Main interactive script (v3.3+)
├── vendor/                 # Bundled dependencies (~11MB)
├── requirements.txt        # Dependencies list
└── README.md              # This file
```

### Repository Files

| File | Purpose |
|------|---------|
| `bulk-upload.py` | Main interactive script |
| `vendor/` | Bundled Python packages |
| `requirements.txt` | Dependencies list |
| `README.md` | Documentation |

### User Data (Not in Repository)

These files are created in `~/.config/internetarchive/` during use:

| File | Purpose | In Git? |
|------|---------|---------|
| `identifiers.json` | Saved identifier → path mappings | ❌ No (user-specific) |
| `metadata.json` | Metadata templates per identifier | ❌ No (user-specific) |
| `upload_log.db` | SQLite upload tracking database | ❌ No (user-specific) |

### Reinstall Dependencies

If `vendor/` is missing, recreate it:

```bash
python3 -m pip install --target=vendor questionary internetarchive tqdm
```

Or use the requirements list:

```bash
pip install -r requirements.txt
```

---

## 💡 Tips & Best Practices

### Upload Management
- 🔄 **Resumable uploads**: If interrupted, just run again - it resumes where it left off
- 📊 **Large collections**: The script handles thousands of files efficiently
- 🔍 **Skip verification**: Press Ctrl+C during verification if you trust the upload

### Identifier Tips
- Use descriptive identifiers (e.g., `project-name-2026`)
- The script saves identifier→path mappings for quick reuse
- You can have multiple identifiers pointing to different directories

### File Organization
- Organize files in subdirectories - structure is preserved on IA
- The script follows symbolic links (with loop protection)
- Hidden files (starting with `.`) are included

---

## ⚠️ Notes

- **MD5 Verification** can be slow for large files - you can skip with Ctrl+C
- **One upload at a time**: IA processes uploads sequentially per identifier
- **Internet connection**: Stable connection recommended for large uploads
- **Disk space**: Ensure enough space for temporary files during upload

---

## 🐛 Troubleshooting

### "No module named 'questionary'" (if not using bundled libraries)

If you deleted the `vendor/` directory or it's not working:

```bash
# Option 1: Re-download bundled libraries
python3 -m pip install --target=vendor questionary internetarchive tqdm

# Option 2: Install system-wide
pip install questionary internetarchive tqdm
```

### "Permission denied" errors
```bash
# Make script executable
chmod +x bulk-upload.py

# Or run with python explicitly
python3 bulk-upload.py
```

### Upload fails mid-way
- Just run the script again - it tracks uploaded files and resumes
- Check your internet connection
- Verify IA credentials with `ia configure`

### Symbolic link issues
- The script has loop protection enabled
- If you have complex symlink structures, verify they're correct

### Vendor directory missing or corrupted
```bash
# Re-install bundled libraries
python3 -m pip install --target=vendor questionary internetarchive tqdm
```

---

## ❤️ Contributions

Contributions and feedback are welcome!

### How to Contribute
- 🐛 Report bugs via GitHub Issues
- 💡 Suggest new features
- 🔧 Submit PRs with improvements
- ⭐ Star the project to show support

### Development Setup

**For development, use a virtual environment:**

```bash
# Clone the repository
git clone https://github.com/ockentap/Internet-Archive-CLI-Bulk-Upload-Script.git
cd Internet-Archive-CLI-Bulk-Upload-Script

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # or: source venv/bin/activate.fish (fish shell)

# Install dependencies
pip install -r requirements.txt

# Run the script (uses venv libraries instead of vendor/)
python bulk-upload.py
```

**To rebuild the vendor directory:**

```bash
# Remove old vendor directory
rm -rf vendor/

# Create fresh vendor directory with all dependencies
python3 -m pip install --target=vendor questionary internetarchive tqdm
```

---

## 📝 Changelog

### v3.3 (2026-03-31)
- 🗑️ **Delete identifiers** from saved list
  - Select identifier to delete from menu
  - Confirms deletion (does NOT delete from IA)
  - Removes local tracking only
- ✅ **Fixed directory selection flow**
  - Confirming stored path now skips directory browser
  - Faster workflow for repeated uploads

### v3.2 (2026-03-31)
- 📝 **Metadata management** for IA uploads
  - Interactive metadata collection (title, description, tags, etc.)
  - Stored per-identifier in `~/.config/internetarchive/metadata.json`
  - Asks to edit on subsequent runs (default: No)
  - Automatically included with all uploads

### v3.1 (2026-03-31)
- 🔤 **Identifier validation** with auto-suggestions
  - Validates against IA format rules
  - Suggests valid alternatives for invalid identifiers
  - Clear error messages with examples
- 🔄 **Force upload option** to re-upload all files
  - Clears upload log for current identifier
  - Useful for recovering from failed uploads
  - Prompts before clearing to prevent accidents

### v3.0 (2026-03-31)
- ✨ **New interactive UI** with questionary library
- 🎨 Colorful terminal interface with emoji support
- 📁 **Interactive directory browser** with navigation
- 📊 Enhanced progress tracking with statistics
- 🔒 Symlink loop protection
- 💾 Better error handling and user feedback

### v2.0 (Previous)
- Added ncurses-based UI (now deprecated)
- SQLite upload tracking
- MD5 verification

### v1.0 (Original)
- Basic CLI upload functionality
- Identifier management

---

## 📄 License

This script is provided "as is" without warranty of any kind. Use at your own risk.

---

## 🤝 Support

If you find this script useful:
- ⭐ Star the project on GitHub
- 📢 Share it with others
- 💬 Leave feedback or suggestions

**Happy uploading!** 🎉
