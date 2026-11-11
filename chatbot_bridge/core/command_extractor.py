"""Command extraction from chatbot messages."""

import re
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any, Union
import uuid
import time


class OperationType(Enum):
    """Types of operations that can be extracted from commands."""
    CREATE_FILE = "create_file"
    MODIFY_FILE = "modify_file"
    DELETE_FILE = "delete_file"
    EXECUTE_CODE = "execute_code"
    RUN_COMMAND = "run_command"


@dataclass
class ExtractedCommand:
    """
    Represents an extracted command from chatbot message.
    
    Attributes:
        id: Unique identifier for the command
        operation_type: Type of operation (create_file, execute_code, etc.)
        file_path: Target file path (if applicable)
        code_content: Code or content to execute/write
        language: Programming language (python, javascript, bash, etc.)
        metadata: Additional metadata (dependencies, env vars, etc.)
        raw_text: Original text from which command was extracted
        timestamp: When the command was extracted
    """
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operation_type: OperationType = OperationType.EXECUTE_CODE
    file_path: Optional[str] = None
    code_content: Optional[str] = None
    language: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "operation_type": self.operation_type.value,
            "file_path": self.file_path,
            "code_content": self.code_content,
            "language": self.language,
            "metadata": self.metadata,
            "raw_text": self.raw_text,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExtractedCommand':
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            operation_type=OperationType(data.get("operation_type", "execute_code")),
            file_path=data.get("file_path"),
            code_content=data.get("code_content"),
            language=data.get("language"),
            metadata=data.get("metadata", {}),
            raw_text=data.get("raw_text", ""),
            timestamp=data.get("timestamp", time.time())
        )
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate command structure.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.operation_type in [OperationType.CREATE_FILE, OperationType.MODIFY_FILE]:
            if not self.file_path:
                return False, "File path required for file operations"
            if not self.code_content:
                return False, "Content required for file operations"
        
        elif self.operation_type == OperationType.DELETE_FILE:
            if not self.file_path:
                return False, "File path required for delete operation"
        
        elif self.operation_type in [OperationType.EXECUTE_CODE, OperationType.RUN_COMMAND]:
            if not self.code_content:
                return False, "Code content required for execution"
        
        return True, None


