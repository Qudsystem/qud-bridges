"""Browser automation with stealth features."""

import asyncio
import random
import string
from typing import Optional, List
from pathlib import Path
from playwright.async_api import Browser, Page, ElementHandle, async_playwright


class BrowserAutomation:
    """
    Handles all browser automation using Playwright with anti-detection measures.
    """
    
    # Common user agents for randomization
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    ]
    
    # JavaScript to hide automation flags
    STEALTH_JS = """
    // Overwrite the `navigator.webdriver` property
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });
    
    // Overwrite the `plugins` property to add fake plugins
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5]
    });
    
    // Overwrite the `languages` property
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en']
    });
    
    // Remove automation-related properties
    delete navigator.__proto__.webdriver;
    
    // Mock chrome object
    window.chrome = {
        runtime: {}
    };
    
    // Mock permissions
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );
    """
    
    def __init__(
        self,
        headless: bool = False,
        user_agent: Optional[str] = None,
        proxy_manager: Optional[any] = None
    ):
        """
        Initialize browser automation.
        
        Args:
            headless: Whether to run browser in headless mode
            user_agent: Custom user agent string (random if None)
            proxy_manager: Optional proxy manager for rotating proxies
        """
        self.headless = headless
        self.user_agent = user_agent or random.choice(self.USER_AGENTS)
        self.proxy_manager = proxy_manager
        self.playwright = None
        self.browser = None
    
    async def launch_browser(self, profile_path: Optional[str] = None) -> Browser:
        """
        Launch browser with stealth configuration.
        
        Args:
            profile_path: Path to browser profile for session persistence
            
        Returns:
            Playwright Browser instance
        """
        if not self.playwright:
            self.playwright = await async_playwright().start()
        
        # Prepare launch options
        launch_options = {
            'headless': self.headless,
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ]
        }
        
        # Add user data dir if profile path provided
        if profile_path:
            Path(profile_path).mkdir(parents=True, exist_ok=True)
            launch_options['user_data_dir'] = profile_path
        
        # Add proxy if available
        if self.proxy_manager:
            proxy_config = await self.proxy_manager.get_next_proxy()
            if proxy_config:
                launch_options['proxy'] = {
                    'server': proxy_config.url,
                    'username': proxy_config.username,
                    'password': proxy_config.password
                }
        
        # Launch browser
        self.browser = await self.playwright.chromium.launch(**launch_options)
        
        return self.browser
    
    async def create_context(self, browser: Browser):
        """Create a new browser context with stealth settings."""
        context = await browser.new_context(
            user_agent=self.user_agent,
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York',
            permissions=['geolocation', 'notifications'],
        )
        
        return context
    
    async def hide_automation_flags(self, page: Page) -> None:
        """
        Inject JavaScript to hide automation detection flags.
        
        Args:
            page: Playwright page instance
        """
        await page.add_init_script(self.STEALTH_JS)
    
    async def find_element(
        self,
        page: Page,
        selectors: List[str],
        timeout: int = 30000
    ) -> Optional[ElementHandle]:
        """
        Find element using multiple selector strategies with fallback.
        
        Args:
            page: Playwright page instance
            selectors: List of selectors to try (CSS, XPath, text, ARIA)
            timeout: Maximum wait time in milliseconds
            
        Returns:
            Element handle if found, None otherwise
        """
        for selector in selectors:
            try:
                # Try to wait for the selector
                element = await page.wait_for_selector(
                    selector,
                    timeout=timeout,
                    state='visible'
                )
                
                if element:
                    return element
                    
            except Exception:
                # Selector failed, try next one
                continue
        
        # All selectors failed, take diagnostic screenshot
        await self.take_diagnostic_screenshot(page, "element_not_found")
        
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
        # Create screenshots directory
        screenshots_dir = Path("./screenshots")
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        timestamp = asyncio.get_event_loop().time()
        random_suffix = ''.join(random.choices(string.ascii_lowercase, k=6))
        filename = f"{reason}_{int(timestamp)}_{random_suffix}.png"
        filepath = screenshots_dir / filename
        
        # Take screenshot
        await page.screenshot(path=str(filepath), full_page=True)
        
        return str(filepath)
    
    async def close(self):
        """Close browser and playwright instance."""
        if self.browser:
            await self.browser.close()
            self.browser = None
        
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
