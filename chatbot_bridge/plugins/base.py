"""Base chatbot plugin interface."""

from abc import ABC, abstractmethod
from typing import List
from playwright.async_api import Page


class ChatbotPlugin(ABC):
    """
    Abstract base class for chatbot platform plugins.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Chatbot platform name."""
        pass
    
    @property
    @abstractmethod
    def url(self) -> str:
        """Chatbot platform URL."""
        pass
    
    @abstractmethod
    async def navigate_to_chat(self, page: Page) -> None:
        """
        Navigate to chat interface.
        
        Args:
            page: Playwright page instance
        """
        pass
    
    @abstractmethod
    async def get_message_selectors(self) -> List[str]:
        """
        Get selectors for message elements.
        
        Returns:
            List of selectors to try
        """
        pass
    
    @abstractmethod
    async def get_input_selectors(self) -> List[str]:
        """
        Get selectors for input field.
        
        Returns:
            List of selectors to try
        """
        pass
    
    @abstractmethod
    async def send_message(
        self,
        page: Page,
        message: str,
        human_behavior: any  # HumanBehaviorSimulator type
    ) -> bool:
        """
        Send message to chatbot.
        
        Args:
            page: Playwright page instance
            message: Message text
            human_behavior: Human behavior simulator
            
        Returns:
            True if sent successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def wait_for_response(
        self,
        page: Page,
        timeout: int = 60000
    ) -> bool:
        """
        Wait for chatbot response.
        
        Args:
            page: Playwright page instance
            timeout: Maximum wait time in milliseconds
            
        Returns:
            True if response received, False if timeout
        """
        pass
