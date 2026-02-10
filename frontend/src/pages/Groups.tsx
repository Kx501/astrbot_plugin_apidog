import { useEffect, useState } from "react";
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

  const handleSave = () => {
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
  };

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
    setRows((prev) => prev.filter((_, i) => i !== index));
  };

  if (loading) return <p>加载中…</p>;
  return (
    <div className="page">
      <h2>用户/群组 <span className="field-origin">(groups.json)</span></h2>
      {error && <p className="error">{error}</p>}
      <div className="button-row">
        <button type="button" onClick={() => addRow(setUserRows)}>新增用户组</button>
        <button type="button" onClick={() => addRow(setGroupRows)}>新增群组</button>
        <button onClick={handleSave} disabled={saving}>
          {saving ? "保存中…" : "保存"}
        </button>
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
          编辑原始 JSON
        </button>
      </div>
      <section className="page-section">
        <h3>用户组 <span className="field-origin">(user_groups)</span></h3>
        <p className="muted">组名 → 成员 ID 列表，逗号分隔</p>
        <table className="table">
          <thead>
            <tr>
              <th>组名</th>
              <th>成员 <span className="field-origin">(逗号分隔)</span></th>
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
                    className="table-input"
                    value={row.members}
                    onChange={(e) => updateRow(setUserRows, i, "members", e.target.value)}
                  />
                </td>
                <td>
                  <button onClick={() => removeRow(setUserRows, i)}>删除</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="page-section">
        <h3>群组 <span className="field-origin">(group_groups)</span></h3>
        <p className="muted">组名 → 群 ID 列表，逗号分隔</p>
        <table className="table">
          <thead>
            <tr>
              <th>组名</th>
              <th>成员 <span className="field-origin">(逗号分隔)</span></th>
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
                    className="table-input"
                    value={row.members}
                    onChange={(e) => updateRow(setGroupRows, i, "members", e.target.value)}
                  />
                </td>
                <td>
                  <button onClick={() => removeRow(setGroupRows, i)}>删除</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

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
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="groups-raw-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <h3 id="groups-raw-title">编辑原始 JSON</h3>
              <button type="button" className="modal-close" onClick={() => setRawJsonOpen(false)} aria-label="关闭">×</button>
            </div>
            <textarea
              className="json-edit"
              value={raw}
              onChange={(e) => setRaw(e.target.value)}
              rows={14}
            />
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
