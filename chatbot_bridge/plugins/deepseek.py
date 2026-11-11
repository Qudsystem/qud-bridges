"""DeepSeek chatbot plugin."""

import asyncio
from typing import List
from playwright.async_api import Page
from .base import ChatbotPlugin


class DeepSeekPlugin(ChatbotPlugin):
    """Plugin for DeepSeek chatbot platform."""
    
    @property
    def name(self) -> str:
        """Chatbot platform name."""
        return "deepseek"
    
    @property
    def url(self) -> str:
        """Chatbot platform URL."""
        return "https://chat.deepseek.com"
    
    async def navigate_to_chat(self, page: Page) -> None:
        """
        Navigate to chat interface.
        
        Args:
            page: Playwright page instance
        """
        await page.goto(self.url, wait_until='networkidle')
        
        # Wait for chat interface to load
        await asyncio.sleep(2)
    
    async def get_message_selectors(self) -> List[str]:
        """
        Get selectors for message elements.
        
        Returns:
            List of selectors to try
        """
        return [
            '[data-role="assistant"]',
            '.message-content',
            '.assistant-message',
            '[role="article"]',
            '.chat-message',
            'div[class*="message"]',
        ]
    
    async def get_input_selectors(self) -> List[str]:
        """
        Get selectors for input field.
        
        Returns:
            List of selectors to try
        """
        return [
            'textarea[placeholder*="Message"]',
            'textarea[placeholder*="Type"]',
            'textarea',
            '[contenteditable="true"]',
            'input[type="text"]',
        ]
    
    async def send_message(
        self,
        page: Page,
        message: str,
        human_behavior: any
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
        try:
            # Find input field
            input_selectors = await self.get_input_selectors()
            input_element = None
            
            for selector in input_selectors:
                try:
                    input_element = await page.wait_for_selector(
                        selector,
                        timeout=5000,
                        state='visible'
                    )
                    if input_element:
                        break
                except Exception:
                    continue
            
            if not input_element:
                return False
            
            # Type message with human behavior
            await human_behavior.type_text(page, input_selectors[0], message)
            
            # Random pause before sending
            await human_behavior.random_pause()
            
            # Find and click send button
            send_selectors = [
                'button[type="submit"]',
                'button[aria-label*="Send"]',
                'button:has-text("Send")',
                '[data-testid="send-button"]',
            ]
            
            for selector in send_selectors:
                try:
                    send_button = await page.query_selector(selector)
                    if send_button:
                        await send_button.click()
                        return True
                except Exception:
                    continue
            
            # If no send button found, try pressing Enter
            await page.keyboard.press('Enter')
            return True
            
        except Exception:
            return False
    
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
        try:
            # Wait for loading indicator to appear and disappear
            loading_selectors = [
                '.loading',
                '[data-loading="true"]',
                '.spinner',
                '[aria-busy="true"]',
            ]
            
            # Wait a bit for response to start
            await asyncio.sleep(1)
            
            # Wait for response to complete (loading indicator disappears)
            for selector in loading_selectors:
                try:
                    # Wait for loading to appear
                    await page.wait_for_selector(selector, timeout=5000, state='attached')
                    # Wait for loading to disappear
                    await page.wait_for_selector(selector, timeout=timeout, state='detached')
                    return True
                except Exception:
                    continue
            
            # Alternative: wait for new message to appear
            message_selectors = await self.get_message_selectors()
            for selector in message_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=timeout, state='visible')
                    return True
                except Exception:
                    continue
            
            # If no loading indicator, just wait a bit
            await asyncio.sleep(3)
            return True
            
        except Exception:
            return False
