// background.js (service worker)
// content.js ve popup.js ile CorePass local API (http://127.0.0.1:5732) arasında
// köprü görevi görür. Content script'ler CORS/CSP kısıtlamalarına takılmadan
// bu worker üzerinden veri alışverişi yapar.

const API_BASE = "http://127.0.0.1:5732";

chrome.runtime.onInstalled.addListener(() => {
  console.log("CorePass eklentisi kuruldu. Masaüstü uygulamasının açık olduğundan emin olun.");

  chrome.contextMenus.create({
    id: "corepass-fill",
    title: "CorePass ile doldur",
    contexts: ["editable"],
  });
});

async function getToken() {
  const data = await chrome.storage.local.get("corepass_token");
  return data.corepass_token || null;
}

async function apiFetch(path, options = {}) {
  const token = await getToken();
  const headers = Object.assign({}, options.headers, {
    "Content-Type": "application/json",
    "X-CorePass-Token": token || "",
  });
  return fetch(API_BASE + path, { ...options, headers });
}

function domainMatches(entrySite, pageDomain) {
  const a = entrySite.toLowerCase().replace(/^www\./, "");
  const b = pageDomain.toLowerCase().replace(/^www\./, "");
  return a === b || a.includes(b) || b.includes(a);
}

// --------------------------------------------------------------------- //
// content.js / popup.js -> background.js mesajları
// --------------------------------------------------------------------- //
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "GET_MATCHES") {
    (async () => {
      try {
        const res = await apiFetch("/entries");
        if (!res.ok) {
          sendResponse({ matches: [] });
          return;
        }
        const data = await res.json();
        const matches = (data.entries || []).filter((e) => domainMatches(e.site, message.domain));
        sendResponse({ matches });
      } catch (err) {
        sendResponse({ matches: [] });
      }
    })();
    return true; // async yanıt için kanalı açık tut
  }

  if (message.type === "SAVE_ENTRY") {
    (async () => {
      try {
        const res = await apiFetch("/entries", {
          method: "POST",
          body: JSON.stringify({
            site: message.site,
            username: message.username,
            password: message.password,
          }),
        });
        sendResponse({ ok: res.ok });
      } catch (err) {
        sendResponse({ ok: false });
      }
    })();
    return true;
  }
});

// --------------------------------------------------------------------- //
// Sağ tık menüsü: "CorePass ile doldur"
// --------------------------------------------------------------------- //
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "corepass-fill" && tab?.id) {
    chrome.tabs.sendMessage(tab.id, { type: "OPEN_DROPDOWN_AT_ACTIVE" });
  }
});

// --------------------------------------------------------------------- //
// Klavye kısayolu: Ctrl+Shift+L (Mac: Command+Shift+L)
// --------------------------------------------------------------------- //
chrome.commands.onCommand.addListener((command) => {
  if (command === "corepass-autofill") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]?.id) {
        chrome.tabs.sendMessage(tabs[0].id, { type: "AUTOFILL_BEST_MATCH" });
      }
    });
  }
});
