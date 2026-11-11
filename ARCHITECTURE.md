# ARCHITECTURE.md — Bridge-to-IDE
# المعمارية التقنية الكاملة للنظام

---

## 1. نظرة عامة (System Overview)

```
┌─────────────────────────────────────────────────────────────┐
│                    Bridge-to-IDE System                       │
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   SNIFFER    │───▶│    PARSER    │───▶│   EXECUTOR   │   │
│  │  (Layer 1)   │    │  (Layer 2)   │    │  (Layer 3)   │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│         ▲                                        │            │
│         │                                        ▼            │
│  ┌──────────────┐                       ┌──────────────┐    │
│  │   Browser    │                       │     IDE      │    │
│  │ (Chatbot UI) │                       │   + OS FS    │    │
│  └──────────────┘                       └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. تفصيل الطبقات (Layer Details)

### Layer 1 — The Sniffer (`core/sniffer.py`)

**المسؤولية الوحيدة:** مراقبة المتصفح، استخراج الكود الخام.

```
Browser DOM
    │
    ▼
CSS Selector Engine (from adapter)
    │
    ▼
Raw HTML Element
    │
    ▼
text extraction
    │
    ▼
SHA256 Deduplication Check
    │ (new?)
    ▼
CodeBlock(raw_text, url, timestamp, hash)
    │
    ▼ (to Parser via async queue)
```

**المدخلات:** Browser page source (live)
**المخرجات:** `CodeBlock` objects → async queue

**ما لا يجوز له فعله:**
- ❌ تحليل المسارات
- ❌ كتابة ملفات
- ❌ معرفة أي شيء عن الـ IDE

---

### Layer 2 — The Parser (`core/parser.py`)

**المسؤولية الوحيدة:** فهم الكود واستخراج المعنى منه.

```
CodeBlock (raw)
    │
    ▼
Language Detection (via file extension or code patterns)
    │
    ▼
Path Extraction
    │  → Pattern 1: "# path: src/main.py" comment
    │  → Pattern 2: "```python\n# src/main.py"  
    │  → Pattern 3: Contextual (chatbot said "create src/main.py")
    │  → Fallback: temp_{timestamp}.{lang_ext}
    ▼
Terminal Command Extraction
    │  → Pattern: "run: npm install"
    │  → Pattern: "```bash\nnpm install"
    ▼
ParsedCode(code, file_path, language, terminal_commands)
    │
    ▼ (to Executor via async queue)
```

**المدخلات:** `CodeBlock` from Sniffer queue
**المخرجات:** `ParsedCode` objects → Executor queue

**ما لا يجوز له فعله:**
- ❌ فتح متصفح
- ❌ كتابة ملفات
- ❌ تشغيل أوامر terminal

---

### Layer 3 — The Executor (`core/executor.py`)

**المسؤولية الوحيدة:** تنفيذ التغييرات على الـ File System والـ Terminal.

```
ParsedCode
    │
    ▼
Backup existing file? (if exists → backups/ with timestamp)
    │
    ▼
Create parent directories (mkdir -p)
    │
    ▼
Atomic Write (temp file → rename)
    │
    ▼
Open in IDE (via IDE adapter)
    │
    ▼
Execute terminal commands (if any)
    │
    ▼
Log completion
```

**المدخلات:** `ParsedCode` from Parser queue
**المخرجات:** Side effects (files on disk, terminal output)

---

## 3. نظام الـ Adapters

### لماذا Adapters؟

كل chatbot له HTML مختلف. كل IDE له CLI مختلف. الـ Adapters تعزل هذا الاختلاف عن الـ Core.

```
adapters/
├── base.py              ← Abstract interfaces
├── chatbots/
│   ├── deepseek.py      ← DeepSeek CSS selectors + quirks
│   ├── claude.py        ← Claude.ai CSS selectors + quirks
│   └── gemini.py        ← Gemini CSS selectors + quirks
└── ides/
    ├── cursor.py        ← "cursor {path}" command
    └── vscode.py        ← "code {path}" command
