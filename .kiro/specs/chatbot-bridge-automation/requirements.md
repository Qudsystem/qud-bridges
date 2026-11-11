# Requirements Document

## Introduction

نظام Bridge احترافي يربط بين chatbots المجانية (مثل DeepSeek، ChatGPT، Claude) ويحولها إلى API كامل القدرات. يراقب المحادثات، يستخرج الأوامر البرمجية، وينفذها بأمان على الجهاز المحلي مع تقليد السلوك البشري لتجنب الكشف والحظر.

## Glossary

- **Bridge_System**: النظام الكامل الذي يربط بين chatbots والتنفيذ المحلي
- **Chatbot_Monitor**: المكون المسؤول عن مراقبة المحادثات مع chatbots
- **Command_Extractor**: المكون المسؤول عن استخراج الأوامر البرمجية من نصوص المحادثة
- **Path_Validator**: المكون المسؤول عن التحقق من صحة المسارات وأمانها
- **Code_Executor**: المكون المسؤول عن تنفيذ الكود البرمجي بأمان
- **Human_Behavior_Simulator**: المكون المسؤول عن محاكاة السلوك البشري
- **Browser_Automation**: المكون المسؤول عن أتمتة المتصفح باستخدام Playwright
- **Session_Manager**: المكون المسؤول عن إدارة جلسات المتصفح
- **CAPTCHA_Resolver**: المكون المسؤول عن حل CAPTCHA
- **Proxy_Manager**: المكون المسؤول عن إدارة proxies الدوارة
- **PROJECT_ROOT**: المسار الجذر للمشروع الذي يُسمح بالعمل ضمنه فقط
- **Command_Keywords**: الكلمات المفتاحية التي تشير إلى وجود أمر برمجي (مثل: "create file", "run code", "execute")

## Requirements

### Requirement 1: مراقبة المحادثة المستمرة

**User Story:** كمستخدم، أريد أن يراقب النظام المحادثة مع chatbots بشكل مستمر، حتى يتمكن من اكتشاف الأوامر البرمجية فور ظهورها.

#### Acceptance Criteria

1. WHEN المستخدم يبدأ جلسة مع chatbot، THE Chatbot_Monitor SHALL يبدأ المراقبة المستمرة للمحادثة
2. THE Chatbot_Monitor SHALL يفحص الرسائل الجديدة كل 500ms إلى 2000ms بشكل عشوائي
3. WHEN رسالة جديدة تظهر من chatbot، THE Chatbot_Monitor SHALL يمررها إلى Command_Extractor للتحليل
4. THE Chatbot_Monitor SHALL يحفظ سجل المحادثة الكامل في ملف log محلي

### Requirement 2: استخراج الأوامر البرمجية

**User Story:** كمستخدم، أريد أن يستخرج النظام الأوامر البرمجية من نصوص المحادثة، حتى يتمكن من تنفيذها تلقائياً.

#### Acceptance Criteria

1. WHEN نص يحتوي على Command_Keywords، THE Command_Extractor SHALL يستخرج تفاصيل الأمر (نوع العملية، اسم الملف، الكود، المسار)
2. THE Command_Extractor SHALL يدعم استخراج code blocks بصيغة markdown (```python, ```javascript, إلخ)
3. THE Command_Extractor SHALL يتعرف على أنواع العمليات: create_file، modify_file، delete_file، execute_code، run_command
4. WHEN الأمر غير واضح أو ناقص، THE Command_Extractor SHALL يسجل تحذير ويطلب توضيح من المستخدم
5. THE Command_Extractor SHALL يستخرج metadata إضافية (لغة البرمجة، dependencies، environment variables)

### Requirement 3: التحقق من أمان المسارات

**User Story:** كمستخدم، أريد أن يمنع النظام الوصول خارج PROJECT_ROOT، حتى يحمي ملفات النظام من التعديل غير المصرح به.

#### Acceptance Criteria

