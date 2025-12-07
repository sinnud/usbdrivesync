"""
File scanner using Linux find command.
Fast metadata collection for large drives.
"""

import subprocess
import os
from typing import List, Tuple, Optional


def scan_drive(mount_point: str, exclude_hidden: bool = True) -> List[Tuple[str, int, float]]:
    """
    Scan drive using find command for maximum speed.
    
    Returns: List of (relative_filepath, size_bytes, mtime_timestamp)
    """
    if not os.path.exists(mount_point):
        raise ValueError(f"Mount point does not exist: {mount_point}")
    
    if not os.path.ismount(mount_point):
        print(f"⚠️  WARNING: {mount_point} does not appear to be a mount point")
    
    # Build find command
    cmd = ['find', mount_point, '-mount', '-type', 'f']
    
    # Exclude hidden files if requested
    if exclude_hidden:
        cmd.extend(['-not', '-path', '*/.*'])
    
    # Output format: path|size|mtime
    cmd.extend(['-printf', '%p|%s|%T@\\n'])
    
    print(f"🔍 Scanning {mount_point}...")
    print(f"   Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        return parse_find_output(result.stdout, mount_point)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running find command: {e}")
        print(f"   stderr: {e.stderr}")
        raise


def parse_find_output(output: str, mount_point: str) -> List[Tuple[str, int, float]]:
    """
    Parse find command output.
    
    Returns: List of (relative_filepath, size_bytes, mtime_timestamp)
    """
    files = []
    mount_point = mount_point.rstrip('/')
    
    for line in output.strip().split('\n'):
        if not line:
            continue
            
        try:
            parts = line.split('|')
            if len(parts) != 3:
                continue
            
            abs_path, size_str, mtime_str = parts
            
            # Convert to relative path
            if abs_path.startswith(mount_point):
                rel_path = abs_path[len(mount_point):].lstrip('/')
            else:
                rel_path = abs_path
            
            # Parse size and mtime
            size = int(size_str)
            mtime = float(mtime_str)
            
            files.append((rel_path, size, mtime))
            
        except (ValueError, IndexError) as e:
            # Skip malformed lines
            continue
    
    return files


def scan_drive_incremental(mount_point: str, batch_size: int = 10000,
                          exclude_hidden: bool = True):
    """
    Generator that yields batches of files for incremental processing.
    Useful for very large drives to avoid memory issues.
    
    Yields: List of (relative_filepath, size_bytes, mtime_timestamp)
    """
    if not os.path.exists(mount_point):
        raise ValueError(f"Mount point does not exist: {mount_point}")
    
    # Build find command
    cmd = ['find', mount_point, '-mount', '-type', 'f']
    
    if exclude_hidden:
        cmd.extend(['-not', '-path', '*/.*'])
    
    cmd.extend(['-printf', '%p|%s|%T@\\n'])
    
    print(f"🔍 Scanning {mount_point} (incremental)...")
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        batch = []
        mount_point_stripped = mount_point.rstrip('/')
        
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue
            
            try:
                parts = line.split('|')
                if len(parts) != 3:
                    continue
                
                abs_path, size_str, mtime_str = parts
                
                # Convert to relative path
                if abs_path.startswith(mount_point_stripped):
                    rel_path = abs_path[len(mount_point_stripped):].lstrip('/')
                else:
                    rel_path = abs_path
                
                size = int(size_str)
                mtime = float(mtime_str)
                
                batch.append((rel_path, size, mtime))
                
                if len(batch) >= batch_size:
                    yield batch
                    batch = []
                    
            except (ValueError, IndexError):
                continue
        
        # Yield remaining files
        if batch:
            yield batch
        
        # Wait for process to complete
        process.wait()
        
        if process.returncode != 0:
            stderr = process.stderr.read()
            raise subprocess.CalledProcessError(process.returncode, cmd, stderr=stderr)
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running find command: {e}")
        raise


def count_files(mount_point: str, exclude_hidden: bool = True) -> int:
    """Quick count of files on drive"""
    cmd = ['find', mount_point, '-mount', '-type', 'f']
    
    if exclude_hidden:
        cmd.extend(['-not', '-path', '*/.*'])
    
    try:
        result = subprocess.run(
            cmd + ['-printf', '.'],
            capture_output=True,
            text=True,
            check=True
        )
        return len(result.stdout)
    except subprocess.CalledProcessError:
        return 0


def get_directory_size(path: str) -> int:
    """Get total size of directory in bytes"""
    try:
        result = subprocess.run(
            ['du', '-sb', path],
            capture_output=True,
            text=True,
            check=True
        )
        size_str = result.stdout.split()[0]
        return int(size_str)
    except (subprocess.CalledProcessError, ValueError, IndexError):
        return 0


def verify_file_exists(mount_point: str, relative_path: str) -> bool:
    """Verify a file exists at the given path"""
    full_path = os.path.join(mount_point, relative_path)
    return os.path.isfile(full_path)


def get_file_info(mount_point: str, relative_path: str) -> Optional[Tuple[int, float]]:
    """Get size and mtime for a specific file"""
    full_path = os.path.join(mount_point, relative_path)
    
    try:
        stat = os.stat(full_path)
        return (stat.st_size, stat.st_mtime)
    except OSError:
        return None
