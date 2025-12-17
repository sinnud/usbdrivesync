# USB Drive Sync & Backup Tool

A Python-based tool for managing synchronized backups between two USB drives (2-3TB each) on Debian Linux, with master-backup versioning strategy. Supports NTFS and exFAT filesystems.

## Features

- **Master-Backup Model**: Master drive has latest versions, backup keeps version history
- **Efficient Scanning**: Uses Linux `find` command for fast metadata collection
- **Smart Syncing**: Only transfers changed files (delta sync) via `rsync`
- **Multiple Sync Modes**: Traditional staging mode or direct USB 3.0 drive-to-drive sync
- **Versioning**: Modified files on backup are renamed with timestamp before update
- **Safety Checks**: Drive UUID verification and USB 3.0 speed detection
- **Filesystem Support**: NTFS and exFAT drives with automatic detection
- **SQLite Tracking**: Complete metadata and sync history database

## Architecture

- **Linux `find`**: Fast filesystem scanning (5-10x faster than Python)
- **Linux `rsync`**: Reliable incremental file transfers
- **Python**: Intelligence layer (comparison, orchestration, versioning)
- **SQLite**: Metadata storage and audit trail

## Requirements

### Hardware
- Debian Linux laptop with at least one USB 3.0 port (blue port)
- 2× USB drives (2-3TB each, NTFS or exFAT formatted)
- ~200GB+ free space on laptop for staging delta files

### Software (Debian)
```bash
# System packages
sudo apt-get update
sudo apt-get install -y ntfs-3g exfat-fuse exfat-utils rsync python3 python3-pip

# Python 3.8+ (usually pre-installed)
python3 --version
```

## Initial Setup - Windows Desktop

Since your desktop has Windows OS, use it for the initial full rsync (one-time only).

### Option A: Using WSL (Windows Subsystem for Linux) - Recommended

1. **Install WSL** (if not already installed):
   ```powershell
   # Run PowerShell as Administrator
   wsl --install
   # Restart computer
   ```

2. **Install rsync in WSL**:
   ```bash
   # Open WSL terminal
   sudo apt update
   sudo apt install rsync
   ```

3. **Connect both USB drives** to Windows
   - Check drive letters in File Explorer (e.g., D: and E:)

4. **Initial rsync in WSL**:
   ```bash
   # In WSL terminal
   # Windows drives are mounted at /mnt/
   # D: drive = /mnt/d
   # E: drive = /mnt/e
   
   # Full mirror from master to backup
   rsync -avH --progress /mnt/d/ /mnt/e/
   
   # Explanation:
   # -a = archive mode (preserve permissions, timestamps, etc.)
   # -v = verbose (show files being copied)
   # -H = preserve hard links
   # --progress = show transfer progress
   ```

5. **Wait for completion** (2-3 hours for 2TB on USB 3.0)

6. **Safely eject both drives** from Windows

### Option B: Using Robocopy (Windows Native)

If you prefer not to use WSL:

1. **Connect both USB drives** to Windows
   - Check drive letters (e.g., D: and E:)

2. **Open Command Prompt as Administrator**

3. **Run robocopy**:
   ```cmd
   robocopy D:\ E:\ /MIR /R:3 /W:5 /V /ETA
   
   REM Explanation:
   REM /MIR = Mirror (copy all files and folders)
   REM /R:3 = Retry 3 times on failed copies
   REM /W:5 = Wait 5 seconds between retries
   REM /V = Verbose output
   REM /ETA = Show estimated time remaining
   ```

4. **Wait for completion**

5. **Safely eject both drives**

### Option C: Using cwRsync (Windows Port of rsync)

1. **Download cwRsync**: https://itefix.net/cwrsync
2. **Install** to `C:\Program Files\cwRsync`
3. **Open Command Prompt**, navigate to cwRsync bin folder
4. **Run**:
   ```cmd
   cd "C:\Program Files\cwRsync\bin"
   rsync.exe -avH --progress D:/ E:/
   ```

### After Windows Initial Sync

✅ Both drives now have identical content  
⚠️ **Do NOT create any metadata on Windows**  
→ Move to Debian laptop for all metadata operations

---

## Setup - Debian Laptop

### 1. Mount USB Drive with Proper Options

