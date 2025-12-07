"""
Database operations for USB drive sync tool.
Handles SQLite database creation and operations.
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple


class Database:
    def __init__(self, db_path: str = "usb_backup.db"):
        self.db_path = db_path
        self.conn = None
        
    def connect(self):
        """Connect to database and create tables if needed"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            
    def _create_tables(self):
        """Create database tables if they don't exist"""
        cursor = self.conn.cursor()
        
        # Drives table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drives (
                drive_id TEXT PRIMARY KEY,
                drive_role TEXT NOT NULL,
                drive_serial TEXT,
                drive_label TEXT,
                drive_size INTEGER,
                last_scan_timestamp TEXT
            )
        """)
        
        # Files table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                drive_id TEXT NOT NULL,
                filepath TEXT NOT NULL,
                size INTEGER NOT NULL,
                mtime REAL NOT NULL,
                checksum TEXT,
                scan_timestamp TEXT NOT NULL,
                is_deleted INTEGER DEFAULT 0,
                FOREIGN KEY (drive_id) REFERENCES drives(drive_id),
                UNIQUE(drive_id, filepath, scan_timestamp)
            )
        """)
        
        # Index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_files_drive_path 
            ON files(drive_id, filepath, is_deleted)
        """)
        
        # Sync operations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_operations (
                operation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                source_path TEXT NOT NULL,
                dest_path TEXT NOT NULL,
                file_size INTEGER,
                status TEXT NOT NULL,
                error_message TEXT
            )
        """)
        
        # Version history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS version_history (
                version_id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_path TEXT NOT NULL,
                versioned_path TEXT NOT NULL,
                version_timestamp TEXT NOT NULL,
                reason TEXT NOT NULL
            )
        """)
        
        self.conn.commit()
        
    def add_drive(self, drive_id: str, role: str, serial: str = None, 
                  label: str = None, size: int = None):
        """Add or update drive information"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO drives 
            (drive_id, drive_role, drive_serial, drive_label, drive_size, last_scan_timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (drive_id, role, serial, label, size, datetime.now().isoformat()))
        self.conn.commit()
        
    def get_drive(self, role: str) -> Optional[Dict]:
        """Get drive information by role"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM drives WHERE drive_role = ?", (role,))
        row = cursor.fetchone()
        return dict(row) if row else None
        
    def update_drive_scan_time(self, drive_id: str):
        """Update last scan timestamp for drive"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE drives 
            SET last_scan_timestamp = ? 
            WHERE drive_id = ?
        """, (datetime.now().isoformat(), drive_id))
        self.conn.commit()
        
    def add_files_bulk(self, files: List[Tuple], drive_id: str):
        """Bulk insert files (filepath, size, mtime)"""
        cursor = self.conn.cursor()
        scan_timestamp = datetime.now().isoformat()
        
        data = [(drive_id, filepath, size, mtime, scan_timestamp) 
                for filepath, size, mtime in files]
        
        cursor.executemany("""
            INSERT INTO files (drive_id, filepath, size, mtime, scan_timestamp, is_deleted)
            VALUES (?, ?, ?, ?, ?, 0)
        """, data)
        self.conn.commit()
        
    def mark_files_deleted(self, drive_id: str, existing_files: set):
        """Mark files as deleted if they no longer exist on drive"""
        cursor = self.conn.cursor()
        
        # Get all current non-deleted files for this drive
        cursor.execute("""
            SELECT filepath FROM files 
            WHERE drive_id = ? AND is_deleted = 0
        """, (drive_id,))
        
        db_files = {row['filepath'] for row in cursor.fetchall()}
        deleted_files = db_files - existing_files
        
        if deleted_files:
            cursor.executemany("""
                UPDATE files 
                SET is_deleted = 1 
                WHERE drive_id = ? AND filepath = ?
            """, [(drive_id, f) for f in deleted_files])
            self.conn.commit()
            
        return len(deleted_files)
        
    def get_file(self, drive_id: str, filepath: str) -> Optional[Dict]:
        """Get file information"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM files 
            WHERE drive_id = ? AND filepath = ? AND is_deleted = 0
            ORDER BY scan_timestamp DESC
            LIMIT 1
        """, (drive_id, filepath))
        row = cursor.fetchone()
        return dict(row) if row else None
        
    def get_all_files(self, drive_id: str) -> List[Dict]:
        """Get all non-deleted files for a drive"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT filepath, size, mtime 
            FROM files 
            WHERE drive_id = ? AND is_deleted = 0
            ORDER BY filepath
        """, (drive_id,))
        return [dict(row) for row in cursor.fetchall()]
        
    def get_file_stats(self, drive_id: str) -> Dict:
        """Get file statistics for a drive"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_files,
                SUM(size) as total_size,
                SUM(CASE WHEN is_deleted = 1 THEN 1 ELSE 0 END) as deleted_files
            FROM files 
            WHERE drive_id = ?
        """, (drive_id,))
        
        row = cursor.fetchone()
        return dict(row) if row else {}
        
    def log_sync_operation(self, operation_type: str, source_path: str, 
                          dest_path: str, file_size: int = None, 
                          status: str = "pending", error_message: str = None):
        """Log a sync operation"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO sync_operations 
            (timestamp, operation_type, source_path, dest_path, file_size, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), operation_type, source_path, dest_path, 
              file_size, status, error_message))
        self.conn.commit()
        return cursor.lastrowid
        
    def update_sync_operation(self, operation_id: int, status: str, 
                            error_message: str = None):
        """Update sync operation status"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE sync_operations 
            SET status = ?, error_message = ? 
            WHERE operation_id = ?
        """, (status, error_message, operation_id))
        self.conn.commit()
        
    def add_version_history(self, original_path: str, versioned_path: str, 
                           reason: str = "modified"):
        """Record file versioning"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO version_history 
            (original_path, versioned_path, version_timestamp, reason)
            VALUES (?, ?, ?, ?)
        """, (original_path, versioned_path, datetime.now().isoformat(), reason))
        self.conn.commit()
        
    def get_version_history(self, filepath: str) -> List[Dict]:
        """Get version history for a file"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM version_history 
            WHERE original_path = ? 
            ORDER BY version_timestamp DESC
        """, (filepath,))
        return [dict(row) for row in cursor.fetchall()]
        
    def get_recent_sync_operations(self, limit: int = 50) -> List[Dict]:
        """Get recent sync operations"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM sync_operations 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]
        
    def clear_old_scans(self, drive_id: str, keep_latest: int = 1):
        """Remove old scan data, keeping only the latest N scans"""
        cursor = self.conn.cursor()
        
        # Get distinct scan timestamps
        cursor.execute("""
            SELECT DISTINCT scan_timestamp 
            FROM files 
            WHERE drive_id = ? 
            ORDER BY scan_timestamp DESC
        """, (drive_id,))
        
        timestamps = [row['scan_timestamp'] for row in cursor.fetchall()]
        
        if len(timestamps) > keep_latest:
            old_timestamps = timestamps[keep_latest:]
            cursor.executemany("""
                DELETE FROM files 
                WHERE drive_id = ? AND scan_timestamp = ?
            """, [(drive_id, ts) for ts in old_timestamps])
            self.conn.commit()
            return len(old_timestamps)
        return 0
