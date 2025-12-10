#!/usr/bin/env python3
"""
Compare master and backup drives to generate sync plan.
"""

import sys
import os
import json
import argparse
from datetime import datetime

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

from database import Database
from drive_utils import format_size, estimate_transfer_time


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


def compare_drives(show_only: bool = False):
    """Compare master and backup drives"""
    print("=" * 60)
    print("Drive Comparison - Generate Sync Plan")
    print("=" * 60)
    
    # Load config
    config = load_config()
    
    # Open database
    db = Database(DB_FILE)
    db.connect()
    
    # Get drive information
    master_info = db.get_drive('master')
    backup_info = db.get_drive('backup')
    
    if not master_info:
        print("❌ Master drive not found in database")
        print("   Run: python3 src/scan.py --drive /mnt/usb --role master")
        db.close()
        sys.exit(1)
    
    if not backup_info:
        print("❌ Backup drive not found in database")
        print("   Run: python3 src/scan.py --drive /mnt/usb --role backup")
        db.close()
        sys.exit(1)
    
    master_id = master_info['drive_id']
    backup_id = backup_info['drive_id']
    
    print(f"\n📊 Master drive: {master_info.get('drive_label', 'MASTER')}")
    print(f"   Last scan: {master_info.get('last_scan_timestamp', 'Never')}")
    
    print(f"\n📊 Backup drive: {backup_info.get('drive_label', 'BACKUP')}")
    print(f"   Last scan: {backup_info.get('last_scan_timestamp', 'Never')}")
    
    print("\n" + "=" * 60)
    print("Analyzing differences...")
    print("=" * 60)
    
    # Get all files from both drives
    print("\n📂 Loading master files...")
    master_files = {f['filepath']: f for f in db.get_all_files(master_id)}
    print(f"   {len(master_files):,} files")
    
    print("\n📂 Loading backup files...")
    backup_files = {f['filepath']: f for f in db.get_all_files(backup_id)}
    print(f"   {len(backup_files):,} files")
    
    # Find differences
    print("\n🔍 Finding differences...")
    
    new_files = []
    modified_files = []
    deleted_files = []
    
    master_paths = set(master_files.keys())
    backup_paths = set(backup_files.keys())
    
    # New files (on master, not on backup)
    new_paths = master_paths - backup_paths
    for path in new_paths:
        mf = master_files[path]
        new_files.append({
            'path': path,
            'size': mf['size'],
            'mtime': mf['mtime']
        })
    
    # Modified files (on both, but different size or mtime)
    common_paths = master_paths & backup_paths
    for path in common_paths:
        mf = master_files[path]
        bf = backup_files[path]
        
        # Consider modified if size different or mtime significantly different (>1 second)
        if mf['size'] != bf['size'] or abs(mf['mtime'] - bf['mtime']) > 1.0:
            modified_files.append({
                'path': path,
                'size': mf['size'],
                'mtime': mf['mtime'],
                'old_size': bf['size'],
                'old_mtime': bf['mtime']
            })
    
    # Files deleted from master (on backup, not on master, and not marked deleted)
    # We don't delete from backup, but track for information
    deleted_paths = backup_paths - master_paths
    for path in deleted_paths:
        bf = backup_files[path]
        deleted_files.append({
            'path': path,
            'size': bf['size']
        })
    
    # Calculate totals
    new_size = sum(f['size'] for f in new_files)
    modified_size = sum(f['size'] for f in modified_files)
    total_delta_size = new_size + modified_size
    
    # Display results
    print("\n" + "=" * 60)
    print("Comparison Results")
    print("=" * 60)
    
    print(f"\n📦 New files (on master, not on backup):")
    print(f"   Count: {len(new_files):,}")
    print(f"   Size: {format_size(new_size)}")
    
    print(f"\n📝 Modified files (different on master):")
    print(f"   Count: {len(modified_files):,}")
    print(f"   Size: {format_size(modified_size)}")
    
    print(f"\n🗑️  Deleted files (removed from master):")
    print(f"   Count: {len(deleted_files):,}")
    print(f"   Note: These will be kept on backup (versioning strategy)")
    
    print(f"\n📊 Total delta to sync:")
    print(f"   Files: {len(new_files) + len(modified_files):,}")
    print(f"   Size: {format_size(total_delta_size)}")
    
    # Estimate time
    usb_speed = config.get('settings', {}).get('min_usb_speed_mbps', 5000)
    est_time = estimate_transfer_time(usb_speed, total_delta_size / (1024**3))
    print(f"   Estimated time: {est_time * 60:.0f} minutes (USB 3.0)")
    
    # Create sync plan
    sync_plan = {
        'created': datetime.now().isoformat(),
        'master_uuid': master_id,
        'backup_uuid': backup_id,
        'master_label': master_info.get('drive_label', 'MASTER'),
        'backup_label': backup_info.get('drive_label', 'BACKUP'),
        'new_files': [f['path'] for f in new_files],
        'modified_files': [f['path'] for f in modified_files],
        'deleted_files': [f['path'] for f in deleted_files],
        'total_files': len(new_files) + len(modified_files),
        'total_size_bytes': total_delta_size,
        'new_count': len(new_files),
        'modified_count': len(modified_files),
        'deleted_count': len(deleted_files)
    }
    
    db.close()
    
    if show_only:
        print("\n✅ Comparison complete (show-only mode, not saved)")
        return
    
    # Save sync plan
    os.makedirs(PLANS_DIR, exist_ok=True)
    plan_filename = f"sync_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    plan_path = os.path.join(PLANS_DIR, plan_filename)
    
    with open(plan_path, 'w', encoding='utf-8') as f:
        json.dump(sync_plan, f, indent=2, ensure_ascii=False)
    
    # Also save as latest
    latest_path = os.path.join(PLANS_DIR, 'sync_plan_latest.json')
    with open(latest_path, 'w', encoding='utf-8') as f:
        json.dump(sync_plan, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 60)
    print("Sync Plan Saved")
    print("=" * 60)
    print(f"   File: {plan_path}")
    print(f"   Also: {latest_path}")
    
    print("\n✅ Next steps:")
    print("   1. Connect MASTER drive")
    print("   2. Run: python3 src/sync.py --stage-deltas")
    print("   3. Disconnect master, connect BACKUP drive")
    print("   4. Run: python3 src/sync.py --apply-staged")


def main():
    parser = argparse.ArgumentParser(
        description='Compare master and backup drives'
    )
    parser.add_argument('--show-only', action='store_true',
                       help='Only show differences, do not save sync plan')
    
    args = parser.parse_args()
    
    compare_drives(args.show_only)


if __name__ == '__main__':
    main()
