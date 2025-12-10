#!/usr/bin/env python3
"""
Sync executor - Stage deltas and apply to backup.
"""

import sys
import os
import json
import argparse
import shutil

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

from drive_utils import (
    get_device_uuid, verify_drive_uuid, verify_usb_speed,
    get_mount_point_device, format_size, get_drive_free_space
)
from rsync_wrapper import rsync_copy
from versioning import version_file
from database import Database


CONFIG_FILE = 'config.json'
DB_FILE = 'usb_backup.db'
PLANS_DIR = 'plans'


def load_config():
    """Load configuration file"""
    if not os.path.exists(CONFIG_FILE):
        print(f"❌ Config file {CONFIG_FILE} not found")
        sys.exit(1)
    
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)


def load_sync_plan(plan_path: str = None):
    """Load sync plan"""
    if plan_path is None:
        plan_path = os.path.join(PLANS_DIR, 'sync_plan_latest.json')
    
    if not os.path.exists(plan_path):
        print(f"❌ Sync plan not found: {plan_path}")
        print("   Run: python3 src/compare.py")
        sys.exit(1)
    
    with open(plan_path, 'r') as f:
        return json.load(f)


def stage_deltas(mount_point: str, plan_path: str = None, dry_run: bool = False):
    """Stage delta files from master to laptop"""
    print("=" * 60)
    print("Stage Deltas - Copy Changes to Laptop")
    print("=" * 60)
    
    # Load config and plan
    config = load_config()
    plan = load_sync_plan(plan_path)
    
    # Verify this is master drive
    expected_uuid = config['master']['uuid']
    
    print("\n🔐 Verifying MASTER drive...")
    if not verify_drive_uuid(mount_point, expected_uuid, 'master'):
        sys.exit(1)
    
    # Verify USB speed
    device_path = get_mount_point_device(mount_point)
    if device_path:
        device_name = os.path.basename(device_path)
        print("\n⚡ Checking USB speed...")
        min_speed = config.get('settings', {}).get('min_usb_speed_mbps', 5000)
        if not verify_usb_speed(device_name, min_speed, True):
            sys.exit(1)
    
    # Get staging directory
    staging_dir = config.get('settings', {}).get('staging_dir', '/tmp/usb_sync_staging')
    
    print(f"\n📦 Sync Plan:")
    print(f"   New files: {plan['new_count']:,}")
    print(f"   Modified files: {plan['modified_count']:,}")
    print(f"   Total size: {format_size(plan['total_size_bytes'])}")
    
    # Check laptop space
    staging_parent = os.path.dirname(staging_dir)
    if not os.path.exists(staging_parent):
        staging_parent = '/'
    
    free_space = get_drive_free_space(staging_parent)
    print(f"\n💾 Laptop free space: {format_size(free_space)}")
    
    if free_space < plan['total_size_bytes']:
        print(f"❌ Insufficient space!")
        print(f"   Required: {format_size(plan['total_size_bytes'])}")
        print(f"   Available: {format_size(free_space)}")
        sys.exit(1)
    
    print(f"   ✅ Sufficient space available")
    
    # Create staging directory
    if os.path.exists(staging_dir) and not dry_run:
        print(f"\n⚠️  Staging directory exists: {staging_dir}")
        response = input("Clear and recreate? (yes/NO): ")
        if response.lower() == 'yes':
            shutil.rmtree(staging_dir)
        else:
            print("Aborted.")
            sys.exit(1)
    
    if not dry_run:
        os.makedirs(staging_dir, exist_ok=True)
        print(f"\n✅ Staging directory: {staging_dir}")
    
    # Prepare file list
    all_files = plan['new_files'] + plan['modified_files']
    
    if not all_files:
        print("\n✅ No files to sync!")
        return
    
    print(f"\n📋 Preparing to copy {len(all_files):,} files...")
    
    if dry_run:
        print("\n🔍 DRY RUN - No files will be copied")
    
    # Use rsync to copy files
    print("\n" + "=" * 60)
    print("Copying files with rsync...")
    print("=" * 60)
    
    result = rsync_copy(
        source=mount_point,
        dest=staging_dir,
        files=all_files,
        dry_run=dry_run,
        progress=True
    )
    
    if not result['success']:
        print(f"\n❌ Rsync failed!")
        print(f"   {result['stderr']}")
        sys.exit(1)
    
    if dry_run:
        print("\n✅ Dry run complete!")
        return
    
    print("\n✅ Files staged successfully!")
    print(f"   Location: {staging_dir}")
    print(f"   Files: {len(all_files):,}")
    print(f"   Size: {format_size(plan['total_size_bytes'])}")
    
    print("\n📌 Next steps:")
    print("   1. Disconnect MASTER drive")
    print("   2. Connect BACKUP drive")
    print("   3. Run: python3 src/sync.py --apply-staged --drive /media/usbhd")


