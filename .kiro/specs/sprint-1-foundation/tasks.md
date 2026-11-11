# Tasks

## 1. Setup project structure

Create the complete folder structure for Sprint 1:
- `config/` directory with `__init__.py`
- `models/` directory with `__init__.py`
- `core/` directory with `__init__.py`
- `adapters/` directory with `__init__.py` (empty for now)
- `tests/` directory with `__init__.py` (empty for now)
- `.gitignore` with entries for `logs/`, `backups/`, `*.pyc`, `__pycache__/`, `.bridge_chrome_profile/`

**Acceptance:**
- All directories exist
- All `__init__.py` files are present
- `.gitignore` covers runtime artifacts

---

## 2. Implement config loader
**Depends on:** 1

Implement `config/loader.py` with all Pydantic models and `load_config()` function as specified in design.md.

**Key requirements:**
- All config models: `ChatbotConfig`, `IDEConfig`, `BrowserConfig`, `AntiBotConfig`, `ExecutorConfig`, `LoggingConfig`, `AdapterConfig`, `BridgeConfig`
- `load_config()` function with env var override (`BRIDGE_CONFIG_PATH`)
- Custom exceptions: `ConfigNotFoundError`, `ConfigValidationError`
- Validator for `project_root` to reject placeholder value
- All paths normalized to absolute

**Acceptance:**
- Can load `settings.json` successfully
- Raises `ConfigNotFoundError` if file missing
- Raises `ConfigValidationError` if `project_root` is still `"REPLACE_WITH_YOUR_PROJECT_PATH"`
- Raises `ConfigValidationError` if any field has wrong type
- Respects `BRIDGE_CONFIG_PATH` env var

---

## 3. Implement data models
**Depends on:** 1

Implement `models/code_block.py` with `CodeBlock` and `ParsedCode` models as specified in design.md.

**Key requirements:**
- `CodeBlock` with fields: `raw_text`, `source_url`, `detected_at`, `content_hash`
- `CodeBlock.from_raw()` factory classmethod that auto-computes hash and timestamp
- SHA256 hash with normalization (strip + `\r\n` → `\n`)
- `frozen=True` config (immutable)
- Validation: reject empty text or URL

**Acceptance:**
- `CodeBlock.from_raw("print('hi')", "https://example.com")` creates valid block
- Hash is 64 hex characters
- Raises `ValueError` if text or URL is empty
- Two blocks with identical text have identical hash

---

## 4. Implement Sniffer browser launch
**Depends on:** 2, 3

Implement `core/sniffer.py` — `Sniffer` class with `start()` method that launches browser.

**Key requirements:**
- Use `undetected_chromedriver`
- Persistent Chrome profile from `browser.user_data_dir` config
- Navigate to `chatbot.url`
- Wait for page load (`initial_load_wait_ms`)
- Raise `BrowserNotFoundError` if Chrome not found
- Raise `ChatbotLoadError` if page fails to load

**Acceptance:**
- `sniffer.start()` launches Chrome and opens DeepSeek
- Browser window size matches config
- Profile directory is created if doesn't exist
- Page is loaded before `start()` returns

---

## 5. Implement Sniffer polling loop with deduplication
**Depends on:** 4

Implement `Sniffer.watch()` async generator that polls DOM and yields new `CodeBlock` objects.

**Key requirements:**
- Poll every `polling_interval_ms` with gaussian jitter for anti-bot
- Use CSS selector from `adapters.deepseek.code_block_selector` in config
- Stability check: only yield if element text unchanged for 1 poll cycle
- Deduplication: maintain `_seen_hashes` set, skip if hash already seen
- Create `CodeBlock.from_raw()` for each new block

**Acceptance:**
- Yields code blocks as they appear in DeepSeek chat
- No duplicates yielded (same code block not yielded twice)
- Streaming responses only yielded once fully loaded (stability check works)
- CPU usage < 5% during polling

---

## 6. Implement Executor file write
**Depends on:** 2

Implement `core/executor.py` — `Executor` class with `write_file()` method.

**Key requirements:**
- Atomic write using temp file + `shutil.move()`
- Auto-backup to `backup_dir` with timestamp if file exists and `auto_backup=true`
- Security check: reject paths outside `project_root`
- Dry run mode: log without writing if `dry_run=true`
- Create parent directories automatically
- Custom exceptions: `SecurityError`, `ExecutorWriteError`

**Acceptance:**
- Writing `test.txt` creates the file atomically
- If `test.txt` exists, backup is created before overwrite
- Attempting to write `/etc/passwd` raises `SecurityError`
- Dry run mode logs but doesn't write
- Disk full error is caught and re-raised as `ExecutorWriteError`

---

## 7. Implement main CLI
**Depends on:** 2, 3, 4, 5

Implement `main.py` as CLI entry point using `click` and `rich`.

**Key requirements:**
- `@click.command()` with `--config` option
- Load config via `load_config()`
- Setup `loguru` logger from config
- Create `Sniffer`, call `start()`, then loop over `watch()`
- Print each `CodeBlock` to terminal with syntax highlighting using `rich`
- Handle `KeyboardInterrupt` gracefully
- Catch config/browser errors and exit with code 1

**Acceptance:**
- `python main.py` starts successfully
- Browser opens and DeepSeek loads
- Code blocks appear in terminal with syntax highlighting
- Ctrl+C stops cleanly with "Bridge stopped by user" message
- Config errors show friendly message (no traceback)
- `python main.py --config custom.json` uses custom config

---

## 8. Update requirements.txt

Ensure `requirements.txt` has all dependencies needed for Sprint 1:
- `undetected-chromedriver>=3.5.0`
- `selenium>=4.18.0`
- `pydantic>=2.0.0`
- `loguru>=0.7.0`
- `python-dotenv>=1.0.0`
- `rich>=13.0.0`
- `click>=8.1.0`

**Acceptance:**
- `pip install -r requirements.txt` installs all needed packages
- No missing imports when running `main.py`

---

## 9. Manual end-to-end test
**Depends on:** 1, 2, 3, 4, 5, 6, 7, 8

Perform manual validation of Sprint 1:

1. Set `project_root` in `settings.json` to a test directory
2. Run `python main.py`
3. Open DeepSeek in launched browser, log in if needed
4. Ask DeepSeek: "Write a Python hello.py file with print('hello world')"
5. Verify terminal shows:
   - "Code Block Detected"
   - Hash (first 8 characters)
   - Source URL
   - Syntax-highlighted code
6. Ask DeepSeek the same question again
7. Verify terminal does NOT show duplicate (deduplication works)
8. Press Ctrl+C
9. Verify clean shutdown

**Acceptance:**
- All steps complete without errors
- Code appears in terminal exactly once
- No duplicate detection
- Clean Ctrl+C shutdown
- Log file created in `logs/` directory

---

## 10. Update ROADMAP.md
**Depends on:** 9

Update `ROADMAP.md` to mark Sprint 1 as complete:
- Change Sprint 1 status from "⬜ Not Started" to "✅ Complete"
- Add completion date

**Acceptance:**
- `ROADMAP.md` shows Sprint 1 as ✅ Complete
