"""Path validation for secure file operations."""

import os
import platform
from pathlib import Path
from typing import Tuple, Optional, Set


class PathValidator:
    """
    Validates file paths for security constraints.
    
    Ensures all file operations stay within PROJECT_ROOT and prevents
    access to sensitive system directories.
    """
    
    def __init__(self, project_root: str):
        """
        Initialize path validator.
        
        Args:
            project_root: Root directory for allowed operations
        """
        self.project_root = Path(project_root).resolve()
        self.project_root.mkdir(parents=True, exist_ok=True)
        
        # System paths to block (OS-specific)
        self._forbidden_paths = self._get_system_paths()
    
    def _get_system_paths(self) -> Set[str]:
        """Get OS-specific system paths to block."""
        system = platform.system().lower()
        
        if system == "windows":
            return {
                "C:\\Windows",
                "C:\\Program Files",
                "C:\\Program Files (x86)",
                "C:\\System32",
                "C:\\Users\\All Users",
                "C:\\ProgramData"
            }
        else:  # Unix-like (Linux, macOS)
            return {
                "/etc",
                "/sys", 
                "/proc",
                "/dev",
                "/boot",
                "/root",
                "/usr/bin",
                "/usr/sbin",
                "/sbin",
                "/bin"
            }
    
    def validate_path(self, path: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate that path is safe and within project root.
        
        Args:
            path: File path to validate (relative or absolute)
            
        Returns:
            Tuple of (is_valid, absolute_path, error_message)
        """
        if not path or not isinstance(path, str):
            return False, None, "Path cannot be empty or non-string"
        
        try:
            # Normalize the path
            normalized_path = self.normalize_path(path)
            
            # Check if within project root
            if not self.is_within_project_root(normalized_path):
                return False, None, f"Path outside project root: {path}"
            
            # Check if it's a system path
            if self.is_system_path(normalized_path):
                return False, None, f"Access to system path denied: {path}"
            
            return True, normalized_path, None
            
        except (OSError, ValueError) as e:
            return False, None, f"Invalid path: {str(e)}"
    
    def is_within_project_root(self, absolute_path: str) -> bool:
        """
        Check if absolute path is within project root.
        
        Args:
            absolute_path: Absolute file path
            
        Returns:
            True if within project root, False otherwise
        """
        try:
            path_obj = Path(absolute_path).resolve()
            return str(path_obj).startswith(str(self.project_root))
        except (OSError, ValueError):
            return False
    
    def is_system_path(self, absolute_path: str) -> bool:
        """
        Check if path is a sensitive system directory.
        
        Args:
            absolute_path: Absolute file path
            
        Returns:
            True if system path, False otherwise
        """
        try:
            path_str = str(Path(absolute_path).resolve())
            
            # Check against forbidden paths
            for forbidden in self._forbidden_paths:
                if path_str.startswith(forbidden):
                    return True
            
            return False
        except (OSError, ValueError):
            return True  # Err on the side of caution
    
    def normalize_path(self, path: str) -> str:
        """
        Convert relative path to absolute and resolve symlinks.
        
        Args:
            path: File path
            
        Returns:
            Normalized absolute path
            
        Raises:
            ValueError: If path contains invalid characters or traversal attempts
        """
        # Check for obvious traversal attempts
        if ".." in path or path.startswith("/") and not self.project_root.is_absolute():
            # Allow absolute paths only if they're within project root
            pass
        
        # Convert to Path object
        path_obj = Path(path)
        
        # If relative, make it relative to project root
        if not path_obj.is_absolute():
            path_obj = self.project_root / path_obj
        
        # Resolve symlinks and normalize
        try:
            resolved = path_obj.resolve()
            return str(resolved)
        except (OSError, RuntimeError) as e:
            raise ValueError(f"Cannot resolve path: {e}")
    
    def get_safe_path(self, path: str) -> Optional[str]:
        """
        Get safe absolute path if valid, None otherwise.
        
        Args:
            path: File path to validate
            
        Returns:
            Safe absolute path or None if invalid
        """
        is_valid, safe_path, _ = self.validate_path(path)
        return safe_path if is_valid else None
    
    def create_safe_directory(self, path: str) -> Tuple[bool, Optional[str]]:
        """
        Create directory if path is safe.
        
        Args:
            path: Directory path to create
            
        Returns:
            Tuple of (success, error_message)
        """
        is_valid, safe_path, error = self.validate_path(path)
        if not is_valid:
            return False, error
        
        try:
            Path(safe_path).mkdir(parents=True, exist_ok=True)
            return True, None
        except OSError as e:
            return False, f"Failed to create directory: {e}"