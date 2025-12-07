#!/usr/bin/env python3
"""
Verify drive integrity - check metadata against actual files.
"""

import sys
import os
import json
import argparse

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

from drive_utils import get_device_uuid, verify_drive_uuid, format_size
from file_scanner import verify_file_exists, get_file_info
from database import Database


CONFIG_FILE = 'config.json'
DB_FILE = 'usb_backup.db'


def load_config():
    """Load configuration file"""
    if not os.path.exists(CONFIG_FILE):
        print(f"❌ Config file {CONFIG_FILE} not found")
        sys.exit(1)
    
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)


def verify_drive(mount_point: str, role: str):
    """Verify drive integrity"""
    print("=" * 60)
    print(f"Verify Drive - {role.upper()}")
    print("=" * 60)
    
    # Load config
    config = load_config()
    
    if role not in config:
        print(f"❌ {role} drive not configured")
        sys.exit(1)
    
    expected_uuid = config[role]['uuid']
    
    # Verify UUID
    print("\n🔐 Verifying drive identity...")
    if not verify_drive_uuid(mount_point, expected_uuid, role):
        sys.exit(1)
    
    # Open database
    db = Database(DB_FILE)
    db.connect()
    
    drive_info = db.get_drive(role)
    if not drive_info:
        print(f"\n❌ Drive {role} not found in database")
        db.close()
        sys.exit(1)
    
    drive_id = drive_info['drive_id']
    
    print(f"\n📊 Loading metadata from database...")
    db_files = db.get_all_files(drive_id)
    print(f"   {len(db_files):,} files in database")
    
    print(f"\n🔍 Verifying files on drive...")
    print("   (This may take several minutes)")
    
    missing_files = []
    mismatched_files = []
    verified_count = 0
    verified_size = 0
    
    for i, file_info in enumerate(db_files):
        filepath = file_info['filepath']
        expected_size = file_info['size']
        expected_mtime = file_info['mtime']
        
        # Progress
        if (i + 1) % 1000 == 0:
            print(f"   Progress: {i+1:,} / {len(db_files):,} files", end='\r')
        
        # Check if file exists
        if not verify_file_exists(mount_point, filepath):
            missing_files.append(filepath)
            continue
        
        # Get actual file info
        actual_info = get_file_info(mount_point, filepath)
        if actual_info is None:
            missing_files.append(filepath)
            continue
        
        actual_size, actual_mtime = actual_info
        
        # Check size match
        if actual_size != expected_size:
            mismatched_files.append({
                'path': filepath,
                'expected_size': expected_size,
                'actual_size': actual_size,
                'reason': 'size'
            })
            continue
        
        # Mtime can differ slightly, allow 1 second tolerance
        if abs(actual_mtime - expected_mtime) > 1.0:
            mismatched_files.append({
                'path': filepath,
                'expected_mtime': expected_mtime,
                'actual_mtime': actual_mtime,
                'reason': 'mtime'
            })
            continue
        
        verified_count += 1
        verified_size += actual_size
    
    print()  # Clear progress line
    
    db.close()
    
    # Display results
    print("\n" + "=" * 60)
    print("Verification Results")
    print("=" * 60)
    
    print(f"\n✅ Verified files: {verified_count:,}")
    print(f"   Total size: {format_size(verified_size)}")
    
    if missing_files:
        print(f"\n❌ Missing files: {len(missing_files):,}")
        print("   (Files in database but not on drive)")
        if len(missing_files) <= 10:
            for f in missing_files:
                print(f"   - {f}")
        else:
            for f in missing_files[:10]:
                print(f"   - {f}")
            print(f"   ... and {len(missing_files) - 10} more")
    else:
        print(f"\n✅ No missing files")
    
    if mismatched_files:
        print(f"\n⚠️  Mismatched files: {len(mismatched_files):,}")
        print("   (Files exist but size/mtime differs)")
        if len(mismatched_files) <= 10:
            for f in mismatched_files:
                print(f"   - {f['path']} ({f['reason']} mismatch)")
        else:
            for f in mismatched_files[:10]:
                print(f"   - {f['path']} ({f['reason']} mismatch)")
            print(f"   ... and {len(mismatched_files) - 10} more")
    else:
        print(f"\n✅ No mismatched files")
    
    # Overall status
    print("\n" + "=" * 60)
    
    if missing_files or mismatched_files:
        print("⚠️  VERIFICATION FAILED")
        print("\nRecommendations:")
        print("1. Run scan again: python3 src/scan.py --drive /mnt/usb --role " + role)
        print("2. If issues persist, files may be corrupted")
    else:
        print("✅ VERIFICATION PASSED")
        print("\nDrive integrity confirmed!")
    
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='Verify drive integrity'
    )
    parser.add_argument('--role', required=True, choices=['master', 'backup'],
                       help='Drive role to verify')
    parser.add_argument('--drive',
                       help='Mount point of the drive (will prompt if not provided)')
    
    args = parser.parse_args()
    
    if not args.drive:
        args.drive = input(f"Enter mount point for {args.role} drive (e.g., /mnt/usb): ").strip()
    
    if not args.drive:
        print("❌ Mount point required")
        sys.exit(1)
    
    verify_drive(args.drive, args.role)


if __name__ == '__main__':
    main()
