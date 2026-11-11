"""Basic usage example for chatbot bridge."""

import asyncio
from chatbot_bridge import ChatbotBridge


async def main():
    """Basic usage example."""
    # Create bridge with configuration
    async with ChatbotBridge(config_path="config.yaml") as bridge:
        print("Starting DeepSeek session...")
        
        # Start session
        session_id = await bridge.start("deepseek")
        print(f"Session started: {session_id}")
        
        print("Bridge is now monitoring the chatbot conversation.")
        print("Commands will be automatically detected and executed.")
        print("Press Ctrl+C to stop.")
        
        try:
            # Keep running
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping session...")


if __name__ == "__main__":
    asyncio.run(main())
