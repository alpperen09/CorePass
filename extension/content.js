// content.js
// Web sayfalarına enjekte edilir. Görevleri:
//   1. Kullanıcı adı/şifre alanlarını algılamak
//   2. Şifre alanının içine tıklanabilir bir CorePass ikonu yerleştirmek
//   3. İkona tıklanınca bu site için eşleşen hesapları açılır listede göstermek
//   4. Seçilen hesabı forma otomatik doldurmak
//   5. Form gönderildiğinde, eşleşen kayıt yoksa "kaydetmek ister misiniz?" banner'ı göstermek
//
// Tüm enjekte edilen arayüz elemanları Shadow DOM içinde tutulur; böylece
// ziyaret edilen sitenin CSS'i CorePass arayüzünü bozamaz ve tam tersi de olmaz.

(() => {
  if (window.__corepassInjected) return;
  window.__corepassInjected = true;

  const ACCENT = "#3DAEE9";
  const BG_CARD = "#1E2530";
  const BG_DARK = "#131826";
  const TEXT = "#E8EDF4";
  const TEXT_DIM = "#8A94A6";

  let hostRoot = null; // Shadow DOM host elementi
  let shadow = null;
  let currentMatches = [];
  let trackedFieldPairs = []; // { userField, passField, icon }

  // ------------------------------------------------------------------ //
  // Shadow DOM kurulumu (dropdown ve banner için ortak konteyner)
  // ------------------------------------------------------------------ //
  function ensureShadowHost() {
    if (hostRoot) return shadow;
    hostRoot = document.createElement("div");
    hostRoot.id = "corepass-shadow-host";
    hostRoot.style.cssText = "all: initial; position: fixed; top:0; left:0; z-index: 2147483647;";
    document.documentElement.appendChild(hostRoot);
    shadow = hostRoot.attachShadow({ mode: "open" });

    const style = document.createElement("style");
    style.textContent = `
      * { box-sizing: border-box; font-family: "Segoe UI", "Inter", system-ui, sans-serif; }
      .dropdown {
        position: absolute;
        min-width: 240px;
        max-width: 300px;
        background: ${BG_CARD};
        border: 1px solid #2A3242;
        border-radius: 10px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.45);
        overflow: hidden;
        pointer-events: auto;
      }
      .dropdown-header {
        display: flex; align-items: center; gap: 6px;
        padding: 8px 10px; font-size: 11px; font-weight: 700;
        color: ${ACCENT}; border-bottom: 1px solid #2A3242;
      }
      .dropdown-item {
        display: flex; flex-direction: column; padding: 8px 10px;
        cursor: pointer; border-bottom: 1px solid #232C3A;
      }
      .dropdown-item:last-child { border-bottom: none; }
      .dropdown-item:hover { background: #232C3A; }
      .dropdown-site { color: ${TEXT}; font-size: 12px; font-weight: 600; }
      .dropdown-user { color: ${TEXT_DIM}; font-size: 11px; margin-top: 1px; }
      .dropdown-empty { padding: 12px 10px; font-size: 12px; color: ${TEXT_DIM}; }

      .banner {
        position: fixed; top: 16px; right: 16px;
        width: 280px; background: ${BG_CARD}; color: ${TEXT};
        border: 1px solid #2A3242; border-radius: 12px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        padding: 14px; pointer-events: auto;
        animation: corepass-slide-in 0.18s ease-out;
      }
      @keyframes corepass-slide-in {
        from { transform: translateY(-10px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
      }
      .banner-title { font-size: 13px; font-weight: 700; color: ${ACCENT}; margin-bottom: 4px; }
      .banner-sub { font-size: 11px; color: ${TEXT_DIM}; margin-bottom: 10px; line-height: 1.4; }
      .banner-row { display: flex; gap: 6px; }
      .banner-btn {
        flex: 1; padding: 7px; border: none; border-radius: 7px;
        font-size: 12px; font-weight: 600; cursor: pointer;
      }
      .banner-btn.primary { background: ${ACCENT}; color: ${BG_DARK}; }
      .banner-btn.secondary { background: #2A3242; color: ${TEXT}; }

      .field-icon {
        position: absolute; width: 20px; height: 20px; cursor: pointer;
        border-radius: 5px; display: flex; align-items: center; justify-content: center;
        background: rgba(61,174,233,0.15); pointer-events: auto;
      }
      .field-icon:hover { background: rgba(61,174,233,0.3); }
    `;
    shadow.appendChild(style);
    return shadow;
  }

  function closeDropdown() {
    const el = shadow && shadow.querySelector(".dropdown");
    if (el) el.remove();
  }

  function closeBanner() {
    const el = shadow && shadow.querySelector(".banner");
    if (el) el.remove();
  }

  document.addEventListener("click", (e) => {
    // Shadow DOM dışına tıklanınca açık dropdown'ı kapat
    if (!hostRoot || !hostRoot.contains(e.target)) closeDropdown();
  });

  // ------------------------------------------------------------------ //
  // Form değerini "gerçek" bir kullanıcı girişi gibi ayarlama
  // React/Vue gibi framework'lerin state'ini de güncellemesi için native
  // setter kullanılır, ardından input/change event'leri tetiklenir.
  // ------------------------------------------------------------------ //
  function setNativeValue(field, value) {
    const proto = Object.getPrototypeOf(field);
    const descriptor = Object.getOwnPropertyDescriptor(proto, "value");
    if (descriptor && descriptor.set) {
      descriptor.set.call(field, value);
    } else {
      field.value = value;
    }
    field.dispatchEvent(new Event("input", { bubbles: true }));
    field.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function fillCredentials(userField, passField, username, password) {
    if (userField) {
      userField.focus();
      setNativeValue(userField, username);
    }
    if (passField) {
      passField.focus();
      setNativeValue(passField, password);
      passField.blur();
    }
    closeDropdown();
  }

  // ------------------------------------------------------------------ //
  // Kullanıcı adı / şifre alanlarını algılama
  // ------------------------------------------------------------------ //
  function findUsernameField(passwordField) {
    const form = passwordField.closest("form") || document;
    const candidates = Array.from(
      form.querySelectorAll('input[type="text"], input[type="email"], input:not([type])')
    );
    // Şifre alanından önce gelen, görünür ilk metin alanını kullanıcı adı say
    let best = null;
    for (const input of candidates) {
      if (isVisible(input) && comparePosition(input, passwordField) < 0) {
        best = input; // en son bulunan (şifre alanına en yakın) tercih edilir
      }
    }
    return best;
  }

  function comparePosition(a, b) {
    const pos = a.compareDocumentPosition(b);
    return pos & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1;
  }

  function isVisible(el) {
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0 && el.offsetParent !== null;
  }

  function getPasswordFields() {
    return Array.from(document.querySelectorAll('input[type="password"]')).filter(isVisible);
  }

  // ------------------------------------------------------------------ //
  // Şifre alanının içine CorePass ikonu yerleştirme
  // ------------------------------------------------------------------ //
  function injectIcon(passField) {
    if (passField.dataset.corepassBound) return;
    passField.dataset.corepassBound = "1";

    const userField = findUsernameField(passField);

    // Alana tıklama alanı bırakmak için sağ padding ekle (siteyi bozmadan, sadece bu alan için)
    const existingPaddingRight = window.getComputedStyle(passField).paddingRight;
    if (parseInt(existingPaddingRight, 10) < 28) {
      passField.style.paddingRight = "28px";
    }

    const icon = document.createElement("div");
    icon.textContent = "🔒";
    icon.title = "CorePass ile doldur";
    icon.style.cssText = `
      position: fixed; width: 20px; height: 20px; cursor: pointer;
      font-size: 13px; display: flex; align-items: center; justify-content: center;
      border-radius: 5px; background: rgba(61,174,233,0.18); z-index: 2147483647;
    `;
    document.body.appendChild(icon);

    function positionIcon() {
      const rect = passField.getBoundingClientRect();
      icon.style.top = rect.top + (rect.height - 20) / 2 + "px";
      icon.style.left = rect.right - 26 + "px";
      icon.style.display = isVisible(passField) ? "flex" : "none";
    }
    positionIcon();
    window.addEventListener("scroll", positionIcon, true);
    window.addEventListener("resize", positionIcon);

    icon.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      openDropdownFor(passField, userField, icon);
    });

    trackedFieldPairs.push({ userField, passField, icon, reposition: positionIcon });
  }

  function scanAndInject() {
    getPasswordFields().forEach(injectIcon);
  }

  // ------------------------------------------------------------------ //
  // Eşleşen hesapları açılır listede gösterme
  // ------------------------------------------------------------------ //
  function openDropdownFor(passField, userField, anchorIcon) {
    ensureShadowHost();
    closeDropdown();

    const dropdown = document.createElement("div");
    dropdown.className = "dropdown";

    const rect = anchorIcon.getBoundingClientRect();
    dropdown.style.top = rect.bottom + 6 + "px";
    dropdown.style.left = Math.max(8, rect.right - 260) + "px";

    const header = document.createElement("div");
    header.className = "dropdown-header";
    header.textContent = "🔒 CorePass — Bu site için hesaplar";
    dropdown.appendChild(header);

    if (currentMatches.length === 0) {
      const empty = document.createElement("div");
      empty.className = "dropdown-empty";
      empty.textContent = "Bu site için kayıtlı hesap bulunamadı.";
      dropdown.appendChild(empty);
    } else {
      currentMatches.forEach((entry) => {
        const item = document.createElement("div");
        item.className = "dropdown-item";
        item.innerHTML = `<span class="dropdown-site"></span><span class="dropdown-user"></span>`;
        item.querySelector(".dropdown-site").textContent = entry.site;
        item.querySelector(".dropdown-user").textContent = entry.username;
        item.addEventListener("click", () => {
          fillCredentials(userField, passField, entry.username, entry.password);
        });
        dropdown.appendChild(item);
      });
    }

    shadow.appendChild(dropdown);
  }

  // ------------------------------------------------------------------ //
  // Arka plana bu site için eşleşen hesapları sorma
  // ------------------------------------------------------------------ //
  function requestMatches() {
    chrome.runtime.sendMessage({ type: "GET_MATCHES", domain: window.location.hostname }, (res) => {
      if (chrome.runtime.lastError) return;
      currentMatches = (res && res.matches) || [];
    });
  }

  // ------------------------------------------------------------------ //
  // "Yeni hesabı kaydet?" banner'ı — form gönderildiğinde tetiklenir
  // ------------------------------------------------------------------ //
  function showSaveBanner(site, username, password) {
    ensureShadowHost();
    closeBanner();

    const banner = document.createElement("div");
    banner.className = "banner";
    banner.innerHTML = `
      <div class="banner-title">🔒 CorePass</div>
      <div class="banner-sub">"${escapeHtml(site)}" için <b>${escapeHtml(username)}</b> hesabını kasanıza kaydetmek ister misiniz?</div>
      <div class="banner-row">
        <button class="banner-btn secondary" id="corepass-skip">Hayır</button>
        <button class="banner-btn primary" id="corepass-save">Kaydet</button>
      </div>
    `;
    shadow.appendChild(banner);

    banner.querySelector("#corepass-skip").addEventListener("click", closeBanner);
    banner.querySelector("#corepass-save").addEventListener("click", () => {
      chrome.runtime.sendMessage(
        { type: "SAVE_ENTRY", site, username, password },
        () => closeBanner()
      );
    });

    setTimeout(closeBanner, 15000); // 15 sn sonra otomatik kapanır
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function watchFormSubmits() {
    document.addEventListener(
      "submit",
      (e) => {
        const form = e.target;
        if (!(form instanceof HTMLFormElement)) return;

        const passField = form.querySelector('input[type="password"]');
        if (!passField || !passField.value) return;

        const userField = findUsernameField(passField);
        const username = userField ? userField.value : "";
        if (!username) return;

        const alreadySaved = currentMatches.some(
          (m) => m.username.toLowerCase() === username.toLowerCase()
        );
        if (alreadySaved) return;

        const site = window.location.hostname;
        const password = passField.value;
        // Sayfa yönlendirmeden önce banner'ı göstermek için küçük bir gecikme
        setTimeout(() => showSaveBanner(site, username, password), 400);
      },
      true
    );
  }

  // ------------------------------------------------------------------ //
  // Popup veya klavye kısayolundan gelen komutlar
  // ------------------------------------------------------------------ //
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "FILL_CREDENTIALS") {
      const passField = getPasswordFields()[0];
      const userField = passField ? findUsernameField(passField) : null;
      fillCredentials(userField, passField, message.username, message.password);
      sendResponse({ ok: true });
    }
    if (message.type === "AUTOFILL_BEST_MATCH") {
      if (currentMatches.length > 0) {
        const passField = getPasswordFields()[0];
        const userField = passField ? findUsernameField(passField) : null;
        fillCredentials(userField, passField, currentMatches[0].username, currentMatches[0].password);
      }
      sendResponse({ ok: true });
    }
    if (message.type === "OPEN_DROPDOWN_AT_ACTIVE") {
      const active = document.activeElement;
      if (active && active.tagName === "INPUT" && active.type === "password") {
        const pair = trackedFieldPairs.find((p) => p.passField === active);
        if (pair) openDropdownFor(pair.passField, pair.userField, pair.icon);
      }
      sendResponse({ ok: true });
    }
    return true;
  });

  // ------------------------------------------------------------------ //
  // Başlangıç + dinamik olarak eklenen formları izleme (SPA desteği)
  // ------------------------------------------------------------------ //
  function init() {
    requestMatches();
    scanAndInject();
    watchFormSubmits();

    const observer = new MutationObserver(() => {
      scanAndInject();
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
