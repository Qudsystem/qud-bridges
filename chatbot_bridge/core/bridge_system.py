"""Main bridge system orchestrator."""

import asyncio
import time
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path

from .config import BridgeConfig
from .session_manager import SessionManager
from .chatbot_monitor import ChatbotMonitor
from .command_extractor import CommandExtractor
from .path_validator import PathValidator
from .code_executor import CodeExecutor, ExecutionResult
from ..automation.browser import BrowserAutomation
from ..automation.human_behavior import HumanBehaviorSimulator
from ..automation.proxy_manager import ProxyManager
from ..automation.captcha_resolver import CAPTCHAResolver
from ..plugins.base import ChatbotPlugin
from ..plugins.deepseek import DeepSeekPlugin
from ..plugins.chatgpt import ChatGPTPlugin
from ..plugins.claude import ClaudePlugin
from ..utils.logger import get_logger


class BridgeSystem:
    """
    Main orchestrator for the chatbot bridge system.
    """
    
    # Available plugins
    PLUGINS = {
        'deepseek': DeepSeekPlugin,
        'chatgpt': ChatGPTPlugin,
        'claude': ClaudePlugin,
    }
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize bridge system.
        
        Args:
            config: System configuration dictionary
        """
        # Load configuration
        if isinstance(config, dict):
            self.config = BridgeConfig(**config)
        else:
            self.config = config
        
        # Validate configuration
        is_valid, error = self.config.validate()
        if not is_valid:
            raise ValueError(f"Invalid configuration: {error}")
        
        # Initialize logger
        self.logger = get_logger('bridge_system', self.config.logs_dir)
        
        # Initialize components
        self.session_manager = SessionManager(self.config.sessions_dir)
        self.command_extractor = CommandExtractor()
        self.path_validator = PathValidator(self.config.project_root)
        self.code_executor = CodeExecutor(
            timeout=self.config.execution_timeout,
            memory_limit_mb=self.config.memory_limit_mb,
            cpu_limit_percent=self.config.cpu_limit_percent
        )
        self.human_behavior = HumanBehaviorSimulator(
            typing_delay_range=self.config.typing_delay_range,
            typo_rate=self.config.typo_rate,
            pause_range=self.config.pause_range
        )
        
        # Initialize proxy manager if proxies configured
        self.proxy_manager = None
        if self.config.proxies:
            self.proxy_manager = ProxyManager(
                proxies=self.config.proxies,
                rotation_interval=self.config.proxy_rotation_interval
            )
        
        # Initialize CAPTCHA resolver
        self.captcha_resolver = CAPTCHAResolver(
            api_key=self.config.captcha_api_key,
            timeout=self.config.captcha_timeout
        )
        
        # Active sessions
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Event hooks
        self._event_hooks: Dict[str, List[Callable]] = {
            'on_command_detected': [],
            'on_execution_complete': [],
            'on_error': []
        }
        
        self.logger.info("Bridge system initialized")
    
    async def start_session(
        self,
        chatbot_name: str,
        session_id: Optional[str] = None
    ) -> str:
        """
        Start new chatbot session.
        
        Args:
            chatbot_name: Name of chatbot platform
            session_id: Optional existing session ID
            
        Returns:
            Session ID
        """
        self.logger.info(f"Starting session for {chatbot_name}")
        
        # Validate chatbot name
        if chatbot_name not in self.PLUGINS:
            raise ValueError(f"Unknown chatbot: {chatbot_name}. Available: {list(self.PLUGINS.keys())}")
        
        # Create or load session
        if session_id:
            profile_path = self.session_manager.load_session(chatbot_name, session_id)
            if not profile_path:
                raise ValueError(f"Session not found: {session_id}")
        else:
            session_id = self.session_manager.create_session(chatbot_name)
            session = self.session_manager.get_session(session_id)
            profile_path = session.profile_path
        
        # Initialize browser automation
        browser_automation = BrowserAutomation(
            headless=self.config.headless,
            user_agent=self.config.user_agent,
            proxy_manager=self.proxy_manager
        )
        
        # Launch browser
        browser = await browser_automation.launch_browser(profile_path)
        context = await browser_automation.create_context(browser)
        page = await context.new_page()
        
        # Hide automation flags
        await browser_automation.hide_automation_flags(page)
        
        # Initialize chatbot plugin
        plugin_class = self.PLUGINS[chatbot_name]
        plugin = plugin_class()
        
        # Navigate to chatbot
        await plugin.navigate_to_chat(page)
        
        # Check for CAPTCHA
        captcha_type = await self.captcha_resolver.detect_captcha(page)
        if captcha_type:
            self.logger.warning(f"CAPTCHA detected: {captcha_type}")
            solved = await self.captcha_resolver.solve_captcha(page, captcha_type)
            if not solved:
                await browser_automation.close()
                raise RuntimeError("Failed to solve CAPTCHA")
        
        # Initialize monitor
        monitor = ChatbotMonitor(
            page=page,
            chatbot_plugin=plugin,
            check_interval_range=self.config.check_interval_range
        )
        
        # Store session data
        self._active_sessions[session_id] = {
            'browser_automation': browser_automation,
            'browser': browser,
            'context': context,
            'page': page,
            'plugin': plugin,
            'monitor': monitor,
            'chatbot_name': chatbot_name
        }
        
        # Start monitoring
        await monitor.start_monitoring(
            lambda msg: self._handle_new_message(session_id, msg)
        )
        
        self.logger.info(f"Session started: {session_id}")
        return session_id
    
    async def stop_session(self, session_id: str) -> None:
        """
        Stop active session.
        
        Args:
            session_id: Session ID to stop
        """
        if session_id not in self._active_sessions:
            return
        
        self.logger.info(f"Stopping session: {session_id}")
        
        session_data = self._active_sessions[session_id]
        
        # Stop monitoring
        await session_data['monitor'].stop_monitoring()
        
        # Close browser
        await session_data['browser_automation'].close()
        
        # Deactivate session
        self.session_manager.deactivate_session(session_id)
        
        # Remove from active sessions
        del self._active_sessions[session_id]
        
        self.logger.info(f"Session stopped: {session_id}")
    
    async def process_message(
        self,
        session_id: str,
        message: str
    ) -> List[ExecutionResult]:
        """
        Process chatbot message and execute commands.
        
        Args:
            session_id: Active session ID
            message: Chatbot message
            
        Returns:
            List of execution results
        """
        self.logger.info(f"Processing message for session {session_id}")
        
        results = []
        
        # Extract commands
        commands = self.command_extractor.extract_commands(message)
        
        if not commands:
            self.logger.debug("No commands found in message")
            return results
        
        self.logger.info(f"Found {len(commands)} command(s)")
        
        # Trigger event hook
        await self._trigger_event('on_command_detected', commands)
        
        # Process each command
        for cmd in commands:
            try:
                # Validate path if present
                if cmd.file_path:
                    is_valid, abs_path, error = self.path_validator.validate_path(cmd.file_path)
                    
                    if not is_valid:
                        self.logger.error(f"Path validation failed: {error}")
                        result = ExecutionResult(
                            success=False,
                            stdout="",
                            stderr="",
                            exit_code=-1,
                            execution_time=0.0,
                            error_message=f"Security violation: {error}"
                        )
                        results.append(result)
                        continue
                    
                    # Update command with validated path
                    cmd.file_path = abs_path
                
                # Execute command based on type
                if cmd.operation_type == 'execute_code' and cmd.code_content:
                    result = await self.code_executor.execute_code(
                        code=cmd.code_content,
                        language=cmd.language or 'python',
                        working_dir=cmd.metadata.get('working_directory'),
                        env_vars=cmd.metadata.get('environment_variables')
                    )
                    results.append(result)
                    
                elif cmd.operation_type == 'create_file' and cmd.file_path and cmd.code_content:
                    # Create file
                    Path(cmd.file_path).parent.mkdir(parents=True, exist_ok=True)
                    with open(cmd.file_path, 'w') as f:
                        f.write(cmd.code_content)
                    
                    result = ExecutionResult(
                        success=True,
                        stdout=f"File created: {cmd.file_path}",
                        stderr="",
                        exit_code=0,
                        execution_time=0.0
                    )
                    results.append(result)
                
                # Trigger completion event
                await self._trigger_event('on_execution_complete', result)
                
            except Exception as e:
                self.logger.error(f"Error executing command: {e}")
                result = ExecutionResult(
                    success=False,
                    stdout="",
                    stderr="",
                    exit_code=-1,
                    execution_time=0.0,
                    error_message=str(e)
                )
                results.append(result)
                await self._trigger_event('on_error', e)
        
        return results
    
    async def send_result_to_chatbot(
        self,
        session_id: str,
        result: ExecutionResult
    ) -> bool:
        """
        Send execution result back to chatbot.
        
        Args:
            session_id: Active session ID
            result: Execution result
            
        Returns:
            True if sent successfully, False otherwise
        """
        if session_id not in self._active_sessions:
            return False
        
        session_data = self._active_sessions[session_id]
        page = session_data['page']
        plugin = session_data['plugin']
        
        # Format result for chatbot
        message = result.format_for_chatbot()
        
        # Add response delay
        delay = self.config.response_delay_range
        await asyncio.sleep(asyncio.uniform(delay[0] / 1000, delay[1] / 1000))
        
        # Send message
        success = await plugin.send_message(page, message, self.human_behavior)
        
        if success:
            # Wait for response
            await plugin.wait_for_response(page)
        
        return success
    
    def register_event_hook(
        self,
        event_name: str,
        callback: Callable
    ) -> None:
        """
        Register event hook.
        
        Args:
            event_name: Event name (on_command_detected, on_execution_complete, on_error)
            callback: Callback function
        """
        if event_name in self._event_hooks:
            self._event_hooks[event_name].append(callback)
    
    async def _handle_new_message(self, session_id: str, message: str):
        """Handle new message from chatbot."""
        self.logger.info(f"New message in session {session_id}")
        
        # Process message
        results = await self.process_message(session_id, message)
        
        # Send results back to chatbot
        for result in results:
            await self.send_result_to_chatbot(session_id, result)
    
    async def _trigger_event(self, event_name: str, *args):
        """Trigger event hooks."""
        if event_name in self._event_hooks:
            for callback in self._event_hooks[event_name]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(*args)
                    else:
                        callback(*args)
                except Exception as e:
                    self.logger.error(f"Error in event hook {event_name}: {e}")
