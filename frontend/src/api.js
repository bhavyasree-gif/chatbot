// Small fetch wrapper: JSON in, JSON out, readable errors.
export async function api(path, { method = "GET", body, params, headers = {} } = {}) {
  const query = params
    ? "?" + new URLSearchParams(Object.entries(params).filter(([, v]) => v !== "" && v != null))
    : "";
  let res;
  const jsonBody = body != null && !(body instanceof FormData);
  try {
    res = await fetch("/api" + path + query, {
      method,
      headers: { ...(jsonBody ? { "Content-Type": "application/json" } : {}), ...headers },
      body: jsonBody ? JSON.stringify(body) : body,
    });
  } catch {
    throw new Error("Cannot reach the API. Start the backend with: python -m backend.app");
  }
  let data = null;
  try { data = await res.json(); } catch { /* empty body */ }
  if (!res.ok) throw new Error(data?.error || `Request failed (${res.status})`);
  return data;
}

export const fmtBytes = (b = 0) =>
  b >= 1048576 ? (b / 1048576).toFixed(1) + " MB" : b >= 1024 ? (b / 1024).toFixed(1) + " KB" : b + " B";
export const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" }) : "");
