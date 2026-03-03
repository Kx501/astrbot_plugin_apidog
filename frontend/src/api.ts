const base =
  (import.meta.env.VITE_API_URL && String(import.meta.env.VITE_API_URL).trim()) ||
  (typeof window !== "undefined" ? `${window.location.origin}/api` : "http://localhost:5787/api");

const PASSWORD_KEY = "apidog_config_password";

export function getStoredPassword(): string | null {
  return sessionStorage.getItem(PASSWORD_KEY);
}

export function setStoredPassword(pwd: string): void {
  sessionStorage.setItem(PASSWORD_KEY, pwd);
}

export function clearStoredPassword(): void {
  sessionStorage.removeItem(PASSWORD_KEY);
}

/** 前端只存哈希，不存明文。与后端 SHA-256 一致。 */
export async function hashPassword(plain: string): Promise<string> {
  const enc = new TextEncoder().encode(plain);
  const buf = await crypto.subtle.digest("SHA-256", enc);
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/** 无需密码，用于判断是否已初始化 */
export async function getStatus(): Promise<{ initialized: boolean }> {
  const res = await fetch(`${base}/status`);
  if (!res.ok) throw new Error("Failed to get status");
  return res.json();
}

/** 仅未初始化时可用，设置密码并写入后端 config */
export async function postInit(password: string): Promise<{ status: string }> {
  const res = await fetch(`${base}/init`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password: password.trim() }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error((err as { detail?: string }).detail ?? "Request failed");
  }
  return res.json() as Promise<{ status: string }>;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const password = getStoredPassword();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string>),
  };
  if (password) headers["X-Config-Password"] = password;

  const res = await fetch(`${base}${path}`, { ...options, headers });
  if (res.status === 401) {
    clearStoredPassword();
    window.location.href = "/";
    throw new Error("Unauthorized");
  }
  if (res.status === 429) {
    const err = await res.json().catch(() => ({ detail: "Too many attempts" }));
    throw new Error((err as { detail?: string }).detail ?? "请求过于频繁，请稍后再试");
  }
  if (res.status === 403) {
    const err = await res.json().catch(() => ({}));
    if ((err as { detail?: string }).detail === "not_initialized") {
      window.location.href = "/";
    }
    throw new Error((err as { detail?: string }).detail ?? "Forbidden");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error((err as { detail?: string }).detail ?? "Request failed");
  }
  return res.json() as Promise<T>;
}

export async function getConfig() {
  return request<Record<string, unknown>>("/config");
}
export async function putConfig(body: Record<string, unknown>) {
  return request<{ status: string }>("/config", { method: "PUT", body: JSON.stringify(body) });
}

export async function getApis() {
  return request<Record<string, unknown>[]>("/apis");
}
export async function putApis(apis: Record<string, unknown>[]) {
  return request<{ status: string }>("/apis", { method: "PUT", body: JSON.stringify({ apis }) });
}

export async function getSchedules() {
  return request<Record<string, unknown>[]>("/schedules");
}
export async function putSchedules(schedules: Record<string, unknown>[]) {
  return request<{ status: string }>("/schedules", { method: "PUT", body: JSON.stringify({ schedules }) });
}

export async function getGroups() {
  return request<{ user_groups?: Record<string, string[]>; group_groups?: Record<string, string[]> }>("/groups");
}
export async function putGroups(body: Record<string, unknown>) {
  return request<{ status: string }>("/groups", { method: "PUT", body: JSON.stringify(body) });
}

export async function getAuth() {
  return request<Record<string, unknown>>("/auth");
}
export async function putAuth(body: Record<string, unknown>) {
  return request<{ status: string }>("/auth", { method: "PUT", body: JSON.stringify(body) });
}
