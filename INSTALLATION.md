# Installation & Setup Guide

## System Requirements

### Hardware
- Debian Linux laptop with USB 3.0 port (blue port)
- 2× NTFS USB drives (2-3TB each)
- 200GB+ free space on laptop for staging
- Windows desktop (for initial sync only)

### Software Prerequisites

#### On Debian Linux
```bash
sudo apt-get update
sudo apt-get install -y ntfs-3g rsync python3

# Verify installations
which find      # Should output: /usr/bin/find
which rsync     # Should output: /usr/bin/rsync
which python3   # Should output: /usr/bin/python3
python3 --version  # Should be 3.8 or higher
```

No additional Python packages needed - uses only standard library!

---

## Installation Steps

### 1. Get the Project

```bash
# Option A: If using git
git clone <repository-url> ~/usbdrivesync
cd ~/usbdrivesync

# Option B: If you have the files
# Copy the entire usbdrivesync folder to ~/usbdrivesync
cd ~/usbdrivesync
```

### 2. Verify Structure

```bash
ls -la
# Should see:
# - README.md
# - src/ directory with Python scripts
# - logs/ directory
# - plans/ directory
```

### 3. Make Scripts Executable (if needed)

```bash
chmod +x src/*.py
```

### 4. Test Installation

```bash
# Should show help
python3 src/setup.py --help
python3 src/scan.py --help

# Verify rsync
rsync --version
```

---

## Initial Configuration

### Step 1: Prepare Drives

#### A. Initial Sync on Windows Desktop

Follow detailed instructions in `WINDOWS_INITIAL_SYNC.md`.

**Quick summary:**
```bash
# In WSL on Windows desktop
rsync -avH --progress /mnt/d/ /mnt/e/
```

Both drives should now be identical.

#### B. Physical Labeling (Recommended)

Use stickers to label your drives:
- Drive 1: "MASTER DRIVE"
- Drive 2: "BACKUP DRIVE"

### Step 2: Mount Drive on Debian

```bash
# Create mount point
sudo mkdir -p /mnt/usb

# Plug in first drive (into USB 3.0 / blue port)
# Check device name
lsblk

# Mount (replace sdb1 with your device)
sudo mount -t ntfs-3g -o big_writes,noatime /dev/sdb1 /mnt/usb

# Verify
df -h | grep usb
```

**Pro tip:** Add to `/etc/fstab` for easier mounting (optional):
```bash
# Get UUID
sudo blkid /dev/sdb1

# Add to /etc/fstab
UUID=your-uuid /mnt/usb ntfs-3g big_writes,noatime,users,noauto 0 0

# Now you can mount with:
mount /mnt/usb
```

### Step 3: Run Setup

```bash
cd ~/usbdrivesync

# Start setup wizard
python3 src/setup.py --scan-drives
```

**The wizard will:**
1. Scan for NTFS drives
2. Ask you to identify MASTER drive
3. Ask you to identify BACKUP drive (or do later)
4. Create `config.json` with UUIDs
5. Initialize `usb_backup.db`

**Output:** 
- `config.json` created
- `usb_backup.db` created

### Step 4: Scan Master Drive

```bash
# Master drive should still be mounted at /mnt/usb
python3 src/scan.py --drive /mnt/usb --role master

# This will take ~10 minutes for 2TB
# Shows progress and statistics
```

### Step 5: Scan Backup Drive

```bash
# Unmount master
sudo umount /mnt/usb

# Plug in backup drive (into USB 3.0 / blue port)
sudo mount -t ntfs-3g -o big_writes,noatime /dev/sdb1 /mnt/usb

# Scan
python3 src/scan.py --drive /mnt/usb --role backup

# Unmount when done
sudo umount /mnt/usb
```

---

## Verify Installation

### Check Configuration

```bash
cat config.json
# Should show master and backup UUIDs
```

### Check Database

```bash
ls -lh usb_backup.db
# Should exist and be several MB

# View summary
python3 src/report.py --summary
```

### Expected Output:
```
============================================================
USB Drive Sync - Status Summary
============================================================

📀 Master Drive:
   Label: MASTER_DRIVE_2024
   UUID: A1B2C3D4...
   Last scan: 2024-12-07 18:30:00
   Files: 1,234,567
   Active: 1,234,567
   Size: 1.98 TB

📀 Backup Drive:
   Label: BACKUP_DRIVE_2024
   UUID: F6E5D4C3...
   Last scan: 2024-12-07 18:45:00
   Files: 1,234,567
   Active: 1,234,567
   Size: 1.98 TB

📊 No sync operations yet
============================================================
```

✅ **Installation Complete!**

---

## Quick Test

Try a dry-run comparison:

```bash
python3 src/compare.py --show-only
```

Should show zero differences if drives are identical.

---

## Troubleshooting Installation

### Issue: "ntfs-3g not found"
```bash
sudo apt-get install ntfs-3g
```

### Issue: "Permission denied" when mounting
```bash
# Use sudo
sudo mount -t ntfs-3g /dev/sdb1 /mnt/usb

# Or add yourself to disk group
sudo usermod -a -G disk $USER
# Log out and back in
```

### Issue: "Python version too old"
```bash
python3 --version
# Should be 3.8+

# If older, upgrade:
sudo apt-get install python3.9
```

### Issue: "Device busy" when unmounting
```bash
# Check what's using it
lsof | grep /mnt/usb

# Kill processes or:
sudo umount -l /mnt/usb  # Lazy unmount
```

### Issue: "Database locked"
```bash
# Close all scripts
# Remove lock file
rm usb_backup.db-journal
```

---

## Next Steps

1. ✅ Installation complete
2. ✅ Both drives scanned
3. ✅ Configuration created

**You're ready to use the tool!**

See `QUICKSTART.md` for regular usage workflow.

---

## Uninstallation (if needed)

```bash
cd ~/usbdrivesync

# Remove database and config
rm usb_backup.db config.json

# Remove logs and plans
rm -rf logs/ plans/

# Remove entire project
cd ~
rm -rf usbdrivesync
```

---

## Getting Help

- **Quick Start**: `QUICKSTART.md`
- **Full Documentation**: `README.md`
- **Windows Setup**: `WINDOWS_INITIAL_SYNC.md`
- **Project Overview**: `PROJECT_SUMMARY.md`

---

*Installation guide version 1.0.0*
