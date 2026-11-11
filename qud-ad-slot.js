/**
 * QudSystem Centralized Updatable Ad Slot & Ecosystem Footer Widget
 * - Zero-dependency Shadow DOM widget (isolated CSS, never breaks host layout)
 * - Fetches updatable ad feed from QudSystem Unified Portal / GitHub CDN
 * - Automatically hides ads in Paid / Pro Tier (Ad-Free Complete Experience)
 * - Displays QudSystem suite attribution + Upcoming Qud Office AI Suite notice
 */
(function () {
  if (typeof window === 'undefined' || typeof document === 'undefined') return;
  if (window.__QUD_ECOSYSTEM_WIDGET_LOADED__) return;
  window.__QUD_ECOSYSTEM_WIDGET_LOADED__ = true;

  var scriptEl = document.currentScript;
  var cfg = Object.assign(
    {
      projectName: (scriptEl && scriptEl.getAttribute('data-project-name')) || document.title || 'QudSystem Product',
      projectSlug: (scriptEl && scriptEl.getAttribute('data-project-slug')) || 'qudsystem-app',
      category: (scriptEl && scriptEl.getAttribute('data-category')) || 'QudSystem Software Suite',
      portalUrl: 'https://github.com/Qudsystem/qudsystem-website',
      adEndpoints: [
        'https://cdn.jsdelivr.net/gh/Qudsystem/qudsystem-website@main/public/ads/qud-ad-slot.json',
        'https://raw.githubusercontent.com/Qudsystem/qudsystem-website/main/public/ads/qud-ad-slot.json'
      ],
      paidTier: false
    },
    window.QUD_CONFIG || {}
  );

  function isPaidTier() {
    try {
      if (cfg.paidTier === true || window.QUD_PAID_TIER === true) return true;
      var lsTier = window.localStorage && window.localStorage.getItem('qud_license_tier');
      if (lsTier === 'pro' || lsTier === 'enterprise' || lsTier === 'paid') return true;
      var params = new URLSearchParams(window.location.search);
      if (params.get('qud_tier') === 'pro') return true;
    } catch (_) {}
    return false;
  }

  var DEFAULT_FEED = {
    version: '2026.1',
    enabled: true,
    officeAiBanner: {
      badge: 'قريباً / قادم',
      titleAr: 'حزمة Qud Office AI — الجيل القادم من إنتاجية الأعمال والذكاء الاصطناعي',
      titleEn: 'Coming Soon: Qud Office AI Suite',
      url: 'https://github.com/Qudsystem'
    },
    paidTierNoteAr: 'النسخة المدفوعة بالباقات المتاحة قريباً: تجربة كاملة 100% بدون إعلانات',
    paidTierNoteEn: 'Paid Plans (Coming Soon): 100% Ad-Free Complete Experience',
    ads: [
      {
        id: 'qud-office-ai-launch',
        tag: 'إعلان رسمي • QudSystem',
        title: 'قريباً: حزمة Qud Office AI المتكاملة للمؤسسات والأفراد',
        description: 'مجموعة متكاملة من أدوات الذكاء الاصطناعي، الأتمتة، التعليم، والأمن السيبراني ضمن منظومة QudSystem.',
        ctaText: 'استكشف المنظومة',
        ctaUrl: 'https://github.com/Qudsystem',
        theme: 'linear-gradient(135deg, #0f172a 0%, #1e3a8a 55%, #312e81 100%)'
      }
    ]
  };

  function fetchAdFeed(urls, idx, cb) {
    if (idx >= urls.length) return cb(DEFAULT_FEED);
    var controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
    var timer = controller ? setTimeout(function () { controller.abort(); }, 3500) : null;
    fetch(urls[idx], { cache: 'no-store', signal: controller ? controller.signal : undefined })
      .then(function (r) {
        if (timer) clearTimeout(timer);
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (json) {
        if (json && Array.isArray(json.ads)) cb(json);
        else fetchAdFeed(urls, idx + 1, cb);
      })
      .catch(function () {
        if (timer) clearTimeout(timer);
        fetchAdFeed(urls, idx + 1, cb);
      });
  }

  function esc(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function renderWidget(feed) {
    var host = document.createElement('div');
    host.id = 'qudsystem-ecosystem-root';
    var shadow = host.attachShadow ? host.attachShadow({ mode: 'open' }) : host;

    var paid = isPaidTier();
    var dismissed = false;
    try {
      dismissed = window.sessionStorage && window.sessionStorage.getItem('qud_ad_dismissed') === '1';
    } catch (_) {}

    var ad = (feed.ads && feed.ads[0]) || DEFAULT_FEED.ads[0];
    var showAd = !paid && !dismissed && feed.enabled !== false && ad;

    var styles = [
      ':host { all: initial; display: block; font-family: system-ui, -apple-system, "Segoe UI", Tahoma, Arial, sans-serif; direction: rtl; }',
      '.qud-wrap { margin: 24px auto 0; padding: 16px 20px; background: #0b1120; color: #e2e8f0; border-top: 1px solid rgba(59,130,246,0.35); box-sizing: border-box; font-size: 13px; line-height: 1.6; }',
      '.qud-inner { max-width: 1200px; margin: 0 auto; display: flex; flex-direction: column; gap: 12px; }',
      '.qud-ad-box { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 18px; border-radius: 12px; background: ' + (ad.theme || 'linear-gradient(135deg,#0f172a,#1e3a8a)') + '; border: 1px solid rgba(96,165,250,0.35); color: #fff; position: relative; }',
      '.qud-ad-meta { flex: 1; min-width: 240px; }',
      '.qud-ad-tag { display: inline-block; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 999px; background: rgba(59,130,246,0.28); color: #93c5fd; margin-bottom: 4px; }',
      '.qud-ad-title { font-size: 15px; font-weight: 700; margin: 2px 0; color: #fff; }',
      '.qud-ad-desc { font-size: 12.5px; color: #cbd5e1; margin: 0; }',
      '.qud-ad-actions { display: flex; align-items: center; gap: 8px; }',
      '.qud-btn { display: inline-block; padding: 8px 16px; border-radius: 8px; background: #3b82f6; color: #fff !important; text-decoration: none; font-weight: 600; font-size: 12.5px; border: none; cursor: pointer; }',
      '.qud-btn:hover { background: #2563eb; }',
      '.qud-close { background: rgba(255,255,255,0.12); color: #e2e8f0; border: none; border-radius: 6px; padding: 6px 10px; cursor: pointer; font-size: 12px; }',
      '.qud-footer { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px; padding-top: 6px; border-top: 1px solid rgba(148,163,184,0.15); }',
      '.qud-brand { font-weight: 600; color: #f8fafc; }',
      '.qud-pill { display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 999px; font-size: 11.5px; font-weight: 600; background: rgba(16,185,129,0.15); color: #6ee7b7; border: 1px solid rgba(16,185,129,0.35); }',
      '.qud-office-pill { background: rgba(139,92,246,0.18); color: #ddd6fe; border: 1px solid rgba(139,92,246,0.4); }',
      '.qud-links a { color: #93c5fd; text-decoration: none; margin-inline-start: 12px; font-size: 12px; }',
      '.qud-links a:hover { text-decoration: underline; }'
    ].join('\n');

    var adHtml = showAd
      ? '<div class="qud-ad-box" id="qud-ad-card">' +
          '<div class="qud-ad-meta">' +
            '<span class="qud-ad-tag">' + esc(ad.tag || 'إعلان QudSystem') + '</span>' +
            '<div class="qud-ad-title">' + esc(ad.title) + '</div>' +
            '<p class="qud-ad-desc">' + esc(ad.description) + '</p>' +
          '</div>' +
          '<div class="qud-ad-actions">' +
            '<a class="qud-btn" href="' + esc(ad.ctaUrl || cfg.portalUrl) + '" target="_blank" rel="noopener noreferrer">' + esc(ad.ctaText || 'التفاصيل') + '</a>' +
            '<button class="qud-close" type="button" id="qud-ad-dismiss" title="إخفاء مؤقت">✕</button>' +
          '</div>' +
        '</div>'
      : '';

    var tierBadge = paid
      ? '<span class="qud-pill">✓ النسخة المدفوعة — تجربة كاملة بدون إعلانات</span>'
      : '<span class="qud-pill">النسخة المجانية (مدعومة بإعلان قابل للتحديث) • الباقات المدفوعة بدون إعلانات قريباً</span>';

    var officeBadge = '<span class="qud-pill qud-office-pill">🚀 ' + esc((feed.officeAiBanner && feed.officeAiBanner.titleAr) || DEFAULT_FEED.officeAiBanner.titleAr) + '</span>';

    shadow.innerHTML =
      '<style>' + styles + '</style>' +
      '<div class="qud-wrap">' +
        '<div class="qud-inner">' +
          adHtml +
          '<div class="qud-footer">' +
            '<div class="qud-brand">' +
              '<span>من تقديم شركة <strong>QudSystem</strong> • ' + esc(cfg.projectName) + ' (' + esc(cfg.category) + ') — ضمن حزمة برمجية متكاملة</span>' +
            '</div>' +
            '<div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;">' +
              officeBadge +
              tierBadge +
            '</div>' +
            '<div class="qud-links">' +
              '<a href="https://github.com/Qudsystem" target="_blank" rel="noopener noreferrer">منظومة QudSystem على GitHub</a>' +
              '<a href="' + esc(cfg.portalUrl) + '" target="_blank" rel="noopener noreferrer">الموقع الموحد</a>' +
            '</div>' +
          '</div>' +
        '</div>' +
      '</div>';

    var target = document.body || document.documentElement;
    if (target) target.appendChild(host);

    var dismissBtn = shadow.getElementById ? shadow.getElementById('qud-ad-dismiss') : null;
    if (dismissBtn) {
      dismissBtn.addEventListener('click', function () {
        var card = shadow.getElementById('qud-ad-card');
        if (card) card.style.display = 'none';
        try { window.sessionStorage && window.sessionStorage.setItem('qud_ad_dismissed', '1'); } catch (_) {}
      });
    }
  }

  function boot() {
    fetchAdFeed(cfg.adEndpoints, 0, renderWidget);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
