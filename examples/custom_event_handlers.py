"""Example with custom event handlers."""

import asyncio
from chatbot_bridge import ChatbotBridge


async def on_command_detected(commands):
    """Called when commands are detected in chatbot messages."""
    print(f"\n🔍 Detected {len(commands)} command(s):")
    for cmd in commands:
        print(f"  - Type: {cmd.operation_type}")
        if cmd.file_path:
            print(f"    File: {cmd.file_path}")
        if cmd.language:
            print(f"    Language: {cmd.language}")


async def on_execution_complete(result):
    """Called when command execution completes."""
    status = "✅ Success" if result.success else "❌ Failed"
    print(f"\n{status} - Execution time: {result.execution_time:.2f}s")
    
    if result.stdout:
        print(f"Output: {result.stdout[:100]}...")
    
    if result.error_message:
        print(f"Error: {result.error_message}")


async def on_error(error):
    """Called when an error occurs."""
    print(f"\n⚠️  Error: {error}")


async def main():
    """Example with custom event handlers."""
    async with ChatbotBridge(config_path="config.yaml") as bridge:
        # Register event handlers
        bridge.on_command_detected(on_command_detected)
        bridge.on_execution_complete(on_execution_complete)
        bridge.on_error(on_error)
        
        print("Starting session with custom event handlers...")
        session_id = await bridge.start("deepseek")
        print(f"Session: {session_id}\n")
        
        print("Event handlers registered:")
        print("  - on_command_detected: Log detected commands")
        print("  - on_execution_complete: Log execution results")
        print("  - on_error: Log errors")
        print("\nPress Ctrl+C to stop.")
        
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")


if __name__ == "__main__":
    asyncio.run(main())
