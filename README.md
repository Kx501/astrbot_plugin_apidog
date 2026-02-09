# ApiDog (AstrBot Star)

可配置 API 与指令绑定，通过单指令 `/api <接口名> [参数...]` 调用配置的 HTTP 接口。核心逻辑在 `core/` 包内，与具体 bot 平台无关；AstrBot 入口为 `main.py`（符合 [AstrBot 插件规范](https://docs.astrbot.app/dev/star/guides/simple.html)）。

## 安装

将本插件放入 AstrBot 的 `data/plugins/` 下（如 `data/plugins/apidog/`），在管理面板中启用并安装依赖（httpx、apscheduler）。

## 配置

- 数据目录：由 AstrBot 官方 API 按插件目录名自动确定（如 `data/plugin_data/astrbot_plugin_apidog/`）。将 `sample_apis.json` 复制到该目录下为 `apis.json` 并按需编辑。
- 可选：将 **sample_config.json** 复制为同目录下 **config.json**，配置全局默认超时与重试；不创建则使用内置默认（超时 30 秒、不重试）。
- 可选：将 `sample_auth.json` 复制为同目录下 `auth.json` 配置认证；将 `sample_groups.json` 复制为 `groups.json` 配置用户组与群组（API 权限由组名引用，见下）。

## 用法

- `/api <接口名> [参数...]`  
  例如：`/api 天气 北京`、`/api 翻译 "hello world" zh`
- `/api help`：列出所有已配置接口（命令、名称及可选描述）
- `/api help <接口名>`：查看该接口的详细帮助（参数、示例等）
- 支持引号包裹含空格的参数；支持 `key=value` 命名参数

## API 配置字段

- `id` / `command`：查表用，用户输入的接口名
- `method`, `url`, `headers`, `params`, `body`
- 占位符：`{{args.0}}`、`{{named.xxx}}`、`{{named.xxx|默认值}}`、`{{config.xxx}}`
- `response_type`：**text** / **image** / **video** / **audio**；`response_path`：从 JSON 取结果的路径（媒体类型且为 URL 时为 URL 字段路径）
- **`response_media_from`**：**url**（默认）或 **body**。为 `url` 时从响应 JSON 的 `response_path` 或兜底取媒体 URL；为 `body` 时接口直接返回二进制媒体（如 image/jpeg），将响应体作为媒体内容。对接「直接返回图片/音视频 body」的接口时使用 `body`。
- 权限（仅按组）：**`require_admin`**（可选）、**`allowed_user_groups`**（可选，组名字符串数组）、**`allowed_group_groups`**（可选，组名字符串数组）。组定义在数据目录下的 **groups.json**（`user_groups`、`group_groups`），将 `sample_groups.json` 复制为 `groups.json` 并按需填写。未配置或空数组表示不限制该维度；配置了 `allowed_group_groups` 的接口仅群聊可调，私聊不可用。
- **`description`**（可选）：一句话说明，用于 `/api help` 列表展示。
- **`help_text`**（或 `help`，可选）：详情页自定义说明。配置后，在 `/api help <接口名>` 中会优先展示该段文案，便于管理员在后台或 apis.json 中维护使用说明、示例等。
- **`enabled`**（可选，默认 true）：为 false 时该接口禁用，不可调用且不出现在 `/api help` 中。
- **`rate_limit`**（可选）：按 (user_id, api_key) 限流，与权限组无关。仅支持对象 `{"max": N, "window_seconds": S}`（如 `{"max": 10, "window_seconds": 60}` 表示 60 秒内最多 10 次）。仅单进程有效，多实例需自行扩展。
- **`rate_limit_global`**（可选）：按 api_key 全局限流，该 API 所有调用（真人 + 计划任务）在窗口内总次数不超过 N。格式同上。先检查全局限流，再检查 per-user 限流。
- **`timeout_seconds`**（可选）：该 API 请求超时（秒），不配则使用 config.json 中的全局默认（或内置 30 秒）。
- **`retry`**（可选）：重试策略。`false` 或 `0` 表示不重试；对象 `{ "max_attempts": N, "backoff_seconds": S }` 表示最多重试 N 次、间隔 S 秒。不配则使用 config.json 中的全局默认。仅对超时、5xx、429 重试。

## 计划任务

- 将 **sample_schedules.json** 复制为数据目录下的 **schedules.json**，配置定时调用的 API。每项包含 **api_key**、**cron**（5 位 cron 表达式，如 `0 9 * * *` 每天 9 点）、可选 **args**（位置参数数组）、**named**（命名参数对象）。
- **主动推送结果**：每项可配置 **target_session**（字符串，取值格式由当前 bot 平台决定）。配置后，计划任务执行完会将结果主动发送到该会话。AstrBot 下该值为目标群/私聊的 `unified_msg_origin`（可从一次消息事件获得，格式如 `平台:类型:会话ID`）。
- 计划任务使用固定身份 **scheduler**（`user_id="scheduler"`）。在 **groups.json** 的 **user_groups** 中增加 **system** 组、成员为 `["scheduler"]`；需要被定时调用的 API 在 `allowed_user_groups` 中包含 `"system"`（或不限制用户组）。计划任务与真人一样参与 per-user 限流和全局限流。

## 认证 (auth.json)

- `bearer`：`type: bearer`, `token: "..."`
- `api_key`：`type: api_key`, `header: "X-API-Key"`, `value: "..."` 或 `in: query`
- `basic`：`type: basic`, `username`, `password`

## 迁移到其他平台

核心逻辑在 `core/` 包内（仅依赖 httpx，内含 `parse_args` 等），无任何 bot 依赖。迁移时保留整个 `core/` 目录及数据目录结构，按目标平台要求新建或替换入口文件（如 `main.py`），在入口中：从平台事件解析出用户输入与 `user_id` / `group_id` / `is_admin`，构造 `CallContext`，调用 `core.run(data_dir, raw_args, context, extra_config)`，再根据返回的 `CallResult`（`success`、`result_type`、`message`、`media_url` 或 `media_bytes`+`media_content_type`）调用该平台的发文本/图/视频/音频 API。

## TODO

- 配置校验 / 热重载
- 结果缓存
