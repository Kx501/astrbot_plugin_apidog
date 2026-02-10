import { useEffect, useState } from "react";
import { getSchedules, putSchedules } from "../api";

export default function Schedules() {
  const [list, setList] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getSchedules()
      .then(setList)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = () => {
    setSaving(true);
    setError(null);
    putSchedules(list)
      .then(() => setSaving(false))
      .catch((e) => {
        setError(String(e));
        setSaving(false);
      });
  };

  const update = (index: number, key: string, value: unknown) => {
    const next = [...list];
    next[index] = { ...next[index], [key]: value };
    setList(next);
  };
  const remove = (index: number) => setList(list.filter((_, i) => i !== index));
  const add = () =>
    setList([...list, { api_key: "", cron: "0 9 * * *", args: [], named: {}, target_session: "" }]);

  if (loading) return <p>加载中…</p>;
  return (
    <div className="page">
      <h2>计划任务 <span className="field-origin">(schedules.json)</span></h2>
      {error && <p className="error">{error}</p>}
      <div className="button-row">
        <button onClick={add}>新增</button>
        <button onClick={handleSave} disabled={saving}>
          {saving ? "保存中…" : "保存"}
        </button>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>接口键 <span className="field-origin">(api_key)</span></th>
            <th>cron 表达式 <span className="field-origin">(cron)</span></th>
            <th>目标会话 <span className="field-origin">(target_session)</span></th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {list.map((row, i) => (
            <tr key={i}>
              <td>
                <input
                  className="table-input"
                  value={String(row.api_key ?? "")}
                  onChange={(e) => update(i, "api_key", e.target.value)}
                />
              </td>
              <td>
                <input
                  className="table-input"
                  value={String(row.cron ?? "")}
                  onChange={(e) => update(i, "cron", e.target.value)}
                />
              </td>
              <td>
                <input
                  className="table-input"
                  value={String(row.target_session ?? "")}
                  onChange={(e) => update(i, "target_session", e.target.value)}
                />
              </td>
              <td>
                <button onClick={() => remove(i)}>删除</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
