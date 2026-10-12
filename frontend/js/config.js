// Frontend configuration. The ONLY link between this UI and the backend is the API base URL.
// Override without editing code:  ?api=http://host:port   (remembered in localStorage)

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

function resolveApiBase() {
  try {
    const fromQuery = new URLSearchParams(window.location.search).get("api");
    if (fromQuery) localStorage.setItem("learn4all.api", fromQuery);
    return (fromQuery || localStorage.getItem("learn4all.api") || DEFAULT_API_BASE_URL).replace(/\/+$/, "");
  } catch {
    return DEFAULT_API_BASE_URL;
  }
}

export const config = {
  apiBaseUrl: resolveApiBase(),
  defaultApiBaseUrl: DEFAULT_API_BASE_URL,
  setApiBaseUrl(url) {
    try { localStorage.setItem("learn4all.api", url.replace(/\/+$/, "")); } catch { /* ignore */ }
    this.apiBaseUrl = url.replace(/\/+$/, "");
  },
};