1. WHEN مسار ملف يُستخرج من أمر، THE Path_Validator SHALL يتحقق أن المسار ضمن PROJECT_ROOT
2. IF مسار يحتوي على ".." أو يحاول الوصول خارج PROJECT_ROOT، THEN THE Path_Validator SHALL يرفض الأمر ويسجل محاولة الوصول غير المصرح
3. THE Path_Validator SHALL يحول المسارات النسبية إلى مسارات مطلقة قبل التحقق
4. THE Path_Validator SHALL يمنع الوصول إلى مسارات النظام الحساسة (/etc، /sys، /proc على Linux)
5. WHEN مسار صالح، THE Path_Validator SHALL يمرر الأمر إلى Code_Executor

### Requirement 4: التنفيذ الآمن للكود

**User Story:** كمستخدم، أريد أن ينفذ النظام الكود بأمان، حتى لا يتسبب في تعطيل النظام أو استهلاك موارد غير محدود.

#### Acceptance Criteria

1. WHEN أمر تنفيذ كود يُستلم، THE Code_Executor SHALL ينفذ الكود في subprocess معزول
2. THE Code_Executor SHALL يطبق timeout قدره 30 ثانية على كل عملية تنفيذ
3. THE Code_Executor SHALL يحد من استخدام الذاكرة إلى 512MB لكل عملية
4. THE Code_Executor SHALL يحد من استخدام CPU إلى 50% لكل عملية
5. IF عملية تتجاوز timeout أو حدود الموارد، THEN THE Code_Executor SHALL يوقف العملية ويسجل خطأ
6. THE Code_Executor SHALL يلتقط stdout وstderr من العملية المنفذة
7. WHEN تنفيذ ينتهي، THE Code_Executor SHALL يعيد النتيجة (success/failure، output، error messages)

### Requirement 5: إرجاع النتائج إلى المحادثة

**User Story:** كمستخدم، أريد أن يكتب النظام نتيجة التنفيذ في المحادثة، حتى يعرف chatbot نتيجة الأمر ويتابع بناءً عليها.

#### Acceptance Criteria

1. WHEN تنفيذ كود ينتهي بنجاح، THE Bridge_System SHALL يكتب رسالة تحتوي على النتيجة في chatbot
2. WHEN تنفيذ كود يفشل، THE Bridge_System SHALL يكتب رسالة خطأ مفصلة في chatbot
3. THE Bridge_System SHALL يستخدم Human_Behavior_Simulator عند كتابة الرسائل
4. THE Bridge_System SHALL يتضمن في الرسالة: حالة التنفيذ، output، error messages، وقت التنفيذ

### Requirement 6: محاكاة السلوك البشري

**User Story:** كمستخدم، أريد أن يقلد النظام السلوك البشري، حتى لا يتم اكتشافه وحظره من قبل chatbot platforms.

#### Acceptance Criteria

1. WHEN النظام يحرك الماوس، THE Human_Behavior_Simulator SHALL يستخدم مسارات bezier curves طبيعية
2. WHEN النظام يكتب نص، THE Human_Behavior_Simulator SHALL يضيف تأخير عشوائي بين 50ms و150ms بين كل حرف
3. THE Human_Behavior_Simulator SHALL يضيف أخطاء كتابة عشوائية بنسبة 2% ثم يصححها
4. THE Human_Behavior_Simulator SHALL يضيف توقفات عشوائية (pauses) بين 500ms و3000ms بين الإجراءات
5. THE Human_Behavior_Simulator SHALL يحاكي scroll behavior طبيعي عند قراءة الرسائل الطويلة
6. THE Human_Behavior_Simulator SHALL يضيف تأخير عشوائي بين 1s و5s قبل الرد على رسائل chatbot

### Requirement 7: أتمتة المتصفح باستخدام Playwright

**User Story:** كمستخدم، أريد أن يستخدم النظام Playwright لأتمتة المتصفح، حتى يكون أكثر موثوقية وأقل قابلية للكشف من Selenium.

#### Acceptance Criteria

