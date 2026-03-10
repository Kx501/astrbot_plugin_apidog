import { createContext } from "react";

/** 供子页面在顶栏右侧注册操作按钮（如「保存该页」） */
export const HeaderActionContext = createContext<{
  setAction: (node: React.ReactNode) => void;
}>({ setAction: () => {} });
