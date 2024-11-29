```markdown
# 📚 Internet Archive CLI Bulk-Upload Script

🚀 A script to simplify and automate bulk uploads to the Internet Archive using the `ia` CLI. This script helps manage uploads efficiently by leveraging your existing `ia` configuration and tracking uploaded files with a SQLite database.

## 🌟 Features
- Automates the bulk upload process.
- Utilizes your `ia` configuration stored at `~/.config/internetarchive`.
- Tracks uploaded files in a SQLite database to avoid re-hashing files.
- Option to create a standalone script for unattended uploads.
- Verifies file integrity via MD5 hash (optional).

---

## 🛠️ Installation & Usage

### 1️⃣ Install Internet Archive CLI and Dependencies

**Using `pip`:**
```bash
pip install internetarchive
pip install tqdm
```

**For Debian-based systems:**
```bash
sudo apt install python3-internetarchive
sudo apt install python3-tqdm
```

---

### 2️⃣ Configure `ia` CLI

Run the following command and provide your Internet Archive credentials:
```bash
ia configure
```

---

### 3️⃣ Run the Script

Execute the script using Python:
```bash
python3 bulk-upload.py
```

---

### 4️⃣ Provide Upload Details

The script will prompt you for the following:

1. **Identifier Name**  
   - If previously used, it will appear in the list.
   - Press `0` to type a new identifier.

2. **File Location**  
   - Previously used paths will appear for quick selection.
   - Press `Enter` to confirm the displayed path or provide a new one.

3. **Standalone Script Creation**  
   - Optionally save the script as a standalone file for automated uploads.
   - Perfect for auto-uploads (e.g., adding it to your `crontab`).

---

## ❗ Notes
- After uploads are complete, the script verifies MD5 hashes between local and uploaded files.  
  ⏳ **This can be slow** — you may cancel with `Ctrl+C` if not needed.

- Ensure you log in via `ia configure` before using the script.

---

### ❤️ Contributions
Contributions and feedback are welcome! Fork, star 🌟, and submit your PRs to help improve this project.

---

## 📝 License
This script is provided "as is" without warranty of any kind. Use at your own risk.

---

### 🤝 Support
If you find this script useful, consider sharing it with others! 🙌
```

