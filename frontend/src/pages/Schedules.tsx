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
    setList([...list, { api_key: "", cron: "0 9 * * *", args: [], named: {}, target_session: "", enabled: true }]);

  if (loading) return <p>加载中…</p>;
  return (
    <div className="page">
      <h2>计划任务 <span className="field-origin">(schedules.json)</span></h2>
      {error && <p className="error">{error}</p>}
      <div className="button-row">
        <button onClick={add}>新增</button>
        <button onClick={handleSave} disabled={saving}>
          {saving ? "保存中…" : "保存当前页"}
        </button>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>接口 id <span className="field-origin">(api_key)</span></th>
            <th>cron 表达式 <span className="field-origin">(cron)</span></th>
            <th>目标会话 <span className="field-origin">(target_session)</span></th>
            <th>启用 <span className="field-origin">(enabled)</span></th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {list.map((row, i) => (
            <tr key={i}>
              <td>
                <input
                  className="table-input table-input--wide"
                  value={String(row.api_key ?? "")}
                  onChange={(e) => update(i, "api_key", e.target.value)}
                  placeholder="接口 id"
                />
              </td>
              <td>
                <input
                  className="table-input table-input--wide"
                  value={String(row.cron ?? "")}
                  onChange={(e) => update(i, "cron", e.target.value)}
                  placeholder="0 9 * * *"
                />
              </td>
              <td>
                <input
                  className="table-input table-input--wide"
                  value={String(row.target_session ?? "")}
                  onChange={(e) => update(i, "target_session", e.target.value)}
                  placeholder="可选"
                />
              </td>
              <td>
                <label className="toggle">
                  <input
                    type="checkbox"
                    checked={row.enabled !== false}
                    onChange={() => update(i, "enabled", row.enabled === false)}
                  />
                  <span className="toggle__track" aria-hidden="true" />
                </label>
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
