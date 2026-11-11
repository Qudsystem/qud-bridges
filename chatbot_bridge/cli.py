"""Command-line interface for chatbot bridge."""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

from .core.config import BridgeConfig
from .core.bridge_system import BridgeSystem
from .utils.logger import get_logger


def create_default_config(output_path: str = "config.yaml"):
    """
    Create default configuration file.
    
    Args:
        output_path: Path to save configuration file
    """
    config = BridgeConfig(
        project_root=str(Path.cwd()),
        sessions_dir="./sessions",
        logs_dir="./logs"
    )
    
    config.to_yaml(output_path)
    print(f"✅ Configuration file created: {output_path}")
    print(f"Please edit the file to customize settings.")


async def start_session(args):
    """Start a new chatbot session."""
    # Load configuration
    config_path = args.config or "config.yaml"
    
    if not Path(config_path).exists():
        print(f"❌ Configuration file not found: {config_path}")
        print(f"Run 'chatbot-bridge config --init' to create one.")
        return 1
    
    try:
        config = BridgeConfig.from_yaml(config_path)
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return 1
    
    # Initialize bridge system
    try:
        bridge = BridgeSystem(config)
    except Exception as e:
        print(f"❌ Failed to initialize bridge system: {e}")
        return 1
    
    # Start session
    try:
        print(f"🚀 Starting session with {args.chatbot}...")
        
        session_id = await bridge.start_session(
            chatbot_name=args.chatbot,
            session_id=args.session
        )
        
        print(f"✅ Session started: {session_id}")
        print(f"Monitoring chatbot conversation...")
        print(f"Press Ctrl+C to stop.")
        
        # Keep running until interrupted
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print(f"\n⏹️  Stopping session...")
            await bridge.stop_session(session_id)
            print(f"✅ Session stopped.")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


async def stop_session(args):
    """Stop an active session."""
    # Load configuration
    config_path = args.config or "config.yaml"
    
    if not Path(config_path).exists():
        print(f"❌ Configuration file not found: {config_path}")
        return 1
    
    try:
        config = BridgeConfig.from_yaml(config_path)
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return 1
    
    # Initialize bridge system
    try:
        bridge = BridgeSystem(config)
    except Exception as e:
        print(f"❌ Failed to initialize bridge system: {e}")
        return 1
    
    # Stop session
    try:
        await bridge.stop_session(args.session)
        print(f"✅ Session stopped: {args.session}")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def list_sessions(args):
    """List all sessions."""
    # Load configuration
    config_path = args.config or "config.yaml"
    
    if not Path(config_path).exists():
        print(f"❌ Configuration file not found: {config_path}")
        return 1
    
    try:
        config = BridgeConfig.from_yaml(config_path)
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return 1
    
    # Initialize session manager
    from .core.session_manager import SessionManager
    session_manager = SessionManager(config.sessions_dir)
    
    # List sessions
    sessions = session_manager.list_sessions(args.chatbot)
    
    if not sessions:
        print("No sessions found.")
        return 0
    
    print(f"\n{'ID':<40} {'Chatbot':<15} {'Status':<10} {'Messages':<10} {'Commands':<10}")
    print("-" * 95)
    
    for session in sessions:
        status = "Active" if session['is_active'] else "Inactive"
        print(f"{session['id']:<40} {session['chatbot_name']:<15} {status:<10} {session['message_count']:<10} {session['command_count']:<10}")
    
    print()
    return 0


def config_command(args):
    """Handle config command."""
    if args.init:
        output_path = args.output or "config.yaml"
        create_default_config(output_path)
        return 0
    else:
        print("Usage: chatbot-bridge config --init [--output PATH]")
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Chatbot Bridge Automation - Transform chatbots into APIs",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--config',
        '-c',
        help='Path to configuration file (default: config.yaml)',
        default=None
    )
    
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Start command
    start_parser = subparsers.add_parser('start', help='Start a new chatbot session')
    start_parser.add_argument(
        '--chatbot',
        required=True,
        choices=['deepseek', 'chatgpt', 'claude'],
        help='Chatbot platform to use'
    )
    start_parser.add_argument(
        '--session',
        help='Existing session ID to resume'
    )
    
    # Stop command
    stop_parser = subparsers.add_parser('stop', help='Stop an active session')
    stop_parser.add_argument(
        '--session',
        required=True,
        help='Session ID to stop'
    )
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all sessions')
    list_parser.add_argument(
        '--chatbot',
        choices=['deepseek', 'chatgpt', 'claude'],
        help='Filter by chatbot platform'
    )
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Manage configuration')
    config_parser.add_argument(
        '--init',
        action='store_true',
        help='Create default configuration file'
    )
    config_parser.add_argument(
        '--output',
        help='Output path for configuration file'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    if args.command == 'start':
        return asyncio.run(start_session(args))
    elif args.command == 'stop':
        return asyncio.run(stop_session(args))
    elif args.command == 'list':
        return list_sessions(args)
    elif args.command == 'config':
        return config_command(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
