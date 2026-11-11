"""Browser automation components."""

from .browser import BrowserAutomation
from .human_behavior import HumanBehaviorSimulator
from .proxy_manager import ProxyManager, ProxyConfig
from .captcha_resolver import CAPTCHAResolver

__all__ = [
    'BrowserAutomation',
    'HumanBehaviorSimulator',
    'ProxyManager',
    'ProxyConfig',
    'CAPTCHAResolver',
]
