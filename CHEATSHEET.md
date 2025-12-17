# USB Drive Sync - Command Cheat Sheet

Quick reference for all commands.

---

## Initial Setup (One-Time)

### Windows Desktop - Initial Sync
```bash
# WSL method (recommended)
rsync -avH --progress /mnt/d/ /mnt/e/

# Robocopy method
robocopy D:\ E:\ /MIR /R:3 /W:5 /V /ETA
```

### Debian Laptop - First Time Setup
```bash
# 1. Install prerequisites
sudo apt-get install -y ntfs-3g rsync python3

# 2. Mount drive
sudo mount -t ntfs-3g -o big_writes,noatime /dev/sdb1 /mnt/usb

# 3. Run setup wizard
python3 src/setup.py --scan-drives

# 4. Scan master
python3 src/scan.py --drive /mnt/usb --role master

# 5. Scan backup (after swapping drives)
python3 src/scan.py --drive /mnt/usb --role backup
```

---

## Regular Monthly Sync

### Complete Workflow
```bash
# 1. Mount and scan master
sudo mount -t ntfs-3g /dev/sdb1 /mnt/usb
python3 src/scan.py --drive /mnt/usb --role master
sudo umount /mnt/usb

# 2. Compare drives
python3 src/compare.py

# 3. Stage deltas (master drive)
sudo mount -t ntfs-3g /dev/sdb1 /mnt/usb
python3 src/sync.py --stage-deltas --drive /mnt/usb
sudo umount /mnt/usb

# 4. Apply to backup (backup drive)
sudo mount -t ntfs-3g /dev/sdb1 /mnt/usb
python3 src/sync.py --apply-staged --drive /mnt/usb
sudo umount /mnt/usb

# 5. Optional: Verify
sudo mount -t ntfs-3g /dev/sdb1 /mnt/usb
python3 src/verify.py --role backup --drive /mnt/usb
sudo umount /mnt/usb
```

---

## Drive Management

### Mount Drive
```bash
# Basic mount
sudo mount -t ntfs-3g /dev/sdb1 /mnt/usb

# With options (recommended)
sudo mount -t ntfs-3g -o big_writes,noatime /dev/sdb1 /mnt/usb

# With user permissions
sudo mount -t ntfs-3g -o uid=$(id -u),gid=$(id -g) /dev/sdb1 /mnt/usb
```

### Unmount Drive
```bash
# Normal unmount
sudo umount /mnt/usb

# Force unmount (if busy)
sudo umount -l /mnt/usb

# Check what's using it
lsof | grep /mnt/usb
```

### Check Drive Info
```bash
# List block devices
lsblk

# Check USB speed
lsusb -t | grep -i "5000M"  # USB 3.0
lsusb -t | grep -i "480M"   # USB 2.0

# Get UUID
sudo blkid /dev/sdb1

# Check space
df -h /mnt/usb
```

---

## Scanning

### Scan Drive
```bash
# Scan master
python3 src/scan.py --drive /mnt/usb --role master

# Scan backup
python3 src/scan.py --drive /mnt/usb --role backup
```

---

## Comparison

### Compare Drives
```bash
# Generate sync plan (saves to plans/)
python3 src/compare.py

# Show only (don't save)
python3 src/compare.py --show-only
```

---

## Syncing

### Stage Deltas
```bash
# Stage from master to laptop
python3 src/sync.py --stage-deltas --drive /mnt/usb

# Dry run (preview only)
python3 src/sync.py --stage-deltas --drive /mnt/usb --dry-run

# Use specific plan
python3 src/sync.py --stage-deltas --drive /mnt/usb --plan plans/sync_plan_20241207.json
```

### Apply to Backup
```bash
# Apply staged changes
python3 src/sync.py --apply-staged --drive /mnt/usb

# Dry run
python3 src/sync.py --apply-staged --drive /mnt/usb --dry-run
```

### Direct Sync (USB 3.0 Direct)
```bash
# Direct sync from master to backup (no staging needed)
python3 src/sync.py --direct-sync --master-drive /mnt/master --backup-drive /mnt/backup

# Dry run
python3 src/sync.py --direct-sync --master-drive /mnt/master --backup-drive /mnt/backup --dry-run
```

---

## Reporting

### Status Summary
```bash
# Overall status
python3 src/report.py --summary

# Or just
python3 src/report.py
```

### Sync History
```bash
# Recent 50 operations
python3 src/report.py --history

# Last 100 operations
python3 src/report.py --history --limit 100
```

### File Versions
```bash
# Version history of a file
python3 src/report.py --versions photos/2024/img001.jpg
```

### Deleted Files
```bash
# Files deleted from master
python3 src/report.py --deleted
```

---

## Verification

### Verify Drive
```bash
# Verify backup integrity
python3 src/verify.py --role backup --drive /mnt/usb

# Verify master
python3 src/verify.py --role master --drive /mnt/usb
```

---

## Identification

### Check Drive
```bash
# Identify which drive is connected
python3 src/identify.py /mnt/usb
```

---

## Maintenance

