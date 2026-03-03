import { useState } from "react";
import { getConfig, hashPassword, setStoredPassword } from "../api";

export default function Login() {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password.trim()) return;
    setError(null);
    setLoading(true);
    try {
      const hash = await hashPassword(password.trim());
      setStoredPassword(hash);
      await getConfig();
      window.location.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "验证失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page page--narrow page--login">
      <div className="login-card">
        <h2 className="login-title">配置管理登录</h2>
        <p className="muted">请输入你设置的 Config API 密码。</p>
        {error && <p className="error">{error}</p>}
        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label>密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="请输入密码"
              autoFocus
            />
          </div>
          <button type="submit" disabled={loading} className="login-submit">
            {loading ? "验证中…" : "登录"}
          </button>
        </form>
      </div>
    </div>
  );
}
