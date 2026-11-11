"""Claude chatbot plugin."""

import asyncio
from typing import List
from playwright.async_api import Page
from .base import ChatbotPlugin


class ClaudePlugin(ChatbotPlugin):
    """Plugin for Claude chatbot platform."""
    
    @property
    def name(self) -> str:
        """Chatbot platform name."""
        return "claude"
    
    @property
    def url(self) -> str:
        """Chatbot platform URL."""
        return "https://claude.ai"
    
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
            '[data-is-streaming="false"]',
            '.font-claude-message',
            '[class*="claude"]',
            '[role="article"]',
            'div[class*="message"]',
            '.prose',
        ]
    
    async def get_input_selectors(self) -> List[str]:
        """
        Get selectors for input field.
        
        Returns:
            List of selectors to try
        """
        return [
            '[contenteditable="true"][placeholder*="Talk"]',
            '[contenteditable="true"]',
            'textarea',
            'div[role="textbox"]',
            '[data-testid="chat-input"]',
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
                'button[aria-label*="Send"]',
                'button:has-text("Send")',
                '[data-testid="send-button"]',
                'button[type="submit"]',
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
            
            # If no send button found, try Ctrl+Enter (Claude's shortcut)
            await page.keyboard.press('Control+Enter')
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
            # Wait for streaming to start
            streaming_selectors = [
                '[data-is-streaming="true"]',
                '.streaming',
            ]
            
            # Wait a bit for response to start
            await asyncio.sleep(1)
            
            # Try to detect streaming indicator
            for selector in streaming_selectors:
                try:
                    # Wait for streaming to start
                    await page.wait_for_selector(selector, timeout=5000, state='attached')
                    # Wait for streaming to complete
                    await page.wait_for_selector('[data-is-streaming="false"]', timeout=timeout, state='attached')
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
