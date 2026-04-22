# PowerMem MCP Server

PowerMem MCP Server - 用于 PowerMem 内存管理的模型上下文协议服务器。

[English](README.md) | 简体中文

## 运行模式

PowerMem MCP Server 支持两种运行模式：

### 嵌入模式（默认）

powermem 库在进程内运行，无需外部服务。通过 `.env` 文件配置：

```ini
DATABASE_PROVIDER=sqlite
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=qwen
# ... 其他 powermem 配置
```

### 代理模式

PowerMem MCP 作为中间件，将所有请求通过 HTTP 转发到远端 PowerMem Server。适用于避免 powermem-mcp 与已部署的 powermem 服务之间的版本冲突。

在 `.env` 中设置 `POWERMEM_SERVER_URL` 即可启用：

```ini
POWERMEM_SERVER_URL=http://127.0.0.1:8000
POWERMEM_SERVER_API_KEY=your_server_api_key_here   # 可选
```

设置 `POWERMEM_SERVER_URL` 后，数据库、LLM、Embedding 等配置均由远端服务管理，`.env` 中可省略这些配置项。

## 前置条件

在使用嵌入模式时，请确保：

1. **已安装 PowerMem**：服务器需要 PowerMem 已安装：
   ```shell
   pip install powermem
   ```

2. **配置文件存在**：在工作目录或项目根目录创建 `.env` 文件，包含 PowerMem 配置。服务器会自动在以下位置搜索 `.env` 文件：
   - 当前工作目录的 `.env`
   - 项目根目录的 `.env`
   - `examples/configs/.env`

   您可以复制 `.env.example` 文件作为模板：
   ```shell
   cp powermem_mcp/.env.example .env
   ```
   
   然后编辑 `.env` 文件并配置以下关键设置：
   
   - **数据库提供商**：从 `sqlite`、`oceanbase` 或 `postgres` 中选择
   - **LLM 提供商**：从 `qwen`、`openai` 等选择
   - **嵌入模型提供商**：从 `qwen`、`openai` 等选择
   - **API 密钥**：设置您的 LLM 和嵌入模型 API 密钥

PowerMem 安装和配置请参考：[PowerMem 文档](https://powermem.ai/docs)

## 启动

### 支持多种类型的 MCP

可通过如下指令启动不同协议的 PowerMem MCP：

```shell
uvx powermem-mcp sse # sse 模式，默认端口 8000（推荐使用）
uvx powermem-mcp stdio # stdio 模式
uvx powermem-mcp sse 8001 # sse 模式，指定端口 8001
uvx powermem-mcp streamable-http # streamable-http 模式，默认端口 8000
uvx powermem-mcp streamable-http 8001 # streamable-http 模式，指定端口 8001
```

## 使用方式

配合 MCP Client 使用，必须使用支持 Prompt 的客户端，如：Claude Desktop。输入请求前需要手动选取所需的 Prompt，然后输入请求。

Claude Desktop 配置示例：

```json
{
  "mcpServers": {
    "powermem": {
      "url": "http://{host}:8000/mcp"
    }
  }
}
```

## 可用工具

### 核心记忆工具

- **add_memory**：向存储中添加新记忆。支持字符串、消息字典或消息列表格式。可使用智能模式进行自动推理。
- **search_memories**：通过查询文本搜索记忆，支持可选过滤器、限制和相似度阈值。
- **get_memory_by_id**：根据 ID 获取特定记忆（`memory_id` 支持 `int` 和 `str` 两种类型）。
- **update_memory**：更新现有记忆的内容和元数据。
- **delete_memory**：根据 ID 删除特定记忆。
- **delete_all_memories**：根据 user_id、agent_id 或 run_id 批量删除记忆。
- **list_memories**：列出所有记忆，支持分页（limit 和 offset）和可选过滤器。

### 用户画像工具

- **add_memory_with_profile**：添加记忆并从对话中提取用户画像。支持 `content`（自然语言描述）和 `topics`（结构化 JSON）两种画像类型。
- **search_memories_with_profile**：搜索记忆并可选附带用户画像，用于个性化响应。
- **get_user_profile**：根据 user_id 获取用户画像。
- **list_user_profiles**：列出用户画像，支持按 user_id 和 topic 字段过滤。
- **delete_user_profile**：根据 user_id 删除用户画像。
- **delete_memory_with_profile**：删除记忆，并可选同时删除关联的用户画像。

## 社区

当你需要帮助时，你可以在 [https://github.com/oceanbase/powermem](https://github.com/oceanbase/powermem) 上找到开发者和其他的社区伙伴。

当你发现项目缺陷时，请在 [issues](https://github.com/oceanbase/powermem/issues) 页面创建一个新的 issue。

## 许可证

更多信息见 [LICENSE](LICENSE)。
