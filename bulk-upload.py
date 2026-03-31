#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Internet Archive Bulk Upload Script with Interactive UI

Features:
    📁 Interactive directory selection with file browser
    🏷️  Identifier management with colorful menu
    📊 Upload progress with statistics
    ✅ Verification with detailed reporting
    💾 SQLite-based upload tracking for resumable uploads
"""

import os
import hashlib
import json
import sqlite3
import sys
import signal
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# ─────────────────────────────────────────────────────────────────────────────
# Vendored Libraries Support
# ─────────────────────────────────────────────────────────────────────────────
# Add the 'vendor' directory to Python path for bundled dependencies
# This allows running the script without virtual environments or system installs
SCRIPT_DIR = Path(__file__).parent.resolve()
VENDOR_DIR = SCRIPT_DIR / "vendor"
if VENDOR_DIR.exists():
    sys.path.insert(0, str(VENDOR_DIR))

# ─────────────────────────────────────────────────────────────────────────────
# Third-party Imports (from vendor or system)
# ─────────────────────────────────────────────────────────────────────────────
import questionary
from internetarchive import get_item
from tqdm import tqdm

# ─────────────────────────────────────────────────────────────────────────────
# Configuration & Identifiers
# ─────────────────────────────────────────────────────────────────────────────
CONFIG_DIR = Path.home() / ".config" / "internetarchive"
IDENTIFIERS_FILE = CONFIG_DIR / "identifiers.json"
METADATA_FILE = CONFIG_DIR / "metadata.json"
UPLOAD_LOG_DB = CONFIG_DIR / "upload_log.db"

# Global flag for graceful shutdown
quit_flag = False

# ─────────────────────────────────────────────────────────────────────────────
# Signal Handling
# ─────────────────────────────────────────────────────────────────────────────
def signal_handler(sig, frame):
    global quit_flag
    if quit_flag:
        # Second interrupt - force exit
        print("\n\n⚠️  Force exit...")
        sys.exit(1)
    
    print("\n\n⚠️  Received interrupt signal. Exiting gracefully...")
    quit_flag = True
    # Raise KeyboardInterrupt to break out of blocking operations
    raise KeyboardInterrupt("Interrupted by user")


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ─────────────────────────────────────────────────────────────────────────────
# Configuration Directory & Identifiers
# ─────────────────────────────────────────────────────────────────────────────
def ensure_config_dir():
    """Create config directory if it doesn't exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_identifiers() -> Dict[str, str]:
    """Load saved identifier → directory mappings."""
    ensure_config_dir()
    if IDENTIFIERS_FILE.exists():
        try:
            with open(IDENTIFIERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_identifiers(identifiers: Dict[str, str]):
    """Save identifier → directory mappings."""
    ensure_config_dir()
    with open(IDENTIFIERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(identifiers, f, indent=4, sort_keys=True)


def load_metadata(identifier: str) -> Dict[str, Any]:
    """Load metadata for a specific identifier."""
    ensure_config_dir()
    if METADATA_FILE.exists():
        try:
            with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                all_metadata = json.load(f)
                return all_metadata.get(identifier, {})
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_metadata(identifier: str, metadata: Dict[str, Any]):
    """Save metadata for a specific identifier."""
    ensure_config_dir()
    all_metadata = {}
    if METADATA_FILE.exists():
        try:
            with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                all_metadata = json.load(f)
        except (json.JSONDecodeError, IOError):
            all_metadata = {}
    
    all_metadata[identifier] = metadata
    
    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_metadata, f, indent=4, sort_keys=True)


def get_default_metadata() -> Dict[str, Any]:
    """Return default metadata structure."""
    return {
        'title': '',
        'description': '',
        'creator': '',
        'date': '',
        'subject': '',  # Tags (semicolon-separated)
        'language': 'eng',
        'mediatype': 'data',
    }


def collect_metadata(identifier: str, existing_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Interactively collect metadata from user.
    If existing_metadata is provided, show current values as defaults.
    """
    import datetime
    
    if existing_metadata is None:
        existing_metadata = get_default_metadata()
    
    print("\n" + "=" * 60)
    print("📝  Metadata for Internet Archive Upload")
    print("=" * 60)
    print("\nEnter metadata for your upload. This information will be")
    print("stored and used for future uploads to this identifier.\n")
    
    # Get current date as default
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Title
    title = questionary.text(
        "📌 Title:",
        default=existing_metadata.get('title', ''),
        qmark="✏️"
    ).ask()
    
    if not title or quit_flag:
        title = identifier  # Use identifier as fallback
    
    # Description
    description = questionary.text(
        "📄 Description:",
        default=existing_metadata.get('description', ''),
        qmark="✏️"
    ).ask()
    
    # Creator
    creator = questionary.text(
        "👤 Creator/Author:",
        default=existing_metadata.get('creator', ''),
        qmark="✏️"
    ).ask()
    
    # Date
    date = questionary.text(
        "📅 Date (YYYY-MM-DD):",
        default=existing_metadata.get('date', today),
        qmark="✏️"
    ).ask()
    
    # Subject/Tags
    subject = questionary.text(
        "🏷️  Subjects/Tags (semicolon-separated):",
        default=existing_metadata.get('subject', ''),
        qmark="✏️"
    ).ask()
    
    # Language
    language = questionary.text(
        "🌐 Language (3-letter code, e.g., 'eng'):",
        default=existing_metadata.get('language', 'eng'),
        qmark="✏️"
    ).ask()
    
    # Build metadata dict
    metadata = {
        'title': title.strip() if title else identifier,
        'description': description.strip() if description else '',
        'creator': creator.strip() if creator else '',
        'date': date.strip() if date else today,
        'subject': subject.strip() if subject else '',
        'language': language.strip() if language else 'eng',
        'mediatype': 'data',
    }
    
    return metadata


# ─────────────────────────────────────────────────────────────────────────────
# SQLite Upload Log
# ─────────────────────────────────────────────────────────────────────────────
def create_upload_log_db():
    """Create upload log database if it doesn't exist."""
    ensure_config_dir()
    conn = sqlite3.connect(UPLOAD_LOG_DB)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS upload_log (
            identifier TEXT,
            filename TEXT,
            size INTEGER,
            uploaded INTEGER,
            md5_hash TEXT,
            PRIMARY KEY (identifier, filename)
        )
    ''')
    conn.commit()
    conn.close()


def update_upload_log(identifier: str, files_info: List[Dict[str, Any]]):
    """Update upload log with file information."""
    conn = sqlite3.connect(UPLOAD_LOG_DB)
    c = conn.cursor()
    data = [
        (identifier, f['relative_path'], f['size'], f['uploaded'], f.get('md5_hash'))
        for f in files_info
    ]
    c.executemany('''
        INSERT OR REPLACE INTO upload_log (identifier, filename, size, uploaded, md5_hash)
        VALUES (?, ?, ?, ?, ?)
    ''', data)
    conn.commit()
    conn.close()


def load_upload_log(identifier: str) -> Dict[str, Dict[str, Any]]:
    """Load upload log for a specific identifier."""
    conn = sqlite3.connect(UPLOAD_LOG_DB)
    c = conn.cursor()
    c.execute(
        'SELECT filename, size, uploaded, md5_hash FROM upload_log WHERE identifier = ?',
        (identifier,)
    )
    rows = c.fetchall()
    conn.close()
    return {
        row[0]: {'size': row[1], 'uploaded': bool(row[2]), 'md5_hash': row[3]}
        for row in rows
    }


# ─────────────────────────────────────────────────────────────────────────────
# File Operations
# ─────────────────────────────────────────────────────────────────────────────
def validate_identifier(identifier: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validate Internet Archive identifier format.
    
    Returns: (is_valid, error_message, suggested_fix)
    
    IA Identifier Rules:
    - Must start with alphanumeric character
    - Can contain: a-z, A-Z, 0-9, _, ., -
    - Length: 5-101 characters
    - Pattern: ^[a-zA-Z0-9][a-zA-Z0-9_.-]{4,100}$
    """
    import re
    
    if not identifier:
        return False, "Identifier cannot be empty", None
    
    if len(identifier) < 5:
        suggested = identifier.replace(" ", "_") + "0" * (5 - len(identifier.replace(" ", "_")))
        return False, f"Identifier must be at least 5 characters (currently {len(identifier)})", suggested
    
    if len(identifier) > 101:
        return False, f"Identifier must be at most 101 characters (currently {len(identifier)})", identifier[:101]
    
    # Check if it matches the valid pattern
    pattern = r'^[a-zA-Z0-9][a-zA-Z0-9_.-]{4,100}$'
    if re.match(pattern, identifier):
        return True, "", None
    
    # Try to suggest a fix
    # Replace invalid characters with underscores
    suggested = re.sub(r'[^a-zA-Z0-9_.-]', '_', identifier)
    # Ensure it starts with alphanumeric
    if suggested and not suggested[0].isalnum():
        suggested = 'id_' + suggested
    
    if re.match(pattern, suggested):
        return False, f"Identifier contains invalid characters", suggested
    
    return False, f"Identifier format is invalid (use only letters, numbers, underscores, dots, hyphens)", suggested


def calc_md5(filepath: Path) -> Optional[str]:
    """Calculate MD5 hash of a file."""
    try:
        h = hashlib.md5()
        with filepath.open('rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        print(f"⚠️  Error calculating MD5 for {filepath}: {e}")
        return None


def get_local_files(directory: Path) -> Dict[str, Dict[str, Any]]:
    """
    Recursively scan directory and return file information.
    Uses followlinks=True to follow symbolic links.
    """
    local_files = {}
    visited_inodes = set()

    try:
        for root, dirs, files in os.walk(directory, followlinks=True):
            if quit_flag:
                break

            # Symlink loop protection
            try:
                inode = os.stat(root).st_ino
                if inode in visited_inodes:
                    dirs[:] = []
                    continue
                visited_inodes.add(inode)
            except OSError:
                pass

            for filename in files:
                if quit_flag:
                    break
                filepath = Path(root) / filename
                relative_path = filepath.relative_to(directory).as_posix()
                try:
                    size = filepath.stat().st_size
                    local_files[relative_path] = {
                        'path': filepath,
                        'size': size
                    }
                except OSError:
                    continue
    except PermissionError as e:
        print(f"⚠️  Permission denied accessing {directory}: {e}")

    return local_files


def fetch_ia_files(identifier: str) -> Dict[str, Dict[str, Any]]:
    """Fetch file list from Internet Archive."""
    item = get_item(identifier)
    ia_files = {}
    for file in item.files:
        if quit_flag:
            break
        name = file.get('name')
        size = int(file.get('size', 0)) if file.get('size') else None
        md5 = file.get('md5')
        ia_files[name] = {'size': size, 'md5': md5}
    return ia_files


# ─────────────────────────────────────────────────────────────────────────────
# Interactive UI - Directory Picker
# ─────────────────────────────────────────────────────────────────────────────
def format_size(size: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def directory_browser(start_path: Optional[str] = None) -> Optional[str]:
    """
    Interactive directory browser using questionary.
    Returns the selected directory path or None if cancelled.
    """
    current_path = Path(start_path).expanduser().resolve() if start_path else Path.home()

    try:
        while not quit_flag:
            # Get directory contents
            entries = []
            parent = current_path.parent

            # Add parent directory option if not at root
            if current_path != current_path.parent:
                entries.append(('..', parent, '📁', 'Parent directory'))

            # Add subdirectories
            dirs = []
            files = []
            try:
                for item in current_path.iterdir():
                    try:
                        if item.is_dir():
                            dirs.append(item)
                        elif item.is_file():
                            files.append(item)
                    except (PermissionError, OSError):
                        continue
            except PermissionError:
                print(f"⚠️  Permission denied: {current_path}")
                # Go to parent
                current_path = parent
                continue

            # Sort directories and files
            dirs.sort(key=lambda x: x.name.lower())
            files.sort(key=lambda x: x.name.lower())

            # Add directories
            for d in dirs:
                entries.append((d.name, d, '📁', 'Directory'))

            # Add files (for info, but not selectable for upload root)
            for f in files[:5]:  # Show first 5 files as preview
                size = format_size(f.stat().st_size)
                entries.append((f.name, f, '📄', f'File ({size})'))

            if len(files) > 5:
                entries.append(('...', None, '📄', f'... and {len(files) - 5} more files'))

            # Build choice list
            choices = []
            for name, path, icon, desc in entries:
                choices.append(questionary.Choice(
                    title=f"{icon}  {name}",
                    value=str(path) if path else None,
                    description=desc
                ))

            # Add action choices
            choices.append(questionary.Choice(
                title="✅  SELECT THIS DIRECTORY",
                value="__SELECT__",
                description="Use this directory for upload"
            ))
            choices.append(questionary.Choice(
                title="🏠  Go to Home",
                value=str(Path.home()),
                description="Navigate to home directory"
            ))
            choices.append(questionary.Choice(
                title="❌  Cancel",
                value=None,
                description="Cancel directory selection"
            ))

            # Prompt user
            selected = questionary.select(
                f"📁  Browsing: {current_path}\n\n" + "=" * 60,
                choices=choices,
                use_shortcuts=False,
                qmark="🔍"
            ).ask()

            if selected is None or quit_flag:
                return None

            if selected == "__SELECT__":
                return str(current_path)
            elif selected == str(Path.home()):
                current_path = Path.home()
            else:
                selected_path = Path(selected)
                if selected_path.is_dir():
                    current_path = selected_path
                elif selected_path.is_file():
                    # User selected a file, go to its parent
                    current_path = selected_path.parent

    except KeyboardInterrupt:
        return None
    except Exception as e:
        print(f"⚠️  Error: {e}")
        return None

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Interactive UI - Main Menu
# ─────────────────────────────────────────────────────────────────────────────
def show_identifier_menu(identifiers: Dict[str, str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Show interactive identifier selection menu.
    Returns (identifier, directory_path) tuple.
    """
    # Clean up empty or invalid identifiers
    identifiers_to_remove = [k for k in identifiers.keys() if not k or not k.strip()]
    for key in identifiers_to_remove:
        del identifiers[key]
        save_identifiers(identifiers)
    
    if not identifiers:
        print("\n📭 No stored identifiers found.")
        return get_custom_identifier_and_path()

    while True:
        # Build menu choices
        choices = []

        # Add existing identifiers (only non-empty ones)
        for identifier, path in sorted(identifiers.items()):
            if identifier and identifier.strip():  # Skip empty identifiers
                choices.append(questionary.Choice(
                    title=f"🏷️  {identifier}",
                    value=identifier,
                    description=f"📁 {path}"
                ))

        # Add action choices
        choices.append(questionary.Choice(
            title="➕  Custom identifier",
            value="__CUSTOM__",
            description="Enter a new identifier"
        ))
        choices.append(questionary.Choice(
            title="🗑️  Delete identifier",
            value="__DELETE__",
            description="Remove an identifier from the list"
        ))
        choices.append(questionary.Choice(
            title="❌  Exit",
            value=None,
            description="Exit the program"
        ))

        # Show menu
        selected = questionary.select(
            "📦  Internet Archive Bulk Upload\n" + "=" * 60 + "\n\nSelect an identifier:",
            choices=choices,
            use_shortcuts=False,
            qmark="🔖"
        ).ask()

        if selected is None or quit_flag:
            return None, None

        if selected == "__CUSTOM__":
            return get_custom_identifier_and_path()

        if selected == "__DELETE__":
            # Delete identifier
            delete_identifier(identifiers)
            continue  # Show menu again

        # Use selected identifier
        identifier = selected
        default_path = identifiers[identifier]

        # Ask if user wants to change the path
        use_stored = questionary.confirm(
            f"📁 Use stored path: {default_path}",
            default=True,
            qmark="✅"
        ).ask()

        if use_stored and not quit_flag:
            # User confirmed - use stored path directly (skip browser)
            # Validate before saving
            is_valid, _, _ = validate_identifier(identifier)
            if not is_valid:
                print(f"\n⚠️  Warning: Identifier '{identifier}' is not valid for IA.")
                print("   Consider deleting it and creating a new one with a valid name.\n")
            return identifier, default_path

        # User wants to change - open browser
        new_path = directory_browser(default_path)
        if new_path and not quit_flag:
            # Validate identifier before saving
            is_valid, _, _ = validate_identifier(identifier)
            if not is_valid:
                print(f"\n⚠️  Warning: Identifier '{identifier}' is not valid for IA.")
                print("   Consider deleting it and creating a new one with a valid name.\n")
            identifiers[identifier] = new_path
            save_identifiers(identifiers)
            return identifier, new_path
        elif quit_flag:
            return None, None

    return None, None


def delete_identifier(identifiers: Dict[str, str]):
    """Delete an identifier from the saved list."""
    if not identifiers:
        print("\n📭 No identifiers to delete.")
        return
    
    # Build choices for deletion
    choices = []
    for identifier, path in sorted(identifiers.items()):
        choices.append(questionary.Choice(
            title=f"🏷️  {identifier}",
            value=identifier,
            description=f"📁 {path}"
        ))
    
    choices.append(questionary.Choice(
        title="❌  Cancel",
        value=None,
        description="Cancel deletion"
    ))
    
    # Select identifier to delete
    to_delete = questionary.select(
        "🗑️  Select identifier to delete:",
        choices=choices,
        use_shortcuts=False,
        qmark="⚠️"
    ).ask()
    
    if to_delete and not quit_flag:
        # Confirm deletion
        confirm = questionary.confirm(
            f"Delete '{to_delete}' from saved identifiers?\n   (This will NOT delete files from Internet Archive)",
            default=False,
            qmark="⚠️"
        ).ask()
        
        if confirm and not quit_flag:
            del identifiers[to_delete]
            save_identifiers(identifiers)
            print(f"✅ Deleted '{to_delete}' from saved identifiers.")


def get_custom_identifier_and_path() -> Tuple[Optional[str], Optional[str]]:
    """Prompt for custom identifier and directory."""
    if quit_flag:
        return None, None

    while True:
        identifier = questionary.text(
            "🏷️  Enter Internet Archive identifier:",
            qmark="✏️"
        ).ask()

        if not identifier or quit_flag:
            return None, None

        # Validate identifier
        is_valid, error_msg, suggested = validate_identifier(identifier)
        
        if is_valid:
            break
        
        # Show error and suggestion
        print(f"\n❌ {error_msg}")
        print(f"   Your input: '{identifier}'")
        
        if suggested:
            use_suggested = questionary.confirm(
                f"Use suggested identifier '{suggested}' instead?",
                default=True,
                qmark="💡"
            ).ask()
            
            if use_suggested and suggested:
                identifier = suggested
                break
            else:
                print("\n⚠️  Please enter a valid identifier.\n")
        else:
            print("\n⚠️  Please enter a valid identifier.\n")

    # Let user browse for directory
    print("\n📁  Select directory to upload:")
    directory = directory_browser()

    if not directory or quit_flag:
        return None, None

    return identifier, directory


# ─────────────────────────────────────────────────────────────────────────────
# Progress Wrapper for Upload
# ─────────────────────────────────────────────────────────────────────────────
class TqdmFileWithCounter:
    """
    Wraps a file object and updates a tqdm progress bar as data is read.
    """
    def __init__(self, filename: Path, desc: str, index: int, total_files: int):
        self.file = open(filename, 'rb')
        self.index = index
        self.total_files = total_files
        counter = f"({index}/{total_files}) "
        desc = f"{counter}{desc}"
        self.tqdm = tqdm(
            total=filename.stat().st_size,
            desc=desc,
            unit='B',
            unit_scale=True,
            unit_divisor=1024
        )

    def read(self, size=-1):
        if quit_flag:
            raise KeyboardInterrupt("Upload interrupted by user.")
        data = self.file.read(size)
        if data:
            self.tqdm.update(len(data))
        return data

    def __getattr__(self, attr):
        return getattr(self.file, attr)

    def close(self):
        self.file.close()
        self.tqdm.close()


# ─────────────────────────────────────────────────────────────────────────────
# Main Upload Logic
# ─────────────────────────────────────────────────────────────────────────────
def process_upload(identifier: str, local_directory: str, force_upload: bool = False, metadata: Optional[Dict[str, Any]] = None):
    """Main upload and verification process."""
    global quit_flag

    local_dir = Path(local_directory).expanduser().resolve()

    # Validate directory
    if not local_dir.exists():
        print(f"❌ Directory does not exist: {local_dir}")
        return False

    if not local_dir.is_dir():
        print(f"❌ Path is not a directory: {local_dir}")
        return False

    if quit_flag:
        print("⚠️  Exiting due to user request.")
        return False

    # Initialize database
    create_upload_log_db()

    # Handle force upload - clear existing log for this identifier
    if force_upload:
        print("\n🔄 Force upload mode - clearing existing upload log...")
        conn = sqlite3.connect(UPLOAD_LOG_DB)
        c = conn.cursor()
        c.execute('DELETE FROM upload_log WHERE identifier = ?', (identifier,))
        conn.commit()
        conn.close()
        upload_log = {}
        print("✅ Upload log cleared. All files will be re-uploaded.")
    
    # Sync with IA to get accurate file list (default: Yes)
    if not quit_flag:
        sync_with_ia = questionary.confirm(
            "📡 Sync with Internet Archive to check existing files?",
            default=True,  # Always default to Yes
            qmark="🔄"
        ).ask()

        if sync_with_ia and not quit_flag:
            try:
                ia_files = fetch_ia_files(identifier)
                existing_files_info = []
                for filename, info in ia_files.items():
                    if quit_flag:
                        break
                    existing_files_info.append({
                        'relative_path': filename,
                        'size': info['size'] or 0,
                        'uploaded': True,
                        'md5_hash': info.get('md5')
                    })
                
                if existing_files_info:
                    update_upload_log(identifier, existing_files_info)
                    upload_log = load_upload_log(identifier)
                    print(f"✅ Synced {len(existing_files_info)} files from IA")
                else:
                    print("ℹ️  No files found on IA for this identifier (new upload)")
            except Exception as e:
                print(f"⚠️  Could not fetch files from IA: {e}")
                print("   Continuing with local database only...")
                upload_log = load_upload_log(identifier)
        else:
            # User skipped sync
            upload_log = load_upload_log(identifier)
            if not upload_log:
                print("\n⚠️  No upload history found. Files will be compared by size only.")

    # Scan local files
    print("\n📂 Scanning local files...")
    local_files = get_local_files(local_dir)

    if not local_files:
        print(f"❌ No files found in '{local_dir}'.")
        return False

    # Calculate total size
    total_size = sum(f['size'] for f in local_files.values())
    print(f"   Found {len(local_files)} files ({format_size(total_size)})")

    # Determine which files need uploading
    files_to_upload = []
    already_uploaded = []

    for relative_path, file_info in local_files.items():
        if quit_flag:
            break

        filepath = file_info['path']
        size = file_info['size']
        log_entry = upload_log.get(relative_path)

        needs_upload = False
        reason = ""

        if log_entry:
            if not log_entry['uploaded']:
                needs_upload = True
                reason = "previous upload failed"
            elif log_entry['size'] != size:
                needs_upload = True
                reason = f"size changed ({log_entry['size']} → {size})"
            else:
                already_uploaded.append(relative_path)
                continue
        else:
            needs_upload = True
            reason = "not yet uploaded"

        if needs_upload:
            files_to_upload.append({
                'relative_path': relative_path,
                'path': filepath,
                'size': size,
                'uploaded': False,
                'reason': reason
            })

    if quit_flag:
        print("⚠️  Exiting due to user request.")
        return False

    # Show summary
    print("\n" + "=" * 60)
    print(f"📊 Upload Summary")
    print("=" * 60)
    print(f"   📁 Local files:     {len(local_files)}")
    print(f"   ✅ Already on IA:   {len(already_uploaded)}")
    print(f"   📤 To upload:       {len(files_to_upload)}")
    
    if already_uploaded and len(files_to_upload) > 0:
        print(f"\n   Files already on IA (skipping):")
        for f in already_uploaded[:5]:
            print(f"      • {f}")
        if len(already_uploaded) > 5:
            print(f"      ... and {len(already_uploaded) - 5} more")

    if not files_to_upload:
        print("\n✅ All files are already uploaded!")
        return True

    print(f"\n📤 {len(files_to_upload)} files to upload")

    # Get the item
    item = get_item(identifier)

    # Prepare metadata for upload
    upload_metadata = {}
    if metadata:
        # Convert metadata to IA format
        if metadata.get('title'):
            upload_metadata['title'] = metadata['title']
        if metadata.get('description'):
            upload_metadata['description'] = metadata['description']
        if metadata.get('creator'):
            upload_metadata['creator'] = metadata['creator']
        if metadata.get('date'):
            upload_metadata['date'] = metadata['date']
        if metadata.get('subject'):
            upload_metadata['subject'] = metadata['subject']
        if metadata.get('language'):
            upload_metadata['language'] = metadata['language']
        if metadata.get('mediatype'):
            upload_metadata['mediatype'] = metadata['mediatype']
    
    if upload_metadata:
        print(f"📝 Using metadata: {len(upload_metadata)} fields")

    for index, file_info in enumerate(files_to_upload, start=1):
        if quit_flag:
            break

        relative_path = file_info['relative_path']
        filepath = file_info['path']

        print(f"\n📤 [{index}/{len(files_to_upload)}] Uploading '{relative_path}'...")

        # Upload with retry logic
        max_retries = 3
        retry_delay = 5  # seconds between retries
        upload_success = False

        for attempt in range(1, max_retries + 1):
            try:
                # Add delay between uploads to respect rate limits
                if index > 1:
                    time.sleep(1)

                wrapped_file = TqdmFileWithCounter(
                    filepath,
                    desc=f"Uploading {relative_path}",
                    index=index,
                    total_files=len(files_to_upload)
                )

                r = item.upload(
                    files={relative_path: wrapped_file},
                    verbose=False,
                    retries=5,
                    checksum=False,
                    metadata=upload_metadata
                )

                if r and r[0] and r[0].status_code in [200, 201]:
                    file_info['uploaded'] = True
                    print(f"   ✅ Upload successful")
                    upload_success = True
                    break
                elif r and r[0] and r[0].status_code == 403 and 'already exists' in r[0].text.lower():
                    file_info['uploaded'] = True
                    print(f"   ℹ️  File already exists on IA")
                    upload_success = True
                    break
                else:
                    status = r[0].status_code if r and r[0] else 'N/A'
                    print(f"   ⚠️  Attempt {attempt}/{max_retries} failed (HTTP {status})")
                    if attempt < max_retries:
                        print(f"   ⏳ Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        print(f"   ❌ Failed after {max_retries} attempts")
                        file_info['uploaded'] = False

            except KeyboardInterrupt:
                print("\n⚠️  Upload interrupted by user.")
                if 'wrapped_file' in locals():
                    wrapped_file.close()
                raise
            except Exception as e:
                error_msg = str(e)
                if 'rate' in error_msg.lower() or 'overload' in error_msg.lower() or 'SlowDown' in error_msg.lower():
                    print(f"   ⚠️  Rate limit hit - attempt {attempt}/{max_retries}")
                    if attempt < max_retries:
                        print(f"   ⏳ Waiting {retry_delay} seconds before retry...")
                        time.sleep(retry_delay)
                    else:
                        print(f"   ❌ Skipping file after {max_retries} attempts")
                        file_info['uploaded'] = False
                else:
                    print(f"   ❌ Error: {e}")
                    if attempt < max_retries:
                        print(f"   ⏳ Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        print(f"   ❌ Skipping file after {max_retries} attempts")
                        file_info['uploaded'] = False
            finally:
                if 'wrapped_file' in locals():
                    wrapped_file.close()

        # Update log after each file
        update_upload_log(identifier, [file_info])

    if quit_flag:
        print("\n⚠️  Exiting due to user request.")
        return False

    # Verification
    print("\n🔍 Verifying files on IA...")
    item = get_item(identifier)
    ia_files = {}
    for file in item.files:
        if quit_flag:
            break
        name = file.get('name')
        size = int(file.get('size', 0)) if file.get('size') else None
        md5 = file.get('md5')
        ia_files[name] = {'size': size, 'md5': md5}

    mismatched = []
    total_files = len(local_files)

    for index, (relative_path, file_info) in enumerate(local_files.items(), start=1):
        if quit_flag:
            break

        filepath = file_info['path']
        local_size = file_info['size']

        print(f"🔍 [{index}/{total_files}] {relative_path}...", end=" ")

        # Get or calculate local MD5
        log_entry = upload_log.get(relative_path, {})
        local_md5 = log_entry.get('md5_hash')

        if not local_md5:
            local_md5 = calc_md5(filepath)
            if local_md5:
                update_upload_log(identifier, [{
                    'relative_path': relative_path,
                    'size': local_size,
                    'uploaded': log_entry.get('uploaded', False),
                    'md5_hash': local_md5
                }])

        # Compare with IA
        if relative_path in ia_files:
            ia_size = ia_files[relative_path]['size']
            ia_md5 = ia_files[relative_path]['md5']

            if ia_size == local_size and local_md5 == ia_md5:
                print("✅ OK")
            else:
                print("❌ MISMATCH")
                mismatched.append(relative_path)
        else:
            print("❌ MISSING")
            mismatched.append(relative_path)

    # Summary
    print("\n" + "=" * 60)
    if mismatched:
        print(f"⚠️  Verification complete - {len(mismatched)} file(s) have issues:")
        for f in mismatched[:10]:
            print(f"   • {f}")
        if len(mismatched) > 10:
            print(f"   ... and {len(mismatched) - 10} more")
    else:
        print("✅ Verification complete - all files match!")

    return True


# ─────────────────────────────────────────────────────────────────────────────
# Script Generator
# ─────────────────────────────────────────────────────────────────────────────
def create_configured_script(identifier: str, local_directory: str):
    """Create a new script with pre-configured settings."""
    script_path = Path(__file__).resolve()
    with open(script_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find CONFIG_PLACEHOLDER
    placeholder_idx = None
    for i, line in enumerate(lines):
        if '# CONFIG_PLACEHOLDER' in line or '# Pre-configured settings' in line:
            placeholder_idx = i
            break

    if placeholder_idx is None:
        print("⚠️  Could not find placeholder for configuration.")
        return

    indent = "    "
    config_lines = [
        f"{indent}identifier = '{identifier}'\n",
        f"{indent}local_directory = r'{local_directory}'\n",
    ]

    # Insert config after placeholder
    lines[placeholder_idx] = lines[placeholder_idx].rstrip() + '\n'
    for i, config_line in enumerate(config_lines):
        lines.insert(placeholder_idx + 1 + i, config_line)

    new_script_name = f"{identifier}.py"
    with open(new_script_name, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print(f"✅ Script '{new_script_name}' created!")


# ─────────────────────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────────────────────
def main():
    """Main entry point."""
    global quit_flag

    try:
        print("\n" + "=" * 60)
        print("📦  Internet Archive Bulk Upload Script")
        print("=" * 60)

        # Check for command-line arguments
        if len(sys.argv) >= 3:
            identifier = sys.argv[1]
            local_directory = sys.argv[2]
            print(f"✅ Using identifier: {identifier}")
            print(f"✅ Using directory: {local_directory}")
        else:
            # Interactive mode
            identifiers = load_identifiers()
            identifier, local_directory = show_identifier_menu(identifiers)

            if not identifier or not local_directory or quit_flag:
                print("\n👋 Goodbye!")
                return

            # Save the identifier/path
            identifiers[identifier] = local_directory
            save_identifiers(identifiers)

            # Wrap questionary calls in try-except for KeyboardInterrupt
            try:
                # Ask about creating a configured script
                create_script = questionary.confirm(
                    "Create a pre-configured script for quick future uploads?",
                    default=False,
                    qmark="📝"
                ).ask()

                if create_script and not quit_flag:
                    create_configured_script(identifier, local_directory)

                # Handle metadata
                existing_metadata = load_metadata(identifier)
                if existing_metadata:
                    edit_metadata = questionary.confirm(
                        "📝 Metadata already exists for this identifier. Edit it?",
                        default=False,
                        qmark="✏️"
                    ).ask()

                    if edit_metadata and not quit_flag:
                        metadata = collect_metadata(identifier, existing_metadata)
                        save_metadata(identifier, metadata)
                    else:
                        metadata = existing_metadata
                else:
                    add_metadata = questionary.confirm(
                        "📝 Add metadata (title, description, tags, etc.) for this upload?",
                        default=True,
                        qmark="✏️"
                    ).ask()

                    if add_metadata and not quit_flag:
                        metadata = collect_metadata(identifier)
                        save_metadata(identifier, metadata)
                    else:
                        metadata = {}

                # Ask about force upload
                force_upload = questionary.confirm(
                    "🔄 Force upload all files (ignore upload log and re-upload everything)?",
                    default=False,
                    qmark="⚠️"
                ).ask()
            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted. Exiting...")
                print("\n👋 Goodbye!\n")
                return

        # Run the upload process
        if not quit_flag:
            success = process_upload(identifier, local_directory, force_upload=force_upload, metadata=metadata)

            if success:
                print("\n🎉 Upload process completed successfully!")
            else:
                print("\n⚠️  Upload process completed with issues.")

        print("\n👋 Goodbye!\n")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Force exit...")
        print("\n👋 Goodbye!\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
