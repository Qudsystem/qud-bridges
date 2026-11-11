# Design — Sprint 1: Foundation
**Project:** Bridge-to-IDE  
**Sprint:** 1 — Foundation Layer  
**Owner:** QudSystem  
**Status:** Draft

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                    Sprint 1 Scope                          │
│                                                            │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐     │
│  │   main.py  │───▶│  Sniffer   │───▶│  Executor  │     │
│  │ (CLI only) │    │  (Layer 1) │    │  (Layer 3) │     │
│  └────────────┘    └────────────┘    └────────────┘     │
│         │                 │                  │            │
│         ▼                 ▼                  ▼            │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐     │
│  │   Config   │    │ CodeBlock  │    │ File System│     │
│  │   Loader   │    │   Model    │    │            │     │
│  └────────────┘    └────────────┘    └────────────┘     │
└──────────────────────────────────────────────────────────┘

Note: Parser (Layer 2) is deferred to Sprint 2
```

---

## Module Design

### 1. `config/loader.py`

**Responsibility:** Load and validate configuration from `settings.json`.

**Public Interface:**
```python
from __future__ import annotations
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Literal

class ChatbotConfig(BaseModel):
    name: Literal["deepseek", "claude", "gemini"]
    url: str
    polling_interval_ms: int = Field(gt=0)
    initial_load_wait_ms: int = Field(gt=0)
    max_scroll_depth: int = Field(ge=0)

class IDEConfig(BaseModel):
    name: Literal["cursor", "vscode"]
    project_root: Path
    auto_open_files: bool
    open_delay_ms: int = Field(ge=0)
    
    @field_validator("project_root")
    @classmethod
    def validate_project_root(cls, v: Path) -> Path:
        if str(v) == "REPLACE_WITH_YOUR_PROJECT_PATH":
            raise ValueError("project_root must be set in settings.json")
        if not v.is_absolute():
            raise ValueError("project_root must be an absolute path")
        return v

class BrowserConfig(BaseModel):
    driver: Literal["chrome", "firefox"]
    headless: bool
    user_data_dir: Path
    window_size: tuple[int, int]

class AntiBotConfig(BaseModel):
    enabled: bool
    min_delay_ms: int = Field(gt=0)
    max_delay_ms: int = Field(gt=0)
    mouse_simulation: bool
    max_actions_per_minute: int = Field(gt=0)

class ExecutorConfig(BaseModel):
    dry_run: bool
    auto_backup: bool
    backup_dir: Path
    backup_max_age_days: int = Field(gt=0)
    auto_run_terminal_commands: bool
    terminal_command_timeout_s: int = Field(gt=0)