```bash
# Create mount point
sudo mkdir -p /mnt/usb

# Check filesystem type
lsblk -f | grep sdX1

# Mount NTFS drive (replace sdX1 with your device)
sudo mount -t ntfs-3g -o uid=$(id -u),gid=$(id -g),big_writes,noatime /dev/sdX1 /mnt/usb

# OR mount exFAT drive
sudo mount -t exfat -o uid=$(id -u),gid=$(id -g) /dev/sdX1 /mnt/usb

# OR auto-detect filesystem (recommended)
sudo mount -o uid=$(id -u),gid=$(id -g) /dev/sdX1 /mnt/usb

# Verify mount
df -h | grep /mnt/usb
```

**💡 Tip: Use the mount helper script** (auto-detects filesystem):
```bash
# Make it executable (first time only)
chmod +x mount-usb.sh

# Mount any drive automatically
./mount-usb.sh /dev/sdb1

# Or specify custom mount point
./mount-usb.sh /dev/sdb1 /mnt/backup
```

### 2. Clone This Repository

```bash
cd ~
git clone <repository-url> usbdrivesync
cd usbdrivesync
```

Or if you have the files already:
```bash
cd ~/usbdrivesync
```

### 3. Initial Drive Identification

```bash
# Plug in MASTER drive to USB 3.0 port (BLUE port)
python3 src/setup.py --scan-drives

# Follow prompts to identify master drive
# This creates config.json with drive UUIDs
```

### 4. Scan Master Drive

```bash
# Master drive still connected
python3 src/scan.py --drive /mnt/usb --role master

# Wait for scan to complete (~10 minutes for 2TB)
```

### 5. Scan Backup Drive

```bash
# Unplug master, plug in BACKUP drive to USB 3.0 port
python3 src/scan.py --drive /mnt/usb --role backup

# Wait for scan to complete
```

✅ **Setup complete!** SQLite database now has metadata for both drives.

---

## Regular Usage - Monthly Sync

### Step 1: Scan Master Drive
```bash
# Plug master drive into USB 3.0 (BLUE) port
python3 src/scan.py --drive /mnt/usb --role master

# Shows: X new files, Y modified, Z deleted
```

### Step 2: Compare & Generate Sync Plan
```bash
# Unplug master drive
python3 src/compare.py

# Shows delta size and saves sync plan
```

### Step 3: Stage Deltas to Laptop
```bash
# Plug master drive back in
python3 src/sync.py --stage-deltas

# Copies only changed files to /tmp/usb_sync_staging/
```

### Step 4: Apply to Backup
```bash
# Unplug master, plug backup drive
python3 src/sync.py --apply-staged

# Applies changes with versioning
# Modified files: old version renamed with timestamp
```

### Step 5: Verify (Optional)
```bash
# Backup drive still connected
python3 src/verify.py --role backup
```

---

## Command Reference

### scan.py - Scan drive metadata
```bash
python3 src/scan.py --drive /mnt/usb --role master
python3 src/scan.py --drive /mnt/usb --role backup
```

### compare.py - Compare drives
```bash
python3 src/compare.py                    # Generate sync plan
python3 src/compare.py --show-only        # Just show differences
```

### sync.py - Execute sync
```bash
python3 src/sync.py --stage-deltas        # Copy deltas to laptop
python3 src/sync.py --apply-staged        # Apply to backup drive
python3 src/sync.py --dry-run             # Preview only
```

### report.py - View status
```bash
python3 src/report.py --summary           # Overall status
python3 src/report.py --history           # Recent operations
python3 src/report.py --versions <path>   # File version history
python3 src/report.py --deleted           # Files deleted from master
```

### verify.py - Integrity check
```bash
python3 src/verify.py --role backup       # Verify backup integrity
```

### identify.py - Check drive
```bash
python3 src/identify.py /mnt/usb          # What drive is this?
```

---

## File Versioning

When a file is modified on master:

**Before sync:**
- Master: `photo.jpg` (new version, 2MB, modified 2024-12-07)
- Backup: `photo.jpg` (old version, 1.8MB, modified 2024-11-15)

**After sync:**
- Master: `photo.jpg` (unchanged)
- Backup: `photo.jpg` (new version from master)
- Backup: `photo.jpg.20241115_143022` (old version, preserved)

