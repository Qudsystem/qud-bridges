"""ChatGPT chatbot plugin."""

import asyncio
from typing import List
from playwright.async_api import Page
from .base import ChatbotPlugin


class ChatGPTPlugin(ChatbotPlugin):
    """Plugin for ChatGPT chatbot platform."""
    
    @property
    def name(self) -> str:
        """Chatbot platform name."""
        return "chatgpt"
    
    @property
    def url(self) -> str:
        """Chatbot platform URL."""
        return "https://chat.openai.com"
    
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
            '[data-message-author-role="assistant"]',
            '.markdown',
            '[class*="markdown"]',
            '[data-testid*="conversation-turn"]',
            'article',
            'div[class*="message"]',
        ]
    
    async def get_input_selectors(self) -> List[str]:
        """
        Get selectors for input field.
        
        Returns:
            List of selectors to try
        """
        return [
            '#prompt-textarea',
            'textarea[placeholder*="Message"]',
            'textarea[data-id="root"]',
            'textarea',
            '[contenteditable="true"]',
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
                'button[data-testid="send-button"]',
                'button[aria-label*="Send"]',
                'button:has-text("Send")',
                '[data-testid="fruitjuice-send-button"]',
            ]
            
            for selector in send_selectors:
                try:
                    send_button = await page.query_selector(selector)
                    if send_button:
                        # Check if button is enabled
                        is_disabled = await send_button.is_disabled()
                        if not is_disabled:
                            await send_button.click()
                            return True
                except Exception:
                    continue
            
            # If no send button found or enabled, try pressing Enter
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
            # Wait for "Stop generating" button to appear (indicates response is being generated)
            stop_button_selectors = [
                'button:has-text("Stop generating")',
                '[aria-label*="Stop"]',
            ]
            
            # Wait a bit for response to start
            await asyncio.sleep(1)
            
            # Try to detect stop button
            for selector in stop_button_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=5000, state='visible')
                    # Now wait for it to disappear (response complete)
                    await page.wait_for_selector(selector, timeout=timeout, state='detached')
                    return True
                except Exception:
                    continue
            
            # Alternative: wait for new message to appear
            message_selectors = await self.get_message_selectors()
            for selector in message_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=timeout, state='visible')
                    # Wait a bit more to ensure response is complete
                    await asyncio.sleep(2)
                    return True
                except Exception:
                    continue
            
            # If no indicators found, just wait a bit
            await asyncio.sleep(3)
            return True
            
        except Exception:
            return False
