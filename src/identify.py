#!/usr/bin/env python3
"""
Quick drive identification tool.
Check which drive is currently connected.
"""

import sys
import os
import json
import argparse

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

from drive_utils import get_device_uuid, get_device_label, get_mount_point_device


CONFIG_FILE = 'config.json'


def identify_drive(mount_point: str):
    """Identify which drive is connected"""
    if not os.path.exists(mount_point):
        print(f"❌ Mount point does not exist: {mount_point}")
        sys.exit(1)
    
    # Get UUID
    uuid = get_device_uuid(mount_point)
    
    if not uuid:
        print(f"❌ Cannot read UUID from {mount_point}")
        print("   Drive may not be properly mounted")
        sys.exit(1)
    
    # Get label
    label = get_device_label(mount_point)
    
    # Get device path
    device_path = get_mount_point_device(mount_point)
    
    print("\n" + "=" * 60)
    print("Drive Information")
    print("=" * 60)
    print(f"Mount point: {mount_point}")
    if device_path:
        print(f"Device: {device_path}")
    print(f"UUID: {uuid}")
    print(f"Label: {label or '(no label)'}")
    
    # Check against configuration
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        print("\n" + "=" * 60)
        print("Drive Role")
        print("=" * 60)
        
        found = False
        
        if 'master' in config and config['master']['uuid'] == uuid:
            print("✅ This is the MASTER drive")
            print(f"   Label: {config['master'].get('label', 'MASTER')}")
            found = True
        
        if 'backup' in config and config['backup']['uuid'] == uuid:
            print("✅ This is the BACKUP drive")
            print(f"   Label: {config['backup'].get('label', 'BACKUP')}")
            found = True
        
        if not found:
            print("⚠️  This drive is NOT configured")
            print("   Not master or backup drive")
            print("\n   Run: python3 src/setup.py --scan-drives")
    else:
        print("\n⚠️  No configuration file found")
        print("   Run: python3 src/setup.py --scan-drives")
    
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description='Identify which USB drive is connected'
    )
    parser.add_argument('mount_point', 
                       help='Mount point to check (e.g., /mnt/usb)')
    
    args = parser.parse_args()
    
    identify_drive(args.mount_point)


if __name__ == '__main__':
    main()
