import { useCallback, useContext, useEffect, useRef, useState } from "react";
import { HeaderActionContext } from "../HeaderActionContext";
import { ConfirmDialog } from "../ConfirmDialog";
import { getGroups, putGroups } from "../api";

type GroupRow = { name: string; members: string };

function toRows(g: Record<string, string[]> | undefined): GroupRow[] {
  if (!g || typeof g !== "object") return [];
  return Object.entries(g).map(([name, arr]) => ({
    name,
    members: Array.isArray(arr) ? arr.join(", ") : "",
  }));
}

function fromRows(rows: GroupRow[]): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  for (const r of rows) {
    const name = r.name.trim();
    if (!name) continue;
    out[name] = r.members
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
  }
  return out;
}

export default function Groups() {
  const [userRows, setUserRows] = useState<GroupRow[]>([]);
  const [groupRows, setGroupRows] = useState<GroupRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [raw, setRaw] = useState("");
  const [rawJsonOpen, setRawJsonOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<{ kind: "user" | "group"; index: number } | null>(null);

  useEffect(() => {
    getGroups()
      .then((r) => {
        setUserRows(toRows(r.user_groups));
        setGroupRows(toRows(r.group_groups));
        setRaw(JSON.stringify({ user_groups: r.user_groups ?? {}, group_groups: r.group_groups ?? {} }, null, 2));
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = useCallback(() => {
    const body = {
      user_groups: fromRows(userRows),
      group_groups: fromRows(groupRows),
    };
    setSaving(true);
    setError(null);
    putGroups(body)
      .then(() => {
        setSaving(false);
        setRaw(JSON.stringify(body, null, 2));
      })
      .catch((e) => {
        setError(String(e));
        setSaving(false);
      });
  }, [userRows, groupRows]);

  const { setAction } = useContext(HeaderActionContext);
  const saveRef = useRef(handleSave);
  useEffect(() => {
    saveRef.current = handleSave;
  }, [handleSave]);
  useEffect(() => {
    setAction(
      <button
        type="button"
        className="app-header__btn"
        onClick={() => saveRef.current()}
        disabled={saving}
      >
        {saving ? "保存中…" : "保存此页"}
      </button>
    );
    return () => setAction(null);
  }, [saving, setAction]);

  const handleSaveRaw = () => {
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(raw);
    } catch {
      setError("JSON 格式无效");
      return;
    }
    const ug = (parsed.user_groups as Record<string, string[]>) ?? {};
    const gg = (parsed.group_groups as Record<string, string[]>) ?? {};
    setUserRows(toRows(ug));
    setGroupRows(toRows(gg));
    setSaving(true);
    setError(null);
    putGroups(parsed)
      .then(() => {
        setSaving(false);
        setRawJsonOpen(false);
      })
      .catch((e) => {
        setError(String(e));
        setSaving(false);
      });
  };

  const updateRow = (
    setRows: React.Dispatch<React.SetStateAction<GroupRow[]>>,
    index: number,
    field: "name" | "members",
    value: string
  ) => {
    setRows((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  };
  const addRow = (setRows: React.Dispatch<React.SetStateAction<GroupRow[]>>) => {
    setRows((prev) => [...prev, { name: "", members: "" }]);
  };
  const removeRow = (setRows: React.Dispatch<React.SetStateAction<GroupRow[]>>, index: number) => {
    setConfirmDelete({ kind: setRows === setUserRows ? "user" : "group", index });
  };
  const doRemove = () => {
    if (!confirmDelete) return;
    if (confirmDelete.kind === "user") {
      setUserRows((prev) => prev.filter((_, i) => i !== confirmDelete.index));
    } else {
      setGroupRows((prev) => prev.filter((_, i) => i !== confirmDelete.index));
    }
    setConfirmDelete(null);
  };

  if (loading) return <p>加载中…</p>;
  return (
    <div className="page page--groups">
      <h2>用户/群组 <span className="field-origin">(groups.json)</span></h2>
      {error && <p className="error">{error}</p>}
      <div className="button-row">
        <button type="button" onClick={() => addRow(setUserRows)}>添加用户组</button>
        <button type="button" onClick={() => addRow(setGroupRows)}>添加群组</button>
        <button
          type="button"
          onClick={() => {
            setRaw(
              JSON.stringify(
                {
                  user_groups: fromRows(userRows),
                  group_groups: fromRows(groupRows),
                },
                null,
                2
              )
            );
            setRawJsonOpen(true);
          }}
        >
          编辑 JSON
        </button>
      </div>
      <section className="page-section">
        <h3>用户组 <span className="field-origin">(user_groups)</span></h3>
        <p className="muted">组名 → 成员 ID 列表，逗号分隔</p>
        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <th>组名 <span className="field-origin">(name)</span></th>
                <th>成员 <span className="field-origin">(members)</span></th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {userRows.map((row, i) => (
                <tr key={i}>
                  <td>
                    <input
                      className="table-input table-input--wide"
                      value={row.name}
                      onChange={(e) => updateRow(setUserRows, i, "name", e.target.value)}
                    />
                  </td>
                  <td>
                    <input
                      className="table-input table-input--wide"
                      value={row.members}
                      onChange={(e) => updateRow(setUserRows, i, "members", e.target.value)}
                      placeholder="id1, id2"
                    />
                  </td>
                  <td>
                    <span className="button-group">
                      <button type="button" onClick={() => removeRow(setUserRows, i)}>删除</button>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="page-section">
        <h3>群组 <span className="field-origin">(group_groups)</span></h3>
        <p className="muted">组名 → 群 ID 列表，逗号分隔</p>
        <div className="table-scroll">
          <table className="table">
            <thead>
              <tr>
                <th>组名 <span className="field-origin">(name)</span></th>
                <th>成员 <span className="field-origin">(members)</span></th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {groupRows.map((row, i) => (
                <tr key={i}>
                  <td>
                    <input
                      className="table-input table-input--wide"
                      value={row.name}
                      onChange={(e) => updateRow(setGroupRows, i, "name", e.target.value)}
                    />
                  </td>
                  <td>
                    <input
                      className="table-input table-input--wide"
                      value={row.members}
                      onChange={(e) => updateRow(setGroupRows, i, "members", e.target.value)}
                      placeholder="id1, id2"
                    />
                  </td>
                  <td>
                    <span className="button-group">
                      <button type="button" onClick={() => removeRow(setGroupRows, i)}>删除</button>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {confirmDelete !== null && (
        <ConfirmDialog
          open={true}
          title="确认删除"
          message="确定要删除此分组吗？"
          onConfirm={doRemove}
          onCancel={() => setConfirmDelete(null)}
        />
      )}
      {rawJsonOpen && (
        <div
          className="modal-backdrop"
          onClick={() => setRawJsonOpen(false)}
          onKeyDown={(e) => e.key === "Escape" && setRawJsonOpen(false)}
          role="button"
          tabIndex={0}
          aria-label="关闭"
        >
          <div
            className="modal modal--raw-json"
            role="dialog"
            aria-modal="true"
            aria-labelledby="groups-raw-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <h3 id="groups-raw-title">编辑 JSON</h3>
              <button type="button" className="modal-close" onClick={() => setRawJsonOpen(false)} aria-label="关闭">❌</button>
            </div>
            <div className="modal-body">
              <textarea
                className="json-edit json-edit--modal"
                value={raw}
                onChange={(e) => setRaw(e.target.value)}
                rows={14}
              />
            </div>
            <div className="button-row">
              <button onClick={handleSaveRaw} disabled={saving}>
                从 JSON 保存
              </button>
              <button type="button" onClick={() => setRawJsonOpen(false)}>取消</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