class LoggingConfig(BaseModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"]
    log_dir: Path
    rotation: str
    retention: str
    colorized: bool

class AdapterConfig(BaseModel):
    """Dynamic adapter config — indexed by chatbot name."""
    code_block_selector: str
    copy_button_selector: str
    message_container_selector: str

class BridgeConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    chatbot: ChatbotConfig
    ide: IDEConfig
    browser: BrowserConfig
    anti_bot: AntiBotConfig
    executor: ExecutorConfig
    logging: LoggingConfig
    adapters: dict[str, AdapterConfig]

# Main loader function
def load_config(config_path: Path | None = None) -> BridgeConfig:
    """Load and validate config from JSON file.
    
    Args:
        config_path: Optional override. Defaults to BRIDGE_CONFIG_PATH env var,
                    then ./config/settings.json
    
    Raises:
        ConfigNotFoundError: If config file doesn't exist
        ConfigValidationError: If validation fails
    """
    ...

# Custom exceptions
class ConfigNotFoundError(FileNotFoundError): ...
class ConfigValidationError(ValueError): ...
```

**Implementation Notes:**
- Use `os.getenv("BRIDGE_CONFIG_PATH")` for env override
- Default path: `Path.cwd() / "config" / "settings.json"`
- On validation error, re-raise Pydantic's `ValidationError` as `ConfigValidationError` with field names extracted
- All `Path` fields: convert relative paths to absolute (relative to config file's directory)

---

### 2. `models/code_block.py`

**Responsibility:** Immutable data containers for code blocks and parsed code.

**Public Interface:**
```python
from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict, field_validator
from pathlib import Path
import hashlib
import time

class CodeBlock(BaseModel):
    """Raw code extracted from chatbot DOM."""
    model_config = ConfigDict(frozen=True)
    
    raw_text: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    detected_at: float = Field(gt=0.0)
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    
    @classmethod
    def from_raw(cls, text: str, url: str) -> CodeBlock:
        """Factory: compute hash and timestamp automatically."""
        if not text.strip():
            raise ValueError("Cannot create CodeBlock from empty text")
        if not url.strip():
            raise ValueError("source_url cannot be empty")
        
        normalized = text.strip().replace("\r\n", "\n")
        content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        
        return cls(
            raw_text=normalized,
            source_url=url,
            detected_at=time.time(),
            content_hash=content_hash
        )

class ParsedCode(BaseModel):
    """Code after parser processing. (Sprint 2 — placeholder for now)"""
    model_config = ConfigDict(frozen=True)
    
    code: str
    file_path: Path
    language: str
    terminal_commands: list[str] = Field(default_factory=list)
    requires_backup: bool = True
    source_block: CodeBlock
```

**Implementation Notes:**
- `from_raw` is the ONLY way to create a `CodeBlock` — never call `CodeBlock(...)` directly
- SHA256 is overkill for deduplication but future-proof (collision-free even at scale)

---

### 3. `core/sniffer.py`

**Responsibility:** Monitor browser DOM, extract code blocks, deduplicate.

**Public Interface:**
```python
from __future__ import annotations
from typing import AsyncGenerator
from pathlib import Path
from models.code_block import CodeBlock
from config.loader import BridgeConfig
import asyncio

class Sniffer:
    """Browser-based code block detector with deduplication."""
    
    def __init__(self, config: BridgeConfig):
        self.config = config
        self.driver = None  # Selenium WebDriver
        self._seen_hashes: set[str] = set()
    
    async def start(self) -> None:
        """Launch browser and navigate to chatbot URL.
        
        Raises:
            BrowserNotFoundError: Chrome not found
            ChatbotLoadError: Failed to load chatbot page
        """
        ...
    
    async def watch(self) -> AsyncGenerator[CodeBlock, None]:
        """Poll DOM for new code blocks. Yields only new blocks (deduplicated).
        
        Yields:
            CodeBlock: Each unique code block found
        
        Usage:
            async for block in sniffer.watch():
                print(block.content_hash[:8], block.raw_text[:100])
        """
        ...
    
    async def stop(self) -> None:
        """Close browser cleanly."""
        ...

# Custom exceptions
class BrowserNotFoundError(RuntimeError): ...
class ChatbotLoadError(RuntimeError): ...
```

**Implementation Details:**

**Browser Setup:**
```python
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

async def start(self):
    options = uc.ChromeOptions()
    if self.config.browser.headless:
        options.add_argument("--headless")
    options.add_argument(f"--user-data-dir={self.config.browser.user_data_dir}")
    options.add_argument(f"--window-size={self.config.browser.window_size[0]},{self.config.browser.window_size[1]}")
    
    try:
        self.driver = uc.Chrome(options=options)
    except Exception as e:
        raise BrowserNotFoundError("Chrome not found. Install from https://google.com/chrome") from e
    
    self.driver.get(self.config.chatbot.url)
    
    # Wait for page load
    await asyncio.sleep(self.config.chatbot.initial_load_wait_ms / 1000)
    
    if "error" in self.driver.title.lower():
        raise ChatbotLoadError(f"Failed to load {self.config.chatbot.url}")
```

**Polling Loop:**
```python
async def watch(self):
    adapter_config = self.config.adapters[self.config.chatbot.name]
    selector = adapter_config.code_block_selector
    last_seen_texts: dict[str, str] = {}  # element ID → text (for stability check)
    
    while True:
        # Anti-bot: random delay
        jitter = random.gauss(
            (self.config.anti_bot.min_delay_ms + self.config.anti_bot.max_delay_ms) / 2,
            (self.config.anti_bot.max_delay_ms - self.config.anti_bot.min_delay_ms) / 4
        )
        jitter = max(self.config.anti_bot.min_delay_ms, min(self.config.anti_bot.max_delay_ms, jitter))
        await asyncio.sleep(jitter / 1000)
        
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
        except Exception:
            continue  # Page not ready yet
        
        for elem in elements:
            elem_id = elem.id  # Selenium element ID (unique per session)
            current_text = elem.text.strip()
            
            if not current_text:
                continue
            
            # Stability check: only yield if text hasn't changed since last poll
            if elem_id in last_seen_texts and last_seen_texts[elem_id] == current_text:
                # Text is stable — check deduplication
                block = CodeBlock.from_raw(current_text, self.driver.current_url)
                
                if block.content_hash not in self._seen_hashes:
                    self._seen_hashes.add(block.content_hash)
                    yield block
            
            # Update last seen text
            last_seen_texts[elem_id] = current_text
```

**Stability Check Rationale:**
DeepSeek streams responses. We don't want to yield a code block 50 times as it's being typed. The stability check ensures we only yield once the text has been unchanged for one full polling cycle.

---

### 4. `core/executor.py`

**Responsibility:** Write files to disk with atomic write + backup.

**Public Interface:**
```python
from __future__ import annotations
from pathlib import Path
from config.loader import BridgeConfig
from loguru import logger
import tempfile
import shutil
from datetime import datetime

class Executor:
    """File system operations with atomic write and backup."""
    
    def __init__(self, config: BridgeConfig):
        self.config = config
    
    async def write_file(self, path: Path, content: str) -> None:
        """Write file atomically with optional backup.
        
        Args:
            path: Target file path (must be inside project_root)
            content: File content
        
        Raises:
            SecurityError: If path is outside project_root
            ExecutorWriteError: If write fails
        """
        # Security check
        try:
            path.resolve().relative_to(self.config.ide.project_root.resolve())
        except ValueError:
            raise SecurityError(f"Cannot write outside project_root: {path}")
        
        # Backup existing file
        if path.exists() and self.config.executor.auto_backup:
            await self._backup_file(path)
        
        # Dry run
        if self.config.executor.dry_run:
            logger.info(f"[DRY RUN] Would write {len(content)} bytes to {path}")
            return
        
        # Create parent directories
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Atomic write
        try:
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".tmp", dir=path.parent) as tmp:
                tmp.write(content)
                tmp_path = Path(tmp.name)
            
            shutil.move(str(tmp_path), str(path))
            logger.success(f"File synced | path={path} | size={len(content)}B")
        
        except OSError as e:
            if tmp_path.exists():
                tmp_path.unlink()
            raise ExecutorWriteError(f"Failed to write {path}") from e
    
    async def _backup_file(self, path: Path) -> None:
        """Copy existing file to backup dir with timestamp."""
        backup_dir = self.config.executor.backup_dir
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{path.stem}_{timestamp}{path.suffix}.bak"
        backup_path = backup_dir / backup_name
        
        shutil.copy2(str(path), str(backup_path))
        logger.info(f"Backup created | original={path} | backup={backup_path}")

