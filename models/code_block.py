"""Data models for Bridge-to-IDE."""
from __future__ import annotations

import hashlib
import time
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CodeBlock(BaseModel):
    """Raw code extracted from chatbot DOM.
    
    This is an immutable container for code blocks detected by the Sniffer.
    Use the `from_raw()` factory method to create instances — never call
    `CodeBlock(...)` directly.
    
    Attributes:
        raw_text: The raw code content (normalized: stripped, LF line endings)
        source_url: The URL where this code was detected
        detected_at: Unix timestamp when detected
        content_hash: SHA256 hash for deduplication
    """
    
    model_config = ConfigDict(frozen=True)
    
    raw_text: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    detected_at: float = Field(gt=0.0)
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    
    @classmethod
    def from_raw(cls, text: str, url: str) -> CodeBlock:
        """Factory method: create CodeBlock with auto-computed hash and timestamp.
        
        Args:
            text: Raw code content
            url: Source URL
            
        Returns:
            Immutable CodeBlock instance
            
        Raises:
            ValueError: If text or URL is empty
        """
        if not text.strip():
            raise ValueError("Cannot create CodeBlock from empty text")
        if not url.strip():
            raise ValueError("source_url cannot be empty")
        
        # Normalize: strip whitespace, use LF line endings
        normalized = text.strip().replace("\r\n", "\n")
        
        # Compute SHA256 hash for deduplication
        content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        
        return cls(
            raw_text=normalized,
            source_url=url,
            detected_at=time.time(),
            content_hash=content_hash
        )


class ParsedCode(BaseModel):
    """Code after parser processing.
    
    This will be populated in Sprint 2. For now it's a placeholder.
    
    Attributes:
        code: The parsed code content
        file_path: Target file path (absolute)
        language: Detected language (python, javascript, etc.)
        terminal_commands: Commands to execute after writing file
        requires_backup: Whether to backup existing file before overwrite
        source_block: Original CodeBlock this was parsed from
    """
    
    model_config = ConfigDict(frozen=True)
    
    code: str
    file_path: Path
    language: str
    terminal_commands: list[str] = Field(default_factory=list)
    requires_backup: bool = True
    source_block: CodeBlock
