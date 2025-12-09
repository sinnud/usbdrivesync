#!/usr/bin/env python3
"""
Setup script for USB drive sync tool.
Identifies drives and creates initial configuration.
"""

import sys
import os
import json
import argparse

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

from drive_utils import (
    get_ntfs_drives, get_usb_storage_devices, get_device_uuid, get_device_serial,
    get_device_label, get_device_size, format_size
)
from database import Database


CONFIG_FILE = 'config.json'
DB_FILE = 'usb_backup.db'


def scan_available_drives():
    """Scan and display available NTFS drives"""
    print("\n🔍 Scanning for NTFS drives...")
    drives = get_ntfs_drives()
    
    if not drives:
        print("❌ No mounted NTFS drives found")
        
        # Check if any USB storage devices are connected
        usb_devices = get_usb_storage_devices()
        if usb_devices:
            print("\n⚠️  USB storage device(s) detected but not ready:")
            for usb in usb_devices:
                speed_info = ""
                if usb.get('speed'):
                    speed = usb['speed']
                    version = usb.get('usb_version', 'Unknown')
                    if speed < 5000:
                        speed_info = f" ⚠️  USB {version} ({speed} Mbps) - TOO SLOW!"
                    else:
                        speed_info = f" ✅ USB {version} ({speed} Mbps)"
                else:
                    speed_info = " ⚠️  USB speed unknown"
                
                print(f"\n   Device: /dev/{usb['name']} ({usb['size']}){speed_info}")
                
                if usb['children']:
                    for child in usb['children']:
                        fstype = child['fstype'] or 'unknown'
                        mounted = child['mountpoint'] or 'NOT MOUNTED'
                        print(f"   └─ /dev/{child['name']}: {fstype}, {mounted}")
                else:
                    print(f"   └─ No partitions found (may need partitioning)")
            
            # Check if any device is too slow
            slow_devices = [u for u in usb_devices if u.get('speed') and u['speed'] < 5000]
            if slow_devices:
                print("\n   ⚡ WARNING: USB drive is on USB 2.0 port!")
                print("   Please plug into a BLUE USB 3.0 port for better performance.")
                print("   Expected transfer time (100GB):")
                for u in slow_devices:
                    from drive_utils import estimate_transfer_time
                    print(f"     USB 2.0: ~{estimate_transfer_time(u['speed'], 100)} hours")
                    print(f"     USB 3.0: ~{estimate_transfer_time(5000, 100)} hours")
            
            print("\n   Please ensure:")
            print("   1. Drive is formatted as NTFS")
            print("   2. Drive is mounted (mount it with: sudo mount /dev/sdX1 /mnt/usb)")
        else:
            print("\n   Please ensure:")
            print("   1. USB drive is connected")
            print("   2. Drive is formatted as NTFS")
            print("   3. Drive is mounted (or mount it manually)")
        
        return []
    
    print(f"\n✅ Found {len(drives)} NTFS drive(s):\n")
    
    for i, drive in enumerate(drives, 1):
        print(f"{i}. Device: /dev/{drive['name']}")
        print(f"   Size: {drive['size']}")
        print(f"   Label: {drive['label'] or '(no label)'}")
        print(f"   UUID: {drive['uuid']}")
        print(f"   Mount: {drive['mountpoint'] or '(not mounted)'}")
        print()
    
    return drives


def identify_drive(drive_info):
    """Get detailed information about a drive"""
    device_path = f"/dev/{drive_info['name']}"
    uuid = drive_info['uuid'] or get_device_uuid(device_path)
    
    # Try to get serial (requires root, might fail)
    device_name = drive_info['name'].rstrip('0123456789')  # Remove partition number
    serial = get_device_serial(device_name)
    
    label = drive_info['label'] or get_device_label(device_path)
    
    # Get size
    try:
        size = get_device_size(device_path)
    except:
        size = None
    
    return {
        'uuid': uuid,
        'serial': serial,
        'label': label,
        'size': size,
        'device': device_path
    }


