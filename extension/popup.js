// popup.js
// CorePass masaüstü uygulamasının yerel API'siyle (http://127.0.0.1:5732) haberleşir.

const API_BASE = "http://127.0.0.1:5732";

const els = {
  statusDot: document.getElementById("status-dot"),
  viewOffline: document.getElementById("view-offline"),
  viewPair: document.getElementById("view-pair"),
  viewLocked: document.getElementById("view-locked"),
  viewMain: document.getElementById("view-main"),
  pairingInput: document.getElementById("pairing-input"),
  pairError: document.getElementById("pair-error"),
  btnPair: document.getElementById("btn-pair"),
  btnRetry: document.getElementById("btn-retry"),
  btnRetry2: document.getElementById("btn-retry-2"),
  searchInput: document.getElementById("search-input"),
  entriesList: document.getElementById("entries-list"),
  siteMatchesSection: document.getElementById("site-matches-section"),
  siteMatchesList: document.getElementById("site-matches-list"),
  tabButtons: document.querySelectorAll(".tab-btn"),
  tabEntries: document.getElementById("tab-entries"),
  tabGenerator: document.getElementById("tab-generator"),
  generatedPassword: document.getElementById("generated-password"),
  btnCopyGenerated: document.getElementById("btn-copy-generated"),
  strengthLabel: document.getElementById("strength-label"),
  lengthSlider: document.getElementById("length-slider"),
  lengthValue: document.getElementById("length-value"),
  optUpper: document.getElementById("opt-upper"),
  optDigits: document.getElementById("opt-digits"),
  optSymbols: document.getElementById("opt-symbols"),
  btnGenerate: document.getElementById("btn-generate"),
};

let allEntries = [];
let currentDomain = "";

function showView(name) {
  [els.viewOffline, els.viewPair, els.viewLocked, els.viewMain].forEach((v) => v.classList.add("hidden"));
  const map = { offline: els.viewOffline, pair: els.viewPair, locked: els.viewLocked, main: els.viewMain };
  map[name].classList.remove("hidden");
}

function setStatusDot(state) {
  els.statusDot.className = "status-dot status-" + state;
}

async function getStoredToken() {
  const data = await chrome.storage.local.get("corepass_token");
  return data.corepass_token || null;
}

async function saveToken(token) {
  await chrome.storage.local.set({ corepass_token: token });
}

async function apiFetch(path, options = {}) {
  const token = await getStoredToken();
  const headers = Object.assign({}, options.headers, {
    "Content-Type": "application/json",
    "X-CorePass-Token": token || "",
  });
  const res = await fetch(API_BASE + path, { ...options, headers });
  return res;
}

async function init() {
  const token = await getStoredToken();
  if (!token) {
    setStatusDot("unknown");
    showView("pair");
    return;
  }

  try {
    const res = await apiFetch("/status");
    if (res.status === 401) {
      // Token geçersiz -> yeniden eşleştirme gerekli
      await saveToken(null);
      showView("pair");
      setStatusDot("offline");
      return;
    }
    const data = await res.json();
    setStatusDot("online");
    if (!data.unlocked) {
      showView("locked");
    } else {
      showView("main");
      loadEntries();
    }
  } catch (err) {
    setStatusDot("offline");
    showView("offline");
  }
}

async function pair() {
  const code = els.pairingInput.value.trim();
  els.pairError.classList.add("hidden");

  if (code.length !== 8) {
    els.pairError.textContent = "Kod 8 karakter olmalıdır.";
    els.pairError.classList.remove("hidden");
    return;
  }

  try {
    const res = await fetch(API_BASE + "/pair", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pairing_code: code }),
    });
    if (!res.ok) {
      els.pairError.textContent = "Eşleştirme kodu hatalı.";
      els.pairError.classList.remove("hidden");
      return;
    }
    const data = await res.json();
    await saveToken(data.token);
    init();
  } catch (err) {
    setStatusDot("offline");
    showView("offline");
  }
}

async function getCurrentTabDomain() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.url) return "";
    return new URL(tab.url).hostname.replace(/^www\./, "");
  } catch (err) {
    return "";
  }
}

function domainMatches(entrySite, domain) {
  if (!domain) return false;
  const a = entrySite.toLowerCase().replace(/^www\./, "");
  const b = domain.toLowerCase();
  return a === b || a.includes(b) || b.includes(a);
}

