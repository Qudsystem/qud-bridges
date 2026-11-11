"""Browser automation with stealth features using Playwright."""

import asyncio
import random
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright
from chatbot_bridge.automation.human_behavior import HumanBehaviorSimulator


class BrowserAutomation:
    """
    Handles browser automation using Playwright with anti-detection measures.
    
    Features:
    - Stealth configuration to avoid detection
    - User agent randomization
    - Automation flag hiding
    - Dynamic element detection with fallbacks
    - Screenshot capture for debugging
    """
    
    def __init__(
        self,
        headless: bool = False,
        user_agent: Optional[str] = None,
        proxy_config: Optional[Dict[str, str]] = None,
        screenshots_dir: str = "./screenshots"
    ):
        """
        Initialize browser automation.
        
        Args:
            headless: Whether to run browser in headless mode
            user_agent: Custom user agent string (random if None)
            proxy_config: Proxy configuration dict
            screenshots_dir: Directory to save diagnostic screenshots
        """
        self.headless = headless
        self.user_agent = user_agent or self._get_random_user_agent()
        self.proxy_config = proxy_config
        self.screenshots_dir = Path(screenshots_dir)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        
        # Element detection strategies
        self.selector_strategies = [
            "css",
            "xpath", 
            "text",
            "aria_label",
            "placeholder",
            "role"
        ]
    
    async def launch_browser(self, profile_path: Optional[str] = None) -> Browser:
        """
        Launch browser with stealth configuration.
        
        Args:
            profile_path: Path to browser profile for session persistence
            
        Returns:
            Playwright Browser instance
        """
        self.playwright = await async_playwright().start()
        
        # Browser launch arguments for stealth
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--disable-extensions-except=",
            "--disable-extensions",
            "--disable-plugins",
            "--disable-images",  # Faster loading
            "--disable-javascript-harmony-shipping",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-backgrounding-occluded-windows",
            "--disable-ipc-flooding-protection"
        ]
        
        # Viewport size randomization
        viewport_options = [
            {"width": 1366, "height": 768},
            {"width": 1440, "height": 900},
            {"width": 1920, "height": 1080},
            {"width": 1280, "height": 720}
        ]
        viewport = random.choice(viewport_options)
        
        # Launch options
        launch_options = {
            "headless": self.headless,
            "args": launch_args,
            "ignore_default_args": ["--enable-automation"],
        }
        
        # Add proxy if configured
        if self.proxy_config:
            launch_options["proxy"] = self.proxy_config
        
        # Use persistent context if profile path provided
        if profile_path:
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=profile_path,
                viewport=viewport,
                user_agent=self.user_agent,
                **launch_options
            )
            self.browser = self.context.browser
        else:
            self.browser = await self.playwright.chromium.launch(**launch_options)
            self.context = await self.browser.new_context(
                viewport=viewport,
                user_agent=self.user_agent
            )
        
        return self.browser
    
    async def new_page(self) -> Page:
        """Create new page with stealth configuration."""
        if not self.context:
            raise RuntimeError("Browser not launched. Call launch_browser() first.")
        
        page = await self.context.new_page()
        await self.hide_automation_flags(page)
        return page
    
    async def hide_automation_flags(self, page: Page) -> None:
        """
        Inject JavaScript to hide automation detection flags.
        
        Args:
            page: Playwright page instance
        """
        stealth_script = """
        // Hide webdriver property
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        
        // Mock plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
        
        // Mock languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });
        
        // Mock permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Mock chrome runtime
        if (!window.chrome) {
            window.chrome = {};
        }
        if (!window.chrome.runtime) {
            window.chrome.runtime = {};
        }
        
        // Hide automation indicators
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        """
        
        await page.add_init_script(stealth_script)
    
    async def find_element(
        self,
        page: Page,
        selectors: List[str],
        timeout: int = 30000,
        strategy: str = "any"
    ) -> Optional[str]:
        """
        Find element using multiple selector strategies with fallback.
        
        Args:
            page: Playwright page instance
            selectors: List of selectors to try
            timeout: Maximum wait time in milliseconds
            strategy: "any" (first match) or "all" (all must match)
            
        Returns:
            Working selector if found, None otherwise
        """
        start_time = time.time()
        
        while (time.time() - start_time) * 1000 < timeout:
            for selector in selectors:
                try:
                    # Try different selector types
                    if selector.startswith("//"):
                        # XPath selector
                        elements = await page.locator(f"xpath={selector}").count()
                    elif selector.startswith("text="):
                        # Text selector
                        elements = await page.locator(selector).count()
                    elif selector.startswith("role="):
                        # ARIA role selector
                        elements = await page.locator(selector).count()
                    else:
                        # CSS selector
                        elements = await page.locator(selector).count()
                    
                    if elements > 0:
                        return selector
                        
                except Exception:
                    continue
            
            # Wait a bit before retrying
            await asyncio.sleep(0.5)
        
        return None
    
    async def smart_click(
        self,
        page: Page,
        selectors: List[str],
        human_behavior: Optional[HumanBehaviorSimulator] = None,
        timeout: int = 30000
    ) -> bool:
        """
        Click element with smart detection and human behavior.
        
        Args:
            page: Playwright page instance
            selectors: List of selectors to try
            human_behavior: Human behavior simulator
            timeout: Maximum wait time
            
        Returns:
            True if clicked successfully, False otherwise
        """
        working_selector = await self.find_element(page, selectors, timeout)
        
        if not working_selector:
            await self.take_diagnostic_screenshot(page, "element_not_found")
            return False
        
        try:
            if human_behavior:
                await human_behavior.click_with_movement(page, working_selector)
            else:
                await page.click(working_selector)
            return True
        except Exception as e:
            await self.take_diagnostic_screenshot(page, f"click_failed_{str(e)[:50]}")
            return False
    
    async def smart_type(
        self,
        page: Page,
        selectors: List[str],
        text: str,
        human_behavior: Optional[HumanBehaviorSimulator] = None,
        timeout: int = 30000
    ) -> bool:
        """
        Type text with smart detection and human behavior.
        
        Args:
            page: Playwright page instance
            selectors: List of selectors to try
            text: Text to type
            human_behavior: Human behavior simulator
            timeout: Maximum wait time
            
        Returns:
            True if typed successfully, False otherwise
        """
        working_selector = await self.find_element(page, selectors, timeout)
        
        if not working_selector:
            await self.take_diagnostic_screenshot(page, "input_not_found")
            return False
        
        try:
            if human_behavior:
                await human_behavior.type_text(page, working_selector, text)
            else:
                await page.fill(working_selector, text)
            return True
        except Exception as e:
            await self.take_diagnostic_screenshot(page, f"type_failed_{str(e)[:50]}")
            return False
    
    async def wait_for_element(
        self,
        page: Page,
        selectors: List[str],
        timeout: int = 30000,
        state: str = "visible"
    ) -> Optional[str]:
        """
        Wait for element to appear with multiple selector fallbacks.
        
        Args:
            page: Playwright page instance
            selectors: List of selectors to try
            timeout: Maximum wait time
            state: Element state to wait for
            
        Returns:
            Working selector if found, None otherwise
        """
        start_time = time.time()
        
        while (time.time() - start_time) * 1000 < timeout:
            for selector in selectors:
                try:
                    await page.wait_for_selector(selector, timeout=1000, state=state)
                    return selector
                except Exception:
                    continue
            
            await asyncio.sleep(0.5)
        
        return None
    
    async def take_diagnostic_screenshot(
        self,
        page: Page,
        reason: str
    ) -> str:
        """
        Take screenshot for debugging when element detection fails.
        
        Args:
            page: Playwright page instance
            reason: Reason for taking screenshot
            
        Returns:
            Path to saved screenshot
        """
        timestamp = int(time.time())
        filename = f"debug_{reason}_{timestamp}.png"
        screenshot_path = self.screenshots_dir / filename
        
        try:
            await page.screenshot(path=str(screenshot_path), full_page=True)
            return str(screenshot_path)
        except Exception:
            return ""
    
    async def get_page_info(self, page: Page) -> Dict[str, Any]:
        """Get diagnostic information about current page."""
        try:
            return {
                "url": page.url,
                "title": await page.title(),
                "viewport": await page.viewport_size(),
                "user_agent": await page.evaluate("navigator.userAgent"),
                "cookies_count": len(await page.context.cookies()),
                "local_storage_keys": await page.evaluate("Object.keys(localStorage).length"),
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_random_user_agent(self) -> str:
        """Get random realistic user agent string."""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        ]
        return random.choice(user_agents)
    
    async def close(self):
        """Clean up browser resources."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.launch_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()