def apply_staged(mount_point: str, plan_path: str = None, dry_run: bool = False):
    """Apply staged changes to backup drive"""
    print("=" * 60)
    print("Apply Staged - Update Backup Drive")
    print("=" * 60)
    
    # Load config and plan
    config = load_config()
    plan = load_sync_plan(plan_path)
    
    # Verify this is backup drive
    expected_uuid = config['backup']['uuid']
    
    print("\n🔐 Verifying BACKUP drive...")
    if not verify_drive_uuid(mount_point, expected_uuid, 'backup'):
        sys.exit(1)
    
    # Verify USB speed
    device_path = get_mount_point_device(mount_point)
    if device_path:
        device_name = os.path.basename(device_path)
        print("\n⚡ Checking USB speed...")
        min_speed = config.get('settings', {}).get('min_usb_speed_mbps', 5000)
        if not verify_usb_speed(device_name, min_speed, True):
            sys.exit(1)
    
    # Get staging directory
    staging_dir = config.get('settings', {}).get('staging_dir', '/tmp/usb_sync_staging')
    
    if not os.path.exists(staging_dir):
        print(f"\n❌ Staging directory not found: {staging_dir}")
        print("   Run: python3 src/sync.py --stage-deltas first")
        sys.exit(1)
    
    print(f"\n📦 Sync Plan:")
    print(f"   New files: {plan['new_count']:,}")
    print(f"   Modified files: {plan['modified_count']:,}")
    print(f"   Total size: {format_size(plan['total_size_bytes'])}")
    
    # Version modified files first
    if plan['modified_files']:
        print(f"\n📦 Versioning {len(plan['modified_files']):,} modified files...")
        
        if not dry_run:
            # Open database for logging
            db = Database(DB_FILE)
            db.connect()
            
            versioned_count = 0
            for filepath in plan['modified_files']:
                versioned = version_file(mount_point, filepath)
                if versioned:
                    versioned_count += 1
                    # Log to database
                    db.add_version_history(filepath, versioned, "modified")
            
            print(f"   ✅ Versioned {versioned_count} files")
            db.close()
        else:
            print("   (DRY RUN - would version these files)")
    
    # Apply changes with rsync
    print("\n" + "=" * 60)
    print("Applying changes with rsync...")
    print("=" * 60)
    
    result = rsync_copy(
        source=staging_dir,
        dest=mount_point,
        dry_run=dry_run,
        progress=True
    )
    
    if not result['success']:
        print(f"\n❌ Rsync failed!")
        print(f"   {result['stderr']}")
        sys.exit(1)
    
    if dry_run:
        print("\n✅ Dry run complete!")
        return
    
    # Log sync operations
    db = Database(DB_FILE)
    db.connect()
    
    for filepath in plan['new_files']:
        db.log_sync_operation('add', filepath, filepath, status='completed')
    
    for filepath in plan['modified_files']:
        db.log_sync_operation('modify', filepath, filepath, status='completed')
    
    db.close()
    
    print("\n✅ Sync complete!")
    print(f"   New files: {plan['new_count']:,}")
    print(f"   Modified files: {plan['modified_count']:,}")
    
    # Clean up staging
    print(f"\n🧹 Cleaning up staging directory...")
    try:
        shutil.rmtree(staging_dir)
        print(f"   ✅ Removed: {staging_dir}")
    except Exception as e:
        print(f"   ⚠️  Could not remove staging: {e}")
    
    print("\n✅ All done!")
    print("   Backup drive is now synchronized with master")
    print("\n   Optionally run: python3 src/verify.py --role backup")


def main():
    parser = argparse.ArgumentParser(
        description='Sync executor - stage deltas and apply to backup'
    )
    parser.add_argument('--stage-deltas', action='store_true',
                       help='Stage delta files from master to laptop')
    parser.add_argument('--apply-staged', action='store_true',
                       help='Apply staged changes to backup drive')
    parser.add_argument('--drive', 
                       help='Mount point of the drive (required for both operations)')
    parser.add_argument('--plan',
                       help='Path to sync plan (default: plans/sync_plan_latest.json)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview only, do not make changes')
    
    args = parser.parse_args()
    
    if not args.stage_deltas and not args.apply_staged:
        parser.print_help()
        sys.exit(1)
    
    if not args.drive:
        print("❌ --drive argument required")
        parser.print_help()
        sys.exit(1)
    
    if args.stage_deltas:
        stage_deltas(args.drive, args.plan, args.dry_run)
    elif args.apply_staged:
        apply_staged(args.drive, args.plan, args.dry_run)


if __name__ == '__main__':
    main()
