"""
Rsync wrapper for file synchronization operations.
"""

import subprocess
import os
from typing import List, Optional, Dict
import tempfile


def rsync_copy(source: str, dest: str, files: Optional[List[str]] = None,
               dry_run: bool = False, progress: bool = True) -> Dict:
    """
    Copy files using rsync.
    
    Args:
        source: Source directory path (with trailing slash)
        dest: Destination directory path
        files: Optional list of relative file paths to copy
        dry_run: If True, only show what would be copied
        progress: Show progress
        
    Returns:
        Dict with status, stdout, stderr
    """
    cmd = ['rsync', '-avh']
    
    if dry_run:
        cmd.append('--dry-run')
    
    if progress:
        cmd.append('--progress')
    
    # Itemized changes for detailed logging
    cmd.append('--itemize-changes')
    
    # Handle file list
    if files:
        # Create temporary file with list
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            for file in files:
                f.write(f"{file}\n")
            files_from = f.name
        
        cmd.extend(['--files-from', files_from])
    
    # Ensure source has trailing slash
    if not source.endswith('/'):
        source += '/'
    
    cmd.extend([source, dest])
    
    print(f"📦 Running rsync...")
    if dry_run:
        print("   (DRY RUN - no changes will be made)")
    print(f"   {' '.join(cmd[:4])}...")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        # Clean up temp file
        if files and os.path.exists(files_from):
            os.unlink(files_from)
        
        success = result.returncode == 0
        
        if success:
            print("✅ Rsync completed successfully")
        else:
            print(f"⚠️  Rsync completed with warnings (exit code: {result.returncode})")
        
        return {
            'success': success,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
        
    except Exception as e:
        if files and os.path.exists(files_from):
            os.unlink(files_from)
        raise


def rsync_with_stats(source: str, dest: str, files: Optional[List[str]] = None,
                     dry_run: bool = False) -> Dict:
    """
    Copy files using rsync with detailed statistics.
    
    Returns:
        Dict with stats: files_transferred, bytes_transferred, etc.
    """
    result = rsync_copy(source, dest, files, dry_run, progress=True)
    
    # Parse rsync output for statistics
    stats = parse_rsync_output(result['stdout'])
    result['stats'] = stats
    
    return result


def parse_rsync_output(output: str) -> Dict:
    """Parse rsync output to extract statistics"""
    stats = {
        'files_transferred': 0,
        'bytes_transferred': 0,
        'total_size': 0
    }
    
    for line in output.split('\n'):
        if 'Number of files:' in line:
            try:
                parts = line.split(':')[1].strip().split()
                stats['files_transferred'] = int(parts[0].replace(',', ''))
            except (ValueError, IndexError):
                pass
        elif 'Total file size:' in line:
            try:
                size_str = line.split(':')[1].strip().split()[0]
                stats['total_size'] = parse_size(size_str)
            except (ValueError, IndexError):
                pass
        elif 'Total transferred file size:' in line:
            try:
                size_str = line.split(':')[1].strip().split()[0]
                stats['bytes_transferred'] = parse_size(size_str)
            except (ValueError, IndexError):
                pass
    
    return stats


def parse_size(size_str: str) -> int:
    """Parse size string like '1.5G' to bytes"""
    size_str = size_str.strip().replace(',', '')
    
    multipliers = {
        'K': 1024,
        'M': 1024 ** 2,
        'G': 1024 ** 3,
        'T': 1024 ** 4
    }
    
    if size_str[-1] in multipliers:
        return int(float(size_str[:-1]) * multipliers[size_str[-1]])
    
    return int(size_str)


def create_file_list(files: List[str], output_path: str):
    """Create a file list for rsync --files-from"""
    with open(output_path, 'w') as f:
        for file in files:
            f.write(f"{file}\n")


def estimate_rsync_time(total_bytes: int, speed_mbps: int = 5000) -> float:
    """Estimate transfer time in minutes"""
    if speed_mbps <= 0:
        return 0.0
    
    speed_mbs = speed_mbps / 8  # Mbps to MB/s
    real_speed = speed_mbs * 0.8  # 80% efficiency
    
    if real_speed <= 0:
        return 0.0
    
    seconds = (total_bytes / (1024 * 1024)) / real_speed
    return round(seconds / 60, 1)


def verify_rsync_available() -> bool:
    """Check if rsync is installed"""
    try:
        result = subprocess.run(
            ['rsync', '--version'],
            capture_output=True,
            text=True,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_rsync_version() -> Optional[str]:
    """Get rsync version"""
    try:
        result = subprocess.run(
            ['rsync', '--version'],
            capture_output=True,
            text=True,
            check=True
        )
        first_line = result.stdout.split('\n')[0]
        return first_line.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, IndexError):
        return None
