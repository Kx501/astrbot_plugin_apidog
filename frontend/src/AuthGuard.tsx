import { useEffect, useState } from "react";
import { Routes, Route } from "react-router-dom";
import { getStatus, getStoredPassword } from "./api";
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
      .catch(() => setStatus({ initialized: true }));
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
