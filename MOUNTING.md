# Mounting USB Drives - Best Practices

## ⚠️ Critical: Always Use Proper Permissions

**The #1 cause of sync failures is incorrect mount permissions.**

## Correct Mount Command

```bash
sudo mount -t ntfs-3g -o uid=$(id -u),gid=$(id -g) /dev/sdb1 /mnt/usb
```

### What this does:
- `-t ntfs-3g`: Use NTFS driver
- `-o uid=$(id -u)`: Set your user as the owner
- `-o gid=$(id -g)`: Set your group as the owner
- `/dev/sdb1`: The USB drive partition
- `/mnt/usb`: Mount point

## Why This Matters

When syncing, the script:
1. Copies changed files to `/tmp/usb_staging` (owned by your user)
2. Copies from staging to the USB drive
3. **If the USB drive is mounted as root-only, step 2 fails!**

## Step-by-Step Mounting

### 1. Identify Your Drive

```bash
# List all drives
lsblk

# Or with filesystem info
lsblk -f

# Check partition details
sudo fdisk -l
```

Example output:
```
NAME   SIZE TYPE FSTYPE LABEL
sdb   14.8G disk
└─sdb1 14.8G part vfat   USB DISK
```

Your drive is `/dev/sdb1` (or similar).

### 2. Create Mount Point

```bash
sudo mkdir -p /mnt/usb
```

You only need to do this once.

### 3. Mount with Permissions

```bash
sudo mount -t ntfs-3g -o uid=$(id -u),gid=$(id -g) /dev/sdb1 /mnt/usb
```

**For FAT32 drives** (like your test drive):
```bash
sudo mount -t vfat -o uid=$(id -u),gid=$(id -g) /dev/sdb1 /mnt/usb
```

### 4. Verify Mount

```bash
# Check it's mounted
mount | grep /mnt/usb

# Test write permission
touch /mnt/usb/test.txt && rm /mnt/usb/test.txt

# If successful, you're ready to sync!
```

## Common Issues

### "Permission denied" when writing

**Problem:** Drive mounted without user permissions.

**Solution:**
```bash
# Unmount
sudo umount /mnt/usb

# Remount with permissions
sudo mount -t ntfs-3g -o uid=$(id -u),gid=$(id -g) /dev/sdb1 /mnt/usb
```

### "Device busy" when unmounting

**Problem:** Files still open or you're in the directory.

**Solution:**
```bash
# Change directory
cd ~

# Force unmount if needed
sudo umount -l /mnt/usb
```

### Different device names each time

**Problem:** USB drive gets different names (sdb, sdc, etc.)

**Solution:** Always check with `lsblk` before mounting. The scripts verify by UUID, so the device name doesn't matter.

## Unmounting Safely

```bash
# Always unmount before unplugging
sudo umount /mnt/usb

# Verify it's unmounted
mount | grep /mnt/usb  # Should show nothing
```

**Never unplug without unmounting!** You risk data corruption.

## Auto-mount with /etc/fstab (Optional)

If you want the drive to auto-mount on plugin:

```bash
# Get the drive UUID
sudo blkid /dev/sdb1

# Example output:
# /dev/sdb1: UUID="2DB2-F9FE" TYPE="vfat" LABEL="USB DISK"

# Add to /etc/fstab
sudo nano /etc/fstab

# Add this line (adjust UUID):
UUID=2DB2-F9FE /mnt/usb ntfs-3g uid=1000,gid=1000,dmask=022,fmask=133 0 0
```

**Note:** Replace `1000` with your actual UID/GID from `id -u` and `id -g`.

## Quick Reference

```bash
# Mount NTFS with permissions
sudo mount -t ntfs-3g -o uid=$(id -u),gid=$(id -g) /dev/sdb1 /mnt/usb

# Mount FAT32 with permissions
sudo mount -t vfat -o uid=$(id -u),gid=$(id -g) /dev/sdb1 /mnt/usb

# Check mount
mount | grep usb

# Test write
touch /mnt/usb/test.txt && rm /mnt/usb/test.txt

# Unmount
sudo umount /mnt/usb
```

## Summary

✅ **Always** include `-o uid=$(id -u),gid=$(id -g)`  
✅ **Always** unmount before unplugging  
✅ **Always** verify with `lsblk` first  
✅ **Test** write permissions before syncing  

❌ **Never** mount without user permissions  
❌ **Never** unplug without unmounting  
❌ **Never** assume the device name stays the same
