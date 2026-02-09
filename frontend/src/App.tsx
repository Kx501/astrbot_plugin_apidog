import { Link, Outlet, useLocation } from "react-router-dom";
import "./App.css";

function Nav() {
  const loc = useLocation();
  const links = [
    { to: "/", label: "配置总览" },
    { to: "/apis", label: "接口列表" },
    { to: "/schedules", label: "计划任务" },
    { to: "/groups", label: "用户/群组" },
    { to: "/auth", label: "认证" },
  ];
  return (
    <nav>
      {links.map(({ to, label }) => (
        <Link key={to} to={to} className={loc.pathname === to ? "active" : ""}>
          {label}
        </Link>
      ))}
    </nav>
  );
}

export default function App() {
  return (
    <>
      <header>
        <h1>ApiDog 配置管理</h1>
        <Nav />
      </header>
      <main>
        <Outlet />
      </main>
    </>
  );
}
