"""Multi-chatbot example - run multiple chatbots simultaneously."""

import asyncio
from chatbot_bridge import ChatbotBridge


async def main():
    """Run multiple chatbot sessions simultaneously."""
    async with ChatbotBridge(config_path="config.yaml") as bridge:
        print("Starting multiple chatbot sessions...")
        
        # Start multiple sessions
        sessions = {}
        
        for chatbot in ["deepseek", "chatgpt", "claude"]:
            try:
                session_id = await bridge.start(chatbot)
                sessions[chatbot] = session_id
                print(f"✅ {chatbot}: {session_id}")
            except Exception as e:
                print(f"❌ Failed to start {chatbot}: {e}")
        
        print(f"\n{len(sessions)} sessions active.")
        print("All chatbots are being monitored simultaneously.")
        print("Press Ctrl+C to stop all sessions.")
        
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping all sessions...")


if __name__ == "__main__":
    asyncio.run(main())