def interactive_setup():
    """Interactive setup to identify master and backup drives"""
    print("=" * 60)
    print("USB Drive Sync Tool - Initial Setup")
    print("=" * 60)
    
    drives = scan_available_drives()
    
    if len(drives) < 1:
        print("❌ Need at least 1 NTFS drive to continue")
        return False
    
    print("\nWe need to identify your MASTER and BACKUP drives.")
    print("This is done by recording their unique UUIDs.\n")
    
    if len(drives) == 1:
        print("Only 1 drive found. Let's identify it:\n")
    else:
        print(f"{len(drives)} drives found. We'll identify them one at a time.\n")
    
    config = {}
    
    # Identify Master
    print("=" * 60)
    print("MASTER DRIVE (source of truth)")
    print("=" * 60)
    
    if len(drives) == 1:
        selection = 1
    else:
        while True:
            try:
                selection = int(input(f"Enter number for MASTER drive (1-{len(drives)}): "))
                if 1 <= selection <= len(drives):
                    break
                print(f"Please enter a number between 1 and {len(drives)}")
            except ValueError:
                print("Please enter a valid number")
    
    master_drive = drives[selection - 1]
    master_info = identify_drive(master_drive)
    
    print(f"\n✅ Master drive selected:")
    print(f"   UUID: {master_info['uuid']}")
    print(f"   Serial: {master_info['serial'] or '(not available)'}")
    print(f"   Label: {master_info['label'] or '(no label)'}")
    if master_info['size']:
        print(f"   Size: {format_size(master_info['size'])}")
    
    # Optionally set a label
    label = input(f"\nSet a friendly label (or press Enter to keep '{master_info['label']}'): ").strip()
    if label:
        master_info['label'] = label
    
    config['master'] = {
        'uuid': master_info['uuid'],
        'serial': master_info['serial'],
        'label': master_info['label'] or 'MASTER_DRIVE',
        'size': master_info['size']
    }
    
    # Identify Backup
    print("\n" + "=" * 60)
    print("BACKUP DRIVE (versioned backup)")
    print("=" * 60)
    
    if len(drives) == 1:
        print("\n⚠️  Only one drive connected.")
        print("   To set up BACKUP drive:")
        print("   1. Disconnect MASTER drive")
        print("   2. Connect BACKUP drive")
        print("   3. Run this setup again with --add-backup flag\n")
        
        response = input("Continue with only MASTER drive configured? (yes/NO): ")
        if response.lower() != 'yes':
            print("Setup cancelled.")
            return False
    else:
        remaining_drives = [d for i, d in enumerate(drives) if i != selection - 1]
        
        if len(remaining_drives) == 1:
            selection = 1
            backup_drive = remaining_drives[0]
        else:
            print("\nAvailable drives for BACKUP:")
            for i, drive in enumerate(remaining_drives, 1):
                print(f"{i}. /dev/{drive['name']} - {drive['size']} - {drive['label'] or '(no label)'}")
            
            while True:
                try:
                    selection = int(input(f"\nEnter number for BACKUP drive (1-{len(remaining_drives)}): "))
                    if 1 <= selection <= len(remaining_drives):
                        break
                    print(f"Please enter a number between 1 and {len(remaining_drives)}")
                except ValueError:
                    print("Please enter a valid number")
            
            backup_drive = remaining_drives[selection - 1]
        
        backup_info = identify_drive(backup_drive)
        
        print(f"\n✅ Backup drive selected:")
        print(f"   UUID: {backup_info['uuid']}")
        print(f"   Serial: {backup_info['serial'] or '(not available)'}")
        print(f"   Label: {backup_info['label'] or '(no label)'}")
        if backup_info['size']:
            print(f"   Size: {format_size(backup_info['size'])}")
        
        label = input(f"\nSet a friendly label (or press Enter to keep '{backup_info['label']}'): ").strip()
        if label:
            backup_info['label'] = label
        
        config['backup'] = {
            'uuid': backup_info['uuid'],
            'serial': backup_info['serial'],
            'label': backup_info['label'] or 'BACKUP_DRIVE',
            'size': backup_info['size']
        }
    
    # Settings
    config['settings'] = {
        'min_usb_speed_mbps': 5000,
        'warn_on_usb2': True,
        'allow_usb2_override': True,
        'staging_dir': '/tmp/usb_sync_staging',
        'exclude_hidden': True
    }
    
    # Save configuration
    print("\n" + "=" * 60)
    print("Saving configuration...")
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Configuration saved to {CONFIG_FILE}")
    
    # Initialize database
    print(f"\nInitializing database {DB_FILE}...")
    db = Database(DB_FILE)
    db.connect()
    
    # Add drives to database
    if 'master' in config:
        db.add_drive(
            drive_id=config['master']['uuid'],
            role='master',
            serial=config['master']['serial'],
            label=config['master']['label'],
            size=config['master']['size']
        )
        print("✅ Master drive added to database")
    
    if 'backup' in config:
        db.add_drive(
            drive_id=config['backup']['uuid'],
            role='backup',
            serial=config['backup']['serial'],
            label=config['backup']['label'],
            size=config['backup']['size']
        )
        print("✅ Backup drive added to database")
    
    db.close()
    
    print("\n" + "=" * 60)
    print("✅ Setup complete!")
    print("=" * 60)
    
    print("\nNext steps:")
    print("1. Perform initial rsync on Windows desktop (see WINDOWS_INITIAL_SYNC.md)")
    print("2. After initial rsync, return to Debian laptop")
    print("3. Run: python3 src/scan.py --drive /mnt/usb --role master")
    print("4. Run: python3 src/scan.py --drive /mnt/usb --role backup")
    print("5. You're ready to use the sync tools!")
    
    return True


