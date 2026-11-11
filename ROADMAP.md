# ROADMAP.md — Bridge-to-IDE
# خارطة الطريق التطويرية | QudSystem

---

## 🎯 الهدف النهائي (End Goal)
> جسر برمجي يعمل مع أي chatbot وأي IDE، بصلاحيات كاملة، بدون أي تدخل بشري.

---

## Sprint 1 — الهيكل الأساسي (Foundation)
**المدة المقترحة:** 3-5 أيام

### المهام
- [ ] إنشاء هيكل المجلدات الكامل
- [ ] `config/loader.py` — Pydantic config loader
- [ ] `models/code_block.py` — Data models
- [ ] `core/sniffer.py` — DeepSeek فقط + Basic DOM watching
- [ ] `core/executor.py` — File write + mkdir فقط
- [ ] `main.py` — تشغيل Sniffer → print الكود الملتقط
- [ ] تجربة: اطلب من DeepSeek "اكتب hello.py بداخله print hello" وشوف البريدج يلتقطه

### معيار النجاح
```
البريدج يلتقط كود من DeepSeek ويطبعه في الـ Terminal بنجاح
```

---

## Sprint 2 — الذكاء السياقي (Parser Layer)
**المدة المقترحة:** 3-5 أيام

### المهام
- [ ] `core/parser.py` — Path extraction بالـ Regex
- [ ] `core/parser.py` — Terminal command detection
- [ ] `core/parser.py` — Language detection
- [ ] ربط Sniffer → Parser → Executor (الـ 3 طبقات معاً)
- [ ] تجربة: اطلب من DeepSeek "اعمل Flask app في src/app.py" وشوف البريدج يوضع الملف صح
- [ ] `core/human_sim.py` — Random delays + mouse simulation

### معيار النجاح
```
البريدج يكتب src/app.py في المكان الصح تلقائياً
```

---

## Sprint 3 — دعم متعدد المنصات (Multi-Platform)
**المدة المقترحة:** 5-7 أيام

### المهام
- [ ] `adapters/base.py` — Abstract interfaces
- [ ] `adapters/chatbots/claude.py` — Claude.ai adapter
- [ ] `adapters/chatbots/gemini.py` — Gemini adapter
- [ ] `adapters/ides/cursor.py` — Cursor adapter
- [ ] `adapters/ides/vscode.py` — VS Code adapter
- [ ] `--dry-run` mode
- [ ] Backup system
- [ ] Crash recovery (session state persistence)

### معيار النجاح
```
البريدج يشتغل مع DeepSeek + Claude + Gemini بنفس الكفاءة
```

---

## Sprint 4 — الجودة والاستقرار (Quality & Stability)
**المدة المقترحة:** 3-5 أيام

### المهام
- [ ] Test suite كامل (`tests/`)
- [ ] Coverage > 80% للـ `core/`
- [ ] Logging system كامل مع rotation
- [ ] Anti-bot measures متقدمة
- [ ] Error recovery (retry logic)
- [ ] Performance profiling (CPU < 5% في وضع المراقبة)

### معيار النجاح
```
تشغيل البريدج لـ 2 ساعة بدون crash أو detection
```

---

## Sprint 5 — الإصدار التجريبي (Beta Release)
**المدة المقترحة:** 3-5 أيام

### المهام
- [ ] CLI كامل مع `--help`
- [ ] README كامل مع تعليمات واضحة
- [ ] Demo video
- [ ] GitHub release v0.1.0-beta

---

## 🔮 المستقبل (Future — v2.0)
- GUI بسيطة (System Tray App)
- Plugin مدمج في VS Code / Cursor
- دعم Kimi + ChatGPT + Copilot Chat
- Cloud mode (sync عبر أجهزة متعددة)
- Multi-language support (JavaScript, Rust, Go)

---

## 🚦 حالة المشروع الحالية

```
Sprint 1: ✅ Complete (2025-01-16)
Sprint 2: ⬜ Not Started  
Sprint 3: ⬜ Not Started
Sprint 4: ⬜ Not Started
Sprint 5: ⬜ Not Started
```
