import { useEffect, useState } from "react";
import { getGroups, putGroups } from "../api";

export default function Groups() {
  const [raw, setRaw] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getGroups()
      .then((r) => setRaw(JSON.stringify({ user_groups: r.user_groups ?? {}, group_groups: r.group_groups ?? {} }, null, 2)))
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
    putGroups(parsed)
      .then(() => setSaving(false))
      .catch((e) => {
        setError(String(e));
        setSaving(false);
      });
  };

  if (loading) return <p>加载中…</p>;
  return (
    <div className="page">
      <h2>用户/群组 (groups.json)</h2>
      {error && <p className="error">{error}</p>}
      <p>请以 JSON 形式编辑后保存。</p>
      <textarea
        className="json-edit"
        value={raw}
        onChange={(e) => setRaw(e.target.value)}
        rows={20}
      />
      <button onClick={handleSave} disabled={saving}>
        {saving ? "保存中…" : "保存"}
      </button>
    </div>
  );
}
