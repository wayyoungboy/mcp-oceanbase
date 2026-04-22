# PowerMem MCP Server

PowerMem MCP Server - Model Context Protocol server for PowerMem memory management.

English | [简体中文](powermem_mcp_server_CN.md)

## Operating Modes

PowerMem MCP Server supports two operating modes:

Switch between modes via `POWERMEM_MODE` in `.env` (default: `embedded`).

### Embedded Mode (Default)

The powermem library runs in-process. No external service required.

```ini
POWERMEM_MODE=embedded   # or omit entirely

DATABASE_PROVIDER=sqlite
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=qwen
# ... other powermem settings
```

### Proxy Mode

PowerMem MCP acts as a middleware and forwards all requests to a remote PowerMem server via HTTP. This avoids version conflicts between powermem-mcp and a separately deployed powermem server.

```ini
POWERMEM_MODE=proxy
POWERMEM_SERVER_URL=http://127.0.0.1:8000
POWERMEM_SERVER_API_KEY=your_server_api_key_here   # optional
```

When `POWERMEM_MODE=proxy`, all powermem settings (database, LLM, embedding) are managed by the remote server and can be omitted from `.env`.

## Startup

### Support for multiple types of MCP

You can start PowerMem MCP with different protocols using the following commands:

```shell
uvx powermem-mcp sse # sse mode, default port 8000 (recommended)
uvx powermem-mcp stdio # stdio mode
uvx powermem-mcp sse 8001 # sse mode, specify port 8001
uvx powermem-mcp streamable-http # streamable-http mode, default port 8000
uvx powermem-mcp streamable-http 8001 # streamable-http mode, specify port 8001
```

## Usage

Use with MCP Client, must use a client that supports Prompts, such as: Claude Desktop. Before entering a request, you need to manually select the required Prompt, then enter the request.

Claude Desktop config example:

```json
{
  "mcpServers": {
    "powermem": {
      "url": "http://{host}:8000/mcp"
    }
  }
}
```

## Available Tools

### Core Memory Tools

- **add_memory**: Add new memory to storage. Supports string, message dict, or message list format. Can use intelligent mode for automatic inference.
- **search_memories**: Search memories by query text with optional filters, limit, and similarity threshold.
- **get_memory_by_id**: Get a specific memory by its ID (`memory_id` accepts both `int` and `str`).
- **update_memory**: Update the content and metadata of an existing memory.
- **delete_memory**: Delete a specific memory by its ID.
- **delete_all_memories**: Batch delete memories by user_id, agent_id, or run_id.
- **list_memories**: List all memories with pagination support (limit and offset) and optional filters.

### User Profile Tools

- **add_memory_with_profile**: Add memory and extract user profile information from conversation. Supports `content` (natural language) and `topics` (structured JSON) profile types.
- **search_memories_with_profile**: Search memories and optionally include the user's profile in the results for personalized responses.
- **get_user_profile**: Get a user's profile by user_id.
- **list_user_profiles**: List user profiles with optional filtering by user_id and topic fields.
- **delete_user_profile**: Delete a user's profile by user_id.
- **delete_memory_with_profile**: Delete a memory and optionally the associated user profile.

## Community

When you need help, you can find developers and other community partners at [https://github.com/oceanbase/powermem](https://github.com/oceanbase/powermem).

When you discover project defects, please create a new issue on the [issues](https://github.com/oceanbase/powermem/issues) page.

## License

For more information, see [LICENSE](LICENSE).