# Custom exceptions
class SecurityError(ValueError): ...
class ExecutorWriteError(RuntimeError): ...
```

**Implementation Notes:**
- Atomic write pattern prevents corruption if Bridge crashes mid-write
- Backup timestamp format: `yyyymmdd_HHMMSS`
- `shutil.move()` is atomic on the same filesystem (always the case since temp is in parent dir)

---

### 5. `main.py`

**Responsibility:** CLI entry point. Wire components together, handle Ctrl+C.

**Public Interface:**
```python
from __future__ import annotations
import asyncio
import click
from pathlib import Path
from rich.console import Console
from rich.syntax import Syntax
from loguru import logger
from config.loader import load_config, ConfigNotFoundError, ConfigValidationError
from core.sniffer import Sniffer, BrowserNotFoundError, ChatbotLoadError

console = Console()

@click.command()
@click.option("--config", type=click.Path(exists=True, path_type=Path), help="Path to settings.json")
def main(config: Path | None) -> None:
    """Bridge-to-IDE — Sprint 1 Foundation.
    
    Monitors DeepSeek chatbot and prints captured code blocks.
    """
    try:
        cfg = load_config(config)
    except (ConfigNotFoundError, ConfigValidationError) as e:
        console.print(f"[red]Config Error:[/red] {e}")
        raise SystemExit(1)
    
    # Setup logging
    logger.remove()  # Remove default handler
    logger.add(
        cfg.logging.log_dir / "bridge_{time}.log",
        rotation=cfg.logging.rotation,
        retention=cfg.logging.retention,
        level=cfg.logging.level,
        colorize=cfg.logging.colorized
    )
    logger.add(lambda msg: console.print(msg, end=""))  # Console output via rich
    
    asyncio.run(run_bridge(cfg))

