import { useEffect, useState } from "react";
import { getAuth, putAuth } from "../api";

export default function Auth() {
  const [raw, setRaw] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getAuth()
      .then((d) => setRaw(JSON.stringify(d, null, 2)))
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = () => {
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(raw);
    } catch {
      setError("JSON 格式无效");
      return;
    }
    setSaving(true);
    setError(null);
    putAuth(parsed)
      .then(() => setSaving(false))
      .catch((e) => {
        setError(String(e));
        setSaving(false);
      });
  };

  if (loading) return <p>加载中…</p>;
  return (
    <div className="page">
      <h2>认证 (auth.json)</h2>
      <p className="muted">敏感信息，请勿外泄。建议仅在内网或本机使用本管理页。</p>
      {error && <p className="error">{error}</p>}
      <textarea
        className="json-edit"
        value={raw}
        onChange={(e) => setRaw(e.target.value)}
        rows={16}
      />
      <button onClick={handleSave} disabled={saving}>
        {saving ? "保存中…" : "保存"}
      </button>
    </div>
  );
}
