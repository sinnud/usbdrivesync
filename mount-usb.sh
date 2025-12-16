#!/bin/bash
# Helper script to mount USB drives with proper permissions

set -e

DEVICE="${1:-}"
MOUNT_POINT="${2:-/mnt/usb}"

if [ -z "$DEVICE" ]; then
    echo "Usage: $0 <device> [mount_point]"
    echo ""
    echo "Example: $0 /dev/sdb1"
    echo "         $0 /dev/sdb1 /mnt/usb"
    echo ""
    echo "Available devices:"
    lsblk -f | grep -E "sd[b-z][0-9]|ntfs|exfat|vfat"
    exit 1
fi

# Check if device exists
if [ ! -b "$DEVICE" ]; then
    echo "❌ Error: Device $DEVICE not found"
    exit 1
fi

# Get filesystem type
FSTYPE=$(lsblk -no FSTYPE "$DEVICE")

if [ -z "$FSTYPE" ]; then
    echo "❌ Error: Cannot determine filesystem type for $DEVICE"
    exit 1
fi

echo "📀 Device: $DEVICE"
echo "💾 Filesystem: $FSTYPE"
echo "📂 Mount point: $MOUNT_POINT"
echo ""

# Create mount point if it doesn't exist
if [ ! -d "$MOUNT_POINT" ]; then
    echo "Creating mount point $MOUNT_POINT..."
    sudo mkdir -p "$MOUNT_POINT"
fi

# Check if already mounted
if mountpoint -q "$MOUNT_POINT" 2>/dev/null; then
    echo "⚠️  $MOUNT_POINT is already mounted"
    mount | grep "$MOUNT_POINT"
    echo ""
    read -p "Unmount first? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo umount "$MOUNT_POINT"
        echo "✅ Unmounted"
    else
        exit 0
    fi
fi

# Mount with appropriate options
UID=$(id -u)
GID=$(id -g)

echo "Mounting with uid=$UID, gid=$GID..."

case "$FSTYPE" in
    ntfs)
        sudo mount -t ntfs-3g -o "uid=$UID,gid=$GID" "$DEVICE" "$MOUNT_POINT"
        ;;
    exfat)
        sudo mount -t exfat -o "uid=$UID,gid=$GID" "$DEVICE" "$MOUNT_POINT"
        ;;
    vfat)
        sudo mount -t vfat -o "uid=$UID,gid=$GID" "$DEVICE" "$MOUNT_POINT"
        ;;
    *)
        # Try auto-detect
        sudo mount -o "uid=$UID,gid=$GID" "$DEVICE" "$MOUNT_POINT"
        ;;
esac

echo ""
echo "✅ Successfully mounted!"
echo ""

# Show mount info
mount | grep "$MOUNT_POINT"

# Test write permission
if touch "$MOUNT_POINT/.test_write" 2>/dev/null; then
    rm "$MOUNT_POINT/.test_write"
    echo ""
    echo "✅ Write permission verified"
else
    echo ""
    echo "❌ Warning: Cannot write to mount point"
    echo "   You may need to remount with different options"
fi

echo ""
echo "📊 Drive info:"
df -h "$MOUNT_POINT"
