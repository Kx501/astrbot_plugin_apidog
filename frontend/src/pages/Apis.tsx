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
  const [openRateLimit, setOpenRateLimit] = useState(false);
  const [openPermission, setOpenPermission] = useState(false);

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
    setOpenRequest(true);
    setOpenRateLimit(false);
    setOpenPermission(false);
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
      help_text: "",
      auth: undefined as string | undefined,
      allowed_user_groups: [] as string[],
      allowed_group_groups: [] as string[],
      timeout_seconds: undefined as number | undefined,
      retry: undefined as Record<string, unknown> | false | undefined,
      rate_limit: undefined as Record<string, number> | undefined,
      rate_limit_global: undefined as Record<string, number> | undefined,
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

  const arrToStr = (a: unknown): string =>
    Array.isArray(a) ? a.map((x) => String(x)).join(", ") : "";
  const strToArr = (s: string): string[] =>
    s.split(",").map((x) => x.trim()).filter(Boolean);

  const rateLimit = (editRow.rate_limit as Record<string, number> | undefined) ?? {};
  const rateLimitGlobal = (editRow.rate_limit_global as Record<string, number> | undefined) ?? {};
  const retryCfg = editRow.retry as Record<string, number> | false | number | undefined;
  const retryObj = typeof retryCfg === "object" && retryCfg !== null ? retryCfg : {};
  const retryMax: number | "" =
    retryCfg === false || retryCfg === 0 ? 0 : (retryObj.max_attempts ?? "");
  const retryBackoff = retryObj.backoff_seconds ?? "";

  const closeEdit = () => {
    setEditIndex(null);
    setJsonError(null);
  };

  const renderEditForm = () => (
    <>
      <div className="modal-header">
        <h3 id="apis-edit-title">编辑接口</h3>
        <button type="button" className="modal-close" onClick={closeEdit} aria-label="关闭">❌</button>
      </div>
      {jsonError && <p className="error">{jsonError}</p>}
      <div className={`accordion-section ${openBasic ? "open" : ""}`}>
            <div className="accordion-head" onClick={() => setOpenBasic(!openBasic)}>基本</div>
            <div className="accordion-body">
              <div className="form-group">
                <label>ID <span className="field-origin">(id)</span></label>
                <input
                  value={String(editRow.id ?? "")}
                  onChange={(e) => setEditRow({ ...editRow, id: e.target.value })}
                />
              </div>
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
                  className="input-url"
                  type="url"
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
                <textarea
                  value={String(editRow.description ?? "")}
                  onChange={(e) => setEditRow({ ...editRow, description: e.target.value })}
                  rows={3}
                  placeholder="接口简短说明，可选"
                />
              </div>
              <div className="form-group">
                <label>帮助文案 <span className="field-origin">(help_text)</span></label>
                <textarea
                  value={String(editRow.help_text ?? editRow.help ?? "")}
                  onChange={(e) => setEditRow({ ...editRow, help_text: e.target.value })}
                  rows={3}
                  placeholder="对用户的提示文案，可选"
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
          <div className={`accordion-section ${openRateLimit ? "open" : ""}`}>
            <div className="accordion-head" onClick={() => setOpenRateLimit(!openRateLimit)}>限流与重试</div>
            <div className="accordion-body">
              <div className="form-group">
                <label>限流 <span className="field-origin">(rate_limit)</span> 窗口内最大次数</label>
                <input
                  type="number"
                  min={0}
                  value={rateLimit.max ?? ""}
                  onChange={(e) => {
                    const v = e.target.value === "" ? undefined : Number(e.target.value);
                    setEditRow({
                      ...editRow,
                      rate_limit: v === undefined && !rateLimit.window_seconds ? undefined : { ...rateLimit, max: v },
                    });
                  }}
                />
              </div>
              <div className="form-group">
                <label>限流窗口秒数</label>
                <input
                  type="number"
                  min={0}
                  value={rateLimit.window_seconds ?? ""}
                  onChange={(e) => {
                    const v = e.target.value === "" ? undefined : Number(e.target.value);
                    setEditRow({
                      ...editRow,
                      rate_limit: v === undefined && rateLimit.max === undefined ? undefined : { ...rateLimit, window_seconds: v },
                    });
                  }}
                />
              </div>
              <div className="form-group">
                <label>全局限流 <span className="field-origin">(rate_limit_global)</span> 最大次数</label>
                <input
                  type="number"
                  min={0}
                  value={rateLimitGlobal.max ?? ""}
                  onChange={(e) => {
                    const v = e.target.value === "" ? undefined : Number(e.target.value);
                    setEditRow({
                      ...editRow,
                      rate_limit_global: v === undefined && !rateLimitGlobal.window_seconds ? undefined : { ...rateLimitGlobal, max: v },
                    });
                  }}
                />
              </div>
              <div className="form-group">
                <label>全局限流窗口秒数</label>
                <input
                  type="number"
                  min={0}
                  value={rateLimitGlobal.window_seconds ?? ""}
                  onChange={(e) => {
                    const v = e.target.value === "" ? undefined : Number(e.target.value);
                    setEditRow({
                      ...editRow,
                      rate_limit_global: v === undefined && rateLimitGlobal.max === undefined ? undefined : { ...rateLimitGlobal, window_seconds: v },
                    });
                  }}
                />
              </div>
              <div className="form-group">
                <label>超时秒数 <span className="field-origin">(timeout_seconds)</span></label>
                <input
                  type="number"
                  min={1}
                  value={typeof editRow.timeout_seconds === "number" ? editRow.timeout_seconds : ""}
                  onChange={(e) => {
                    const v = e.target.value === "" ? undefined : Number(e.target.value);
                    setEditRow({ ...editRow, timeout_seconds: v });
                  }}
                />
              </div>
              <div className="form-group">
                <label>重试次数 <span className="field-origin">(retry.max_attempts)</span> 不填用全局，填 0 不重试</label>
                <input
                  type="number"
                  min={0}
                  value={typeof retryMax === "number" ? retryMax : ""}
                  onChange={(e) => {
                    const v = e.target.value === "" ? undefined : Number(e.target.value);
                    if (v === undefined && (String(retryBackoff) === "" || retryBackoff === undefined)) {
                      setEditRow({ ...editRow, retry: undefined });
                      return;
                    }
                    if (v === 0) {
                      setEditRow({ ...editRow, retry: false });
                      return;
                    }
                    if (v !== undefined && v > 0) {
                      setEditRow({
                        ...editRow,
                        retry: { max_attempts: v, backoff_seconds: Number(retryBackoff) || 1 },
                      });
                    }
                  }}
                />
              </div>
              <div className="form-group">
                <label>重试间隔秒数 <span className="field-origin">(retry.backoff_seconds)</span></label>
                <input
                  type="number"
                  min={0}
                  value={typeof retryBackoff === "number" ? retryBackoff : ""}
                  onChange={(e) => {
                    const v = e.target.value === "" ? undefined : Number(e.target.value);
                    const currentMax = (retryMax === undefined || String(retryMax) === "") ? undefined : Number(retryMax);
                    if (v === undefined && currentMax === undefined) {
                      setEditRow({ ...editRow, retry: undefined });
                      return;
                    }
                    if (currentMax === 0) {
                      setEditRow({ ...editRow, retry: false });
                      return;
                    }
                    if (currentMax !== undefined && currentMax > 0) {
                      setEditRow({
                        ...editRow,
                        retry: { max_attempts: currentMax, backoff_seconds: v ?? 1 },
                      });
                    }
                  }}
                />
              </div>
            </div>
          </div>
          <div className={`accordion-section ${openPermission ? "open" : ""}`}>
            <div className="accordion-head" onClick={() => setOpenPermission(!openPermission)}>权限</div>
            <div className="accordion-body">
              <div className="form-group">
                <label>认证 <span className="field-origin">(auth / auth_ref)</span> auth.json 中的键名</label>
                <input
                  value={String(editRow.auth ?? editRow.auth_ref ?? "")}
                  onChange={(e) => {
                    const v = e.target.value.trim() || undefined;
                    setEditRow({ ...editRow, auth: v, auth_ref: v });
                  }}
                  placeholder="如 default"
                />
              </div>
              <div className="form-group">
                <label>允许的用户组 <span className="field-origin">(allowed_user_groups)</span> 逗号分隔</label>
                <input
                  value={arrToStr(editRow.allowed_user_groups)}
                  onChange={(e) => setEditRow({ ...editRow, allowed_user_groups: strToArr(e.target.value) })}
                  placeholder="组名1, 组名2"
                />
              </div>
              <div className="form-group">
                <label>允许的群组组 <span className="field-origin">(allowed_group_groups)</span> 逗号分隔</label>
                <input
                  value={arrToStr(editRow.allowed_group_groups)}
                  onChange={(e) => setEditRow({ ...editRow, allowed_group_groups: strToArr(e.target.value) })}
                  placeholder="组名1, 组名2"
                />
              </div>
            </div>
          </div>
      <div className="button-row">
        <button onClick={applyEdit}>应用</button>
        <button onClick={closeEdit}>取消</button>
      </div>
    </>
  );

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
                <label className="toggle">
                  <input
                    type="checkbox"
                    checked={row.enabled !== false}
                    onChange={() => toggleEnabled(i)}
                  />
                  <span className="toggle__track" aria-hidden="true" />
                </label>
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
        <div
          className="modal-backdrop"
          onClick={closeEdit}
          onKeyDown={(e) => e.key === "Escape" && closeEdit()}
          role="button"
          tabIndex={0}
          aria-label="关闭"
        >
          <div
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="apis-edit-title"
            onClick={(e) => e.stopPropagation()}
          >
            {renderEditForm()}
          </div>
        </div>
      )}
    </div>
  );
}
