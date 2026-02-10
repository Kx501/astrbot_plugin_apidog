import { useEffect, useState } from "react";
import { getConfig, putConfig } from "../api";

export default function Config() {
  const [data, setData] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getConfig()
      .then(setData)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = () => {
    setSaving(true);
    setError(null);
    putConfig(data)
      .then(() => setSaving(false))
      .catch((e) => {
        setError(String(e));
        setSaving(false);
      });
  };

  const retry = (data?.retry as Record<string, unknown>) ?? {};
  const statuses = Array.isArray(data?.retry_statuses)
    ? (data.retry_statuses as number[]).join(",")
    : "";

  if (loading) return <p>加载中…</p>;
  return (
    <div className="page">
      <h2>全局配置 <span className="field-origin">(config.json)</span></h2>
      {error && <p className="error">{error}</p>}
      <section className="page-section">
        <h3>端口与超时</h3>
        <div className="form-group">
          <label>API 端口 <span className="field-origin">(api_port)</span></label>
          <input
            type="number"
            min={1}
            max={65535}
            value={Number(data?.api_port ?? 5787)}
            onChange={(e) => setData({ ...data, api_port: Number(e.target.value) || 5787 })}
            placeholder="5787"
          />
          <p className="muted">修改后需重载插件或重启 API 进程生效。</p>
        </div>
        <div className="form-group">
          <label>超时秒数 <span className="field-origin">(timeout_seconds)</span></label>
          <input
            type="number"
            value={Number(data?.timeout_seconds ?? 30)}
            onChange={(e) => setData({ ...data, timeout_seconds: Number(e.target.value) })}
            placeholder="30"
          />
        </div>
      </section>
      <section className="page-section">
        <h3>重试</h3>
        <div className="form-group">
          <label>重试次数 <span className="field-origin">(retry.max_attempts)</span></label>
          <input
            type="number"
            value={Number(retry.max_attempts ?? 0)}
            onChange={(e) =>
              setData({ ...data, retry: { ...retry, max_attempts: Number(e.target.value) } })
            }
          />
        </div>
        <div className="form-group">
          <label>重试间隔秒 <span className="field-origin">(retry.backoff_seconds)</span></label>
          <input
            type="number"
            step="0.5"
            value={Number(retry.backoff_seconds ?? 1)}
            onChange={(e) =>
              setData({ ...data, retry: { ...retry, backoff_seconds: Number(e.target.value) } })
            }
          />
        </div>
        <div className="form-group">
          <label>可重试状态码，逗号分隔 <span className="field-origin">(retry_statuses)</span></label>
          <input
            type="text"
            value={statuses}
            onChange={(e) =>
              setData({
                ...data,
                retry_statuses: e.target.value
                  .split(",")
                  .map((s) => parseInt(s.trim(), 10))
                  .filter((n) => !Number.isNaN(n)),
              })
            }
            placeholder="500, 502, 503, 429"
          />
        </div>
      </section>
      <div className="button-row">
        <button onClick={handleSave} disabled={saving}>
          {saving ? "保存中…" : "保存"}
        </button>
      </div>
    </div>
  );
}
