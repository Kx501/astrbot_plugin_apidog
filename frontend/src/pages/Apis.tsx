import { useEffect, useState } from "react";
import { getApis, putApis } from "../api";

const METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"] as const;
const RESPONSE_TYPES = ["text", "image", "video", "audio"] as const;
const MEDIA_FROM = ["url", "body"] as const;

function safeJsonStringify(val: unknown): string {
  if (val === null || val === undefined) return "{}";
  if (typeof val === "object") return JSON.stringify(val, null, 2);
  return String(val);
}

function safeJsonParse(str: string): unknown {
  const t = str.trim();
  if (!t) return {};
  try {
    return JSON.parse(t);
  } catch {
    return undefined;
  }
}

export default function Apis() {
  const [list, setList] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [editIndex, setEditIndex] = useState<number | null>(null);
  const [editRow, setEditRow] = useState<Record<string, unknown>>({});
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [openBasic, setOpenBasic] = useState(true);
  const [openResponse, setOpenResponse] = useState(false);
  const [openRequest, setOpenRequest] = useState(false);

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
    setJsonError(null);
    setOpenBasic(true);
    setOpenResponse(false);
    setOpenRequest(false);
  };
  const applyEdit = () => {
    if (editIndex === null) return;
    const next = [...list];
    next[editIndex] = editRow;
    setList(next);
    setEditIndex(null);
    setJsonError(null);
  };
  const remove = (index: number) => {
    setList(list.filter((_, i) => i !== index));
    if (editIndex === index) setEditIndex(null);
  };
  const toggleEnabled = (index: number) => {
    const next = [...list];
    const row = next[index] as Record<string, unknown>;
    next[index] = { ...row, enabled: row.enabled === false };
    setList(next);
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
      response_media_from: "url",
      description: "",
    };
    setList([...list, newRow]);
    setEditIndex(list.length);
    setEditRow({ ...newRow });
  };

  const setJsonField = (key: "headers" | "params" | "body", raw: string) => {
    const parsed = safeJsonParse(raw);
    if (parsed === undefined) {
      setJsonError(`${key} 不是合法 JSON，未应用`);
      return;
    }
    setJsonError(null);
    setEditRow({ ...editRow, [key]: parsed });
  };

  if (loading) return <p>加载中…</p>;
  return (
    <div className="page">
      <h2>接口列表 <span className="field-origin">(apis.json)</span></h2>
      {error && <p className="error">{error}</p>}
      <div className="button-row">
        <button onClick={addNew}>新增接口</button>
        <button onClick={handleSaveAll} disabled={saving}>
          {saving ? "保存中…" : "保存全部"}
        </button>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th className="col-command">命令 <span className="field-origin">(command)</span></th>
            <th className="col-name">名称 <span className="field-origin">(name)</span></th>
            <th>启用 <span className="field-origin">(enabled)</span></th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {list.map((row, i) => (
            <tr key={i}>
              <td>{String(row.command ?? row.id)}</td>
              <td>{String(row.name ?? "")}</td>
              <td>
                <input
                  type="checkbox"
                  checked={row.enabled !== false}
                  onChange={() => toggleEnabled(i)}
                />
              </td>
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
          {jsonError && <p className="error">{jsonError}</p>}
          <div className={`accordion-section ${openBasic ? "open" : ""}`}>
            <div className="accordion-head" onClick={() => setOpenBasic(!openBasic)}>基本</div>
            <div className="accordion-body">
              <div className="form-group">
                <label>命令 <span className="field-origin">(command)</span></label>
                <input
                  value={String(editRow.command ?? "")}
                  onChange={(e) => setEditRow({ ...editRow, command: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>名称 <span className="field-origin">(name)</span></label>
                <input
                  value={String(editRow.name ?? "")}
                  onChange={(e) => setEditRow({ ...editRow, name: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>请求方法 <span className="field-origin">(method)</span></label>
                <select
                  value={String(editRow.method ?? "GET")}
                  onChange={(e) => setEditRow({ ...editRow, method: e.target.value })}
                >
                  {METHODS.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>URL <span className="field-origin">(url)</span></label>
                <input
                  value={String(editRow.url ?? "")}
                  onChange={(e) => setEditRow({ ...editRow, url: e.target.value })}
                />
              </div>
            </div>
          </div>
          <div className={`accordion-section ${openResponse ? "open" : ""}`}>
            <div className="accordion-head" onClick={() => setOpenResponse(!openResponse)}>响应与描述</div>
            <div className="accordion-body">
              <div className="form-group">
                <label>响应类型 <span className="field-origin">(response_type)</span></label>
                <select
                  value={String(editRow.response_type ?? "text")}
                  onChange={(e) => setEditRow({ ...editRow, response_type: e.target.value })}
                >
                  {RESPONSE_TYPES.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>响应路径 <span className="field-origin">(response_path)</span></label>
                <input
                  value={String(editRow.response_path ?? "")}
                  onChange={(e) => setEditRow({ ...editRow, response_path: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>媒体来源 <span className="field-origin">(response_media_from)</span></label>
                <select
                  value={String(editRow.response_media_from ?? "url")}
                  onChange={(e) => setEditRow({ ...editRow, response_media_from: e.target.value })}
                >
                  {MEDIA_FROM.map((v) => (
                    <option key={v} value={v}>{v}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>描述 <span className="field-origin">(description)</span></label>
                <input
                  value={String(editRow.description ?? "")}
                  onChange={(e) => setEditRow({ ...editRow, description: e.target.value })}
                />
              </div>
            </div>
          </div>
          <div className={`accordion-section ${openRequest ? "open" : ""}`}>
            <div className="accordion-head" onClick={() => setOpenRequest(!openRequest)}>请求 (headers / params / body)</div>
            <div className="accordion-body">
              <div className="form-group">
                <label>请求头 <span className="field-origin">(headers)</span> JSON</label>
                <textarea
                  className="json-edit-sm"
                  value={safeJsonStringify(editRow.headers)}
                  onChange={(e) => setJsonField("headers", e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>查询参数 <span className="field-origin">(params)</span> JSON</label>
                <textarea
                  className="json-edit-sm"
                  value={safeJsonStringify(editRow.params)}
                  onChange={(e) => setJsonField("params", e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>请求体 <span className="field-origin">(body)</span> JSON</label>
                <textarea
                  className="json-edit-sm"
                  value={typeof editRow.body === "object" && editRow.body !== null
                    ? JSON.stringify(editRow.body, null, 2)
                    : editRow.body === null || editRow.body === undefined
                      ? ""
                      : String(editRow.body)}
                  onChange={(e) => {
                    const raw = e.target.value.trim();
                    if (!raw) {
                      setEditRow({ ...editRow, body: null });
                      setJsonError(null);
                      return;
                    }
                    const parsed = safeJsonParse(e.target.value);
                    if (parsed === undefined) {
                      setJsonError("body 不是合法 JSON，未应用");
                      return;
                    }
                    setJsonError(null);
                    setEditRow({ ...editRow, body: parsed });
                  }}
                />
              </div>
            </div>
          </div>
          <div className="button-row">
            <button onClick={applyEdit}>应用</button>
            <button onClick={() => { setEditIndex(null); setJsonError(null); }}>取消</button>
          </div>
        </div>
      )}
    </div>
  );
}
