# 开发部署指南

## 环境准备

- Python 3.10+
- Node 18+（前端开发时）
- 建议使用虚拟环境：`python -m venv .venv`，激活后 `pip install -r requirements.txt`

## 仅配置管理（后端 + 前端）

不跑 AstrBot，只跑配置管理 API 和前端，用于改接口/计划/认证等配置页。

1. **数据目录**（可选）  
   在项目根下建 `data/`，可放入 `config.json`、`apis.json` 等；不建则使用内置默认（端口 5787）。  
   若需自定义端口，在 `data/config.json` 中设置 `api_port`（如 5787）。

2. **启动后端**  
   在项目根执行：
   ```bash
   python -m api
   ```
   后端会在 `http://0.0.0.0:5787` 提供 API 和静态页面（若存在 `frontend/dist`）。

3. **前端开发（热更新）**  
   另开终端，在 `frontend/` 下：
   ```bash
   npm install
   npm run dev
   ```
   访问 `http://localhost:5173`，前端会请求 `VITE_API_URL`（默认 `http://localhost:5787/api`）。  
   登录密码见后端启动日志中的「Config API 临时密码」。

4. **前端构建**  
   修改前端后若要给插件用或生产部署：
   ```bash
   cd frontend && npm run build
   ```
   产物在 `frontend/dist/`，后端会自动托管该目录下的 `index.html` 与 `assets/`。

## 在 AstrBot 里联调

1. 将本项目复制或软链到 AstrBot 的插件目录，例如：
   `data/plugins/astrbot_plugin_apidog/`
2. 在 AstrBot 管理面板中启用 ApiDog 并安装依赖。
3. 插件会使用 `data/plugin_data/astrbot_plugin_apidog/` 作为数据目录，配置管理端口仍由该目录下 `config.json` 的 `api_port` 决定（默认 5787）。

如需边改边看配置页，可在本仓库 `frontend/` 跑 `npm run dev`，在浏览器访问 5173，并把 `.env.development` 中的 `VITE_API_URL` 指到 AstrBot 启动后的配置 API 地址（同上端口）。
