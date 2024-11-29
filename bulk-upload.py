import os
import hashlib
import json
import sqlite3
from internetarchive import get_item
import sys
import signal
import logging
from tqdm import tqdm

# Set logging level to WARNING to suppress extra output from internetarchive
logging.getLogger('internetarchive').setLevel(logging.WARNING)

CONFIG_DIR = os.path.expanduser('~/.config/internetarchive')
IDENTIFIERS_FILE = os.path.join(CONFIG_DIR, 'identifiers.json')
UPLOAD_LOG_DB = os.path.join(CONFIG_DIR, 'upload_log.db')

# Global flag to indicate if SIGINT was received
quit_flag = False

def ensure_config_dir():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)

def load_identifiers():
    ensure_config_dir()
    if os.path.exists(IDENTIFIERS_FILE):
        with open(IDENTIFIERS_FILE, 'r') as f:
            return json.load(f)
    else:
        return {}

def save_identifiers(identifiers):
    with open(IDENTIFIERS_FILE, 'w') as f:
        json.dump(identifiers, f, indent=4)

def create_upload_log_db():
    conn = sqlite3.connect(UPLOAD_LOG_DB)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS upload_log (
            identifier TEXT,
            filename TEXT,
            size INTEGER,
            uploaded INTEGER,
            PRIMARY KEY (identifier, filename)
        )
    ''')
    conn.commit()
    conn.close()

def update_upload_log(identifier, files_info):
    conn = sqlite3.connect(UPLOAD_LOG_DB)
    c = conn.cursor()
    data = [(identifier, f['relative_path'], f['size'], f['uploaded']) for f in files_info]
    c.executemany('''
        INSERT OR REPLACE INTO upload_log (identifier, filename, size, uploaded)
        VALUES (?, ?, ?, ?)
    ''', data)
    conn.commit()
    conn.close()

def load_upload_log(identifier):
    conn = sqlite3.connect(UPLOAD_LOG_DB)
    c = conn.cursor()
    c.execute('SELECT filename, size, uploaded FROM upload_log WHERE identifier = ?', (identifier,))
    rows = c.fetchall()
    conn.close()
    upload_log = {row[0]: {'size': row[1], 'uploaded': bool(row[2])} for row in rows}
    return upload_log

def get_local_files(directory):
    local_files = {}
    for root, dirs, files in os.walk(directory):
        if quit_flag:
            return local_files
        for filename in files:
            if quit_flag:
                return local_files
            filepath = os.path.join(root, filename)
            relative_path = os.path.relpath(filepath, directory).replace('\\', '/')
            size = os.path.getsize(filepath)
            local_files[relative_path] = {'path': filepath, 'size': size}
    return local_files

def fetch_ia_files(identifier):
    print("Fetching file list from IA...")
    item = get_item(identifier)
    ia_files = {}
    for file in item.files:
        if quit_flag:
            return ia_files
        name = file.get('name')
        size = int(file.get('size', 0)) if file.get('size') else None
        ia_files[name] = {'size': size}
    return ia_files

def signal_handler(sig, frame):
    global quit_flag
    print("\nReceived interrupt signal. Exiting gracefully...")
    quit_flag = True

class TqdmFile(object):
    """
    Wraps a file object and updates a tqdm progress bar as data is read.
    """
    def __init__(self, filename, desc=None, unit='B', unit_scale=True, unit_divisor=1024, max_desc_length=50):
        self.file = open(filename, 'rb')
        # Truncate description if too long
        if desc and len(desc) > max_desc_length:
            desc = desc[:max_desc_length-3] + '...'
        self.tqdm = tqdm(total=os.path.getsize(filename), desc=desc, unit=unit, unit_scale=unit_scale, unit_divisor=unit_divisor)
    
    def read(self, size):
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

def main(identifier=None, local_directory=None):
    global quit_flag
    ensure_config_dir()
    create_upload_log_db()
    identifiers = load_identifiers()

    # Register the SIGINT handler
    signal.signal(signal.SIGINT, signal_handler)

    # CONFIG_PLACEHOLDER

    # If identifier and local_directory are provided, skip prompts
    if identifier and local_directory:
        print(f"Using identifier: {identifier}")
        print(f"Using local directory: {local_directory}")
    else:
        # Display menu of identifiers
        if identifiers:
            print("\nSelect an identifier:")
            print("0 - Custom identifier")
            for idx, idf in enumerate(identifiers.keys(), start=1):
                print(f"{idx} - {idf}")
            choice = input("Enter your choice: ").strip()
            if choice == '0':
                identifier = input("Enter the Internet Archive identifier: ").strip()
                local_directory = input("Enter the path to the local directory to upload: ").strip()
            elif choice.isdigit() and 1 <= int(choice) <= len(identifiers):
                identifier = list(identifiers.keys())[int(choice) - 1]
                default_path = identifiers[identifier]
                print(f"Last used path for '{identifier}' is '{default_path}'")
                local_directory = input(f"Enter the path to the local directory to upload [{default_path}]: ").strip()
                if not local_directory:
                    local_directory = default_path
            else:
                print("Invalid choice.")
                return

            # Save the identifier and path
            identifiers[identifier] = local_directory
            save_identifiers(identifiers)

            # Ask if user wants to create a new script with these settings
            create_script = input("Do you want to create a new script with these settings? (y/N): ").strip().lower()
            if create_script == 'y':
                create_configured_script(identifier, local_directory)
                print(f"New script '{identifier}.py' created with preconfigured settings.")

    # Validate the local directory
    if not os.path.isdir(local_directory):
        print(f"The directory '{local_directory}' does not exist.")
        return

    # Load upload log for this identifier
    if quit_flag:
        print("Exiting due to user request.")
        return

    upload_log = load_upload_log(identifier)

    # Fetch existing files from IA if upload_log is empty
    if not upload_log and not quit_flag:
        ia_files = fetch_ia_files(identifier)
        # Update upload_log with files that already exist on IA
        existing_files_info = []
        for filename, info in ia_files.items():
            if quit_flag:
                print("Exiting due to user request.")
                return
            existing_files_info.append({
                'relative_path': filename,
                'size': info['size'],
                'uploaded': True
            })
        update_upload_log(identifier, existing_files_info)
        # Reload upload_log
        upload_log = load_upload_log(identifier)

    # Get the list of local files
    print("\nScanning local files...")
    local_files = get_local_files(local_directory)

    if not local_files:
        print(f"No files found in '{local_directory}'.")
        return

    # Determine which files need to be uploaded
    files_to_upload = []
    for relative_path, file_info in local_files.items():
        if quit_flag:
            print("Exiting due to user request.")
            return
        filepath = file_info['path']
        size = file_info['size']
        log_entry = upload_log.get(relative_path)

        if log_entry:
            if log_entry['uploaded']:
                if log_entry['size'] == size:
                    # File exists on IA with same size, skip
                    print(f"File '{relative_path}' already uploaded with same size, skipping.")
                    continue
                else:
                    # File size differs, re-upload
                    print(f"File '{relative_path}' size differs, will re-upload.")
            else:
                # File was not successfully uploaded previously
                print(f"File '{relative_path}' was not uploaded successfully previously, will upload.")
        else:
            # File has not been uploaded yet
            print(f"File '{relative_path}' not uploaded yet, will upload.")

        files_to_upload.append({
            'relative_path': relative_path,
            'path': filepath,
            'size': size,
            'uploaded': False
        })

    if files_to_upload and not quit_flag:
        print(f"\n{len(files_to_upload)} files to upload.")

        # Get the item
        item = get_item(identifier)

        for file_info in files_to_upload:
            if quit_flag:
                print("Exiting due to user request.")
                return
            relative_path = file_info['relative_path']
            filepath = file_info['path']
            print(f"Uploading '{relative_path}'...")
            try:
                # Wrap the file with TqdmFile to show progress
                wrapped_file = TqdmFile(filepath, desc=f"Uploading {relative_path}")
                # Use item.upload() to upload individually
                r = item.upload(
                    files={relative_path: wrapped_file},
                    verbose=False,  # Suppress extra messages
                    retries=5,
                    checksum=False,
                    metadata=dict(),
                )
                # Check the response
                if r[0].status_code in [200, 201]:
                    # Upload successful; no need to print additional message
                    file_info['uploaded'] = True
                elif r[0].status_code == 403 and 'file already exists' in r[0].text.lower():
                    print(f"File '{relative_path}' already exists on IA.")
                    file_info['uploaded'] = True
                else:
                    print(f"Failed to upload '{relative_path}'. Status code: {r[0].status_code}")
                    file_info['uploaded'] = False
            except KeyboardInterrupt:
                print("Upload interrupted by user.")
                break
            except Exception as e:
                print(f"Exception occurred while uploading '{relative_path}': {e}")
                file_info['uploaded'] = False
            finally:
                wrapped_file.close()

            # Update the upload log after each file
            update_upload_log(identifier, [file_info])

        print("\nUpload process completed.")
    else:
        if not quit_flag:
            print("\nAll files are already uploaded.")

    if quit_flag:
        print("Exiting due to user request.")
        return

    # Perform verification without prompt
    print("Verifying files on IA...")
    item = get_item(identifier)
    ia_files = {}
    for file in item.files:
        if quit_flag:
            print("Exiting due to user request.")
            return
        name = file.get('name')
        size = int(file.get('size', 0)) if file.get('size') else None
        md5 = file.get('md5')
        ia_files[name] = {'size': size, 'md5': md5}

    mismatched_files = []
    for relative_path, file_info in local_files.items():
        if quit_flag:
            print("Exiting due to user request.")
            return
        filepath = file_info['path']
        local_size = file_info['size']
        if relative_path in ia_files:
            ia_size = ia_files[relative_path]['size']
            if ia_size != local_size:
                mismatched_files.append(relative_path)
            else:
                # Check MD5 hash
                ia_md5 = ia_files[relative_path]['md5']
                try:
                    with open(filepath, "rb") as f:
                        local_md5 = hashlib.md5(f.read()).hexdigest()
                    if ia_md5 != local_md5:
                        mismatched_files.append(relative_path)
                except Exception as e:
                    print(f"Error reading file '{relative_path}' for MD5 verification: {e}")
                    mismatched_files.append(relative_path)
        else:
            mismatched_files.append(relative_path)

    if mismatched_files:
        print("The following files do not match or are missing on IA:")
        for f in mismatched_files:
            print(f"- {f}")
    else:
        print("All files on IA match the local files.")

def create_configured_script(identifier, local_directory):
    # Read the current script's content
    script_path = os.path.realpath(__file__)
    with open(script_path, 'r') as f:
        script_content = f.readlines()

    # Find the line with the CONFIG_PLACEHOLDER
    for index, line in enumerate(script_content):
        if '# CONFIG_PLACEHOLDER' in line:
            placeholder_line = index
            break
    else:
        print("Error: CONFIG_PLACEHOLDER not found in the script.")
        return

    # Determine the indentation level
    indent = script_content[placeholder_line][:len(script_content[placeholder_line]) - len(script_content[placeholder_line].lstrip())]

    # Insert the preconfigured settings after the placeholder
    config_lines = [
        f"{indent}identifier = '{identifier}'\n",
        f"{indent}local_directory = r'{local_directory}'\n",
    ]

    # Remove the placeholder line and insert the config lines
    script_content[placeholder_line:placeholder_line+1] = config_lines

    # Save the new script
    new_script_name = f"{identifier}.py"
    new_script_path = os.path.join(os.path.dirname(script_path), new_script_name)
    with open(new_script_path, 'w') as f:
        f.writelines(script_content)

if __name__ == "__main__":
    main()