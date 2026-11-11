# Requirements — Sprint 1: Foundation
**Project:** Bridge-to-IDE  
**Sprint:** 1 — Foundation Layer  
**Owner:** QudSystem  
**Status:** Draft

---

## Goal

By the end of Sprint 1, the Bridge must be able to:
> Monitor the DeepSeek chatbot page in a real Chrome browser, detect any new code block, and print it to the terminal — automatically, with no human copying.

---

## Requirements

### REQ-01 — Config Loading
**As a** developer running the Bridge,  
**I want** all configuration loaded from `config/settings.json` at startup,  
**So that** I can change chatbot URLs, selectors, and project paths without touching code.

**Acceptance Criteria:**
- [ ] `config/loader.py` loads `settings.json` and returns a validated `BridgeConfig` Pydantic model
- [ ] If `settings.json` is missing → raise `ConfigNotFoundError` with a clear message pointing to the expected path
- [ ] If a required field is missing or invalid type → raise `ConfigValidationError` with the field name and reason
- [ ] `BridgeConfig` exposes nested typed models: `ChatbotConfig`, `BrowserConfig`, `AntiBotConfig`, `ExecutorConfig`, `LoggingConfig`
- [ ] The config path can be overridden via `BRIDGE_CONFIG_PATH` environment variable
- [ ] All path fields in config are normalized to `pathlib.Path` objects automatically

**Edge Cases:**
- `project_root` is `"REPLACE_WITH_YOUR_PROJECT_PATH"` (the default) → raise `ConfigValidationError` telling user to set their project path
- `polling_interval_ms` is 0 or negative → raise `ConfigValidationError`
- Extra unknown keys in JSON → ignore silently (don't crash)

---

### REQ-02 — Data Models
**As a** developer reading the codebase,  
**I want** all data structures defined in one place with strict types,  
**So that** there's a single source of truth and type errors are caught at the boundary.

**Acceptance Criteria:**
- [ ] `models/code_block.py` defines `CodeBlock` with: `raw_text: str`, `source_url: str`, `detected_at: float` (Unix timestamp), `content_hash: str` (SHA256)
- [ ] `CodeBlock` is a Pydantic `BaseModel` (immutable — `model_config = ConfigDict(frozen=True)`)
- [ ] `content_hash` is always 64 hex characters (SHA256)
- [ ] `detected_at` is always a positive float
- [ ] A factory classmethod `CodeBlock.from_raw(text, url)` computes the hash and timestamp automatically so callers never set them manually

**Edge Cases:**
- `raw_text` is empty string → raise `ValueError` ("Cannot create CodeBlock from empty text")
- `source_url` is empty string → raise `ValueError`

---

### REQ-03 — Sniffer: Browser Launch
**As a** user starting the Bridge,  
**I want** the Sniffer to open the DeepSeek chatbot in a persistent Chrome session,  
**So that** I can log in once and the Bridge reuses the same session on every run.

**Acceptance Criteria:**
- [ ] Sniffer uses `undetected-chromedriver` (not plain Selenium) to avoid immediate bot detection
- [ ] Chrome profile is saved to the path specified in `browser.user_data_dir` config — so cookies and login state persist between runs
- [ ] Browser window is opened at the `chatbot.url` from config
- [ ] If Chrome is not found on the system → raise `BrowserNotFoundError` with install instructions
- [ ] If the chatbot URL fails to load within `chatbot.initial_load_wait_ms` → raise `ChatbotLoadError`
- [ ] Browser headless mode is controlled by `browser.headless` config value

**Edge Cases:**
- If browser profile directory doesn't exist → create it (don't crash)
- If another Bridge instance is already using the same profile → log a warning and continue (Chrome handles this)

---

### REQ-04 — Sniffer: Code Block Detection
**As a** user chatting with DeepSeek,  
**I want** the Bridge to automatically detect every code block that appears,  
**So that** I never have to manually copy anything.

**Acceptance Criteria:**
- [ ] Sniffer polls the DOM every `chatbot.polling_interval_ms` milliseconds
- [ ] Uses the CSS selector from `adapters.deepseek.code_block_selector` in config (not hardcoded)
- [ ] For each DOM element matching the selector, extracts its inner text as the raw code
- [ ] Creates a `CodeBlock` using `CodeBlock.from_raw(text, url)`
- [ ] Yields each new `CodeBlock` to the caller (async generator interface)
- [ ] CPU usage during polling must stay below 5% (no tight busy-loop — use `asyncio.sleep`)