async def run_bridge(cfg):
    sniffer = Sniffer(cfg)
    
    try:
        await sniffer.start()
        logger.info(f"Bridge started | chatbot={cfg.chatbot.name} | url={cfg.chatbot.url}")
        
        async for block in sniffer.watch():
            # Print to terminal
            console.print(f"\n[bold green]Code Block Detected[/bold green]")
            console.print(f"  Hash: [cyan]{block.content_hash[:8]}[/cyan]")
            console.print(f"  URL: [blue]{block.source_url}[/blue]")
            console.print(f"  Length: {len(block.raw_text)} chars\n")
            
            # Syntax highlight (truncate if long)
            display_text = block.raw_text[:500] + ("..." if len(block.raw_text) > 500 else "")
            syntax = Syntax(display_text, "python", theme="monokai", line_numbers=False)
            console.print(syntax)
    
    except (BrowserNotFoundError, ChatbotLoadError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    
    except KeyboardInterrupt:
        logger.info("Bridge stopped by user")
    
    finally:
        await sniffer.stop()

if __name__ == "__main__":
    main()
```

**Implementation Notes:**
- `rich` for beautiful terminal output with syntax highlighting
- `click` for `--config` argument
- All errors caught at top level → print friendly message, exit 1 (don't show traceback to user)
- `loguru` configured from config (file + console)

---

## Data Flow (Sprint 1)

```
User runs: python main.py
    ↓
main.py loads config/settings.json via load_config()
    ↓
main.py creates Sniffer(config)
    ↓
Sniffer.start() launches Chrome, navigates to DeepSeek
    ↓
main.py calls async for block in sniffer.watch()
    ↓
Sniffer polls DOM every ~500ms (with jitter)
    ↓
New <pre><code> element found
    ↓
Text is stable (unchanged for 1 poll cycle)
    ↓
CodeBlock.from_raw(text, url) creates immutable block with SHA256 hash
    ↓
Hash not in _seen_hashes → yield block
    ↓
main.py receives block
    ↓
main.py prints to terminal using rich
    ↓
(Loop continues until Ctrl+C)
    ↓
KeyboardInterrupt caught → sniffer.stop() → browser closes
```

---

## File Structure After Sprint 1

```
Bridge-to-IDE/
├── config/
│   ├── __init__.py
│   ├── loader.py              ← NEW
│   └── settings.json          ← Existing
├── models/
│   ├── __init__.py            ← NEW
│   └── code_block.py          ← NEW
├── core/
│   ├── __init__.py            ← NEW
│   ├── sniffer.py             ← NEW
│   └── executor.py            ← NEW (minimal — write_file only)
├── adapters/                   ← Empty for now (Sprint 3)
│   └── __init__.py            ← NEW (empty)
├── tests/                      ← Empty for now (Sprint 4)
│   └── __init__.py            ← NEW (empty)
├── logs/                       ← Auto-created at runtime
├── backups/                    ← Auto-created at runtime
├── main.py                     ← NEW
├── requirements.txt            ← Existing
├── .cursorrules                ← Existing
└── README.md                   ← Existing
```

---

## Testing Strategy (Sprint 1)

**Manual Testing:**
1. Run `python main.py`
2. Open DeepSeek chat in the launched browser
3. Ask DeepSeek: "Write a hello.py file with print('hello')"
4. Verify terminal shows:
   - "Code Block Detected"
   - Hash (8 chars)
   - Source URL
   - Syntax-highlighted code

**Edge Case Testing:**
- Start Bridge before logging in to DeepSeek → Bridge waits for login
- Scroll back to old code blocks → no duplicates printed (deduplication works)
- DeepSeek streams a long response → code block only appears once, after streaming finishes (stability check works)
- Ctrl+C during polling → clean shutdown, no errors

**Unit Tests (deferred to Sprint 4):**
- `test_config_loader.py` — validation errors, env override, path normalization
- `test_code_block.py` — `from_raw`, hash collision, empty text
- `test_sniffer.py` — deduplication, stability check (mock Selenium)
- `test_executor.py` — atomic write, backup, dry run, security check

---

## Performance Targets (Sprint 1)

| Metric | Target | Validation Method |
|--------|--------|-------------------|
| CPU during polling | < 5% | Task Manager / `top` |
| Memory footprint | < 100MB | Task Manager / `ps` |
| Time from code appearance to print | < 2s | Stopwatch |
| Startup time | < 10s | Time from `python main.py` to first poll |

---

## Error Handling Strategy

**Graceful Degradation:**
- Page not loaded yet → log warning, retry next poll cycle
- Element selector fails → skip silently, retry next cycle
- Chrome crashes → log error, exit cleanly (user must restart)

**User-Facing Errors (exit immediately):**
- Config file not found → print path, exit 1
- Config validation fails → print field name + reason, exit 1
- Chrome not installed → print install URL, exit 1
- Chatbot page fails to load → print URL + status code, exit 1

**Developer-Facing Errors (for debugging):**
- All exceptions logged to `logs/bridge_{timestamp}.log` with full traceback
- Loguru automatically rotates logs at 10MB, keeps 7 days

---

## Security Considerations (Sprint 1)

- Executor refuses to write outside `project_root` (prevents path traversal attacks)
- Browser profile is local (no cloud sync — all data stays on user's machine)
- No network requests except to chatbot URL (no telemetry, no analytics)
- Config file can contain sensitive paths but is gitignored in production

---

## Known Limitations (Sprint 1)

- **DeepSeek only** — Claude/Gemini adapters in Sprint 3
- **No path extraction** — all code printed to terminal, not written to files yet (Sprint 2)
- **No terminal command execution** — (Sprint 2)
- **No IDE integration** — (Sprint 3)
- **No mouse simulation** — basic polling only (Sprint 2 for full anti-bot)
- **No tests** — (Sprint 4)

---

## Next Steps (Sprint 2)

After Sprint 1 is validated:
1. Add `core/parser.py` — extract file paths and terminal commands from code blocks
2. Wire Sniffer → Parser → Executor (full pipeline)
3. Add `core/human_sim.py` — mouse simulation, advanced anti-bot
4. Test end-to-end: "create src/app.py" → file appears in correct location
