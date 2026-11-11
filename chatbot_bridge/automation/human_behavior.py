"""Human behavior simulation for browser interactions."""

import asyncio
import random
import math
from typing import List, Tuple, Optional
from playwright.async_api import Page


class HumanBehaviorSimulator:
    """
    Simulates human behavior for browser interactions to avoid detection.
    
    Features:
    - Natural mouse movement using bezier curves
    - Human-like typing with delays and occasional typos
    - Random pauses between actions
    - Natural scrolling behavior
    - Response delays before replying
    """
    
    def __init__(
        self,
        typing_delay_range: Tuple[int, int] = (50, 150),
        typo_rate: float = 0.02,
        pause_range: Tuple[int, int] = (500, 3000),
        response_delay_range: Tuple[int, int] = (1000, 5000)
    ):
        """
        Initialize human behavior simulator.
        
        Args:
            typing_delay_range: Min and max ms between keystrokes
            typo_rate: Probability of typing error (0.0 to 1.0)
            pause_range: Min and max ms for random pauses
            response_delay_range: Min and max ms before responding
        """
        self.typing_delay_range = typing_delay_range
        self.typo_rate = typo_rate
        self.pause_range = pause_range
        self.response_delay_range = response_delay_range
        
        # Common typos mapping
        self.typo_map = {
            'a': ['s', 'q', 'w'],
            'b': ['v', 'g', 'h', 'n'],
            'c': ['x', 'd', 'f', 'v'],
            'd': ['s', 'e', 'r', 'f', 'c', 'x'],
            'e': ['w', 's', 'd', 'r'],
            'f': ['d', 'r', 't', 'g', 'v', 'c'],
            'g': ['f', 't', 'y', 'h', 'b', 'v'],
            'h': ['g', 'y', 'u', 'j', 'n', 'b'],
            'i': ['u', 'j', 'k', 'o'],
            'j': ['h', 'u', 'i', 'k', 'm', 'n'],
            'k': ['j', 'i', 'o', 'l', 'm'],
            'l': ['k', 'o', 'p'],
            'm': ['n', 'j', 'k'],
            'n': ['b', 'h', 'j', 'm'],
            'o': ['i', 'k', 'l', 'p'],
            'p': ['o', 'l'],
            'q': ['w', 'a'],
            'r': ['e', 'd', 'f', 't'],
            's': ['a', 'w', 'e', 'd', 'x', 'z'],
            't': ['r', 'f', 'g', 'y'],
            'u': ['y', 'h', 'j', 'i'],
            'v': ['c', 'f', 'g', 'b'],
            'w': ['q', 'a', 's', 'e'],
            'x': ['z', 's', 'd', 'c'],
            'y': ['t', 'g', 'h', 'u'],
            'z': ['x', 's']
        }
    
    async def type_text(
        self,
        page: Page,
        selector: str,
        text: str,
        clear_first: bool = True
    ) -> None:
        """
        Type text with human-like delays and occasional typos.
        
        Args:
            page: Playwright page instance
            selector: Element selector
            text: Text to type
            clear_first: Whether to clear field before typing
        """
        # Click on the element first
        await page.click(selector)
        await self.random_pause(100, 300)
        
        # Clear field if requested
        if clear_first:
            await page.fill(selector, "")
            await self.random_pause(50, 150)
        
        # Type character by character with human behavior
        for i, char in enumerate(text):
            # Decide if we should make a typo
            if random.random() < self.typo_rate and char.lower() in self.typo_map:
                # Make a typo
                typo_char = random.choice(self.typo_map[char.lower()])
                await page.type(selector, typo_char, delay=0)
                
                # Pause as if realizing the mistake
                await self.random_pause(200, 800)
                
                # Backspace to correct
                await page.keyboard.press("Backspace")
                await self.random_pause(100, 300)
                
                # Type the correct character
                await page.type(selector, char, delay=0)
            else:
                # Type normally
                await page.type(selector, char, delay=0)
            
            # Random delay between keystrokes
            delay = random.uniform(
                self.typing_delay_range[0],
                self.typing_delay_range[1]
            )
            await asyncio.sleep(delay / 1000)
            
            # Occasional longer pauses (thinking)
            if random.random() < 0.05:  # 5% chance
                await self.random_pause(300, 1000)
    
    async def move_mouse(
        self,
        page: Page,
        target_x: int,
        target_y: int,
        steps: int = 20
    ) -> None:
        """
        Move mouse using bezier curve for natural movement.
        
        Args:
            page: Playwright page instance
            target_x: Target X coordinate
            target_y: Target Y coordinate
            steps: Number of intermediate points
        """
        # Get current mouse position (approximate)
        current_pos = await page.evaluate("() => ({ x: window.mouseX || 0, y: window.mouseY || 0 })")
        start_x = current_pos.get('x', 0)
        start_y = current_pos.get('y', 0)
        
        # Generate bezier curve points
        points = self._generate_bezier_curve(
            (start_x, start_y),
            (target_x, target_y),
            steps
        )
        
        # Move mouse along the curve
        for x, y in points:
            await page.mouse.move(x, y)
            # Small delay between movements
            await asyncio.sleep(random.uniform(0.01, 0.03))
        
        # Update stored mouse position
        await page.evaluate(f"window.mouseX = {target_x}; window.mouseY = {target_y};")
    
    async def click_with_movement(
        self,
        page: Page,
        selector: str,
        button: str = "left"
    ) -> None:
        """
        Click element with natural mouse movement.
        
        Args:
            page: Playwright page instance
            selector: Element selector
            button: Mouse button to click
        """
        # Get element position
        element = page.locator(selector)
        box = await element.bounding_box()
        
        if box:
            # Add some randomness to click position
            click_x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
            click_y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
            
            # Move mouse to position
            await self.move_mouse(page, int(click_x), int(click_y))
            
            # Small pause before clicking
            await self.random_pause(50, 200)
            
            # Click
            await page.mouse.click(click_x, click_y, button=button)
        else:
            # Fallback to direct click
            await page.click(selector, button=button)
    
    async def scroll_naturally(
        self,
        page: Page,
        distance: int,
        direction: str = "down"
    ) -> None:
        """
        Scroll page with natural human-like behavior.
        
        Args:
            page: Playwright page instance
            distance: Scroll distance in pixels
            direction: Scroll direction ("up" or "down")
        """
        # Break scrolling into smaller chunks
        chunk_size = random.randint(100, 300)
        chunks = abs(distance) // chunk_size
        remainder = abs(distance) % chunk_size
        
        scroll_delta = chunk_size if direction == "down" else -chunk_size
        
        for _ in range(chunks):
            await page.mouse.wheel(0, scroll_delta)
            # Random pause between scroll chunks
            await self.random_pause(100, 400)
        
        # Handle remainder
        if remainder > 0:
            final_delta = remainder if direction == "down" else -remainder
            await page.mouse.wheel(0, final_delta)
    
    async def read_pause(self, text_length: int) -> None:
        """
        Pause as if reading text (longer for more text).
        
        Args:
            text_length: Length of text being "read"
        """
        # Base reading time: ~200 words per minute
        # Assume average 5 characters per word
        words = text_length / 5
        reading_time = (words / 200) * 60  # seconds
        
        # Add randomness and minimum/maximum bounds
        pause_time = random.uniform(
            max(1.0, reading_time * 0.5),
            min(10.0, reading_time * 1.5)
        )
        
        await asyncio.sleep(pause_time)
    
    async def random_pause(
        self,
        min_ms: Optional[int] = None,
        max_ms: Optional[int] = None
    ) -> None:
        """
        Add random pause between actions.
        
        Args:
            min_ms: Minimum pause in milliseconds (uses default if None)
            max_ms: Maximum pause in milliseconds (uses default if None)
        """
        min_val = min_ms if min_ms is not None else self.pause_range[0]
        max_val = max_ms if max_ms is not None else self.pause_range[1]
        
        pause_ms = random.uniform(min_val, max_val)
        await asyncio.sleep(pause_ms / 1000)
    
    async def response_delay(self) -> None:
        """Add delay before responding to messages (thinking time)."""
        delay_ms = random.uniform(
            self.response_delay_range[0],
            self.response_delay_range[1]
        )
        await asyncio.sleep(delay_ms / 1000)
    
    def _generate_bezier_curve(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        steps: int
    ) -> List[Tuple[int, int]]:
        """
        Generate bezier curve points for mouse movement.
        
        Args:
            start: Starting coordinates
            end: Ending coordinates
            steps: Number of points
            
        Returns:
            List of coordinate tuples
        """
        # Generate control points for natural curve
        start_x, start_y = start
        end_x, end_y = end
        
        # Add some randomness to control points
        mid_x = (start_x + end_x) / 2 + random.uniform(-50, 50)
        mid_y = (start_y + end_y) / 2 + random.uniform(-50, 50)
        
        # Control points for cubic bezier
        cp1_x = start_x + (mid_x - start_x) * 0.5 + random.uniform(-30, 30)
        cp1_y = start_y + (mid_y - start_y) * 0.5 + random.uniform(-30, 30)
        cp2_x = end_x + (mid_x - end_x) * 0.5 + random.uniform(-30, 30)
        cp2_y = end_y + (mid_y - end_y) * 0.5 + random.uniform(-30, 30)
        
        points = []
        for i in range(steps + 1):
            t = i / steps
            
            # Cubic bezier formula
            x = (1-t)**3 * start_x + 3*(1-t)**2*t * cp1_x + 3*(1-t)*t**2 * cp2_x + t**3 * end_x
            y = (1-t)**3 * start_y + 3*(1-t)**2*t * cp1_y + 3*(1-t)*t**2 * cp2_y + t**3 * end_y
            
            points.append((int(x), int(y)))
        
        return points
    
    async def simulate_focus_change(self, page: Page) -> None:
        """Simulate user switching focus (tab change, etc.)."""
        # Simulate brief focus loss and return
        await page.evaluate("window.blur()")
        await self.random_pause(1000, 3000)
        await page.evaluate("window.focus()")
        await self.random_pause(200, 500)
    
    async def simulate_idle_behavior(self, page: Page) -> None:
        """Simulate idle user behavior (small mouse movements, etc.)."""
        # Small random mouse movements
        for _ in range(random.randint(1, 3)):
            current_pos = await page.evaluate("() => ({ x: window.mouseX || 500, y: window.mouseY || 300 })")
            new_x = current_pos['x'] + random.randint(-20, 20)
            new_y = current_pos['y'] + random.randint(-20, 20)
            
            await page.mouse.move(new_x, new_y)
            await self.random_pause(500, 1500)
    
    def adjust_timing_for_fatigue(self, session_duration_minutes: int) -> None:
        """
        Adjust timing parameters based on session duration (simulate fatigue).
        
        Args:
            session_duration_minutes: How long the session has been running
        """
        # Increase delays as session gets longer (fatigue effect)
        fatigue_factor = 1 + (session_duration_minutes / 60) * 0.2  # 20% slower per hour
        
        self.typing_delay_range = (
            int(self.typing_delay_range[0] * fatigue_factor),
            int(self.typing_delay_range[1] * fatigue_factor)
        )
        
        self.pause_range = (
            int(self.pause_range[0] * fatigue_factor),
            int(self.pause_range[1] * fatigue_factor)
        )