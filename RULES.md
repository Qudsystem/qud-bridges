# RULES.md — Bridge-to-IDE
# القواعد الصارمة للمشروع — لا استثناءات
# **أي كود لا يلتزم بهذه القواعد يُرفض فوراً**

---

## 🚨 القواعد غير القابلة للتفاوض

### RULE-01: فصل الطبقات مقدس
```
sniffer.py  → يعرف فقط: المتصفح والـ DOM
parser.py   → يعرف فقط: النصوص والأنماط  
executor.py → يعرف فقط: نظام الملفات والـ Terminal
```
**الانتهاك:** دمج أي مسؤوليتين في ملف واحد = رفض فوري.

---

### RULE-02: لا قيم ثابتة في الكود (No Magic Strings/Numbers)

❌ ممنوع:
```python
driver.get("https://chat.deepseek.com")
time.sleep(2)
```

✅ صحيح:
```python
driver.get(cfg.chatbot.url)
await human_delay(cfg.anti_bot.min_delay_ms / 1000, cfg.anti_bot.max_delay_ms / 1000)
```

---

### RULE-03: لا print() في أي ملف Core
كل الـ Output يمر عبر `loguru`. بدون استثناء.

---

### RULE-04: كل كتابة ملف = Atomic Write
```python
# ✅ الطريقة الوحيدة المقبولة
with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
    tmp.write(content)
shutil.move(tmp.name, str(final_path))
```

---

### RULE-05: كل تفاعل مع المتصفح = Random Delay
```python
# ✅ الطريقة الوحيدة المقبولة
await human_delay()  # من human_sim.py
```

---

### RULE-06: كل type hint إلزامي
```python
# ❌ ممنوع
def extract_code(element, config):
    return element.text

# ✅ صحيح  
def extract_code(element: WebElement, config: SnifferConfig) -> str:
    return element.text
```

---

### RULE-07: كل استثناء = رسالة Log واضحة
```python
# ❌ ممنوع
try:
    ...
except Exception:
    pass

# ✅ صحيح
try:
    ...
except TimeoutException as e:
    logger.warning("Timeout | context={ctx} | error={e}", ctx=context, e=str(e))
    raise
```

---

### RULE-08: كل ملف جديد = Backup أولاً
قبل الكتابة على ملف موجود:
```python
if target_path.exists() and cfg.executor.auto_backup:
    backup_file(target_path)  # من executor.py
```

---

### RULE-09: لا تعديل على core/ بسبب chatbot جديد
إضافة chatbot جديد تعني **فقط** إضافة ملف في `adapters/chatbots/`.
الـ `core/` لا تُلمس.

---

### RULE-10: لا تنفيذ تلقائي بدون Dry Run mode
المستخدم يجب أن يقدر يشغل البريدج في وضع `--dry-run` ويشوف بالضبط:
- أي ملفات هتتكتب
- أي أوامر هتتنفذ
- بدون أن يحدث أي تغيير فعلي

---

## ⚠️ قواعد تحذير (Warnings — تصحيح فوري مطلوب)

### WARN-01: CSS Selectors قد تتغير
كل Selector في `adapters/` يجب أن يكون موثقاً بـ comment يشرح من أين جاء.
```python
# Selector verified on DeepSeek v2.5 (Jan 2025)
# If broken, inspect: .chat-container > .message:last-child pre code
CODE_BLOCK_SELECTOR = "div.ds-markdown pre code"
```

### WARN-02: حجم الـ Logs
```json
"logging": {
  "rotation": "10 MB",
  "retention": "7 days"
}
```
لا تسمح للـ logs بالتراكم بلا حدود.

### WARN-03: Backup Directory Size
الـ Backups تتراكم. أضف cleanup job أو تنبيه للمستخدم عند تجاوز 500MB.

---

## 📋 Checklist قبل أي Commit

```
□ كل function لها type hints على المدخلات والمخرجات
□ لا print() في أي ملف من core/ أو adapters/
□ لا hardcoded strings أو numbers
□ كل browser interaction فيها random delay
□ كل file write هي atomic write
□ كل exception يُلتقط بـ specific type (مش Exception عامة)
□ كل ملف جديد في adapters/ له test مقابل في tests/
□ settings.json مُحدث لو في config جديد
□ requirements.txt مُحدث لو في dependency جديدة
□ README.md مُحدث لو في feature جديدة
```

---

## 🔴 Instant Rejection Criteria

الـ PR يُرفض فوراً لو:
1. يكسر فصل الطبقات
2. فيه hardcoded URL, path, أو selector في `core/`
3. فيه `time.sleep()` بقيمة ثابتة في أي مكان
4. فيه `except:` أو `except Exception:` بدون logging
5. فيه كتابة ملف بدون atomic pattern
6. مفيش tests لـ feature جديدة في `core/`