**Multiple versions accumulate:**
- `photo.jpg` (current)
- `photo.jpg.20241207_181500`
- `photo.jpg.20241115_143022`
- `photo.jpg.20241001_092045`

**Note:** Master deletions do NOT delete from backup (backup keeps everything).

---

## Safety Features

### 1. Drive UUID Verification
Before any operation, verifies the correct drive is connected:
```
✅ Verified: MASTER drive (UUID: A1B2C3D4E5F6)
```

Or warns if wrong drive:
```
❌ ERROR: Expected master drive
   Expected UUID: A1B2C3D4E5F6
   Found UUID: F6E5D4C3B2A1
   This appears to be: BACKUP drive
```

### 2. USB 3.0 Speed Check
Verifies drive is on USB 3.0 port (5000 Mbps):
```
✅ USB speed OK: 5000 Mbps (USB 3.0 or higher)
```

Or warns if on slower port:
```
❌ ERROR: Device on USB 2.0
   Current speed: 480 Mbps
   Required: 5000 Mbps (USB 3.0)
   Expected transfer time for 100GB: 5.7 hours (vs 0.6 hours on USB 3.0)
   
   Please plug into the BLUE USB port!
Continue anyway? (yes/NO):
```

---

## Project Structure

```
usbdrivesync/
├── README.md                # This file
├── WINDOWS_INITIAL_SYNC.md  # Detailed Windows rsync guide
├── config.json              # Drive identities (created by setup.py)
├── usb_backup.db            # SQLite database (created by setup.py)
│
├── src/
│   ├── setup.py            # Initial drive identification
│   ├── scan.py             # Metadata scanner
│   ├── compare.py          # Diff generator
│   ├── sync.py             # Sync executor
│   ├── report.py           # Status reports
│   ├── verify.py           # Integrity checker
│   ├── identify.py         # Drive identifier utility
│   │
│   └── lib/
│       ├── __init__.py
│       ├── database.py     # SQLite operations
│       ├── drive_utils.py  # Drive detection/verification
│       ├── file_scanner.py # Find command wrapper
│       ├── rsync_wrapper.py# Rsync orchestration
│       └── versioning.py   # Version management logic
│
├── logs/                    # Operation logs (auto-created)
└── plans/                   # Saved sync plans (auto-created)
```

---

## Troubleshooting

### Drive not mounting
```bash
# Check if drive is detected
lsblk

# Check filesystem
sudo fdisk -l

# Try manual mount
sudo mount -t ntfs-3g /dev/sdX1 /mnt/usb
```

### USB speed detection fails
```bash
# Manual check
lsusb -t | grep -i "5000M"  # USB 3.0
lsusb -t | grep -i "480M"   # USB 2.0

# Find device speed
device=sdb  # your device
cat /sys/block/$device/device/../speed
```

### Permission issues

**⚠️ CRITICAL: Always mount with user permissions!**

If you get "Permission denied" errors when syncing, it means the drive was mounted without proper permissions.

```bash
# CORRECT way - mount with your user as owner:
sudo mount -t ntfs-3g -o uid=$(id -u),gid=$(id -g) /dev/sdX1 /mnt/usb

# Check current mount options:
mount | grep /mnt/usb

# If mounted incorrectly, remount:
sudo umount /mnt/usb
sudo mount -t ntfs-3g -o uid=$(id -u),gid=$(id -g) /dev/sdX1 /mnt/usb

# Verify you can write:
touch /mnt/usb/test.txt && rm /mnt/usb/test.txt
```

**Why this is needed:** The sync script copies files from `/tmp/usb_staging` (owned by your user) to the USB drive. If the USB drive is mounted as root-only, the copy will fail with permission errors.

---

## Performance

### Initial Sync (Windows Desktop, 2TB)
- ~2-3 hours (USB 3.0 drive-to-drive)

### Monthly Sync (Debian Laptop, 100GB deltas)
- Scan master: ~10 minutes
- Compare: <1 minute
- Stage to laptop: ~6 minutes
- Apply to backup: ~6 minutes
- **Total: ~25 minutes**

### Database Size
- ~500MB for 2 million files

---

## License

MIT License - See LICENSE file

## Author

Created for managing dual USB drive backups on Debian Linux.