**Edge Cases:**
- Page not yet loaded (DOM is empty) → wait and retry, don't crash
- Code block text is only whitespace → skip it (do not yield)
- Streaming response still in progress (text is growing) → only yield when the element's text has been stable for 1 full polling cycle

---

### REQ-05 — Sniffer: Deduplication
**As a** user whose chat history may have many code blocks,  
**I want** the Bridge to only process each unique code block once per session,  
**So that** re-scrolling or page re-renders don't trigger duplicate file writes.

**Acceptance Criteria:**
- [ ] Sniffer maintains an in-memory `set[str]` of seen `content_hash` values
- [ ] Before yielding a `CodeBlock`, check if `content_hash` is already in the set
- [ ] If already seen → skip silently (no log, no yield)
- [ ] If new → add hash to set and yield the block
- [ ] The seen-hashes set is **never** persisted to disk — it resets on every Bridge restart (intentional)

**Edge Cases:**
- Two different code blocks with identical content → treated as the same block (deduplicated by content, not position)

---

### REQ-06 — Executor: File Write
**As a** developer,  
**I want** the Bridge to write captured code to a file on disk,  
**So that** I have the code immediately available in my project without manual copy-paste.

**Acceptance Criteria:**
- [ ] Executor receives a file path and code content
- [ ] Creates all parent directories automatically if they don't exist (`mkdir -p` equivalent)
- [ ] Writes file using **atomic write**: write to a temp file first, then `shutil.move()` to target — never direct write
- [ ] If `executor.auto_backup` is `true` in config AND the target file already exists → copy existing file to `executor.backup_dir/{original_name}.{timestamp}.bak` before overwriting
- [ ] After write, logs: `logger.success("File synced | path={path} | size={size}B")`
- [ ] In `dry_run` mode → print what WOULD be written but do NOT write anything to disk

**Edge Cases:**
- Target path is outside `project_root` → raise `SecurityError` and refuse to write
- Disk is full during temp write → catch `OSError`, log error, clean up temp file, re-raise as `ExecutorWriteError`
- `backup_dir` doesn't exist → create it automatically

---

### REQ-07 — Main Orchestration (Sprint 1 minimal)
**As a** user running `python main.py`,  
**I want** to see captured code blocks printed to the terminal,  
**So that** I can verify the Bridge is working before adding file-write in later sprints.

**Acceptance Criteria:**
- [ ] `main.py` loads config → initializes Sniffer → starts async polling loop
- [ ] For each captured `CodeBlock`, prints to terminal: the hash (first 8 chars), source URL, and the raw code (truncated to 200 chars if long)
- [ ] Handles `KeyboardInterrupt` (Ctrl+C) gracefully: logs "Bridge stopped by user" and exits cleanly
- [ ] `main.py` contains NO business logic — only wires together components
- [ ] CLI accepts `--config PATH` optional argument to override the config file path

**Edge Cases:**
- Config fails validation on startup → print clear error and exit with code 1 (don't show traceback to user)
- Browser fails to launch → print clear error and exit with code 1

---

## Out of Scope for Sprint 1

These are explicitly deferred to later sprints:

- `core/parser.py` — no path extraction or terminal command detection yet
- `core/human_sim.py` — no mouse simulation yet (basic random delays are enough)
- Support for Claude, Gemini adapters
- IDE integration (opening files in Cursor/VS Code)
- Full logging with rotation
- Test suite (to be added in Sprint 4, but recommended to write alongside)

---

## Non-Functional Requirements (Sprint 1)

| Concern | Requirement |
|---------|-------------|
| CPU usage (polling loop) | < 5% on modern hardware |
| Memory footprint | < 100MB at idle |
| Startup time | < 10 seconds to first poll |
| Anti-bot | Random delay between each DOM poll (`asyncio.sleep` with gaussian jitter) |
| Code quality | All functions type-hinted, no `print()` in production code, no bare `except:` |

---

## Dependency Notes

These packages from `requirements.txt` are needed for Sprint 1:

| Package | Used by |
|---------|---------|
| `undetected-chromedriver` | Sniffer — stealth browser |
| `selenium` | Sniffer — DOM access |
| `pydantic >= 2.0` | Config loader + data models |
| `loguru` | All layers — logging |
| `python-dotenv` | Config — `BRIDGE_CONFIG_PATH` env var |
| `rich` | main.py — pretty terminal output |
| `click` | main.py — `--config` CLI argument |