### Add Backup Drive Later
```bash
# If you only configured master initially
python3 src/setup.py --add-backup
```

### Clean Up Staging
```bash
# Remove staging directory
rm -rf /tmp/usb_sync_staging
```

### Database Maintenance
```bash
# View database size
ls -lh usb_backup.db

# Backup database
cp usb_backup.db usb_backup.db.backup

# Remove old logs
rm -rf logs/*.log
```

---

## Troubleshooting

### Check Installation
```bash
# Verify tools installed
which find rsync python3

# Check versions
python3 --version
rsync --version

# Test scripts
python3 src/setup.py --help
```

### Fix Permissions
```bash
# Make scripts executable
chmod +x src/*.py

# Fix database permissions
chmod 644 usb_backup.db

# Fix config permissions
chmod 644 config.json
```

### Database Issues
```bash
# Remove lock file
rm usb_backup.db-journal

# Rebuild database (rescan both drives)
python3 src/scan.py --drive /mnt/usb --role master
python3 src/scan.py --drive /mnt/usb --role backup
```

### Mount Issues
```bash
# Check if already mounted
mount | grep usb

# Check filesystem
sudo fsck.ntfs /dev/sdb1

# Repair NTFS filesystem
sudo ntfsfix /dev/sdb1
```

---

## Useful One-Liners

### Quick Status
```bash
# Files on master
sqlite3 usb_backup.db "SELECT COUNT(*) FROM files WHERE drive_id=(SELECT drive_id FROM drives WHERE drive_role='master') AND is_deleted=0"

# Total size on backup
sqlite3 usb_backup.db "SELECT SUM(size) FROM files WHERE drive_id=(SELECT drive_id FROM drives WHERE drive_role='backup') AND is_deleted=0"

# Recent syncs
sqlite3 usb_backup.db "SELECT timestamp, operation_type, status FROM sync_operations ORDER BY timestamp DESC LIMIT 10"
```

### Quick Disk Space Check
```bash
# Laptop free space
df -h / | awk 'NR==2 {print $4}'

# Drive free space
df -h /mnt/usb | awk 'NR==2 {print $4}'
```

### Count Files
```bash
# Files on mounted drive
find /mnt/usb -type f | wc -l

# Size of mounted drive
du -sh /mnt/usb
```

---

## Configuration Files

### config.json
```bash
# View config
cat config.json

# Edit config
nano config.json

# Reset config (will lose drive identification)
rm config.json
python3 src/setup.py --scan-drives
```

### View Sync Plan
```bash
# Latest plan
cat plans/sync_plan_latest.json

# Specific plan
cat plans/sync_plan_20241207_183000.json

# List all plans
ls -lh plans/
```

---

## Safety Commands

### Dry Run Everything
```bash
# Always test with --dry-run first
python3 src/sync.py --stage-deltas --drive /mnt/usb --dry-run
python3 src/sync.py --apply-staged --drive /mnt/usb --dry-run
```

### Backup Important Files
```bash
# Backup config
cp config.json config.json.backup

# Backup database
cp usb_backup.db usb_backup.db.backup

# Backup sync plan
cp plans/sync_plan_latest.json plans/sync_plan_$(date +%Y%m%d).json
```

---

## Environment Variables (Optional)

```bash
# Set default mount point
export USB_MOUNT_POINT=/mnt/usb

# Set staging directory
export USB_STAGING_DIR=/home/user/usb_staging

# Use in commands
python3 src/scan.py --drive $USB_MOUNT_POINT --role master
```

---

## Keyboard Shortcuts

### Cancel Running Command
- `Ctrl+C` - Stop current operation (safe, won't corrupt data)

### View Output
- `Shift+PgUp/PgDn` - Scroll terminal output

---

## Quick Reference Table

| Task | Command |
|------|---------|
| Setup | `python3 src/setup.py --scan-drives` |
| Scan | `python3 src/scan.py --drive /mnt/usb --role master` |
| Compare | `python3 src/compare.py` |
| Stage | `python3 src/sync.py --stage-deltas --drive /mnt/usb` |
| Apply | `python3 src/sync.py --apply-staged --drive /mnt/usb` |
| Direct Sync | `python3 src/sync.py --direct-sync --master-drive /mnt/master --backup-drive /mnt/backup` |
| Status | `python3 src/report.py --summary` |
| Verify | `python3 src/verify.py --role backup --drive /mnt/usb` |
| Identify | `python3 src/identify.py /mnt/usb` |

---

**Pro Tip:** Create bash aliases for common commands:

```bash
# Add to ~/.bashrc
alias usbmount='sudo mount -t ntfs-3g -o big_writes,noatime /dev/sdb1 /mnt/usb'
alias usbumount='sudo umount /mnt/usb'
alias usbscan='python3 ~/usbdrivesync/src/scan.py --drive /mnt/usb'
alias usbstatus='python3 ~/usbdrivesync/src/report.py --summary'
alias usbidentify='python3 ~/usbdrivesync/src/identify.py /mnt/usb'
```

---

*Cheat sheet version 1.0.0 - Print and keep handy!*
