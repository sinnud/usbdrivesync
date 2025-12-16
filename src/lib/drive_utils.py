"""
Drive utilities for USB drive sync tool.
Handles drive detection, UUID verification, and USB speed checks.
"""

import subprocess
import os
import re
from typing import Optional, Dict, List


def get_block_devices() -> List[Dict]:
    """Get list of all block devices with details"""
    try:
        result = subprocess.run(
            ['lsblk', '-o', 'NAME,SIZE,FSTYPE,UUID,LABEL,MOUNTPOINT,RM,TRAN', '-J'],
            capture_output=True, text=True, check=True
        )
        import json
        data = json.loads(result.stdout)
        return data.get('blockdevices', [])
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return []


def get_device_uuid(device_path: str) -> Optional[str]:
    """Get UUID for a device or mount point"""
    # If it's a mount point, find the device first
    if os.path.ismount(device_path):
        try:
            result = subprocess.run(
                ['findmnt', '-n', '-o', 'SOURCE', device_path],
                capture_output=True, text=True, check=True
            )
            device_path = result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
    
    # Get UUID using blkid
    try:
        result = subprocess.run(
            ['sudo', 'blkid', '-s', 'UUID', '-o', 'value', device_path],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def get_device_label(device_path: str) -> Optional[str]:
    """Get label for a device"""
    try:
        result = subprocess.run(
            ['sudo', 'blkid', '-s', 'LABEL', '-o', 'value', device_path],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def get_device_serial(device_name: str) -> Optional[str]:
    """Get hardware serial number for a device (e.g., 'sdb')"""
    try:
        # Try udevadm first
        result = subprocess.run(
            ['udevadm', 'info', '--query=property', f'--name=/dev/{device_name}'],
            capture_output=True, text=True, check=True
        )
        for line in result.stdout.split('\n'):
            if line.startswith('ID_SERIAL='):
                return line.split('=', 1)[1].strip()
    except subprocess.CalledProcessError:
        pass
    
    # Try lsblk as fallback
    try:
        result = subprocess.run(
            ['lsblk', '-o', 'NAME,SERIAL', '-n'],
            capture_output=True, text=True, check=True
        )
        for line in result.stdout.split('\n'):
            if device_name in line:
                parts = line.split()
                if len(parts) >= 2:
                    return parts[1]
    except subprocess.CalledProcessError:
        pass
    
    return None


def get_device_size(device_path: str) -> Optional[int]:
    """Get device size in bytes"""
    try:
        result = subprocess.run(
            ['blockdev', '--getsize64', device_path],
            capture_output=True, text=True, check=True
        )
        return int(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        return None


def get_usb_speed(device_name: str) -> Optional[int]:
    """
    Get USB speed for a block device in Mbps.
    Returns: 5000 (USB 3.0), 480 (USB 2.0), 12 (USB 1.1), or None
    """
    # Remove partition number if present (sdb1 -> sdb)
    device_name = re.sub(r'\d+$', '', device_name)
    
    # Try sysfs first
    sysfs_path = f"/sys/block/{device_name}/device/../speed"
    if os.path.exists(sysfs_path):
        try:
            with open(sysfs_path, 'r') as f:
                return int(f.read().strip())
        except (IOError, ValueError):
            pass
    
    # Fallback: parse lsusb -t
    try:
        result = subprocess.run(['lsusb', '-t'], 
                              capture_output=True, text=True, check=True)
        
        # Look for speed indicators: 5000M (USB 3.0), 480M (USB 2.0), 12M (USB 1.1)
        for line in result.stdout.split('\n'):
            if 'Mass Storage' in line or 'usb-storage' in line:
                if '5000M' in line:
                    return 5000
                elif '480M' in line:
                    return 480
                elif '12M' in line:
                    return 12
    except subprocess.CalledProcessError:
        pass
    
    return None


def get_usb_version(speed_mbps: int) -> str:
    """Convert USB speed to human-readable version"""
    if speed_mbps >= 5000:
        return "3.0 or higher"
    elif speed_mbps >= 480:
        return "2.0"
    elif speed_mbps >= 12:
        return "1.1"
    else:
        return "Unknown"


def estimate_transfer_time(speed_mbps: int, size_gb: int) -> float:
    """Estimate transfer time in hours"""
    if speed_mbps <= 0:
        return 0.0
    
    speed_mbs = speed_mbps / 8  # Convert Mbps to MB/s
    real_speed = speed_mbs * 0.8  # 80% efficiency
    
    if real_speed <= 0:
        return 0.0
    
    seconds = (size_gb * 1024) / real_speed
    return round(seconds / 3600, 1)


def verify_usb_speed(device_name: str, min_speed: int = 5000, 
                     allow_override: bool = True) -> bool:
    """
    Verify device is on USB 3.0 or faster.
    Returns True if speed check passes or user overrides.
    """
    speed = get_usb_speed(device_name)
    
    if speed is None:
        print("⚠️  WARNING: Cannot determine USB speed")
        print("   Device detection may have failed")
        return True  # Allow to proceed if we can't detect
    
    if speed < min_speed:
        print(f"\n❌ ERROR: Device on USB {get_usb_version(speed)}")
        print(f"   Current speed: {speed} Mbps")
        print(f"   Required: {min_speed} Mbps (USB 3.0)")
        print(f"   Expected transfer time (100GB): {estimate_transfer_time(speed, 100)} hours")
        print(f"   vs USB 3.0: {estimate_transfer_time(5000, 100)} hours")
        print(f"\n   ⚡ Please plug into the BLUE USB 3.0 port!\n")
        
        if allow_override:
            response = input("Continue anyway? (yes/NO): ").strip().lower()
            return response == 'yes'
        return False
    
    print(f"✅ USB speed OK: {speed} Mbps (USB {get_usb_version(speed)})")
    return True


def verify_drive_uuid(mount_point: str, expected_uuid: str, 
                     expected_role: str) -> bool:
    """
    Verify that mounted drive has expected UUID.
    Returns True if verification passes.
    """
    actual_uuid = get_device_uuid(mount_point)
    
    if actual_uuid is None:
        print(f"❌ ERROR: Cannot read UUID from {mount_point}")
        print("   Drive may not be properly mounted")
        return False
    
    if actual_uuid != expected_uuid:
        print(f"\n❌ ERROR: Wrong drive detected!")
        print(f"   Expected: {expected_role.upper()} drive")
        print(f"   Expected UUID: {expected_uuid}")
        print(f"   Found UUID: {actual_uuid}")
        print(f"\n   Please check you plugged in the correct drive.\n")
        return False
    
    print(f"✅ Verified: {expected_role.upper()} drive (UUID: {actual_uuid[:16]}...)")
    return True


def get_mount_point_device(mount_point: str) -> Optional[str]:
    """Get the device path for a mount point (e.g., /dev/sdb1)"""
    try:
        result = subprocess.run(
            ['findmnt', '-n', '-o', 'SOURCE', mount_point],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def is_mounted(device_path: str) -> bool:
    """Check if device is mounted"""
    try:
        result = subprocess.run(
            ['findmnt', '-n', device_path],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except subprocess.CalledProcessError:
        return False


def get_usb_storage_devices() -> List[Dict]:
    """Get list of all USB storage devices (mounted or not) with speed info"""
    devices = get_block_devices()
    usb_devices = []
    
    def is_usb_or_removable(dev) -> bool:
        """Check if device is USB or removable (not internal SATA/NVMe)"""
        tran = dev.get('tran', '').lower()
        if tran == 'usb':
            return True
        if dev.get('rm', False):
            return True
        if tran in ['sata', 'nvme', 'ata', 'scsi']:
            return False
        return False
    
    def extract_usb(dev, parent_dev=None, parent_name='', level=0):
        if isinstance(dev, dict):
            name = dev.get('name', '')
            full_name = f"{parent_name}{name}" if parent_name else name
            check_dev = parent_dev if parent_dev else dev
            
            # Add device if it's USB (parent level) or partition of USB device
            if level == 0 and is_usb_or_removable(dev):
                # Get USB speed for this device
                speed = get_usb_speed(full_name)
                
                # This is a USB device
                usb_devices.append({
                    'name': full_name,
                    'size': dev.get('size', ''),
                    'fstype': dev.get('fstype', ''),
                    'uuid': dev.get('uuid', ''),
                    'label': dev.get('label', ''),
                    'mountpoint': dev.get('mountpoint', ''),
                    'tran': dev.get('tran', ''),
                    'rm': dev.get('rm', False),
                    'speed': speed,
                    'usb_version': get_usb_version(speed) if speed else 'Unknown',
                    'children': []
                })
                # Check children (partitions)
                children = dev.get('children', [])
                for child in children:
                    child_info = {
                        'name': child.get('name', ''),
                        'size': child.get('size', ''),
                        'fstype': child.get('fstype', ''),
                        'uuid': child.get('uuid', ''),
                        'label': child.get('label', ''),
                        'mountpoint': child.get('mountpoint', '')
                    }
                    usb_devices[-1]['children'].append(child_info)
    
    for device in devices:
        extract_usb(device, level=0)
    
    return usb_devices


def get_ntfs_drives() -> List[Dict]:
    """Get list of NTFS/exFAT formatted USB/removable drives (excludes internal drives)"""
    devices = get_block_devices()
    ntfs_drives = []
    
    def is_usb_or_removable(dev) -> bool:
        """Check if device is USB or removable (not internal SATA/NVMe)"""
        # Check transport type - USB drives have tran='usb'
        tran = dev.get('tran', '').lower()
        if tran == 'usb':
            return True
        
        # Check removable flag - USB drives typically have rm=True
        if dev.get('rm', False):
            return True
        
        # Exclude internal drives (sata, nvme, etc.)
        if tran in ['sata', 'nvme', 'ata', 'scsi']:
            return False
        
        return False
    
    def extract_ntfs(dev, parent_dev=None, parent_name=''):
        if isinstance(dev, dict):
            name = dev.get('name', '')
            full_name = f"{parent_name}{name}" if parent_name else name
            
            # Use parent device info if this is a partition
            check_dev = parent_dev if parent_dev else dev
            
            fstype = dev.get('fstype', '').lower()
            if fstype in ['ntfs', 'exfat'] and is_usb_or_removable(check_dev):
                ntfs_drives.append({
                    'name': full_name,
                    'size': dev.get('size', ''),
                    'uuid': dev.get('uuid', ''),
                    'label': dev.get('label', ''),
                    'mountpoint': dev.get('mountpoint', ''),
                    'fstype': fstype
                })
            
            # Check children (partitions inherit parent device properties)
            children = dev.get('children', [])
            for child in children:
                extract_ntfs(child, dev, full_name)
    
    for device in devices:
        extract_ntfs(device)
    
    return ntfs_drives


def format_size(bytes_size: int) -> str:
    """Format bytes to human-readable size"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def check_drive_space(mount_point: str, required_bytes: int) -> bool:
    """Check if drive has enough free space"""
    try:
        stat = os.statvfs(mount_point)
        free_bytes = stat.f_bavail * stat.f_frsize
        return free_bytes >= required_bytes
    except OSError:
        return False


def get_drive_free_space(mount_point: str) -> int:
    """Get free space in bytes"""
    try:
        stat = os.statvfs(mount_point)
        return stat.f_bavail * stat.f_frsize
    except OSError:
        return 0
