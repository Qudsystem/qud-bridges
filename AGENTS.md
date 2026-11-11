# AGENTS.md — Bridge-to-IDE
# Instructions for AI Coding Agents (Claude Code, Cursor Agent, Copilot Workspace)
# READ COMPLETELY BEFORE STARTING ANY TASK.

---

## WHO YOU ARE

You are an AI coding agent working on **Bridge-to-IDE**, a Python automation system built by QudSystem. Your job is to implement features according to the PRD and architecture defined in `docs/`. You are NOT a creative writer — you implement what is specified.

---

## WHAT YOU MUST READ FIRST

Before touching any code, read these files IN ORDER:

1. `docs/PRD.md` — Understand WHAT we're building and WHY
2. `docs/ARCHITECTURE.md` — Understand HOW the system is structured
3. `.cursorrules` — Understand the RULES you must follow
4. `config/settings.json` — Understand current configuration

---

## YOUR OPERATING PRINCIPLES

### Principle 1: Layer Isolation is Sacred
The 3-layer architecture (Sniffer → Parser → Executor) is NON-NEGOTIABLE.
- If a task seems to require crossing layer boundaries, **stop and ask**
- Do NOT "simplify" by merging layers

### Principle 2: Config Over Code
If you find yourself writing a URL, file path, or CSS selector as a string literal in `core/`:
- **STOP**
- Add it to `config/settings.json` and the appropriate adapter in `adapters/`
- Reference it via the config loader

### Principle 3: Anti-Bot is Not Optional
Every browser interaction you write MUST use `human_sim.py` utilities.
There is no such thing as a "quick test" that skips anti-bot measures.
Getting banned by chatbot platforms = project failure.

### Principle 4: Fail Loudly, Recover Gracefully
- Exceptions must be caught, logged with full context, and either:
  - Retried (if transient: network, timeout)
  - Raised as domain-specific error (if logic failure)
  - NEVER silently swallowed

### Principle 5: Leave the Codebase Better Than You Found It
- If you touch a file, ensure it has proper type hints
- If you see a `print()`, replace it with `logger`
- If you see a hardcoded string, move it to config

---

## TASK WORKFLOW

When assigned a task, follow this exact workflow:

```
1. READ the relevant docs and existing code
2. PLAN: Write a comment block describing what you will do BEFORE writing code
3. IMPLEMENT: Write the code following .cursorrules
4. TEST: Write or update tests in tests/
5. VERIFY: Run the checklist in .cursorrules
6. REPORT: Summarize what you did and what you did NOT do (and why)
```

---

## ADAPTER PATTERN — HOW TO ADD A NEW CHATBOT

When adding support for a new chatbot (e.g., Kimi, ChatGPT):

1. Create `adapters/chatbots/kimi.py`
2. Implement the `ChatbotAdapter` interface:

```python
from adapters.base import ChatbotAdapter
from models.code_block import CodeBlock

class KimiAdapter(ChatbotAdapter):
    """Adapter for Kimi (kimi.moonshot.ai)."""
    
    NAME = "kimi"
    BASE_URL = "https://kimi.moonshot.ai"
    
    # CSS selectors for this specific chatbot's DOM
    CODE_BLOCK_SELECTOR = "pre.code-block > code"
    COPY_BUTTON_SELECTOR = "button.copy-btn"
    
    def extract_code_blocks(self, page_source: str) -> list[CodeBlock]:
        """Extract all code blocks from current page state."""
        ...
```

3. Register it in `adapters/__init__.py`
4. Add its config section in `config/settings.json`
5. Write tests in `tests/adapters/test_kimi.py`

**DO NOT** modify `core/sniffer.py` to add chatbot-specific logic. That's what adapters are for.

---

## ADAPTER PATTERN — HOW TO ADD A NEW IDE

When adding support for a new IDE (e.g., PyCharm):

1. Create `adapters/ides/pycharm.py`
2. Implement the `IDEAdapter` interface:

```python
from adapters.base import IDEAdapter
from pathlib import Path

class PyCharmAdapter(IDEAdapter):
    """Adapter for JetBrains PyCharm."""
    
    NAME = "pycharm"
    
    def open_file(self, path: Path) -> bool:
        """Open file in PyCharm via CLI."""
        ...
    
    def run_terminal_command(self, command: str, cwd: Path) -> tuple[int, str]:
        """Execute command in PyCharm's built-in terminal."""
        ...
```

---

## WHAT YOU MUST NEVER DO

| Action | Why |
|--------|-----|
| Add chatbot-specific selectors to `core/sniffer.py` | Breaks extensibility |
| Write files without backup check | Risk of data loss |
| Use `time.sleep()` with fixed values | Bot detection risk |
| Catch `Exception` broadly | Hides real bugs |
| Write to disk from `core/parser.py` | Layer violation |
| Use `os.path` string manipulation | Use `pathlib.Path` |
| Skip writing tests | Non-negotiable |
| Hardcode the project root path | Will break on any other machine |

---

## DEDUPLICATION SYSTEM — HOW IT WORKS

The Sniffer uses SHA256 hashing to avoid processing the same code twice:

```python
import hashlib

def compute_code_hash(code_text: str) -> str:
    """Compute stable hash for deduplication."""
    normalized = code_text.strip().replace("\r\n", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
```

The hash is stored in a session-level `set[str]`. If `hash in seen_hashes`, skip it.
**Never persist hashes to disk** — they reset each Bridge session (intentional).

---

## LOGGING STANDARDS

```python
# Session start
logger.info("Bridge session started | chatbot={chatbot} | ide={ide}", 
            chatbot=cfg.chatbot.name, ide=cfg.ide.name)

# Code detected
logger.success("Code block detected | hash={h} | length={l}", 
               h=code_hash[:8], l=len(raw_code))

# File written
logger.success("File synced | path={p} | size={s}B", 
               p=str(file_path), s=len(content))

# Warning
logger.warning("Retry attempt {n}/3 | reason={r}", n=attempt, r=str(error))

# Error
logger.error("Executor failed | path={p} | error={e}", 
             p=str(file_path), e=str(exc))
```

---

## HOW TO RUN THE PROJECT

```bash
# Install dependencies
pip install -r requirements.txt

# Run with default config
python main.py

# Run in dry-run mode (no actual file writes)
python main.py --dry-run

# Run targeting specific chatbot
python main.py --chatbot deepseek --ide cursor

# Run tests
pytest tests/ -v --cov=core

# Run specific test
pytest tests/test_parser.py -v
```

---

## WHEN YOU'RE STUCK

If a task is ambiguous or conflicts with the architecture:
1. Check `docs/ARCHITECTURE.md` for the canonical answer
2. Check `.cursorrules` for the relevant rule
3. If still unclear: **stop, do not guess, ask for clarification**

The rule is: **a clean no-op is better than a wrong implementation.**
