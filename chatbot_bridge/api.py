"""High-level Python API for programmatic usage."""

import asyncio
from typing import Optional, Dict, Any, Callable
from pathlib import Path

from .core.config import BridgeConfig
from .core.bridge_system import BridgeSystem
from .core.code_executor import ExecutionResult


class ChatbotBridge:
    """
    High-level API wrapper for chatbot bridge system.
    
    Example:
        ```python
        from chatbot_bridge import ChatbotBridge
        
        async def main():
            async with ChatbotBridge(config_path="config.yaml") as bridge:
                session_id = await bridge.start("deepseek")
                # Bridge will monitor and execute commands automatically
                await asyncio.sleep(3600)  # Run for 1 hour
        
        asyncio.run(main())
        ```
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        config_dict: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize chatbot bridge.
        
        Args:
            config_path: Path to YAML configuration file
            config_dict: Configuration dictionary (alternative to config_path)
        """
        if config_path:
            self.config = BridgeConfig.from_yaml(config_path)
        elif config_dict:
            self.config = BridgeConfig(**config_dict)
        else:
            # Use default configuration
            self.config = BridgeConfig(
                project_root=str(Path.cwd()),
                sessions_dir="./sessions",
                logs_dir="./logs"
            )
        
        self.bridge_system = BridgeSystem(self.config)
        self._active_sessions = []
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Stop all active sessions
        for session_id in self._active_sessions:
            await self.stop(session_id)
    
    async def start(
        self,
        chatbot: str,
        session_id: Optional[str] = None
    ) -> str:
        """
        Start a new chatbot session.
        
        Args:
            chatbot: Chatbot platform name (deepseek, chatgpt, claude)
            session_id: Optional existing session ID to resume
            
        Returns:
            Session ID
        """
        session_id = await self.bridge_system.start_session(chatbot, session_id)
        self._active_sessions.append(session_id)
        return session_id
    
    async def stop(self, session_id: str) -> None:
        """
        Stop an active session.
        
        Args:
            session_id: Session ID to stop
        """
        await self.bridge_system.stop_session(session_id)
        if session_id in self._active_sessions:
            self._active_sessions.remove(session_id)
    
    def on_command_detected(self, callback: Callable) -> None:
        """
        Register callback for command detection events.
        
        Args:
            callback: Callback function that receives list of commands
        """
        self.bridge_system.register_event_hook('on_command_detected', callback)
    
    def on_execution_complete(self, callback: Callable) -> None:
        """
        Register callback for execution completion events.
        
        Args:
            callback: Callback function that receives ExecutionResult
        """
        self.bridge_system.register_event_hook('on_execution_complete', callback)
    
    def on_error(self, callback: Callable) -> None:
        """
        Register callback for error events.
        
        Args:
            callback: Callback function that receives exception
        """
        self.bridge_system.register_event_hook('on_error', callback)


def start_bridge(
    chatbot: str,
    config_path: Optional[str] = None,
    **config_kwargs
) -> str:
    """
    Simple function to start a bridge session.
    
    Args:
        chatbot: Chatbot platform name
        config_path: Path to configuration file
        **config_kwargs: Configuration parameters
        
    Returns:
        Session ID
    """
    async def _start():
        if config_path:
            bridge = ChatbotBridge(config_path=config_path)
        else:
            bridge = ChatbotBridge(config_dict=config_kwargs)
        
        return await bridge.start(chatbot)
    
    return asyncio.run(_start())
