"""Configuration loader for Bridge-to-IDE."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatbotConfig(BaseModel):
    """Chatbot platform configuration."""
    
    name: Literal["deepseek", "claude", "gemini"]
    url: str
    polling_interval_ms: int = Field(gt=0)
    initial_load_wait_ms: int = Field(gt=0)
    max_scroll_depth: int = Field(ge=0)


class IDEConfig(BaseModel):
    """IDE integration configuration."""
    
    name: Literal["cursor", "vscode"]
    project_root: Path
    auto_open_files: bool
    open_delay_ms: int = Field(ge=0)
    
    @field_validator("project_root")
    @classmethod
    def validate_project_root(cls, v: Path) -> Path:
        """Reject placeholder value and ensure absolute path."""
        if str(v) == "REPLACE_WITH_YOUR_PROJECT_PATH":
            raise ValueError(
                "project_root must be set in settings.json. "
                "Replace 'REPLACE_WITH_YOUR_PROJECT_PATH' with your actual project path."
            )
        
        if not v.is_absolute():
            raise ValueError(f"project_root must be an absolute path, got: {v}")
        
        return v


class BrowserConfig(BaseModel):
    """Browser automation configuration."""
    
    driver: Literal["chrome", "firefox"]
    headless: bool
    user_data_dir: Path
    window_size: tuple[int, int]


class AntiBotConfig(BaseModel):
    """Anti-bot detection configuration."""
    
    enabled: bool
    min_delay_ms: int = Field(gt=0)
    max_delay_ms: int = Field(gt=0)
    mouse_simulation: bool
    max_actions_per_minute: int = Field(gt=0)
    
    @field_validator("max_delay_ms")
    @classmethod
    def validate_max_delay(cls, v: int, info) -> int:
        """Ensure max_delay >= min_delay."""
        if "min_delay_ms" in info.data and v < info.data["min_delay_ms"]:
            raise ValueError("max_delay_ms must be >= min_delay_ms")
        return v


class ExecutorConfig(BaseModel):
    """File executor configuration."""
    
    dry_run: bool
    auto_backup: bool
    backup_dir: Path
    backup_max_age_days: int = Field(gt=0)
    auto_run_terminal_commands: bool
    terminal_command_timeout_s: int = Field(gt=0)


class LoggingConfig(BaseModel):
    """Logging system configuration."""
    
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"]
    log_dir: Path
    rotation: str
    retention: str
    colorized: bool


class AdapterConfig(BaseModel):
    """Dynamic adapter configuration for a specific chatbot."""
    
    code_block_selector: str = Field(min_length=1)
    copy_button_selector: str = Field(min_length=1)
    message_container_selector: str = Field(min_length=1)


class BridgeConfig(BaseModel):
    """Complete Bridge configuration (immutable)."""
    
    model_config = ConfigDict(frozen=True)
    
    chatbot: ChatbotConfig
    ide: IDEConfig
    browser: BrowserConfig
    anti_bot: AntiBotConfig
    executor: ExecutorConfig
    logging: LoggingConfig
    adapters: dict[str, AdapterConfig]


# Custom exceptions
class ConfigNotFoundError(FileNotFoundError):
    """Configuration file not found."""
    pass


class ConfigValidationError(ValueError):
    """Configuration validation failed."""
    pass


def load_config(config_path: Path | None = None) -> BridgeConfig:
    """Load and validate configuration from JSON file.
    
    Resolution order:
    1. Explicit config_path argument
    2. BRIDGE_CONFIG_PATH environment variable
    3. ./config/settings.json (default)
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        Validated BridgeConfig instance
        
    Raises:
        ConfigNotFoundError: If config file doesn't exist
        ConfigValidationError: If validation fails
        
    Example:
        >>> config = load_config()
        >>> print(config.chatbot.name)
        deepseek
    """
    # Determine config file path
    if config_path is None:
        env_path = os.getenv("BRIDGE_CONFIG_PATH")
        if env_path:
            config_path = Path(env_path)
        else:
            config_path = Path.cwd() / "config" / "settings.json"
    
    # Check file exists
    if not config_path.exists():
        raise ConfigNotFoundError(
            f"Config file not found: {config_path}\n"
            f"Create it or set BRIDGE_CONFIG_PATH environment variable."
        )
    
    # Load JSON
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigValidationError(f"Invalid JSON in {config_path}: {e}") from e
    
    # Normalize paths (make relative paths absolute, relative to config dir)
    config_dir = config_path.parent
    
    def normalize_path(path_str: str) -> str:
        """Convert relative paths to absolute (relative to config file)."""
        p = Path(path_str)
        if not p.is_absolute():
            p = (config_dir / p).resolve()
        return str(p)
    
    # Normalize path fields
    if "ide" in data and "project_root" in data["ide"]:
        data["ide"]["project_root"] = normalize_path(data["ide"]["project_root"])
    
    if "browser" in data and "user_data_dir" in data["browser"]:
        data["browser"]["user_data_dir"] = normalize_path(data["browser"]["user_data_dir"])
    
    if "executor" in data and "backup_dir" in data["executor"]:
        data["executor"]["backup_dir"] = normalize_path(data["executor"]["backup_dir"])
    
    if "logging" in data and "log_dir" in data["logging"]:
        data["logging"]["log_dir"] = normalize_path(data["logging"]["log_dir"])
    
    # Validate with Pydantic
    try:
        config = BridgeConfig(**data)
    except Exception as e:
        # Extract field name from Pydantic error if possible
        error_msg = str(e)
        raise ConfigValidationError(f"Config validation failed: {error_msg}") from e
    
    return config
