"""
File versioning utilities.
Handles renaming files with timestamps for version history.
"""

import os
import shutil
from datetime import datetime
from typing import Optional


def create_version_filename(original_path: str, timestamp: Optional[datetime] = None) -> str:
    """
    Create versioned filename with timestamp.
    
    Examples:
        photo.jpg -> photo.jpg.20241207_182530
        document.pdf -> document.pdf.20241207_182530
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    timestamp_str = timestamp.strftime('%Y%m%d_%H%M%S')
    return f"{original_path}.{timestamp_str}"


def version_file(mount_point: str, relative_path: str) -> Optional[str]:
    """
    Create a versioned copy of a file by renaming it.
    
    Returns: New versioned path (relative) or None if file doesn't exist
    """
    original_full = os.path.join(mount_point, relative_path)
    
    if not os.path.exists(original_full):
        return None
    
    # Create versioned filename
    versioned_name = create_version_filename(relative_path)
    versioned_full = os.path.join(mount_point, versioned_name)
    
    # Ensure versioned name doesn't already exist (very unlikely)
    counter = 1
    while os.path.exists(versioned_full):
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        versioned_name = f"{relative_path}.{timestamp_str}_{counter}"
        versioned_full = os.path.join(mount_point, versioned_name)
        counter += 1
    
    # Rename the file
    try:
        os.rename(original_full, versioned_full)
        print(f"   📦 Versioned: {relative_path}")
        print(f"      → {versioned_name}")
        return versioned_name
    except OSError as e:
        print(f"   ⚠️  Failed to version {relative_path}: {e}")
        return None


def version_files_batch(mount_point: str, relative_paths: list) -> dict:
    """
    Version multiple files.
    
    Returns: Dict with success/failure counts and details
    """
    results = {
        'success': [],
        'failed': [],
        'not_found': []
    }
    
    for rel_path in relative_paths:
        full_path = os.path.join(mount_point, rel_path)
        
        if not os.path.exists(full_path):
            results['not_found'].append(rel_path)
            continue
        
        versioned = version_file(mount_point, rel_path)
        if versioned:
            results['success'].append({
                'original': rel_path,
                'versioned': versioned
            })
        else:
            results['failed'].append(rel_path)
    
    return results


def list_versions(mount_point: str, original_path: str) -> list:
    """
    List all versions of a file (by filename pattern).
    
    Returns: List of versioned filenames
    """
    dir_name = os.path.dirname(original_path)
    base_name = os.path.basename(original_path)
    
    full_dir = os.path.join(mount_point, dir_name) if dir_name else mount_point
    
    if not os.path.exists(full_dir):
        return []
    
    versions = []
    pattern = f"{base_name}."
    
    try:
        for filename in os.listdir(full_dir):
            if filename.startswith(pattern) and filename != base_name:
                # Check if it looks like our versioning pattern (ends with timestamp)
                # Format: filename.ext.YYYYMMDD_HHMMSS[_counter]
                suffix = filename[len(pattern):]
                if len(suffix) >= 15 and suffix[:8].isdigit() and suffix[8] == '_':
                    versions.append(os.path.join(dir_name, filename) if dir_name else filename)
    except OSError:
        pass
    
    return sorted(versions, reverse=True)  # Newest first


def delete_old_versions(mount_point: str, original_path: str, keep_count: int = 5) -> int:
    """
    Delete old versions, keeping only the most recent N versions.
    
    Returns: Number of versions deleted
    """
    versions = list_versions(mount_point, original_path)
    
    if len(versions) <= keep_count:
        return 0
    
    to_delete = versions[keep_count:]
    deleted = 0
    
    for version in to_delete:
        full_path = os.path.join(mount_point, version)
        try:
            os.remove(full_path)
            deleted += 1
        except OSError:
            pass
    
    return deleted


def get_version_info(versioned_filename: str) -> Optional[dict]:
    """
    Parse version information from filename.
    
    Returns: Dict with timestamp, or None if not a versioned file
    """
    # Look for pattern: .YYYYMMDD_HHMMSS[_counter]
    parts = versioned_filename.split('.')
    
    if len(parts) < 2:
        return None
    
    timestamp_part = parts[-1]
    
    # Check if it's a counter version (e.g., 20241207_182530_2)
    if '_' in timestamp_part:
        timestamp_str = '_'.join(timestamp_part.split('_')[:2])
    else:
        timestamp_str = timestamp_part
    
    # Validate format
    if len(timestamp_str) != 15 or timestamp_str[8] != '_':
        return None
    
    try:
        dt = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
        return {
            'timestamp': dt,
            'timestamp_str': timestamp_str
        }
    except ValueError:
        return None


def restore_version(mount_point: str, versioned_path: str, 
                   restore_as: Optional[str] = None) -> bool:
    """
    Restore a versioned file (by copying it).
    
    Args:
        mount_point: Drive mount point
        versioned_path: Path to versioned file (relative)
        restore_as: Optional destination path; if None, extracts original name
        
    Returns: True if successful
    """
    versioned_full = os.path.join(mount_point, versioned_path)
    
    if not os.path.exists(versioned_full):
        return False
    
    # Determine destination
    if restore_as:
        dest_full = os.path.join(mount_point, restore_as)
    else:
        # Extract original filename by removing timestamp suffix
        # e.g., photo.jpg.20241207_182530 -> photo.jpg
        parts = versioned_path.rsplit('.', 1)
        if len(parts) == 2:
            # Check if last part is timestamp
            if get_version_info(versioned_path):
                dest_path = parts[0]
                dest_full = os.path.join(mount_point, dest_path)
            else:
                return False
        else:
            return False
    
    # Copy the file
    try:
        shutil.copy2(versioned_full, dest_full)
        return True
    except (OSError, shutil.Error):
        return False
