"""Proxy management for rotating proxies and avoiding IP blocks."""

import asyncio
import aiohttp
import random
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urlparse


@dataclass
class ProxyConfig:
    """
    Proxy configuration with statistics tracking.
    
    Attributes:
        url: Proxy URL (http://host:port or socks5://user:pass@host:port)
        protocol: Proxy protocol (http, https, socks5)
        username: Optional username for authentication
        password: Optional password for authentication
        last_used: Timestamp of last usage
        failure_count: Number of consecutive failures
        success_count: Number of successful requests
        avg_response_time: Average response time in seconds
        is_working: Whether proxy is currently working
        max_failures: Maximum failures before marking as dead
    """
    
    url: str
    protocol: str = "http"
    username: Optional[str] = None
    password: Optional[str] = None
    last_used: Optional[float] = None
    failure_count: int = 0
    success_count: int = 0
    avg_response_time: float = 0.0
    is_working: bool = True
    max_failures: int = 3
    
    def __post_init__(self):
        """Parse proxy URL and extract components."""
        parsed = urlparse(self.url)
        
        if parsed.scheme:
            self.protocol = parsed.scheme
        
        if parsed.username:
            self.username = parsed.username
        
        if parsed.password:
            self.password = parsed.password
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Playwright proxy config."""
        config = {
            "server": self.url
        }
        
        if self.username and self.password:
            config["username"] = self.username
            config["password"] = self.password
        
        return config
    
    def mark_success(self, response_time: float) -> None:
        """Mark proxy as successful and update stats."""
        self.success_count += 1
        self.failure_count = 0  # Reset failure count on success
        self.is_working = True
        self.last_used = time.time()
        
        # Update average response time
        if self.avg_response_time == 0:
            self.avg_response_time = response_time
        else:
            # Exponential moving average
            self.avg_response_time = 0.7 * self.avg_response_time + 0.3 * response_time
    
    def mark_failure(self) -> None:
        """Mark proxy as failed and update stats."""
        self.failure_count += 1
        
        if self.failure_count >= self.max_failures:
            self.is_working = False
    
    def reset_stats(self) -> None:
        """Reset proxy statistics."""
        self.failure_count = 0
        self.success_count = 0
        self.avg_response_time = 0.0
        self.is_working = True
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        total = self.success_count + self.failure_count
        return (self.success_count / total * 100) if total > 0 else 0.0


class ProxyManager:
    """
    Manages rotating proxies with health checking and statistics.
    
    Features:
    - Automatic proxy rotation
    - Health checking and failure detection
    - Performance monitoring
    - Dead proxy resurrection
    - Load balancing based on performance
    """
    
    def __init__(
        self,
        proxies: List[str],
        rotation_interval: Tuple[int, int] = (10, 20),
        test_timeout: int = 10,
        test_url: str = "http://httpbin.org/ip"
    ):
        """
        Initialize proxy manager.
        
        Args:
            proxies: List of proxy URLs
            rotation_interval: Min and max requests before rotation
            test_timeout: Timeout for proxy testing in seconds
            test_url: URL to use for proxy testing
        """
        self.proxies = [ProxyConfig(url=url) for url in proxies]
        self.rotation_interval = rotation_interval
        self.test_timeout = test_timeout
        self.test_url = test_url
        
        self.current_proxy_index = 0
        self.request_count = 0
        self.next_rotation = random.randint(*rotation_interval)
        
        # Statistics
        self.total_requests = 0
        self.total_failures = 0
        
    async def get_next_proxy(self) -> Optional[ProxyConfig]:
        """
        Get next proxy in rotation.
        
        Returns:
            ProxyConfig or None if no proxies available
        """
        if not self.proxies:
            return None
        
        # Check if we need to rotate
        if self.should_rotate():
            await self._rotate_proxy()
        
        # Find next working proxy
        working_proxies = [p for p in self.proxies if p.is_working]
        
        if not working_proxies:
            # Try to resurrect dead proxies
            await self._resurrect_dead_proxies()
            working_proxies = [p for p in self.proxies if p.is_working]
        
        if not working_proxies:
            return None
        
        # Select proxy (prefer better performing ones)
        proxy = self._select_best_proxy(working_proxies)
        self.request_count += 1
        self.total_requests += 1
        
        return proxy
    
    async def test_proxy(self, proxy: ProxyConfig) -> bool:
        """
        Test if proxy is working.
        
        Args:
            proxy: Proxy configuration
            
        Returns:
            True if proxy works, False otherwise
        """
        start_time = time.time()
        
        try:
            connector = aiohttp.TCPConnector()
            timeout = aiohttp.ClientTimeout(total=self.test_timeout)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            ) as session:
                
                proxy_url = proxy.url
                if proxy.username and proxy.password:
                    # Add auth to URL if not already present
                    parsed = urlparse(proxy.url)
                    if not parsed.username:
                        proxy_url = f"{parsed.scheme}://{proxy.username}:{proxy.password}@{parsed.netloc}{parsed.path}"
                
                async with session.get(
                    self.test_url,
                    proxy=proxy_url
                ) as response:
                    
                    if response.status == 200:
                        response_time = time.time() - start_time
                        proxy.mark_success(response_time)
                        return True
                    else:
                        proxy.mark_failure()
                        return False
                        
        except Exception:
            proxy.mark_failure()
            return False
    
    async def test_all_proxies(self) -> Dict[str, bool]:
        """
        Test all proxies concurrently.
        
        Returns:
            Dictionary mapping proxy URLs to test results
        """
        tasks = []
        for proxy in self.proxies:
            task = asyncio.create_task(self.test_proxy(proxy))
            tasks.append((proxy.url, task))
        
        results = {}
        for url, task in tasks:
            try:
                result = await task
                results[url] = result
            except Exception:
                results[url] = False
        
        return results
    
    def mark_proxy_failed(self, proxy: ProxyConfig) -> None:
        """
        Mark proxy as failed and temporarily remove from rotation.
        
        Args:
            proxy: Proxy configuration
        """
        proxy.mark_failure()
        self.total_failures += 1
    
    def mark_proxy_success(self, proxy: ProxyConfig, response_time: float) -> None:
        """
        Mark proxy as successful.
        
        Args:
            proxy: Proxy configuration
            response_time: Response time in seconds
        """
        proxy.mark_success(response_time)
    
    def should_rotate(self) -> bool:
        """
        Check if it's time to rotate proxy.
        
        Returns:
            True if should rotate, False otherwise
        """
        return self.request_count >= self.next_rotation
    
    async def _rotate_proxy(self) -> None:
        """Rotate to next proxy."""
        working_proxies = [p for p in self.proxies if p.is_working]
        
        if len(working_proxies) > 1:
            # Find current proxy index among working proxies
            current_proxy = self.proxies[self.current_proxy_index] if self.current_proxy_index < len(self.proxies) else None
            
            if current_proxy in working_proxies:
                current_working_index = working_proxies.index(current_proxy)
                next_working_index = (current_working_index + 1) % len(working_proxies)
                next_proxy = working_proxies[next_working_index]
                self.current_proxy_index = self.proxies.index(next_proxy)
            else:
                # Current proxy not working, select best available
                best_proxy = self._select_best_proxy(working_proxies)
                self.current_proxy_index = self.proxies.index(best_proxy)
        
        # Reset rotation counter
        self.request_count = 0
        self.next_rotation = random.randint(*self.rotation_interval)
    
    def _select_best_proxy(self, working_proxies: List[ProxyConfig]) -> ProxyConfig:
        """
        Select best proxy based on performance metrics.
        
        Args:
            working_proxies: List of working proxies
            
        Returns:
            Best proxy to use
        """
        if len(working_proxies) == 1:
            return working_proxies[0]
        
        # Score proxies based on success rate and response time
        scored_proxies = []
        
        for proxy in working_proxies:
            # Base score from success rate
            score = proxy.success_rate
            
            # Bonus for faster response times (lower is better)
            if proxy.avg_response_time > 0:
                time_bonus = max(0, 10 - proxy.avg_response_time)  # Up to 10 points for fast proxies
                score += time_bonus
            
            # Penalty for recent failures
            if proxy.failure_count > 0:
                score -= proxy.failure_count * 5
            
            # Bonus for recent usage (load balancing)
            if proxy.last_used:
                time_since_use = time.time() - proxy.last_used
                if time_since_use > 300:  # 5 minutes
                    score += 5  # Bonus for unused proxies
            
            scored_proxies.append((score, proxy))
        
        # Sort by score (highest first) and add some randomness
        scored_proxies.sort(key=lambda x: x[0], reverse=True)
        
        # Select from top 3 with weighted randomness
        top_proxies = scored_proxies[:3]
        weights = [3, 2, 1][:len(top_proxies)]
        
        selected = random.choices(top_proxies, weights=weights)[0]
        return selected[1]
    
    async def _resurrect_dead_proxies(self) -> None:
        """Try to resurrect dead proxies by testing them."""
        dead_proxies = [p for p in self.proxies if not p.is_working]
        
        if not dead_proxies:
            return
        
        # Test a few dead proxies (not all to avoid overhead)
        test_count = min(3, len(dead_proxies))
        test_proxies = random.sample(dead_proxies, test_count)
        
        for proxy in test_proxies:
            # Reset stats and test
            proxy.reset_stats()
            await self.test_proxy(proxy)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get proxy manager statistics."""
        working_count = len([p for p in self.proxies if p.is_working])
        
        stats = {
            "total_proxies": len(self.proxies),
            "working_proxies": working_count,
            "dead_proxies": len(self.proxies) - working_count,
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "success_rate": ((self.total_requests - self.total_failures) / self.total_requests * 100) if self.total_requests > 0 else 0,
            "current_proxy": self.proxies[self.current_proxy_index].url if self.current_proxy_index < len(self.proxies) else None,
            "next_rotation_in": self.next_rotation - self.request_count
        }
        
        # Per-proxy stats
        stats["proxies"] = []
        for proxy in self.proxies:
            stats["proxies"].append({
                "url": proxy.url,
                "is_working": proxy.is_working,
                "success_count": proxy.success_count,
                "failure_count": proxy.failure_count,
                "success_rate": proxy.success_rate,
                "avg_response_time": proxy.avg_response_time,
                "last_used": proxy.last_used
            })
        
        return stats
    
    def add_proxy(self, proxy_url: str) -> None:
        """
        Add new proxy to the pool.
        
        Args:
            proxy_url: Proxy URL to add
        """
        proxy = ProxyConfig(url=proxy_url)
        self.proxies.append(proxy)
    
    def remove_proxy(self, proxy_url: str) -> bool:
        """
        Remove proxy from the pool.
        
        Args:
            proxy_url: Proxy URL to remove
            
        Returns:
            True if removed successfully
        """
        for i, proxy in enumerate(self.proxies):
            if proxy.url == proxy_url:
                del self.proxies[i]
                
                # Adjust current index if needed
                if self.current_proxy_index >= len(self.proxies):
                    self.current_proxy_index = 0
                
                return True
        
        return False
    
    async def health_check(self) -> None:
        """Perform health check on all proxies."""
        await self.test_all_proxies()
    
    def get_working_proxies(self) -> List[ProxyConfig]:
        """Get list of currently working proxies."""
        return [p for p in self.proxies if p.is_working]