```

### كيف يعمل الـ Adapter Registry

```python
# adapters/__init__.py
CHATBOT_ADAPTERS = {
    "deepseek": DeepSeekAdapter,
    "claude": ClaudeAdapter,
    "gemini": GeminiAdapter,
}

IDE_ADAPTERS = {
    "cursor": CursorAdapter,
    "vscode": VSCodeAdapter,
}

def get_chatbot_adapter(name: str) -> ChatbotAdapter:
    if name not in CHATBOT_ADAPTERS:
        raise UnsupportedChatbotError(f"'{name}' not supported. Add it in adapters/chatbots/")
    return CHATBOT_ADAPTERS[name]()
```

---

## 4. نموذج البيانات (Data Models)

```
CodeBlock                    ParsedCode
─────────────────────        ─────────────────────────────
raw_text: str          ───▶  code: str
source_url: str              file_path: Path
detected_at: float           language: str
content_hash: str            terminal_commands: list[str]
                             requires_backup: bool
                             source_block: CodeBlock
```

---

## 5. نظام الـ Config

```json
{
  "chatbot": {
    "name": "deepseek",
    "url": "https://chat.deepseek.com",
    "polling_interval_ms": 500
  },
  "ide": {
    "name": "cursor",
    "project_root": "/home/user/my-project"
  },
  "browser": {
    "driver": "chrome",
    "headless": false,
    "user_data_dir": "./.bridge_profile"
  },
  "anti_bot": {
    "min_delay_ms": 500,
    "max_delay_ms": 3000,
    "mouse_simulation": true
  },
  "executor": {
    "dry_run": false,
    "auto_backup": true,
    "backup_dir": "./backups",
    "auto_open_in_ide": true,
    "auto_run_terminal_commands": true
  },
  "logging": {
    "level": "INFO",
    "log_dir": "./logs",
    "rotation": "10 MB"
  }
}
```

---

## 6. تدفق البيانات الكامل (Full Data Flow)

```
User types in DeepSeek: "Build me a Flask app"
        │
        ▼
DeepSeek responds with code blocks
        │
        ▼
Sniffer detects <pre><code> elements via CSS selector
        │
        ▼
Dedup check: hash not in seen_hashes → proceed
        │
        ▼
CodeBlock created → pushed to async queue
        │
        ▼
Parser receives CodeBlock
Parser finds "# path: app.py" in code comment
Parser detects Python language
Parser finds "run: flask run" in surrounding text
        │
        ▼
ParsedCode created:
  file_path = project_root / "app.py"
  language = "python"
  terminal_commands = ["pip install flask", "flask run"]
        │
        ▼
Executor receives ParsedCode
Executor backs up existing app.py (if exists)
Executor creates directories
Executor writes app.py atomically
Executor opens app.py in Cursor
Executor runs "pip install flask" in terminal
Executor runs "flask run" in terminal
        │
        ▼
logger.success("✅ app.py synced | commands executed")
```

---

## 7. قرارات معمارية (Architecture Decision Records)

### ADR-001: لماذا Selenium وليس Playwright؟
**السبب:** Selenium أكثر استقراراً مع `undetected-chromedriver` لتجاوز Bot Detection. Playwright متاح كـ alternative في الـ Config.

### ADR-002: لماذا Async Queue وليس مزامنة مباشرة؟
**السبب:** الـ Sniffer يراقب باستمرار بينما الـ Executor قد يستغرق وقتاً. الـ Queue يمنع blocking ويسمح بمعالجة متوازية.

### ADR-003: لماذا Pydantic للـ Config وليس dataclasses؟
**السبب:** Pydantic يوفر validation تلقائي، type coercion، وقراءة من JSON/env variables بدون كود إضافي.

### ADR-004: لماذا Atomic Write؟
**السبب:** لو الـ Bridge crash أثناء كتابة ملف، لا يُترك الملف في حالة فاسدة (corrupted). الـ Atomic Write يضمن إما الكتابة الكاملة أو عدم الكتابة.

### ADR-005: لماذا SHA256 للـ Deduplication وليس URL + timestamp؟
**السبب:** نفس الكود قد يظهر عدة مرات في scroll-back أو re-render. الـ Content Hash يضمن معالجة كل كود مرة واحدة فقط.
