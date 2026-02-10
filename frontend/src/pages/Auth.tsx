import { useEffect, useState } from "react";
import { getAuth, putAuth } from "../api";

type AuthEntry = {
  name: string;
  type: "bearer" | "api_key" | "basic";
  token?: string;
  header?: string;
  value?: string;
  inQuery?: boolean;
  username?: string;
  password?: string;
};

function fromApi(data: Record<string, unknown>): AuthEntry[] {
  return Object.entries(data).map(([name, obj]) => {
    if (typeof obj !== "object" || obj === null) {
      return { name, type: "bearer" as const, token: "" };
    }
    const o = obj as Record<string, unknown>;
    const type = String(o.type ?? "bearer").toLowerCase() as AuthEntry["type"];
    const entry: AuthEntry = { name, type: type === "api_key" ? "api_key" : type === "basic" ? "basic" : "bearer" };
    if (entry.type === "bearer") {
      entry.token = String(o.token ?? o.value ?? "");
    } else if (entry.type === "api_key") {
      entry.header = String(o.header ?? o.key ?? "X-API-Key");
      entry.value = String(o.value ?? o.token ?? "");
      entry.inQuery = o.in === "query";
    } else {
      entry.username = String(o.username ?? o.user ?? "");
      entry.password = String(o.password ?? o.pass ?? "");
    }
    return entry;
  });
}

function toApi(entries: AuthEntry[]): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const e of entries) {
    const name = e.name.trim();
    if (!name) continue;
    if (e.type === "bearer") {
      out[name] = { type: "bearer", token: e.token ?? "" };
    } else if (e.type === "api_key") {
      out[name] = {
        type: "api_key",
        header: e.header ?? "X-API-Key",
        value: e.value ?? "",
        ...(e.inQuery ? { in: "query" } : {}),
      };
    } else {
      out[name] = { type: "basic", username: e.username ?? "", password: e.password ?? "" };
    }
  }
  return out;
}

export default function Auth() {
  const [entries, setEntries] = useState<AuthEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [rawOpen, setRawOpen] = useState(false);
  const [raw, setRaw] = useState("");

  useEffect(() => {
    getAuth()
      .then((d) => {
        setEntries(fromApi(d));
        setRaw(JSON.stringify(d, null, 2));
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = () => {
    const body = toApi(entries);
    setSaving(true);
    setError(null);
    putAuth(body)
      .then(() => {
        setSaving(false);
        setRaw(JSON.stringify(body, null, 2));
      })
      .catch((e) => {
        setError(String(e));
        setSaving(false);
      });
  };

  const handleSaveRaw = () => {
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(raw);
    } catch {
      setError("JSON 格式无效");
      return;
    }
    setEntries(fromApi(parsed));
    setSaving(true);
    setError(null);
    putAuth(parsed)
      .then(() => setSaving(false))
      .catch((e) => {
        setError(String(e));
        setSaving(false);
      });
  };

  const update = (index: number, field: keyof AuthEntry, value: string | boolean) => {
    setEntries((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  };
  const add = () => setEntries((prev) => [...prev, { name: "", type: "bearer", token: "" }]);
  const remove = (index: number) => setEntries((prev) => prev.filter((_, i) => i !== index));

  if (loading) return <p>加载中…</p>;
  return (
    <div className="page">
      <h2>认证 <span className="field-origin">(auth.json)</span></h2>
      <p className="muted">敏感信息，请勿外泄。建议仅在内网或本机使用本管理页。</p>
      {error && <p className="error">{error}</p>}
      <div className="button-row">
        <button onClick={add}>新增条目</button>
        <button onClick={handleSave} disabled={saving}>
          {saving ? "保存中…" : "保存"}
        </button>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>名称</th>
            <th>类型 <span className="field-origin">(type)</span></th>
            <th>参数</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e, i) => (
            <tr key={i}>
              <td>
                <input
                  className="table-input"
                  value={e.name}
                  onChange={(ev) => update(i, "name", ev.target.value)}
                />
              </td>
              <td>
                <select
                  value={e.type}
                  onChange={(ev) => update(i, "type", ev.target.value as AuthEntry["type"])}
                  style={{ padding: "0.35rem", minWidth: "8em" }}
                >
                  <option value="bearer">bearer</option>
                  <option value="api_key">api_key</option>
                  <option value="basic">basic</option>
                </select>
              </td>
              <td>
                {e.type === "bearer" && (
                  <input
                    className="table-input"
                    placeholder="token"
                    value={e.token ?? ""}
                    onChange={(ev) => update(i, "token", ev.target.value)}
                  />
                )}
                {e.type === "api_key" && (
                  <span style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
                    <input
                      className="table-input"
                      placeholder="header 名"
                      value={e.header ?? ""}
                      onChange={(ev) => update(i, "header", ev.target.value)}
                      style={{ width: "8em" }}
                    />
                    <input
                      className="table-input"
                      placeholder="value"
                      value={e.value ?? ""}
                      onChange={(ev) => update(i, "value", ev.target.value)}
                      style={{ minWidth: "10em" }}
                    />
                    <label style={{ whiteSpace: "nowrap" }}>
                      <input
                        type="checkbox"
                        checked={e.inQuery ?? false}
                        onChange={(ev) => update(i, "inQuery", ev.target.checked)}
                      />
                      query
                    </label>
                  </span>
                )}
                {e.type === "basic" && (
                  <span style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                    <input
                      className="table-input"
                      placeholder="username"
                      value={e.username ?? ""}
                      onChange={(ev) => update(i, "username", ev.target.value)}
                      style={{ width: "10em" }}
                    />
                    <input
                      className="table-input"
                      placeholder="password"
                      type="password"
                      value={e.password ?? ""}
                      onChange={(ev) => update(i, "password", ev.target.value)}
                      style={{ width: "10em" }}
                    />
                  </span>
                )}
              </td>
              <td>
                <button onClick={() => remove(i)}>删除</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className={`accordion-section ${rawOpen ? "open" : ""}`} style={{ marginTop: "1.5rem" }}>
        <div className="accordion-head" onClick={() => setRawOpen(!rawOpen)}>
          编辑原始 JSON
        </div>
        <div className="accordion-body">
          <textarea
            className="json-edit"
            value={raw}
            onChange={(ev) => setRaw(ev.target.value)}
            rows={12}
          />
          <div className="button-row">
            <button onClick={handleSaveRaw} disabled={saving}>
              从 JSON 保存
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