1. THE Browser_Automation SHALL يستخدم Playwright لجميع عمليات أتمتة المتصفح
2. THE Browser_Automation SHALL يخفي علامات الأتمتة (webdriver، automation flags)
3. THE Browser_Automation SHALL يستخدم متصفح غير headless بشكل افتراضي
4. WHERE المستخدم يفعل headless mode، THE Browser_Automation SHALL يستخدم headless مع stealth plugins
5. THE Browser_Automation SHALL يحقن JavaScript لإخفاء navigator.webdriver
6. THE Browser_Automation SHALL يستخدم user agent حقيقي ومتغير

### Requirement 8: إدارة الجلسات والحفاظ عليها

**User Story:** كمستخدم، أريد أن يحفظ النظام جلسات المتصفح، حتى لا أحتاج لتسجيل الدخول في كل مرة.

#### Acceptance Criteria

1. WHEN جلسة جديدة تُنشأ، THE Session_Manager SHALL يحفظ browser profile في مجلد محلي
2. WHEN النظام يبدأ، THE Session_Manager SHALL يحمل browser profile الموجود إن وُجد
3. THE Session_Manager SHALL يحفظ cookies وlocal storage وsession storage
4. THE Session_Manager SHALL يدعم جلسات متعددة لchatbots مختلفة في نفس الوقت
5. WHEN جلسة تنتهي صلاحيتها، THE Session_Manager SHALL يطلب من المستخدم تسجيل الدخول مجدداً

### Requirement 9: الاكتشاف الديناميكي لعناصر الواجهة

**User Story:** كمستخدم، أريد أن يكتشف النظام عناصر الواجهة ديناميكياً، حتى يستمر في العمل عند تغيير تصميم الموقع.

#### Acceptance Criteria

1. WHEN النظام يبحث عن عنصر واجهة، THE Browser_Automation SHALL يستخدم multiple selectors (CSS، XPath، text content، ARIA labels)
2. IF selector رئيسي يفشل، THEN THE Browser_Automation SHALL يجرب selectors بديلة تلقائياً
3. THE Browser_Automation SHALL يستخدم semantic selectors (role، aria-label) كأولوية أولى
4. WHEN جميع selectors تفشل، THE Browser_Automation SHALL يسجل خطأ ويلتقط screenshot للتشخيص
5. THE Browser_Automation SHALL يحدث selectors تلقائياً بناءً على التغييرات المكتشفة

### Requirement 10: دعم chatbots متعددة

**User Story:** كمستخدم، أريد أن يدعم النظام chatbots متعددة، حتى أتمكن من استخدام DeepSeek وChatGPT وClaude في نفس الوقت.

#### Acceptance Criteria

1. THE Bridge_System SHALL يدعم DeepSeek chatbot
2. THE Bridge_System SHALL يدعم ChatGPT (chat.openai.com)
3. THE Bridge_System SHALL يدعم Claude (claude.ai)
4. THE Bridge_System SHALL يسمح بتشغيل جلسات متعددة لchatbots مختلفة بشكل متزامن
5. WHERE chatbot جديد يُضاف، THE Bridge_System SHALL يستخدم plugin architecture لإضافة دعم بسهولة

### Requirement 11: دعم Proxies الدوارة

**User Story:** كمستخدم، أريد أن يستخدم النظام proxies دوارة، حتى يتجنب حظر IP عند الاستخدام المكثف.

#### Acceptance Criteria

1. WHERE المستخدم يوفر قائمة proxies، THE Proxy_Manager SHALL يستخدمها بشكل دوار
2. THE Proxy_Manager SHALL يختبر كل proxy قبل استخدامه
3. IF proxy يفشل أو يتجاوز timeout، THEN THE Proxy_Manager SHALL يزيله من القائمة مؤقتاً ويجرب proxy آخر
4. THE Proxy_Manager SHALL يدعم HTTP، HTTPS، وSOCKS5 proxies
5. THE Proxy_Manager SHALL يدور proxies بعد كل 10 إلى 20 طلب بشكل عشوائي

### Requirement 12: حل CAPTCHA

**User Story:** كمستخدم، أريد أن يحل النظام CAPTCHA تلقائياً أو يدوياً، حتى لا تتوقف العملية عند ظهور CAPTCHA.

