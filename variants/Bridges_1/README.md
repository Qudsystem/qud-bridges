# 🌉 Bridge-to-IDE — المايسترو التقني
**بديل ذكي للـ APIs المدفوعة | QudSystem**

---

## ما هو Bridge-to-IDE؟

جسر برمجي يحاكي سلوك المبرمج البشري: يراقب أي Chatbot في المتصفح، يفهم الكود اللي بيطلع، وينفذه مباشرة في IDE بتاعك — **بدون API، بدون تكلفة**.

```
ChatBot (DeepSeek/Claude/Gemini)
           │
           ▼ (Auto-detected)
    Bridge-to-IDE 🌉
           │
           ▼ (Auto-executed)
    IDE (Cursor/VS Code)
```

---

## ⚡ Quick Start

```bash
# 1. Install
git clone https://github.com/qudsystem/bridge-to-ide
cd Bridge-to-IDE
pip install -r requirements.txt

# 2. Config
# Edit config/settings.json:
# - Set your IDE project root path
# - Set your preferred chatbot

# 3. Run
python main.py --chatbot deepseek --ide cursor

# 4. Dry Run (preview without changes)
python main.py --dry-run
```

---

## 📁 Project Structure

```
Bridge-to-IDE/
├── .cursorrules          ← AI coding rules (read by Cursor/Claude Code)
├── docs/
│   ├── PRD.md            ← What we're building & why
│   ├── ARCHITECTURE.md   ← How the system works
│   ├── AGENTS.md         ← Instructions for AI coding agents
│   └── RULES.md          ← Non-negotiable constraints
├── config/
│   └── settings.json     ← Your configuration
├── core/                 ← The 3 layers (never merge them)
│   ├── sniffer.py        ← Layer 1: Watch browser
│   ├── parser.py         ← Layer 2: Understand code
│   └── executor.py       ← Layer 3: Execute changes
├── adapters/             ← Chatbot + IDE integrations
├── models/               ← Pydantic data models
├── tests/                ← Test suite
├── logs/                 ← Auto-created
├── backups/              ← Auto-created
├── main.py               ← Entry point
└── requirements.txt
```

---

## 🤖 Supported Platforms

### Chatbots
| Platform | Status |
|---|---|
| DeepSeek | ✅ |
| Claude.ai | ✅ |
| Gemini | ✅ |
| Kimi | 🔜 |

### IDEs
| IDE | Method |
|---|---|
| Cursor | CLI |
| VS Code | CLI |

### OS
| OS | Status |
|---|---|
| Windows 10/11 | ✅ |
| Linux | ✅ |
| macOS | 🔜 |

---

## 📖 Documentation

- **للمطورين:** `docs/ARCHITECTURE.md`
- **للـ AI Agents:** `docs/AGENTS.md`
- **للقواعد:** `docs/RULES.md`
- **للمتطلبات:** `docs/PRD.md`

---

## 🛡️ تحذير أمني

البريدج يمتلك صلاحيات كتابة وحذف ملفات في مشروعك. تأكد دائماً من تشغيله على مشاريع لها **Version Control (Git)** عشان تقدر ترجع لأي نقطة.

---

**QudSystem © 2025 | باشمهندس حسام**
