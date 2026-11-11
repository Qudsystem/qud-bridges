"""CAPTCHA resolution with automatic and manual fallback."""

import asyncio
import aiohttp
from typing import Optional
from playwright.async_api import Page


class CAPTCHAResolver:
    """
    Resolves CAPTCHA challenges using 2captcha service or manual intervention.
    """
    
    # CAPTCHA detection selectors
    CAPTCHA_SELECTORS = {
        'recaptcha_v2': [
            'iframe[src*="recaptcha"]',
            '.g-recaptcha',
            '#recaptcha'
        ],
        'recaptcha_v3': [
            'script[src*="recaptcha/releases"]'
        ],
        'hcaptcha': [
            'iframe[src*="hcaptcha"]',
            '.h-captcha',
            '#hcaptcha'
        ]
    }
    
    # 2captcha API endpoint
    TWOCAPTCHA_API = "https://2captcha.com/in.php"
    TWOCAPTCHA_RESULT_API = "https://2captcha.com/res.php"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 120
    ):
        """
        Initialize CAPTCHA resolver.
        
        Args:
            api_key: 2captcha API key (manual mode if None)
            timeout: Maximum time to wait for solution in seconds
        """
        self.api_key = api_key
        self.timeout = timeout
    
    async def detect_captcha(self, page: Page) -> Optional[str]:
        """
        Detect if CAPTCHA is present on page.
        
        Args:
            page: Playwright page instance
            
        Returns:
            CAPTCHA type (recaptcha_v2, recaptcha_v3, hcaptcha) or None
        """
        # Check for each CAPTCHA type
        for captcha_type, selectors in self.CAPTCHA_SELECTORS.items():
            for selector in selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        return captcha_type
                except Exception:
                    continue
        
        return None
    
    async def solve_captcha(
        self,
        page: Page,
        captcha_type: str,
        max_attempts: int = 3
    ) -> bool:
        """
        Solve CAPTCHA challenge.
        
        Args:
            page: Playwright page instance
            captcha_type: Type of CAPTCHA
            max_attempts: Maximum solution attempts
            
        Returns:
            True if solved successfully, False otherwise
        """
        for attempt in range(max_attempts):
            try:
                if self.api_key:
                    # Try automatic solution with 2captcha
                    solution = await self._solve_with_service(page, captcha_type)
                    
                    if solution:
                        # Inject solution into page
                        success = await self._inject_solution(page, captcha_type, solution)
                        if success:
                            return True
                else:
                    # Fall back to manual solution
                    success = await self._solve_manually(page)
                    if success:
                        return True
                
                # Wait before retry
                if attempt < max_attempts - 1:
                    await asyncio.sleep(5)
                    
            except Exception:
                # Continue to next attempt
                continue
        
        return False
    
    async def _solve_with_service(
        self,
        page: Page,
        captcha_type: str
    ) -> Optional[str]:
        """
        Solve CAPTCHA using 2captcha service.
        
        Args:
            page: Playwright page instance
            captcha_type: Type of CAPTCHA
            
        Returns:
            Solution token or None
        """
        try:
            # Get site key from page
            site_key = await self._extract_site_key(page, captcha_type)
            if not site_key:
                return None
            
            # Get page URL
            page_url = page.url
            
            # Submit CAPTCHA to 2captcha
            task_id = await self._submit_captcha(captcha_type, site_key, page_url)
            if not task_id:
                return None
            
            # Poll for solution
            solution = await self._get_solution(task_id)
            return solution
            
        except Exception:
            return None
    
    async def _extract_site_key(self, page: Page, captcha_type: str) -> Optional[str]:
        """Extract CAPTCHA site key from page."""
        try:
            if captcha_type == 'recaptcha_v2' or captcha_type == 'recaptcha_v3':
                # Try to find data-sitekey attribute
                site_key = await page.evaluate("""
                    () => {
                        const element = document.querySelector('[data-sitekey]');
                        return element ? element.getAttribute('data-sitekey') : null;
                    }
                """)
                return site_key
            
            elif captcha_type == 'hcaptcha':
                # Try to find data-sitekey for hCaptcha
                site_key = await page.evaluate("""
                    () => {
                        const element = document.querySelector('[data-sitekey]');
                        return element ? element.getAttribute('data-sitekey') : null;
                    }
                """)
                return site_key
            
        except Exception:
            return None
    
    async def _submit_captcha(
        self,
        captcha_type: str,
        site_key: str,
        page_url: str
    ) -> Optional[str]:
        """Submit CAPTCHA to 2captcha service."""
        try:
            params = {
                'key': self.api_key,
                'method': 'userrecaptcha' if 'recaptcha' in captcha_type else 'hcaptcha',
                'googlekey': site_key,
                'pageurl': page_url,
                'json': 1
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.TWOCAPTCHA_API, data=params) as response:
                    result = await response.json()
                    
                    if result.get('status') == 1:
                        return result.get('request')
                    
                    return None
                    
        except Exception:
            return None
    
    async def _get_solution(self, task_id: str) -> Optional[str]:
        """Poll 2captcha for solution."""
        try:
            # Poll every 5 seconds
            for _ in range(self.timeout // 5):
                await asyncio.sleep(5)
                
                params = {
                    'key': self.api_key,
                    'action': 'get',
                    'id': task_id,
                    'json': 1
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(self.TWOCAPTCHA_RESULT_API, params=params) as response:
                        result = await response.json()
                        
                        if result.get('status') == 1:
                            return result.get('request')
                        
                        # Check if still processing
                        if result.get('request') == 'CAPCHA_NOT_READY':
                            continue
                        
                        # Error occurred
                        return None
            
            return None
            
        except Exception:
            return None
    
    async def _inject_solution(
        self,
        page: Page,
        captcha_type: str,
        solution: str
    ) -> bool:
        """Inject CAPTCHA solution into page."""
        try:
            if 'recaptcha' in captcha_type:
                # Inject reCAPTCHA solution
                await page.evaluate(f"""
                    () => {{
                        document.getElementById('g-recaptcha-response').innerHTML = '{solution}';
                    }}
                """)
                
                # Trigger callback if exists
                await page.evaluate("""
                    () => {
                        if (typeof grecaptcha !== 'undefined') {
                            grecaptcha.getResponse = () => document.getElementById('g-recaptcha-response').value;
                        }
                    }
                """)
                
                return True
            
            elif captcha_type == 'hcaptcha':
                # Inject hCaptcha solution
                await page.evaluate(f"""
                    () => {{
                        document.querySelector('[name="h-captcha-response"]').value = '{solution}';
                    }}
                """)
                
                return True
            
        except Exception:
            return False
    
    async def _solve_manually(self, page: Page) -> bool:
        """
        Request manual CAPTCHA solution from user.
        
        Args:
            page: Playwright page instance
            
        Returns:
            True if user solved it, False otherwise
        """
        print("\n" + "="*60)
        print("CAPTCHA DETECTED - Manual intervention required")
        print("="*60)
        print(f"Please solve the CAPTCHA in the browser window.")
        print(f"Page URL: {page.url}")
        print("Press Enter when you have solved the CAPTCHA...")
        print("="*60 + "\n")
        
        # Wait for user input (in a real implementation, this would be async)
        # For now, we'll wait and check periodically
        for _ in range(self.timeout):
            await asyncio.sleep(1)
            
            # Check if CAPTCHA is still present
            captcha_type = await self.detect_captcha(page)
            if not captcha_type:
                # CAPTCHA solved!
                print("✅ CAPTCHA appears to be solved. Continuing...")
                return True
        
        print("❌ CAPTCHA resolution timeout.")
        return False
