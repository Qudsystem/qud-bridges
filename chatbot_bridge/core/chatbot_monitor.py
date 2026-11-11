"""Chatbot conversation monitoring."""

import asyncio
import random
import time
from typing import Callable, Awaitable, Optional, List, Dict, Tuple
from playwright.async_api import Page


class ChatbotMonitor:
    """
    Monitors chatbot conversations and detects new messages.
    """
    
    def __init__(
        self,
        page: Page,
        chatbot_plugin: any,  # ChatbotPlugin type
        check_interval_range: Tuple[int, int] = (500, 2000)
    ):
        """
        Initialize chatbot monitor.
        
        Args:
            page: Playwright page instance
            chatbot_plugin: Plugin for specific chatbot platform
            check_interval_range: Min and max milliseconds between checks
        """
        self.page = page
        self.chatbot_plugin = chatbot_plugin
        self.check_interval_range = check_interval_range
        
        # Monitoring state
        self.is_monitoring = False
        self.last_message_count = 0
        self.conversation_history: List[Dict[str, str]] = []
        
        # Monitoring task
        self._monitor_task: Optional[asyncio.Task] = None
    
    async def start_monitoring(
        self,
        on_message_callback: Callable[[str], Awaitable[None]]
    ) -> None:
        """
        Start continuous monitoring loop.
        
        Args:
            on_message_callback: Async callback function for new messages
        """
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self._monitor_task = asyncio.create_task(
            self._monitoring_loop(on_message_callback)
        )
    
    async def stop_monitoring(self) -> None:
        """Stop monitoring loop."""
        self.is_monitoring = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
    
    async def get_latest_message(self) -> Optional[str]:
        """
        Get the latest message from chatbot.
        
        Returns:
            Message text if available, None otherwise
        """
        try:
            # Get message selectors from plugin
            selectors = await self.chatbot_plugin.get_message_selectors()
            
            # Find all message elements
            for selector in selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    
                    if elements:
                        # Get the last message
                        last_element = elements[-1]
                        text = await last_element.inner_text()
                        
                        if text and text.strip():
                            return text.strip()
                        
                except Exception:
                    continue
            
            return None
            
        except Exception:
            return None
    
    async def get_conversation_history(self) -> List[Dict[str, str]]:
        """
        Get full conversation history.
        
        Returns:
            List of message dictionaries with 'role' and 'content'
        """
        return self.conversation_history.copy()
    
    async def _monitoring_loop(
        self,
        on_message_callback: Callable[[str], Awaitable[None]]
    ):
        """
        Main monitoring loop.
        
        Args:
            on_message_callback: Callback for new messages
        """
        while self.is_monitoring:
            try:
                # Get latest message
                message = await self.get_latest_message()
                
                if message:
                    # Check if this is a new message
                    if not self.conversation_history or message != self.conversation_history[-1].get('content'):
                        # New message detected
                        self.conversation_history.append({
                            'role': 'assistant',
                            'content': message,
                            'timestamp': time.time()
                        })
                        
                        # Call callback
                        try:
                            await on_message_callback(message)
                        except Exception as e:
                            # Log error but continue monitoring
                            print(f"Error in message callback: {e}")
                
                # Random delay before next check
                delay = random.uniform(
                    self.check_interval_range[0] / 1000,
                    self.check_interval_range[1] / 1000
                )
                await asyncio.sleep(delay)
                
            except asyncio.CancelledError:
                # Monitoring stopped
                break
            except Exception as e:
                # Log error and continue
                print(f"Error in monitoring loop: {e}")
                await asyncio.sleep(1)
    
    def add_user_message(self, message: str):
        """
        Add user message to conversation history.
        
        Args:
            message: User message content
        """
        self.conversation_history.append({
            'role': 'user',
            'content': message,
            'timestamp': time.time()
        })
