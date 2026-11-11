"""Bridge-to-IDE — Sprint 1 Foundation.

Command-line interface for the Bridge. Monitors chatbot page and prints
captured code blocks to terminal with syntax highlighting.

Usage:
    python main.py                    # Use default config
    python main.py --config path.json # Use custom config
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click
from loguru import logger
from rich.console import Console
from rich.syntax import Syntax

from config.loader import (
    ConfigNotFoundError,
    ConfigValidationError,
    load_config,
)
from core.sniffer import BrowserNotFoundError, ChatbotLoadError, Sniffer

console = Console()


@click.command()
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    help="Path to settings.json (default: config/settings.json)",
)
def main(config: Path | None) -> None:
    """Bridge-to-IDE — Sprint 1 Foundation.
    
    Monitors DeepSeek chatbot and prints captured code blocks to terminal.
    
    \b
    Controls:
      - Ctrl+C: Stop the Bridge cleanly
    
    \b
    Config:
      - Edit config/settings.json before running
      - Set project_root to your project directory
      - Or use --config to override
    """
    # Load configuration
    try:
        cfg = load_config(config)
    except ConfigNotFoundError as e:
        console.print(f"[bold red]Config Error:[/bold red] {e}", style="red")
        sys.exit(1)
    except ConfigValidationError as e:
        console.print(f"[bold red]Config Validation Failed:[/bold red]", style="red")
        console.print(str(e))
        console.print(
            "\n[yellow]Hint:[/yellow] Check config/settings.json — "
            "did you set project_root?"
        )
        sys.exit(1)
    
    # Setup logging
    logger.remove()  # Remove default handler
    
    # File logging
    log_dir = cfg.logging.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        log_dir / "bridge_{time}.log",
        rotation=cfg.logging.rotation,
        retention=cfg.logging.retention,
        level=cfg.logging.level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    )
    
    # Console logging (via rich)
    if cfg.logging.colorized:
        logger.add(
            lambda msg: console.print(msg, end=""),
            format="<level>{message}</level>",
            level=cfg.logging.level,
        )
    else:
        logger.add(sys.stderr, level=cfg.logging.level)
    
    # Run bridge
    try:
        asyncio.run(run_bridge(cfg))
    except KeyboardInterrupt:
        console.print("\n[yellow]Bridge stopped by user[/yellow]")
        sys.exit(0)


async def run_bridge(cfg):
    """Main bridge loop.
    
    Args:
        cfg: Validated BridgeConfig
    """
    sniffer = Sniffer(cfg)
    
    try:
        # Start browser
        console.print("[bold cyan]Bridge-to-IDE — Sprint 1[/bold cyan]")
        console.print(f"Chatbot: [green]{cfg.chatbot.name}[/green]")
        console.print(f"URL: [blue]{cfg.chatbot.url}[/blue]")
        console.print("\n[yellow]Starting browser...[/yellow]")
        
        await sniffer.start()
        
        console.print("[bold green]✓ Browser ready[/bold green]")
        console.print("\n[cyan]Watching for code blocks... (Ctrl+C to stop)[/cyan]\n")
        
        # Poll for code blocks
        async for block in sniffer.watch():
            # Print detection header
            console.print("\n" + "─" * 60)
            console.print("[bold green]● Code Block Detected[/bold green]")
            console.print(f"  Hash: [cyan]{block.content_hash[:8]}...[/cyan]")
            console.print(f"  URL: [blue]{block.source_url}[/blue]")
            console.print(f"  Length: {len(block.raw_text)} chars")
            console.print("─" * 60 + "\n")
            
            # Syntax highlight code (truncate if very long)
            display_text = block.raw_text
            if len(display_text) > 1000:
                display_text = display_text[:1000] + "\n... (truncated)"
            
            # Try to detect language from content
            language = "python"  # Default
            if "function" in display_text or "const " in display_text:
                language = "javascript"
            elif "def " in display_text or "import " in display_text:
                language = "python"
            elif "<html" in display_text.lower():
                language = "html"
            
            syntax = Syntax(
                display_text,
                language,
                theme="monokai",
                line_numbers=True,
                word_wrap=False,
            )
            console.print(syntax)
            console.print()  # Extra newline
    
    except BrowserNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e}", style="red")
        sys.exit(1)
    
    except ChatbotLoadError as e:
        console.print(f"[bold red]Error:[/bold red] {e}", style="red")
        console.print(
            "\n[yellow]Hint:[/yellow] Check your internet connection and "
            "verify the chatbot URL in config/settings.json"
        )
        sys.exit(1)
    
    except Exception as e:
        console.print(f"[bold red]Unexpected Error:[/bold red] {e}", style="red")
        logger.exception("Fatal error")
        sys.exit(1)
    
    finally:
        await sniffer.stop()


if __name__ == "__main__":
    main()
