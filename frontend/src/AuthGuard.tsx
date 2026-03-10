import { useEffect, useState } from "react";
import { Routes, Route } from "react-router-dom";
import { getStatus, getStoredPassword, clearStoredPassword } from "./api";
import App from "./App.tsx";
import Init from "./pages/Init.tsx";
import Login from "./pages/Login.tsx";
import Config from "./pages/Config.tsx";
import Apis from "./pages/Apis.tsx";
import Schedules from "./pages/Schedules.tsx";
import Groups from "./pages/Groups.tsx";
import Auth from "./pages/Auth.tsx";

export default function AuthGuard() {
  const [status, setStatus] = useState<{ initialized: boolean } | null>(null);

  useEffect(() => {
    getStatus()
      .then(setStatus)
      .catch(() => {
        // 如果状态接口请求失败，清除本地密码，强制回到登录页，避免在断连时直接进入控制台
        clearStoredPassword();
        setStatus({ initialized: true });
      });
  }, []);

  if (status === null) {
    return <p style={{ padding: "2rem", textAlign: "center" }}>加载中…</p>;
  }
  if (!status.initialized) {
    return <Init />;
  }
  if (!getStoredPassword()) {
    return <Login />;
  }
  return (
    <Routes>
      <Route path="/" element={<App />}>
        <Route index element={<Config />} />
        <Route path="apis" element={<Apis />} />
        <Route path="schedules" element={<Schedules />} />
        <Route path="groups" element={<Groups />} />
        <Route path="auth" element={<Auth />} />
      </Route>
    </Routes>
  );
}
