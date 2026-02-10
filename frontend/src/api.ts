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