#### Acceptance Criteria

1. WHEN CAPTCHA يُكتشف، THE CAPTCHA_Resolver SHALL يحاول حله تلقائياً باستخدام 2captcha service
2. WHERE المستخدم لم يوفر API key لـ2captcha، THE CAPTCHA_Resolver SHALL يطلب حل يدوي من المستخدم
3. THE CAPTCHA_Resolver SHALL يدعم reCAPTCHA v2 وv3 وhCaptcha
4. THE CAPTCHA_Resolver SHALL يطبق timeout قدره 120 ثانية على حل CAPTCHA
5. IF حل CAPTCHA يفشل بعد 3 محاولات، THEN THE CAPTCHA_Resolver SHALL يوقف العملية ويسجل خطأ

### Requirement 13: معالجة الأخطاء والتكيف

**User Story:** كمستخدم، أريد أن يتكيف النظام مع الأخطاء، حتى يستمر في العمل حتى عند مواجهة مشاكل مؤقتة.

#### Acceptance Criteria

1. WHEN خطأ شبكة يحدث، THE Bridge_System SHALL يعيد المحاولة حتى 3 مرات مع exponential backoff
2. WHEN rate limiting يُكتشف، THE Bridge_System SHALL يزيد التأخير بين الطلبات بنسبة 200%
3. IF chatbot يستجيب ببطء، THEN THE Bridge_System SHALL يزيد timeout تلقائياً
4. THE Bridge_System SHALL يسجل جميع الأخطاء مع timestamps وcontext كامل
5. WHEN خطأ حرج يحدث، THE Bridge_System SHALL يرسل إشعار للمستخدم

### Requirement 14: حزمة pip قابلة للتثبيت

**User Story:** كمطور، أريد أن يكون المشروع حزمة pip قابلة للتثبيت، حتى يسهل توزيعه واستخدامه.

#### Acceptance Criteria

1. THE Bridge_System SHALL يتضمن setup.py أو pyproject.toml صحيح
2. THE Bridge_System SHALL يحدد جميع dependencies في requirements.txt
3. WHEN المستخدم ينفذ "pip install chatbot-bridge"، THE Bridge_System SHALL يُثبت بنجاح
4. THE Bridge_System SHALL يوفر CLI entry point (chatbot-bridge command)
5. THE Bridge_System SHALL يتضمن documentation كاملة (README، API docs، examples)

### Requirement 15: واجهة برمجية (API) قابلة للاستخدام

**User Story:** كمطور، أريد أن يوفر النظام API واضحة، حتى أتمكن من دمجه في تطبيقاتي بسهولة.

#### Acceptance Criteria

1. THE Bridge_System SHALL يوفر Python API للتحكم البرمجي
2. THE Bridge_System SHALL يوفر REST API اختيارية للوصول عن بعد
3. THE Bridge_System SHALL يوفر WebSocket API للتحديثات الفورية
4. THE Bridge_System SHALL يوفر configuration file (YAML أو JSON) لإعدادات النظام
5. THE Bridge_System SHALL يوفر event hooks (on_command_detected، on_execution_complete، on_error)

### Requirement 16: Parser وPretty Printer للأوامر

**User Story:** كمطور، أريد parser موثوق للأوامر، حتى يتم استخراج الأوامر بدقة من نصوص المحادثة.

#### Acceptance Criteria

1. WHEN نص محادثة يُمرر، THE Command_Parser SHALL يستخرج جميع الأوامر البرمجية بصيغة structured format
2. WHEN أمر غير صالح يُكتشف، THE Command_Parser SHALL يعيد رسالة خطأ وصفية مع موقع الخطأ
3. THE Command_Pretty_Printer SHALL يحول structured commands إلى نص قابل للقراءة
4. FOR ALL أوامر صالحة، parsing ثم printing ثم parsing مرة أخرى SHALL ينتج نفس الأمر (round-trip property)
5. THE Command_Parser SHALL يدعم escape sequences وspecial characters في أسماء الملفات والمسارات
