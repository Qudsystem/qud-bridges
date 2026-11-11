"""Code block sniffer for Bridge-to-IDE."""
from __future__ import annotations

import asyncio
import random
from typing import AsyncGenerator

import undetected_chromedriver as uc
from loguru import logger
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By

from config.loader import BridgeConfig
from models.code_block import CodeBlock


class BrowserNotFoundError(RuntimeError):
    """Chrome browser not found on system."""
    pass


class ChatbotLoadError(RuntimeError):
    """Failed to load chatbot page."""
    pass


class Sniffer:
    """Browser-based code block detector with deduplication.
    
    The Sniffer opens a browser, navigates to the chatbot, and continuously
    polls the DOM for code blocks. Each unique code block (by content hash)
    is yielded exactly once per session.
    
    Anti-bot measures:
    - Uses undetected-chromedriver (stealth mode)
    - Persistent browser profile (login once, reuse forever)
    - Random delays with gaussian distribution
    - Stability check (only yield after text stops changing)
    """
    
    def __init__(self, config: BridgeConfig):
        """Initialize sniffer with configuration.
        
        Args:
            config: Bridge configuration
        """
        self.config = config
        self.driver = None
        self._seen_hashes: set[str] = set()  # For deduplication
    
    async def start(self) -> None:
        """Launch browser and navigate to chatbot URL.
        
        This method:
        1. Configures Chrome options (profile, window size, headless mode)
        2. Launches undetected-chromedriver
        3. Navigates to chatbot URL
        4. Waits for page to load
        
        Raises:
            BrowserNotFoundError: If Chrome is not installed
            ChatbotLoadError: If page fails to load
            
        Example:
            >>> sniffer = Sniffer(config)
            >>> await sniffer.start()
            >>> # Browser is now open at chatbot URL
        """
        logger.info("Starting browser...")
        
        # Configure Chrome options
        options = uc.ChromeOptions()
        
        if self.config.browser.headless:
            options.add_argument("--headless=new")
        
        # Persistent profile (login persists between runs)
        profile_dir = self.config.browser.user_data_dir
        options.add_argument(f"--user-data-dir={profile_dir}")
        
        # Window size
        width, height = self.config.browser.window_size
        options.add_argument(f"--window-size={width},{height}")
        
        # Additional stealth options
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        
        # Launch browser
        try:
            self.driver = uc.Chrome(options=options, version_main=None)
        except Exception as e:
            raise BrowserNotFoundError(
                f"Chrome not found. Please install from: https://www.google.com/chrome\n"
                f"Error: {e}"
            ) from e
        
        # Navigate to chatbot
        logger.info(f"Navigating to {self.config.chatbot.url}...")
        try:
            self.driver.get(self.config.chatbot.url)
        except Exception as e:
            raise ChatbotLoadError(
                f"Failed to load {self.config.chatbot.url}: {e}"
            ) from e
        
        # Wait for page to load
        wait_seconds = self.config.chatbot.initial_load_wait_ms / 1000
        await asyncio.sleep(wait_seconds)
        
        # Verify page loaded (basic check)
        if not self.driver.current_url:
            raise ChatbotLoadError(
                f"Failed to load {self.config.chatbot.url} (empty URL)"
            )
        
        logger.success(f"Browser ready | url={self.driver.current_url}")
    
    async def watch(self) -> AsyncGenerator[CodeBlock, None]:
        """Poll DOM for new code blocks (async generator).
        
        This continuously polls the page for code blocks matching the
        configured CSS selector. For each element:
        
        1. Extract text content
        2. Check stability (text unchanged for 1 poll cycle)
        3. Create CodeBlock with SHA256 hash
        4. Check deduplication (hash not seen before)
        5. Yield block if new
        
        Yields:
            CodeBlock: Each unique code block found
            
        Example:
            >>> async for block in sniffer.watch():
            ...     print(f"Found code: {block.content_hash[:8]}")
        """
        if self.driver is None:
            raise RuntimeError("Must call start() before watch()")
        
        # Get adapter config for this chatbot
        adapter_config = self.config.adapters[self.config.chatbot.name]
        selector = adapter_config.code_block_selector
        
        # Track last seen text for stability check
        last_seen_texts: dict[str, str] = {}  # element_id → text
        
        logger.info(f"Watching for code blocks | selector={selector}")
        
        while True:
            # Anti-bot: random delay with gaussian distribution
            if self.config.anti_bot.enabled:
                jitter = random.gauss(
                    (self.config.anti_bot.min_delay_ms + self.config.anti_bot.max_delay_ms) / 2,
                    (self.config.anti_bot.max_delay_ms - self.config.anti_bot.min_delay_ms) / 4
                )
                jitter = max(
                    self.config.anti_bot.min_delay_ms,
                    min(self.config.anti_bot.max_delay_ms, jitter)
                )
                await asyncio.sleep(jitter / 1000)
            else:
                # Fallback: use polling_interval_ms
                await asyncio.sleep(self.config.chatbot.polling_interval_ms / 1000)
            
            # Find code block elements
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            except (TimeoutException, WebDriverException):
                # Page not ready yet or DOM changed, skip this cycle
                continue
            
            # Process each element
            for elem in elements:
                try:
                    # Get unique element ID (Selenium-generated)
                    elem_id = elem.id
                    
                    # Extract text
                    current_text = elem.text.strip()
                    
                    # Skip empty
                    if not current_text:
                        continue
                    
                    # Stability check: only process if text unchanged since last poll
                    if elem_id in last_seen_texts:
                        prev_text = last_seen_texts[elem_id]
                        
                        if prev_text == current_text:
                            # Text is stable — check deduplication
                            try:
                                block = CodeBlock.from_raw(current_text, self.driver.current_url)
                            except ValueError:
                                # Empty text after normalization
                                continue
                            
                            if block.content_hash not in self._seen_hashes:
                                # New block!
                                self._seen_hashes.add(block.content_hash)
                                logger.debug(
                                    f"Code block detected | hash={block.content_hash[:8]} | "
                                    f"length={len(block.raw_text)}"
                                )
                                yield block
                    
                    # Update last seen text
                    last_seen_texts[elem_id] = current_text
                
                except Exception as e:
                    # Don't crash the whole loop for one element
                    logger.debug(f"Error processing element: {e}")
                    continue
    
    async def stop(self) -> None:
        """Close browser cleanly.
        
        Example:
            >>> await sniffer.stop()
        """
        if self.driver:
            logger.info("Closing browser...")
            try:
                self.driver.quit()
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
            finally:
                self.driver = None
