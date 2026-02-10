# ApiDog（AstrBot 插件）

可配置 API 与指令绑定，通过单指令 `/api <接口名> [参数...]` 调用配置的 HTTP 接口。

## 安装

将本插件放入 AstrBot 的 `data/plugins/` 下（如 `data/plugins/astrbot_plugin_apidog/`），在管理面板中启用并安装依赖（httpx、apscheduler、fastapi、uvicorn；后两者用于配置管理 API）。

## 配置

- **数据目录**：由 AstrBot 按插件目录名确定（如 `data/plugin_data/astrbot_plugin_apidog/`）。将 `sample_apis.json` 复制到该目录为 `apis.json` 并按需编辑。
- **config.json**（可选）：复制 `sample_config.json` 为 `config.json`，配置全局默认超时、重试及可重试状态码。不创建则使用内置默认（超时 30 秒、不重试）。`retry_statuses` 默认 `[500, 502, 503, 429]`，可增加 408、504 等。
- **auth.json / groups.json**（可选）：复制 `sample_auth.json`、`sample_groups.json` 为 `auth.json`、`groups.json`，配置认证与用户组/群组（API 权限由组名引用）。

## 用法

- `/api <接口名> [参数...]`：如 `/api 天气 北京`、`/api 翻译 "hello world" zh`
- `/api help`：列出已配置接口
- `/api help <接口名>`：查看该接口详细帮助
- 支持引号包裹含空格参数、`key=value` 命名参数

## API 配置要点

- **基础**：`id` / `command`、`method`、`url`、`headers`、`params`、`body`
- **占位符**：`{{args.0}}`、`{{named.xxx}}`、`{{named.xxx|默认值}}`、`{{config.xxx}}`
- **响应**：`response_type`（text / image / video / audio）、`response_path`（JSON 取结果路径）、`response_media_from`（url 或 body，body 表示接口直接返回二进制媒体）
- **认证**：`auth` 或 `auth_ref`（填 auth.json 中某条认证的键名，如 `default`）
- **权限**：`allowed_user_groups`、`allowed_group_groups`（组在 groups.json 中定义）
- **说明**：`description`（列表用）、`help_text` / `help`（详情页自定义）
- **开关**：`enabled`（默认 true）
- **限流**：`rate_limit`（按 user_id+api_key）、`rate_limit_global`（按 api_key 全局），格式 `{"max": N, "window_seconds": S}`
- **超时与重试**：`timeout_seconds`、`retry`（false/0 或不配则用 config 默认；对象 `{ "max_attempts": N, "backoff_seconds": S }`）

## 计划任务

将 `sample_schedules.json` 复制为数据目录下 `schedules.json`。每项含 **api_key**（填 API 的 **id**）、**cron**（5 位 cron，如 `0 9 * * *`）、可选 **args** / **named**、**enabled**（默认 true，为 false 时该条不执行）。可配置 **target_session** 主动推送结果（AstrBot 下为 `unified_msg_origin`）。计划任务以 `user_id="scheduler"` 执行，需在 groups.json 的 user_groups 中建 system 组并加入 `scheduler`，API 的 `allowed_user_groups` 含 `"system"` 或不限制用户组。

## 认证 (auth.json)

- **bearer**：`type: bearer`, `token: "..."`
- **api_key**：`type: api_key`, `header: "X-API-Key"`, `value: "..."` 或 `in: query`
- **basic**：`type: basic`, `username`, `password`

在接口配置中通过 **auth** 或 **auth_ref** 填写上述某条认证的键名（如 `default`），该接口请求时会自动带上对应认证。

## 配置管理前端

- 启用插件后访问 **http://localhost:5787/** 即为配置页（端口可在 config.json 的 `api_port` 修改，改后需重载插件）。
- **登录**：每次启动生成新临时密码，在 AstrBot 或控制台日志中查看「Config API 临时密码: xxx」。
- **后端**：读写 config/apis/schedules/groups/auth；插件启用时自动在配置端口启动。独立运行：`python -m api`（端口与数据目录从 config 读取）或 `uvicorn api.app:app --host 0.0.0.0 --port 5787`（数据目录为项目根下 **data**）。
- **改前端**：在 `frontend/` 下执行 `npm install && npm run build`，将 `dist` 提交或覆盖到插件中。

## 项目结构

| 目录/文件 | 说明 |
|-----------|------|
| core/ | 核心逻辑（解析、请求、响应、权限、限流、认证），仅依赖 httpx |
| api/ | 配置管理后端（FastAPI） |
| runtime/ | 计划任务调度（APScheduler） |
| frontend/ | 配置管理前端（React + Vite），产物 `frontend/dist` |
| main.py | AstrBot 插件入口 |
| sample_*.json | 各配置示例 |

## 迁移到其他平台

`core/` 无 bot 依赖。迁移时保留 `core/` 及数据目录结构，在新入口中：从平台事件解析用户输入与 user_id/group_id/is_admin，构造 `CallContext`，调用 `core.run(data_dir, raw_args, context, extra_config)`，再根据返回的 `CallResult` 调用该平台的发消息 API。
