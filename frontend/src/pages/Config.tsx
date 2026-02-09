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
      <h2>全局配置 (config.json)</h2>
      {error && <p className="error">{error}</p>}
      <div className="form-group">
        <label>timeout_seconds</label>
        <input
          type="number"
          value={Number(data?.timeout_seconds ?? 30)}
          onChange={(e) => setData({ ...data, timeout_seconds: Number(e.target.value) })}
        />
      </div>
      <div className="form-group">
        <label>retry.max_attempts</label>
        <input
          type="number"
          value={Number(retry.max_attempts ?? 0)}
          onChange={(e) =>
            setData({ ...data, retry: { ...retry, max_attempts: Number(e.target.value) } })
          }
        />
      </div>
      <div className="form-group">
        <label>retry.backoff_seconds</label>
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
        <label>retry_statuses (逗号分隔)</label>
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
        />
      </div>
      <button onClick={handleSave} disabled={saving}>
        {saving ? "保存中…" : "保存"}
      </button>
    </div>
  );
}
