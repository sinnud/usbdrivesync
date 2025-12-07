# Windows Initial Sync Guide

This guide provides detailed instructions for performing the initial full synchronization between your two USB drives using a Windows desktop.

**Note:** This is a ONE-TIME operation. All subsequent metadata scanning and syncing will be done on Debian Linux.

---

## Prerequisites

- Windows desktop with at least 2 USB ports
- Both USB drives connected simultaneously
- Drives formatted as NTFS
- Administrator access

---

## Method 1: Using WSL (Recommended)

### Why WSL?
- Native Linux `rsync` command (same as production)
- Better handling of file attributes
- Progress monitoring
- Can resume interrupted transfers

### Step 1: Install WSL

1. **Open PowerShell as Administrator**
   - Press `Win + X`
   - Select "Windows PowerShell (Admin)" or "Terminal (Admin)"

2. **Install WSL**:
   ```powershell
   wsl --install
   ```

3. **Restart your computer** when prompted

4. **After restart**, WSL will finish installation and prompt for username/password

### Step 2: Install rsync in WSL

1. **Open WSL terminal**:
   - Press `Win + R`
   - Type `wsl` and press Enter
   - Or search "Ubuntu" in Start Menu

2. **Update package list**:
   ```bash
   sudo apt update
   ```

3. **Install rsync**:
   ```bash
   sudo apt install -y rsync
   ```

### Step 3: Identify Your Drives

1. **Open File Explorer** and check drive letters
   - Example: Master drive = `D:`, Backup drive = `E:`
   
2. **Important**: Note which drive is your MASTER (source of truth)

### Step 4: Run rsync

1. **In WSL terminal**, Windows drives are automatically mounted at `/mnt/`:
   - `C:` → `/mnt/c`
   - `D:` → `/mnt/d`
   - `E:` → `/mnt/e`

2. **Navigate and verify drives**:
   ```bash
   # Check master drive
   ls /mnt/d
   
   # Check backup drive
   ls /mnt/e
   ```

3. **Run the sync** (replace d and e with your actual drive letters):
   ```bash
   # Dry run first (preview only, no changes)
   rsync -avH --dry-run --progress /mnt/d/ /mnt/e/
   
   # If everything looks good, run actual sync:
   rsync -avH --progress /mnt/d/ /mnt/e/
   ```

   **Important**: Note the trailing slashes:
   - `/mnt/d/` (with slash) = copy contents of d into e
   - `/mnt/d` (no slash) = copy d folder itself into e
   
   **Always use trailing slashes for drive roots!**

### Step 5: Monitor Progress

The `--progress` flag shows:
```
sending incremental file list
photos/2024/IMG_001.jpg
    2.51M 100%   89.32MB/s    0:00:00 (xfr#1, to-chk=12543/15000)
photos/2024/IMG_002.jpg
    1.83M 100%   76.45MB/s    0:00:00 (xfr#2, to-chk=12542/15000)
...
```

**Expected time**: 2-3 hours for 2TB on USB 3.0

### Step 6: Verify Completion

After rsync finishes:
```bash
# Check file counts match
find /mnt/d -type f | wc -l
find /mnt/e -type f | wc -l

# Check total sizes match (approximately)
du -sh /mnt/d
du -sh /mnt/e
```

### Step 7: Safely Eject

1. Exit WSL terminal: `exit`
2. In Windows, right-click drives and "Eject"
3. Physically disconnect drives

---

## Method 2: Using Robocopy (Windows Native)

### Why Robocopy?
- Built into Windows (no installation needed)
- Fast and reliable
- Can resume interrupted copies

### Step 1: Identify Drives

1. Open File Explorer
2. Note drive letters (e.g., Master = `D:`, Backup = `E:`)

### Step 2: Open Command Prompt as Administrator

1. Press `Win + X`
2. Select "Command Prompt (Admin)" or "Terminal (Admin)"

### Step 3: Run Robocopy

```cmd
robocopy D:\ E:\ /MIR /R:3 /W:5 /V /ETA /LOG:C:\robocopy_log.txt

REM Explanation of flags:
REM /MIR    = Mirror mode (exact copy, including deletions)
REM /R:3    = Retry 3 times on failed copies
REM /W:5    = Wait 5 seconds between retries
REM /V      = Verbose output (show all files)
REM /ETA    = Show estimated time remaining
REM /LOG:   = Save log file for review
```

**Alternative with more details**:
```cmd
robocopy D:\ E:\ /MIR /R:3 /W:5 /V /ETA /BYTES /NP /TEE /LOG:C:\robocopy_log.txt

REM Additional flags:
REM /BYTES  = Show sizes in bytes
REM /NP     = No progress percentage (cleaner output)
REM /TEE    = Output to console AND log file
```

### Step 4: Monitor Progress

Robocopy shows:
```
------------------------------------------------------------------------------
   ROBOCOPY     ::     Robust File Copy for Windows
------------------------------------------------------------------------------

  Started : Saturday, December 7, 2024 6:30:00 PM
   Source : D:\
     Dest : E:\

    Files : *.*
  Options : *.* /V /DCOPY:DA /COPY:DAT /MIR /R:3 /W:5 

------------------------------------------------------------------------------

          New Dir         123    D:\photos\
            New File        2.51 M    IMG_001.jpg
            New File        1.83 M    IMG_002.jpg
            ...
            
   Total    Copied   Skipped  Mismatch    FAILED    Extras
    Dirs :   1234     1234         0         0         0         0
   Files :  15000    15000         0         0         0         0
   Bytes :  1.98 TB  1.98 TB       0         0         0         0
```

