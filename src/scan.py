#!/usr/bin/env python3
"""
Scan USB drive and update metadata in database.
"""

import sys
import os
import json
import argparse
import time

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

from drive_utils import (
    get_device_uuid, verify_drive_uuid, verify_usb_speed,
    get_mount_point_device, format_size
)
from file_scanner import scan_drive_incremental, count_files
from database import Database


CONFIG_FILE = 'config.json'
DB_FILE = 'usb_backup.db'


def load_config():
    """Load configuration file"""
    if not os.path.exists(CONFIG_FILE):
        print(f"❌ Config file {CONFIG_FILE} not found")
        print("   Run: python3 src/setup.py --scan-drives")
        sys.exit(1)
    
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)


def scan_drive_command(mount_point: str, role: str):
    """Scan drive and update database"""
    print("=" * 60)
    print(f"USB Drive Scan - {role.upper()} Drive")
    print("=" * 60)
    
    # Load configuration
    config = load_config()
    
    if role not in config:
        print(f"❌ {role} drive not configured")
        print(f"   Run: python3 src/setup.py --scan-drives")
        sys.exit(1)
    
    expected_uuid = config[role]['uuid']
    expected_label = config[role].get('label', role.upper())
    
    # Verify mount point exists
    if not os.path.exists(mount_point):
        print(f"❌ Mount point does not exist: {mount_point}")
        sys.exit(1)
    
    if not os.path.ismount(mount_point):
        print(f"⚠️  WARNING: {mount_point} does not appear to be a mount point")
        response = input("Continue anyway? (yes/NO): ")
        if response.lower() != 'yes':
            sys.exit(1)
    
    # Get device path
    device_path = get_mount_point_device(mount_point)
    if device_path:
        device_name = os.path.basename(device_path)
        print(f"📀 Device: {device_path}")
    else:
        print(f"📀 Mount point: {mount_point}")
        device_name = None
    
    print()
    
    # Verify UUID
    print("🔐 Verifying drive identity...")
    if not verify_drive_uuid(mount_point, expected_uuid, role):
        sys.exit(1)
    
    # Verify USB speed
    if device_name:
        print("\n⚡ Checking USB connection speed...")
        min_speed = config.get('settings', {}).get('min_usb_speed_mbps', 5000)
        allow_override = config.get('settings', {}).get('allow_usb2_override', True)
        
        if not verify_usb_speed(device_name, min_speed, allow_override):
            sys.exit(1)
    
    print("\n" + "=" * 60)
    print("Starting scan...")
    print("=" * 60)
    
    # Count files first (optional, for progress)
    print("\n📊 Counting files (this may take a few minutes)...")
    exclude_hidden = config.get('settings', {}).get('exclude_hidden', True)
    
    try:
        total_files = count_files(mount_point, exclude_hidden)
        print(f"   Found {total_files:,} files to scan")
    except Exception as e:
        print(f"   Could not count files: {e}")
        total_files = None
    
    # Open database
    db = Database(DB_FILE)
    db.connect()
    
    # Get drive ID from database, or register if not found
    drive_info = db.get_drive(role)
    if not drive_info:
        print(f"📝 Registering {role} drive in database...")
        # Register drive with UUID as drive_id
        db.add_drive(
            drive_id=expected_uuid,
            role=role,
            serial=config[role].get('serial', 'unknown'),
            label=expected_label,
            size=None  # Will be updated during scan
        )
        drive_info = db.get_drive(role)
    
    drive_id = drive_info['drive_id']
    
    # Scan drive incrementally
    print(f"\n🔍 Scanning drive (this will take ~10 minutes for 2TB)...")
    print("   Using fast 'find' command...")
    
    batch_size = 10000
    total_scanned = 0
    total_size = 0
    all_files_set = set()
    
    start_time = time.time()
    
    try:
        for batch in scan_drive_incremental(mount_point, batch_size, exclude_hidden):
            # Add to database
            db.add_files_bulk(batch, drive_id)
            
            # Update statistics
            total_scanned += len(batch)
            total_size += sum(size for _, size, _ in batch)
            
            # Track all files for deletion detection
            all_files_set.update(filepath for filepath, _, _ in batch)
            
            # Progress update
            if total_files:
                progress = (total_scanned / total_files) * 100
                print(f"   Progress: {total_scanned:,} / {total_files:,} files ({progress:.1f}%) - {format_size(total_size)}", end='\r')
            else:
                print(f"   Scanned: {total_scanned:,} files - {format_size(total_size)}", end='\r')
        
        print()  # New line after progress
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Scan interrupted by user")
        db.close()
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error during scan: {e}")
        db.close()
        sys.exit(1)
    
    elapsed = time.time() - start_time
    
    print(f"\n✅ Scan complete!")
    print(f"   Files scanned: {total_scanned:,}")
    print(f"   Total size: {format_size(total_size)}")
    print(f"   Time taken: {elapsed/60:.1f} minutes")
    
    # Mark deleted files
    print(f"\n🗑️  Checking for deleted files...")
    deleted_count = db.mark_files_deleted(drive_id, all_files_set)
    
    if deleted_count > 0:
        print(f"   Marked {deleted_count:,} files as deleted")
    else:
        print(f"   No deleted files")
    
    # Update drive scan timestamp and size
    db.update_drive_scan_time(drive_id)
    
    # Update drive size in database
    cursor = db.conn.cursor()
    cursor.execute("UPDATE drives SET drive_size = ? WHERE drive_id = ?", 
                   (total_size, drive_id))
    db.conn.commit()
    
    # Get statistics
    stats = db.get_file_stats(drive_id)
    
    print("\n" + "=" * 60)
    print(f"Drive Statistics - {role.upper()}")
    print("=" * 60)
    print(f"Total files on this drive: {stats.get('total_files', 0):,}")
    print(f"Active files: {stats.get('total_files', 0) - stats.get('deleted_files', 0):,}")
    print(f"Deleted files: {stats.get('deleted_files', 0):,}")
    print(f"Total size: {format_size(stats.get('total_size', 0))}")
    
    db.close()
    
    print("\n✅ Scan complete and database updated!")
    print(f"   Drive: {expected_label}")
    print(f"   Role: {role.upper()}")


def main():
    parser = argparse.ArgumentParser(
        description='Scan USB drive and update metadata database'
    )
    parser.add_argument('--drive', required=True,
                       help='Mount point of the drive (e.g., /mnt/usb)')
    parser.add_argument('--role', required=True, choices=['master', 'backup'],
                       help='Drive role: master or backup')
    
    args = parser.parse_args()
    
    scan_drive_command(args.drive, args.role)


if __name__ == '__main__':
    main()