def add_backup_drive():
    """Add backup drive to existing configuration"""
    if not os.path.exists(CONFIG_FILE):
        print(f"❌ Config file {CONFIG_FILE} not found")
        print("   Run setup without --add-backup first")
        return False
    
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    
    if 'backup' in config:
        print("⚠️  Backup drive already configured")
        response = input("Replace existing backup configuration? (yes/NO): ")
        if response.lower() != 'yes':
            return False
    
    drives = scan_available_drives()
    
    if not drives:
        return False
    
    print("Select BACKUP drive:")
    for i, drive in enumerate(drives, 1):
        print(f"{i}. /dev/{drive['name']} - {drive['size']}")
    
    while True:
        try:
            selection = int(input(f"\nEnter number (1-{len(drives)}): "))
            if 1 <= selection <= len(drives):
                break
        except ValueError:
            pass
        print(f"Please enter a number between 1 and {len(drives)}")
    
    backup_drive = drives[selection - 1]
    backup_info = identify_drive(backup_drive)
    
    print(f"\n✅ Backup drive: UUID {backup_info['uuid']}")
    
    config['backup'] = {
        'uuid': backup_info['uuid'],
        'serial': backup_info['serial'],
        'label': backup_info['label'] or 'BACKUP_DRIVE',
        'size': backup_info['size']
    }
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Configuration updated")
    
    # Add to database
    db = Database(DB_FILE)
    db.connect()
    db.add_drive(
        drive_id=config['backup']['uuid'],
        role='backup',
        serial=config['backup']['serial'],
        label=config['backup']['label'],
        size=config['backup']['size']
    )
    db.close()
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Setup USB drive sync tool - identify drives'
    )
    parser.add_argument('--scan-drives', action='store_true',
                       help='Scan and list available drives')
    parser.add_argument('--add-backup', action='store_true',
                       help='Add backup drive to existing configuration')
    
    args = parser.parse_args()
    
    if args.scan_drives or len(sys.argv) == 1:
        interactive_setup()
    elif args.add_backup:
        add_backup_drive()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
