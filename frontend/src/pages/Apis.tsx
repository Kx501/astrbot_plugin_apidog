import { useEffect, useState } from "react";
import { getApis, putApis } from "../api";

export default function Apis() {
  const [list, setList] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [editIndex, setEditIndex] = useState<number | null>(null);
  const [editRow, setEditRow] = useState<Record<string, unknown>>({});

  useEffect(() => {
    getApis()
      .then(setList)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const handleSaveAll = () => {
    setSaving(true);
    setError(null);
    putApis(list)
      .then(() => {
        setSaving(false);
        setEditIndex(null);
      })
      .catch((e) => {
        setError(String(e));
        setSaving(false);
      });
  };

  const startEdit = (index: number) => {
    setEditIndex(index);
    setEditRow({ ...list[index] });
  };
  const applyEdit = () => {
    if (editIndex === null) return;
    const next = [...list];
    next[editIndex] = editRow;
    setList(next);
    setEditIndex(null);
  };
  const remove = (index: number) => {
    setList(list.filter((_, i) => i !== index));
    if (editIndex === index) setEditIndex(null);
  };
  const addNew = () => {
    const newRow = {
      enabled: true,
      id: "new",
      command: "new",
      name: "新接口",
      method: "GET",
      url: "",
      headers: {} as Record<string, string>,
      params: {} as Record<string, string>,
      body: null,
      response_type: "text",
      response_path: "",
    };
    setList([...list, newRow]);
    setEditIndex(list.length);
    setEditRow({ ...newRow });
  };

  if (loading) return <p>加载中…</p>;
  return (
    <div className="page">
      <h2>接口列表 (apis.json)</h2>
      {error && <p className="error">{error}</p>}
      <button onClick={addNew}>新增接口</button>
      <button onClick={handleSaveAll} disabled={saving} style={{ marginLeft: 8 }}>
        {saving ? "保存中…" : "保存全部"}
      </button>
      <table className="table">
        <thead>
          <tr>
            <th>command</th>
            <th>name</th>
            <th>enabled</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {list.map((row, i) => (
            <tr key={i}>
              <td>{String(row.command ?? row.id)}</td>
              <td>{String(row.name ?? "")}</td>
              <td>{String(row.enabled !== false)}</td>
              <td>
                <button onClick={() => startEdit(i)}>编辑</button>
                <button onClick={() => remove(i)} style={{ marginLeft: 4 }}>删除</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {editIndex !== null && (
        <div className="modal">
          <h3>编辑接口</h3>
          <div className="form-group">
            <label>command</label>
            <input
              value={String(editRow.command ?? "")}
              onChange={(e) => setEditRow({ ...editRow, command: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label>name</label>
            <input
              value={String(editRow.name ?? "")}
              onChange={(e) => setEditRow({ ...editRow, name: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label>method</label>
            <input
              value={String(editRow.method ?? "GET")}
              onChange={(e) => setEditRow({ ...editRow, method: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label>url</label>
            <input
              value={String(editRow.url ?? "")}
              onChange={(e) => setEditRow({ ...editRow, url: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label>enabled</label>
            <input
              type="checkbox"
              checked={editRow.enabled !== false}
              onChange={(e) => setEditRow({ ...editRow, enabled: e.target.checked })}
            />
          </div>
          <button onClick={applyEdit}>应用</button>
          <button onClick={() => setEditIndex(null)} style={{ marginLeft: 8 }}>取消</button>
        </div>
      )}
    </div>
  );
}
