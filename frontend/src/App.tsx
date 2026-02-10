import { useEffect, useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import "./App.css";

const SIDEBAR_STORAGE_KEY = "apidog_sidebar_collapsed";

function getInitialCollapsed(): boolean {
  try {
    const v = localStorage.getItem(SIDEBAR_STORAGE_KEY);
    if (v === "true") return true;
    if (v === "false") return false;
  } catch {
    /* ignore */
  }
  return true;
}

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

const LINKS = [
  { to: "/", label: "配置总览", short: "配" },
  { to: "/apis", label: "接口列表", short: "接" },
  { to: "/schedules", label: "计划任务", short: "计" },
  { to: "/groups", label: "用户/群组", short: "组" },
  { to: "/auth", label: "认证", short: "证" },
];

export default function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(getInitialCollapsed);
  const location = useLocation();

  useEffect(() => {
    try {
      localStorage.setItem(SIDEBAR_STORAGE_KEY, String(sidebarCollapsed));
    } catch {
      /* ignore */
    }
  }, [sidebarCollapsed]);

  const toggleSidebar = () => setSidebarCollapsed((c) => !c);
  const closeSidebar = () => setSidebarCollapsed(true);

  return (
    <div className={`app ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}>
      <ScrollToTop />
      <button
        type="button"
        className="sidebar-open-btn"
        onClick={toggleSidebar}
        aria-label="打开菜单"
        title="打开菜单"
      >
        &#9776;
      </button>
      <aside
        className={`sidebar ${sidebarCollapsed ? "sidebar--collapsed" : ""}`}
        aria-hidden={sidebarCollapsed}
      >
        <div className="sidebar__head">
          <span className="sidebar__title">ApiDog 配置管理</span>
          <button
            type="button"
            className="sidebar__toggle"
            onClick={toggleSidebar}
            aria-label={sidebarCollapsed ? "展开侧栏" : "折叠侧栏"}
            title={sidebarCollapsed ? "展开" : "折叠"}
          >
            {sidebarCollapsed ? "\u203A" : "\u2039"}
          </button>
        </div>
        <nav className="sidebar-nav">
          {LINKS.map(({ to, label, short }) => (
            <Link
              key={to}
              to={to}
              className={location.pathname === to ? "active" : ""}
              onClick={closeSidebar}
            >
              <span className="sidebar-nav__full">{label}</span>
              <span className="sidebar-nav__short">{short}</span>
            </Link>
          ))}
        </nav>
      </aside>
      {!sidebarCollapsed && (
        <div
          className="sidebar-overlay"
          onClick={closeSidebar}
          onKeyDown={(e) => e.key === "Escape" && closeSidebar()}
          role="button"
          tabIndex={0}
          aria-label="关闭菜单"
        />
      )}
      <main className="main-inner">
        <Outlet />
      </main>
    </div>
  );
}
