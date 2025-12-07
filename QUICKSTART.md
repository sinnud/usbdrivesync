# USB Drive Sync - Quick Start Guide

This guide gets you up and running quickly.

## Prerequisites Check

```bash
# On Debian laptop
sudo apt-get update
sudo apt-get install -y ntfs-3g rsync python3

# Verify installations
which find rsync python3
```

## Initial Setup (One-Time)

### Step 1: Initial Sync on Windows Desktop

See [WINDOWS_INITIAL_SYNC.md](WINDOWS_INITIAL_SYNC.md) for detailed instructions.

**Quick version:**
```bash
# In WSL on Windows
rsync -avH --progress /mnt/d/ /mnt/e/
```

### Step 2: Setup on Debian Laptop

```bash
cd ~/usbdrivesync

# Plug in MASTER drive to USB 3.0 (blue) port
# Mount it (example - adjust device name)
sudo mkdir -p /mnt/usb
sudo mount -t ntfs-3g /dev/sdb1 /mnt/usb

# Identify drives and create config
python3 src/setup.py --scan-drives

# Scan master drive
python3 src/scan.py --drive /mnt/usb --role master

# Unplug master, plug backup, mount
sudo umount /mnt/usb
# Plug backup drive
sudo mount -t ntfs-3g /dev/sdb1 /mnt/usb

# Scan backup drive
python3 src/scan.py --drive /mnt/usb --role backup
```

✅ **Setup complete!** You now have:
- `config.json` with drive UUIDs
- `usb_backup.db` with metadata for both drives

---

## Regular Monthly Sync

### Step 1: Scan Master

```bash
# Plug master drive into USB 3.0 port
sudo mount -t ntfs-3g /dev/sdb1 /mnt/usb

# Scan
python3 src/scan.py --drive /mnt/usb --role master

# Unmount
sudo umount /mnt/usb
```

### Step 2: Compare

```bash
# Generate sync plan
python3 src/compare.py

# Review the output to see what will be synced
```

### Step 3: Stage Deltas

```bash
# Plug master drive back in
sudo mount -t ntfs-3g /dev/sdb1 /mnt/usb

# Stage files to laptop
python3 src/sync.py --stage-deltas --drive /mnt/usb

# Unmount master
sudo umount /mnt/usb
```

### Step 4: Apply to Backup

```bash
# Plug backup drive
sudo mount -t ntfs-3g /dev/sdb1 /mnt/usb

# Apply changes
python3 src/sync.py --apply-staged --drive /mnt/usb

# Unmount
sudo umount /mnt/usb
```

✅ **Sync complete!**

---

## Quick Commands Reference

### Check which drive is connected
```bash
python3 src/identify.py /mnt/usb
```

### View status
```bash
python3 src/report.py --summary
```

### View sync history
```bash
python3 src/report.py --history
```

### View file versions
```bash
python3 src/report.py --versions photos/2024/img001.jpg
```

### Verify backup integrity
```bash
python3 src/verify.py --role backup --drive /mnt/usb
```

### Dry run (preview only)
```bash
python3 src/sync.py --stage-deltas --drive /mnt/usb --dry-run
python3 src/sync.py --apply-staged --drive /mnt/usb --dry-run
```

---

## Troubleshooting

### Drive not detected
```bash
# Check USB devices
lsusb

# Check block devices
lsblk

# Check if mounted
mount | grep usb
```

### Wrong USB port (USB 2.0 instead of 3.0)
```bash
# Check USB speed
lsusb -t | grep -i "5000M"  # Should see 5000M for USB 3.0

# If you see 480M, you're on USB 2.0
# Replug into BLUE port
```

### Permission denied
```bash
# Mount with user permissions
sudo mount -t ntfs-3g -o uid=$(id -u),gid=$(id -g) /dev/sdb1 /mnt/usb
```

### Database issues
```bash
# Check database exists
ls -lh usb_backup.db

# If corrupted, rescan both drives
python3 src/scan.py --drive /mnt/usb --role master
python3 src/scan.py --drive /mnt/usb --role backup
```

---

## File Locations

- **Config**: `config.json`
- **Database**: `usb_backup.db`
- **Sync plans**: `plans/sync_plan_latest.json`
- **Logs**: `logs/` (auto-created)
- **Staging**: `/tmp/usb_sync_staging/` (temporary)

---

## Tips

1. **Always use USB 3.0 (blue) port** - 10x faster
2. **Label your drives** physically with stickers
3. **Run verify** occasionally to check integrity
4. **Keep old versions** - backup keeps all file versions
5. **Laptop must stay powered** during long syncs

---

## Time Estimates

| Operation | Time (USB 3.0) |
|-----------|----------------|
| Initial rsync (2TB) | 2-3 hours |
| Monthly scan | ~10 minutes |
| Compare | <1 minute |
| Sync 100GB delta | ~20 minutes |

---

For detailed documentation, see [README.md](README.md)
