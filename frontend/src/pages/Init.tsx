import { useState } from "react";
import { postInit, setStoredPassword } from "../api";

export default function Init() {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password.trim()) {
      setError("请输入密码");
      return;
    }
    if (password !== confirm) {
      setError("两次输入不一致");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      await postInit(password.trim());
      setStoredPassword(password.trim());
      window.location.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "设置失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page page--narrow page--login">
      <div className="login-card">
        <h2 className="login-title">初始化配置</h2>
        <p className="muted">首次使用请设置 Config API 密码，用于后续登录管理页。忘记密码时可在配置文件中删除 config_api_password 后重新打开本页设置。</p>
        {error && <p className="error">{error}</p>}
        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label>设置密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="请输入密码"
              autoFocus
            />
          </div>
          <div className="form-group">
            <label>确认密码</label>
            <input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="再次输入密码"
            />
          </div>
          <button type="submit" disabled={loading} className="login-submit">
            {loading ? "设置中…" : "完成"}
          </button>
        </form>
      </div>
    </div>
  );
}