class CommandExtractor:
    """
    Extracts programming commands from chatbot messages.
    
    Supports various formats:
    - Markdown code blocks (```python, ```javascript, etc.)
    - Explicit command keywords
    - JSON command structures
    """
    
    def __init__(self, keywords: Optional[List[str]] = None):
        """
        Initialize command extractor.
        
        Args:
            keywords: Custom command keywords (uses defaults if None)
        """
        self.keywords = keywords or [
            "create file", "write file", "save to", "save as",
            "execute", "run", "exec", "نفذ", "شغل", "اكتب ملف",
            "modify", "edit", "update", "change",
            "delete", "remove", "احذف"
        ]
        
        # Compile regex patterns for efficiency
        self._code_block_pattern = re.compile(
            r'```(\w+)?\s*\n?(.*?)```',
            re.DOTALL | re.MULTILINE
        )
        
        self._file_path_pattern = re.compile(
            r'(?:file:|path:|save\s+(?:to|as)|write\s+to)\s*["\']?([^\s"\']+)["\']?',
            re.IGNORECASE
        )
        
        self._command_pattern = re.compile(
            r'(?:' + '|'.join(re.escape(kw) for kw in self.keywords) + r')',
            re.IGNORECASE
        )
    
    def extract_commands(self, message: str) -> List[ExtractedCommand]:
        """
        Extract all commands from message text.
        
        Args:
            message: Chatbot message text
            
        Returns:
            List of extracted commands
        """
        commands = []
        
        # Extract code blocks first
        code_blocks = self.extract_code_blocks(message)
        
        # Check if message contains command keywords
        has_keywords = bool(self._command_pattern.search(message))
        
        if code_blocks and has_keywords:
            # Process each code block as a potential command
            for block in code_blocks:
                command = self._create_command_from_code_block(block, message)
                if command:
                    commands.append(command)
        
        # Look for explicit file operations
        file_commands = self._extract_file_operations(message)
        commands.extend(file_commands)
        
        # Look for JSON command structures
        json_commands = self._extract_json_commands(message)
        commands.extend(json_commands)
        
        return commands
    
    def extract_code_blocks(self, message: str) -> List[Dict[str, str]]:
        """
        Extract markdown code blocks from message.
        
        Args:
            message: Message text
            
        Returns:
            List of dicts with 'language' and 'code' keys
        """
        blocks = []
        matches = self._code_block_pattern.findall(message)
        
        for language, code in matches:
            blocks.append({
                "language": language.lower() if language else "text",
                "code": code.strip()
            })
        
        return blocks
    
    def _create_command_from_code_block(
        self, 
        code_block: Dict[str, str], 
        full_message: str
    ) -> Optional[ExtractedCommand]:
        """Create command from code block and context."""
        language = code_block["language"]
        code = code_block["code"]
        
        if not code.strip():
            return None
        
        # Determine operation type
        operation_type = self.parse_operation_type(full_message)
        
        # Extract file path if mentioned
        file_path = self._extract_file_path(full_message)
        
        # Extract metadata
        metadata = self.extract_metadata(full_message)
        
        return ExtractedCommand(
            operation_type=operation_type,
            file_path=file_path,
            code_content=code,
            language=language if language != "text" else None,
            metadata=metadata,
            raw_text=full_message
        )
    
    def parse_operation_type(self, text: str) -> OperationType:
        """
        Determine operation type from text.
        
        Args:
            text: Command text
            
        Returns:
            Operation type
        """
        text_lower = text.lower()
        
        # File operations
        if any(word in text_lower for word in ["create", "write", "save", "اكتب"]):
            return OperationType.CREATE_FILE
        elif any(word in text_lower for word in ["modify", "edit", "update", "change", "عدل"]):
            return OperationType.MODIFY_FILE
        elif any(word in text_lower for word in ["delete", "remove", "احذف"]):
            return OperationType.DELETE_FILE
        elif any(word in text_lower for word in ["run command", "shell", "bash", "cmd"]):
            return OperationType.RUN_COMMAND
        else:
            return OperationType.EXECUTE_CODE
    
    def _extract_file_path(self, text: str) -> Optional[str]:
        """Extract file path from text."""
        match = self._file_path_pattern.search(text)
        return match.group(1) if match else None
    
    def extract_metadata(self, text: str) -> Dict[str, Any]:
        """
        Extract metadata like dependencies, environment variables.
        
        Args:
            text: Command text
            
        Returns:
            Dictionary of metadata
        """
        metadata = {}
        
        # Extract dependencies
        deps_pattern = r'(?:dependencies?|requires?|imports?)[:\s]+([^\n]+)'
        deps_match = re.search(deps_pattern, text, re.IGNORECASE)
        if deps_match:
            deps_text = deps_match.group(1)
            # Split by common separators
            deps = [dep.strip() for dep in re.split(r'[,;\s]+', deps_text) if dep.strip()]
            metadata["dependencies"] = deps
        
        # Extract environment variables
        env_pattern = r'(?:env|environment)[:\s]+([^\n]+)'
        env_match = re.search(env_pattern, text, re.IGNORECASE)
        if env_match:
            env_text = env_match.group(1)
            # Try to parse as key=value pairs
            env_vars = {}
            for pair in env_text.split(','):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    env_vars[key.strip()] = value.strip()
            if env_vars:
                metadata["environment_variables"] = env_vars
        
        # Extract working directory
        workdir_pattern = r'(?:workdir|working.directory|cd)[:\s]+([^\s]+)'
        workdir_match = re.search(workdir_pattern, text, re.IGNORECASE)
        if workdir_match:
            metadata["working_directory"] = workdir_match.group(1)
        
        return metadata
    
    def _extract_file_operations(self, message: str) -> List[ExtractedCommand]:
        """Extract explicit file operations from message."""
        commands = []
        
        # Look for file creation patterns
        create_patterns = [
            r'create\s+(?:file\s+)?["\']?([^"\']+)["\']?(?:\s+with\s+content[:\s]+(.*?)(?=\n|$))?',
            r'write\s+to\s+["\']?([^"\']+)["\']?[:\s]+(.*?)(?=\n|$)',
        ]
        
        for pattern in create_patterns:
            matches = re.finditer(pattern, message, re.IGNORECASE | re.DOTALL)
            for match in matches:
                file_path = match.group(1).strip()
                content = match.group(2).strip() if match.lastindex >= 2 else ""
                
                commands.append(ExtractedCommand(
                    operation_type=OperationType.CREATE_FILE,
                    file_path=file_path,
                    code_content=content,
                    raw_text=match.group(0)
                ))
        
        return commands
    
    def _extract_json_commands(self, message: str) -> List[ExtractedCommand]:
        """Extract JSON-formatted commands from message."""
        commands = []
        
        # Look for JSON command blocks
        json_pattern = r'```json\s*\n?(.*?)```'
        matches = re.finditer(json_pattern, message, re.DOTALL)
        
        for match in matches:
            try:
                json_data = json.loads(match.group(1))
                if isinstance(json_data, dict) and "operation" in json_data:
                    command = self._parse_json_command(json_data, match.group(0))
                    if command:
                        commands.append(command)
            except json.JSONDecodeError:
                continue
        
        return commands
    
    def _parse_json_command(self, json_data: Dict[str, Any], raw_text: str) -> Optional[ExtractedCommand]:
        """Parse JSON command structure."""
        try:
            operation_str = json_data.get("operation", "execute_code")
            operation_type = OperationType(operation_str)
            
            return ExtractedCommand(
                operation_type=operation_type,
                file_path=json_data.get("file_path"),
                code_content=json_data.get("content") or json_data.get("code"),
                language=json_data.get("language"),
                metadata=json_data.get("metadata", {}),
                raw_text=raw_text
            )
        except (ValueError, KeyError):
            return None