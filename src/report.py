#!/usr/bin/env python3
"""
Report tool - View status, history, and statistics.
"""

import sys
import os
import argparse
from datetime import datetime

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

from database import Database
from drive_utils import format_size


DB_FILE = 'usb_backup.db'


def show_summary():
    """Show overall status summary"""
    print("=" * 60)
    print("USB Drive Sync - Status Summary")
    print("=" * 60)
    
    db = Database(DB_FILE)
    db.connect()
    
    # Get drive info
    master = db.get_drive('master')
    backup = db.get_drive('backup')
    
    if master:
        print(f"\n📀 Master Drive:")
        print(f"   Label: {master.get('drive_label', 'MASTER')}")
        print(f"   UUID: {master['drive_id'][:16]}...")
        print(f"   Last scan: {master.get('last_scan_timestamp', 'Never')}")
        
        stats = db.get_file_stats(master['drive_id'])
        print(f"   Files: {stats.get('total_files', 0):,}")
        print(f"   Active: {stats.get('total_files', 0) - stats.get('deleted_files', 0):,}")
        print(f"   Size: {format_size(stats.get('total_size', 0))}")
    else:
        print("\n📀 Master Drive: Not configured")
    
    if backup:
        print(f"\n📀 Backup Drive:")
        print(f"   Label: {backup.get('drive_label', 'BACKUP')}")
        print(f"   UUID: {backup['drive_id'][:16]}...")
        print(f"   Last scan: {backup.get('last_scan_timestamp', 'Never')}")
        
        stats = db.get_file_stats(backup['drive_id'])
        print(f"   Files: {stats.get('total_files', 0):,}")
        print(f"   Active: {stats.get('total_files', 0) - stats.get('deleted_files', 0):,}")
        print(f"   Size: {format_size(stats.get('total_size', 0))}")
    else:
        print("\n📀 Backup Drive: Not configured")
    
    # Recent sync operations
    operations = db.get_recent_sync_operations(5)
    
    if operations:
        print(f"\n📊 Recent Sync Operations:")
        for op in operations:
            timestamp = op['timestamp'][:19]  # Trim milliseconds
            status_icon = "✅" if op['status'] == 'completed' else "⚠️"
            print(f"   {status_icon} {timestamp} - {op['operation_type']} - {op['source_path']}")
    else:
        print(f"\n📊 No sync operations yet")
    
    db.close()
    print("\n" + "=" * 60)


def show_history(limit: int = 50):
    """Show sync operation history"""
    print("=" * 60)
    print(f"Sync History (last {limit} operations)")
    print("=" * 60)
    
    db = Database(DB_FILE)
    db.connect()
    
    operations = db.get_recent_sync_operations(limit)
    
    if not operations:
        print("\nNo sync operations recorded")
        db.close()
        return
    
    print(f"\nTotal operations: {len(operations)}\n")
    
    for op in operations:
        timestamp = op['timestamp'][:19]
        status_icon = "✅" if op['status'] == 'completed' else "❌" if op['status'] == 'failed' else "⏳"
        
        print(f"{status_icon} {timestamp}")
        print(f"   Type: {op['operation_type']}")
        print(f"   File: {op['source_path']}")
        if op['file_size']:
            print(f"   Size: {format_size(op['file_size'])}")
        if op['status'] == 'failed' and op['error_message']:
            print(f"   Error: {op['error_message']}")
        print()
    
    db.close()


def show_versions(filepath: str):
    """Show version history for a file"""
    print("=" * 60)
    print(f"Version History: {filepath}")
    print("=" * 60)
    
    db = Database(DB_FILE)
    db.connect()
    
    versions = db.get_version_history(filepath)
    
    if not versions:
        print(f"\nNo version history for: {filepath}")
        db.close()
        return
    
    print(f"\nFound {len(versions)} version(s):\n")
    
    for i, ver in enumerate(versions, 1):
        print(f"{i}. {ver['version_timestamp']}")
        print(f"   Original: {ver['original_path']}")
        print(f"   Versioned: {ver['versioned_path']}")
        print(f"   Reason: {ver['reason']}")
        print()
    
    db.close()


def show_deleted():
    """Show files deleted from master"""
    print("=" * 60)
    print("Files Deleted from Master")
    print("=" * 60)
    
    db = Database(DB_FILE)
    db.connect()
    
    master = db.get_drive('master')
    if not master:
        print("\nMaster drive not configured")
        db.close()
        return
    
    # Query deleted files
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT filepath, size, mtime, scan_timestamp
        FROM files
        WHERE drive_id = ? AND is_deleted = 1
        ORDER BY scan_timestamp DESC
    """, (master['drive_id'],))
    
    deleted = cursor.fetchall()
    
    if not deleted:
        print("\nNo deleted files")
        db.close()
        return
    
    print(f"\nTotal deleted files: {len(deleted)}\n")
    
    total_size = 0
    for row in deleted:
        filepath = row['filepath']
        size = row['size']
        mtime = datetime.fromtimestamp(row['mtime']).strftime('%Y-%m-%d %H:%M')
        
        print(f"📄 {filepath}")
        print(f"   Size: {format_size(size)}")
        print(f"   Modified: {mtime}")
        print()
        
        total_size += size
    
    print(f"Total size of deleted files: {format_size(total_size)}")
    print("\nNote: These files are still on the backup drive")
    
    db.close()


def main():
    parser = argparse.ArgumentParser(
        description='View status, history, and statistics'
    )
    parser.add_argument('--summary', action='store_true',
                       help='Show overall status summary')
    parser.add_argument('--history', action='store_true',
                       help='Show sync operation history')
    parser.add_argument('--versions',
                       help='Show version history for a file')
    parser.add_argument('--deleted', action='store_true',
                       help='Show files deleted from master')
    parser.add_argument('--limit', type=int, default=50,
                       help='Limit number of history entries (default: 50)')
    
    args = parser.parse_args()
    
    if not os.path.exists(DB_FILE):
        print(f"❌ Database not found: {DB_FILE}")
        print("   Run: python3 src/setup.py --scan-drives")
        sys.exit(1)
    
    if args.summary or len(sys.argv) == 1:
        show_summary()
    elif args.history:
        show_history(args.limit)
    elif args.versions:
        show_versions(args.versions)
    elif args.deleted:
        show_deleted()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
