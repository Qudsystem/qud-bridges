"""File system executor for Bridge-to-IDE."""
from __future__ import annotations

import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from loguru import logger

from config.loader import BridgeConfig


class SecurityError(ValueError):
    """Attempted to write outside project_root."""
    pass


class ExecutorWriteError(RuntimeError):
    """Failed to write file."""
    pass


class Executor:
    """File system operations with atomic write and backup.
    
    Handles all disk I/O for the Bridge. Writes are atomic (temp + rename),
    with optional automatic backups and dry-run mode for testing.
    """
    
    def __init__(self, config: BridgeConfig):
        """Initialize executor with config.
        
        Args:
            config: Bridge configuration
        """
        self.config = config
    
    async def write_file(self, path: Path, content: str) -> None:
        """Write file atomically with optional backup.
        
        Security: Path must be inside project_root.
        Atomicity: Write to temp file, then rename (atomic on same filesystem).
        Backup: If file exists and auto_backup=true, copy to backup_dir first.
        Dry run: If dry_run=true, log but don't write.
        
        Args:
            path: Target file path (must be inside project_root)
            content: File content to write
            
        Raises:
            SecurityError: If path is outside project_root
            ExecutorWriteError: If write fails
            
        Example:
            >>> await executor.write_file(Path("src/app.py"), "print('hi')")
        """
        # Security check: path must be inside project_root
        try:
            resolved_path = path.resolve()
            resolved_root = self.config.ide.project_root.resolve()
            resolved_path.relative_to(resolved_root)
        except ValueError:
            raise SecurityError(
                f"Cannot write outside project_root.\n"
                f"  Path: {path}\n"
                f"  Root: {self.config.ide.project_root}"
            )
        
        # Backup existing file if needed
        if path.exists() and self.config.executor.auto_backup:
            await self._backup_file(path)
        
        # Dry run mode
        if self.config.executor.dry_run:
            logger.info(
                f"[DRY RUN] Would write {len(content)} bytes to {path}"
            )
            return
        
        # Create parent directories
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Atomic write
        tmp_path = None
        try:
            # Write to temp file in same directory (ensures same filesystem)
            with tempfile.NamedTemporaryFile(
                mode="w",
                delete=False,
                suffix=".tmp",
                dir=path.parent,
                encoding="utf-8"
            ) as tmp:
                tmp.write(content)
                tmp_path = Path(tmp.name)
            
            # Atomic rename
            shutil.move(str(tmp_path), str(path))
            
            logger.success(
                f"File synced | path={path} | size={len(content)}B"
            )
        
        except OSError as e:
            # Clean up temp file if it exists
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except:
                    pass  # Best effort cleanup
            
            raise ExecutorWriteError(
                f"Failed to write {path}: {e}"
            ) from e
    
    async def _backup_file(self, path: Path) -> None:
        """Copy existing file to backup directory with timestamp.
        
        Args:
            path: File to backup
        """
        backup_dir = self.config.executor.backup_dir
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{path.stem}_{timestamp}{path.suffix}.bak"
        backup_path = backup_dir / backup_name
        
        try:
            shutil.copy2(str(path), str(backup_path))
            logger.info(
                f"Backup created | original={path} | backup={backup_path}"
            )
        except OSError as e:
            logger.warning(
                f"Failed to create backup for {path}: {e}"
            )
            # Don't fail the whole operation if backup fails
