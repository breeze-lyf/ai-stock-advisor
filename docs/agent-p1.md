# 投研智能体 P1

## 概览
- `backend/app/agent/`：OpenAI 兼容 tool-calling 循环（最多 `AGENT_MAX_STEPS`=8 步，LLM/工具独立超时，工具结果截断），模型不支持 tools 时自动降级为“预取数据 + 单次回答”。
- 模型解析顺序：用户自定义模型 → 用户自有 Key（BYOK，复用 `model_resolver`）→ 系统中转 `LLM_BASE_URL/LLM_MODEL/LLM_API_KEY` → 现有系统 provider。
- 只读工具（封装现有 service）：`get_quote`、`get_fundamentals`、`get_kline_and_technicals`、`search_news`、`get_portfolio`（仅当前用户）、`run_stock_diagnosis`、`macro_snapshot`。
- 所有回答带“不构成投资建议”免责声明。

## API
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/v1/agent/chat` | `{message, conversation_id?}` → answer/steps/sources/mode（20 次/分钟） |
| GET | `/api/v1/agent/tools` | 工具列表 |
| GET/DELETE | `/api/v1/agent/conversations[/{id}]` | 会话历史 |
| POST/GET/DELETE | `/api/v1/agent/tokens[/{id}]` | 个人 MCP Token（明文只返回一次，库内存 SHA-256，最多 10 个） |
| POST | `/mcp` | MCP Streamable HTTP（2025-06-18，无状态），`Authorization: Bearer asa_...` |

MCP 暴露 7 个只读工具 + `ask_stock_agent`（完整智能体循环，会话 channel=mcp）。

客户端配置示例：
```json
{"mcpServers":{"stock-advisor":{"url":"https://stock.yufeng.fun/mcp","headers":{"Authorization":"Bearer asa_xxx"}}}}
```

## 数据库
新表 `agent_conversations`、`agent_messages`、`user_api_tokens`，迁移 `d7a1b2c3e4f5`（down_revision `c9f1a2b3d4e5`）：
```
cd backend && alembic upgrade head
```

## 环境变量（见 `.env.example`）
`LLM_BASE_URL`（含 `/v1`）、`LLM_MODEL`、`LLM_API_KEY`；可选 `AGENT_MAX_STEPS`、`AGENT_LLM_TIMEOUT_SECONDS`、`AGENT_TOOL_TIMEOUT_SECONDS`、`AGENT_TOOL_RESULT_MAX_CHARS`。

## 部署要点
1. 服务器 backend `.env` 增加上述 LLM 变量。
2. 执行 `alembic upgrade head`。
3. Nginx：`/mcp` 必须转发到后端 8000（Next 中间件只代理 `/api/*`）；`/api/v1/agent/` 需 `proxy_read_timeout 300s`。见 `nginx_routing.conf`。
4. 合并到 main 后由 GitHub Actions 构建部署。

## 安全清理
- 删除 `update_server_password.py`、`update_server_api_key.sh` 并加入 `.gitignore`；CORS 中的服务器 IP 改为 `ALLOWED_ORIGINS` 环境变量配置。
- **注意：git 历史中仍包含这两个脚本和服务器 IP**，如需彻底清除需另行重写历史（本分支未做）。

## 已知不足 / 后续
- 无流式输出；无写操作工具（下单/改持仓）；MCP 无状态无 session 恢复。
- 工具集成测试使用 mock；`google-genai==0.3.0` 为已撤回版本，建议升级。