async function loadEntries() {
  try {
    currentDomain = await getCurrentTabDomain();
    const res = await apiFetch("/entries");
    if (!res.ok) {
      showView("locked");
      return;
    }
    const data = await res.json();
    allEntries = data.entries || [];
    renderSiteMatches();
    renderEntries(allEntries);
  } catch (err) {
    setStatusDot("offline");
    showView("offline");
  }
}

function renderSiteMatches() {
  const matches = allEntries.filter((e) => domainMatches(e.site, currentDomain));
  if (matches.length === 0) {
    els.siteMatchesSection.classList.add("hidden");
    els.siteMatchesList.innerHTML = "";
    return;
  }
  els.siteMatchesSection.classList.remove("hidden");
  renderEntries(matches, els.siteMatchesList, true);
}

function renderEntries(entries, container = els.entriesList, showFill = false) {
  container.innerHTML = "";

  if (entries.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "Kayıtlı hesap bulunamadı.";
    container.appendChild(empty);
    return;
  }

  entries.forEach((entry) => {
    const row = document.createElement("div");
    row.className = "entry-row";

    const info = document.createElement("div");
    info.className = "entry-info";

    const site = document.createElement("span");
    site.className = "entry-site";
    site.textContent = entry.site;

    const user = document.createElement("span");
    user.className = "entry-user";
    user.textContent = entry.username;

    info.appendChild(site);
    info.appendChild(user);

    const actions = document.createElement("div");
    actions.className = "entry-actions";

    if (showFill) {
      const fillBtn = document.createElement("button");
      fillBtn.className = "icon-btn fill-btn";
      fillBtn.textContent = "Doldur";
      fillBtn.style.width = "auto";
      fillBtn.style.padding = "0 8px";
      fillBtn.title = "Formu otomatik doldur";
      fillBtn.addEventListener("click", () => fillOnPage(entry.username, entry.password));
      actions.appendChild(fillBtn);
    }

    const copyBtn = document.createElement("button");
    copyBtn.className = "icon-btn";
    copyBtn.textContent = "⧉";
    copyBtn.title = "Şifreyi panoya kopyala";
    copyBtn.addEventListener("click", () => copyToClipboard(entry.password));
    actions.appendChild(copyBtn);

    row.appendChild(info);
    row.appendChild(actions);
    container.appendChild(row);
  });
}

async function fillOnPage(username, password) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return;
  chrome.tabs.sendMessage(tab.id, { type: "FILL_CREDENTIALS", username, password }, () => {
    window.close();
  });
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text);
}

function filterEntries() {
  const q = els.searchInput.value.toLowerCase();
  const filtered = allEntries.filter(
    (e) => e.site.toLowerCase().includes(q) || e.username.toLowerCase().includes(q)
  );
  renderEntries(filtered);
}

async function generatePassword() {
  try {
    const res = await apiFetch("/generate", {
      method: "POST",
      body: JSON.stringify({
        length: parseInt(els.lengthSlider.value, 10),
        uppercase: els.optUpper.checked,
        lowercase: true,
        digits: els.optDigits.checked,
        symbols: els.optSymbols.checked,
      }),
    });
    const data = await res.json();
    els.generatedPassword.textContent = data.password;
    els.strengthLabel.textContent = "Güç: " + data.strength;
  } catch (err) {
    setStatusDot("offline");
    showView("offline");
  }
}

function switchTab(tabName) {
  els.tabButtons.forEach((btn) => btn.classList.toggle("active", btn.dataset.tab === tabName));
  els.tabEntries.classList.toggle("hidden", tabName !== "entries");
  els.tabGenerator.classList.toggle("hidden", tabName !== "generator");
}

// --- Olay dinleyicileri ---
els.btnPair.addEventListener("click", pair);
els.btnRetry.addEventListener("click", init);
els.btnRetry2.addEventListener("click", init);
els.searchInput.addEventListener("input", filterEntries);
els.btnGenerate.addEventListener("click", generatePassword);
els.btnCopyGenerated.addEventListener("click", () =>
  copyToClipboard(els.generatedPassword.textContent)
);
els.lengthSlider.addEventListener("input", () => {
  els.lengthValue.textContent = els.lengthSlider.value;
});
els.tabButtons.forEach((btn) => btn.addEventListener("click", () => switchTab(btn.dataset.tab)));

document.addEventListener("DOMContentLoaded", init);
