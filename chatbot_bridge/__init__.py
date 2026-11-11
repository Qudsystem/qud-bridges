"""
Chatbot Bridge Automation System

A professional bridge system that connects free chatbots (DeepSeek, ChatGPT, Claude)
and transforms them into fully-functional APIs by monitoring conversations, extracting
programming commands, and executing them safely on the local machine.
"""

__version__ = "0.1.0"
__author__ = "Chatbot Bridge Team"

from chatbot_bridge.api import ChatbotBridge, start_bridge
from chatbot_bridge.core.bridge_system import BridgeSystem
from chatbot_bridge.core.config import BridgeConfig
from chatbot_bridge.core.code_executor import ExecutionResult

__all__ = [
    "ChatbotBridge",
    "start_bridge",
    "BridgeSystem",
    "BridgeConfig",
    "ExecutionResult",
]