### Step 5: Verify Completion

Check the log file at `C:\robocopy_log.txt` for any errors.

### Step 6: Safely Eject

Right-click drives in File Explorer and select "Eject"

---

## Method 3: Using cwRsync (rsync for Windows)

### Why cwRsync?
- Native Windows rsync port
- Same syntax as Linux rsync
- Good if you can't use WSL

### Step 1: Download and Install

1. **Download**: https://itefix.net/cwrsync (Free edition)
2. **Install** to `C:\Program Files\cwRsync`
3. **Add to PATH** (optional but helpful):
   - Search "Environment Variables" in Start Menu
   - Edit "Path" system variable
   - Add: `C:\Program Files\cwRsync\bin`

### Step 2: Identify Drives

Note drive letters in File Explorer (e.g., `D:` and `E:`)

### Step 3: Open Command Prompt

Press `Win + R`, type `cmd`, press Enter

### Step 4: Run cwRsync

```cmd
cd "C:\Program Files\cwRsync\bin"

REM Dry run first
rsync.exe -avH --dry-run --progress D:/ E:/

REM Actual sync
rsync.exe -avH --progress D:/ E:/
```

**Note**: cwRsync uses forward slashes, even on Windows

### Step 5: Monitor and Complete

Same as WSL method above.

---

## Comparison of Methods

| Method | Pros | Cons | Recommended For |
|--------|------|------|-----------------|
| **WSL + rsync** | Native Linux tool, can resume, best compatibility | Requires WSL installation | Most users (best option) |
| **Robocopy** | Built-in, no installation, very fast | Windows-specific, different syntax | Quick start, no WSL |
| **cwRsync** | Rsync syntax, no WSL needed | Third-party download | Can't use WSL |

---

## Common Issues

### Issue: "Access Denied" errors

**Solution**:
```cmd
REM Run Command Prompt as Administrator
REM Or in WSL:
sudo rsync -avH --progress /mnt/d/ /mnt/e/
```

### Issue: Transfer very slow

**Check**:
- Are drives on USB 3.0 ports? (blue ports)
- Check Task Manager → Performance → USB to see transfer speed
- Should be 200-400 MB/s on USB 3.0
- If only 40-50 MB/s, you're on USB 2.0

### Issue: Not enough space on E:

**Solution**:
- Verify E: drive size: `dir E:` or check in File Explorer
- Ensure E: has at least as much space as content on D:

### Issue: Interrupted transfer

**Resume with rsync**:
```bash
# WSL or cwRsync - just run same command again
rsync -avH --progress /mnt/d/ /mnt/e/
# rsync automatically skips already-copied files
```

**Resume with robocopy**:
```cmd
REM Same command - robocopy also resumes
robocopy D:\ E:\ /MIR /R:3 /W:5 /V /ETA
```

---

## After Initial Sync

✅ **Done on Windows!** Both drives now have identical content.

### Next Steps:

1. **Safely eject both drives** from Windows
2. **Move to Debian laptop**
3. **Do NOT use Windows for any more operations**
4. **Follow README.md** for Linux setup:
   - Run `setup.py` to identify drives
   - Run `scan.py` on both drives to create metadata
   - Use `sync.py` for all future syncs

---

## Verification Commands

### WSL Verification
```bash
# File count comparison
echo "Master files:"
find /mnt/d -type f | wc -l
echo "Backup files:"
find /mnt/e -type f | wc -l

# Size comparison
du -sh /mnt/d
du -sh /mnt/e

# Detailed comparison (optional, slow)
rsync -avH --dry-run /mnt/d/ /mnt/e/
# Should show "sending incremental file list" with nothing listed
```

### Windows Command Prompt Verification
```cmd
REM Count files
dir D:\ /s /a-d | find /c ":"
dir E:\ /s /a-d | find /c ":"

REM Check sizes in Explorer
explorer D:\
explorer E:\
REM Right-click drives → Properties → Compare sizes
```

---

## Tips

1. **Label your drives physically** with stickers:
   - "MASTER DRIVE" on one
   - "BACKUP DRIVE" on the other
   
2. **Keep Windows log file** for reference:
   - WSL: Can redirect with `rsync ... 2>&1 | tee rsync.log`
   - Robocopy: Already creates `C:\robocopy_log.txt`
   
3. **Don't modify files during sync**:
   - Close all programs accessing the drives
   - Don't browse files in Explorer during sync
   
4. **Use USB 3.0 ports** (blue ports) for both drives if available

5. **Ensure stable power**:
   - Connect laptop to AC power
   - Don't let computer sleep during sync

---

## Time Estimates

| Drive Size | USB 3.0 | USB 2.0 |
|------------|---------|---------|
| 500 GB | 30-45 min | 3-4 hours |
| 1 TB | 1-1.5 hours | 6-8 hours |
| 2 TB | 2-3 hours | 12-16 hours |
| 3 TB | 3-4.5 hours | 18-24 hours |

**Always use USB 3.0!**

---

## Support

If you encounter issues:
1. Check the log files
2. Verify drive letters didn't change
3. Ensure Administrator/sudo permissions
4. Check available space on destination
5. Try the dry-run mode first

---

**Once complete, proceed to README.md for Debian Linux setup!**
