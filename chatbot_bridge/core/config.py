"""Configuration management for the chatbot bridge system."""

import os
import yaml
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path


@dataclass
class BridgeConfig:
    """
    System configuration for the chatbot bridge.
    
    Attributes:
        project_root: Root directory for allowed file operations
        sessions_dir: Directory to store browser sessions
        logs_dir: Directory to store log files
        headless: Whether to run browser in headless mode
        user_agent: Custom user agent string (random if None)
        check_interval_range: Min and max ms between message checks
        execution_timeout: Maximum execution time for code in seconds
        memory_limit_mb: Maximum memory usage per execution in MB
        cpu_limit_percent: Maximum CPU usage per execution in percent
        typing_delay_range: Min and max ms between keystrokes
        typo_rate: Probability of typing error (0.0 to 1.0)
        pause_range: Min and max ms for random pauses
        response_delay_range: Min and max ms before responding
        captcha_api_key: 2captcha API key (optional)
        captcha_timeout: Maximum time to wait for CAPTCHA solution
        proxies: List of proxy URLs
        proxy_rotation_interval: Min and max requests before proxy rotation
        max_retries: Maximum retry attempts for failed operations
        retry_backoff_factor: Exponential backoff multiplier for retries
        rate_limit_backoff_factor: Backoff multiplier when rate limited
    """
    
    project_root: str
    sessions_dir: str = "./sessions"
    logs_dir: str = "./logs"
    
    # Browser settings
    headless: bool = False
    user_agent: Optional[str] = None
    
    # Monitoring settings
    check_interval_range: Tuple[int, int] = (500, 2000)
    
    # Execution settings
    execution_timeout: int = 30
    memory_limit_mb: int = 512
    cpu_limit_percent: int = 50
    
    # Human behavior settings
    typing_delay_range: Tuple[int, int] = (50, 150)
    typo_rate: float = 0.02
    pause_range: Tuple[int, int] = (500, 3000)
    response_delay_range: Tuple[int, int] = (1000, 5000)
    
    # CAPTCHA settings
    captcha_api_key: Optional[str] = None
    captcha_timeout: int = 120
    
    # Proxy settings
    proxies: List[str] = field(default_factory=list)
    proxy_rotation_interval: Tuple[int, int] = (10, 20)
    
    # Error handling settings
    max_retries: int = 3
    retry_backoff_factor: float = 2.0
    rate_limit_backoff_factor: float = 2.0
    
    def __post_init__(self) -> None:
        """Validate and normalize configuration after initialization."""
        # Normalize paths
        self.project_root = str(Path(self.project_root).resolve())
        self.sessions_dir = str(Path(self.sessions_dir).resolve())
        self.logs_dir = str(Path(self.logs_dir).resolve())
        
        # Create directories if they don't exist
        Path(self.sessions_dir).mkdir(parents=True, exist_ok=True)
        Path(self.logs_dir).mkdir(parents=True, exist_ok=True)
        Path(self.project_root).mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def from_yaml(cls, path: str) -> 'BridgeConfig':
        """
        Load configuration from YAML file.
        
        Args:
            path: Path to YAML configuration file
            
        Returns:
            BridgeConfig instance
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid YAML
            ValueError: If required fields are missing
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data:
            raise ValueError("Configuration file is empty")
        
        if 'project_root' not in data:
            raise ValueError("Required field 'project_root' missing from configuration")
        
        return cls(**data)
    
    def to_yaml(self, path: str) -> None:
        """
        Save configuration to YAML file.
        
        Args:
            path: Path to save YAML configuration file
        """
        data = {
            'project_root': self.project_root,
            'sessions_dir': self.sessions_dir,
            'logs_dir': self.logs_dir,
            'headless': self.headless,
            'user_agent': self.user_agent,
            'check_interval_range': list(self.check_interval_range),
            'execution_timeout': self.execution_timeout,
            'memory_limit_mb': self.memory_limit_mb,
            'cpu_limit_percent': self.cpu_limit_percent,
            'typing_delay_range': list(self.typing_delay_range),
            'typo_rate': self.typo_rate,
            'pause_range': list(self.pause_range),
            'response_delay_range': list(self.response_delay_range),
            'captcha_api_key': self.captcha_api_key,
            'captcha_timeout': self.captcha_timeout,
            'proxies': self.proxies,
            'proxy_rotation_interval': list(self.proxy_rotation_interval),
            'max_retries': self.max_retries,
            'retry_backoff_factor': self.retry_backoff_factor,
            'rate_limit_backoff_factor': self.rate_limit_backoff_factor,
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """
        Validate configuration values.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate project root exists
        if not os.path.exists(self.project_root):
            return False, f"Project root does not exist: {self.project_root}"
        
        # Validate timeout values
        if self.execution_timeout <= 0:
            return False, "execution_timeout must be positive"
        
        if self.captcha_timeout <= 0:
            return False, "captcha_timeout must be positive"
        
        # Validate resource limits
        if self.memory_limit_mb <= 0:
            return False, "memory_limit_mb must be positive"
        
        if self.cpu_limit_percent <= 0 or self.cpu_limit_percent > 100:
            return False, "cpu_limit_percent must be between 1 and 100"
        
        # Validate ranges
        if self.check_interval_range[0] >= self.check_interval_range[1]:
            return False, "check_interval_range min must be less than max"
        
        if self.typing_delay_range[0] >= self.typing_delay_range[1]:
            return False, "typing_delay_range min must be less than max"
        
        if self.pause_range[0] >= self.pause_range[1]:
            return False, "pause_range min must be less than max"
        
        if self.response_delay_range[0] >= self.response_delay_range[1]:
            return False, "response_delay_range min must be less than max"
        
        # Validate typo rate
        if not 0.0 <= self.typo_rate <= 1.0:
            return False, "typo_rate must be between 0.0 and 1.0"
        
        # Validate retry settings
        if self.max_retries < 0:
            return False, "max_retries must be non-negative"
        
        if self.retry_backoff_factor <= 0:
            return False, "retry_backoff_factor must be positive"
        
        if self.rate_limit_backoff_factor <= 0:
            return False, "rate_limit_backoff_factor must be positive"
        
        return True, None
