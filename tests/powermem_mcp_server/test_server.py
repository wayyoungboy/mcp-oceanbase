"""
PowerMem MCP Server integration tests.

Prerequisites:
  - Server running: uvx powermem-mcp streamable-http 8000
  - .env configured with valid database / LLM / embedding settings

Run:
  pytest tests/powermem_mcp_server/test_server.py -v
  pytest tests/powermem_mcp_server/test_server.py -v --base-url http://localhost:8001/mcp
"""

import json
import uuid

import pytest
import requests

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def base_url(request):
    return request.config.getoption("--base-url")


@pytest.fixture(scope="session")
def test_user_id():
    return f"test_user_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="session")
def test_agent_id():
    return f"test_agent_{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def init_session(base_url: str) -> str:
    """Initialize MCP session and return the session ID."""
    payload = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "pytest", "version": "1.0"},
        },
    }
    resp = requests.post(base_url, json=payload, headers=_HEADERS, timeout=10)
    resp.raise_for_status()
    sid = resp.headers.get("mcp-session-id")
    assert sid, "No mcp-session-id in response headers"
    return sid


@pytest.fixture(scope="session")
def session_id(base_url):
    return init_session(base_url)


def call_tool(base_url: str, session_id: str, tool_name: str, arguments: dict) -> dict:
    """Send a JSON-RPC 2.0 tools/call request and return the parsed result."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    headers = {**_HEADERS, "mcp-session-id": session_id}
    resp = requests.post(base_url, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()

    # streamable-http returns SSE; parse first data: line
    data_line = next((l[6:] for l in resp.text.splitlines() if l.startswith("data:")), None)
    assert data_line, f"No data line in response: {resp.text}"
    data = json.loads(data_line)
    assert "error" not in data, f"RPC error: {data['error']}"

    content = data["result"]["content"]
    text = content[0]["text"] if content else "{}"
    return json.loads(text)


# ---------------------------------------------------------------------------
# Tests: core memory tools
# ---------------------------------------------------------------------------

class TestCoreMemoryTools:

    def test_add_memory_string(self, base_url, session_id, test_user_id):
        result = call_tool(base_url, session_id, "add_memory", {
            "messages": "I love hiking in the mountains",
            "user_id": test_user_id,
        })
        assert "error" not in result

    def test_add_memory_list(self, base_url, session_id, test_user_id, test_agent_id):
        result = call_tool(base_url, session_id, "add_memory", {
            "messages": [
                {"role": "user", "content": "My favorite food is sushi"},
                {"role": "assistant", "content": "Good to know!"},
            ],
            "user_id": test_user_id,
            "agent_id": test_agent_id,
        })
        assert "error" not in result

    def test_add_memory_empty_fails(self, base_url, session_id, test_user_id):
        result = call_tool(base_url, session_id, "add_memory", {
            "messages": "",
            "user_id": test_user_id,
        })
        assert result.get("success") is False

    def test_list_memories(self, base_url, session_id, test_user_id):
        result = call_tool(base_url, session_id, "list_memories", {
            "user_id": test_user_id,
            "limit": 10,
        })
        assert "error" not in result

    def test_search_memories(self, base_url, session_id, test_user_id):
        result = call_tool(base_url, session_id, "search_memories", {
            "query": "hiking",
            "user_id": test_user_id,
            "limit": 5,
        })
        assert "error" not in result

    def test_search_memories_with_threshold(self, base_url, session_id, test_user_id):
        result = call_tool(base_url, session_id, "search_memories", {
            "query": "food",
            "user_id": test_user_id,
            "limit": 5,
            "threshold": 0.5,
        })
        assert "error" not in result

    def test_get_and_update_delete_memory(self, base_url, session_id, test_user_id):
        add_result = call_tool(base_url, session_id, "add_memory", {
            "messages": "I play piano on weekends",
            "user_id": test_user_id,
            "infer": False,
        })
        assert "error" not in add_result

        list_result = call_tool(base_url, session_id, "list_memories", {
            "user_id": test_user_id,
            "limit": 100,
        })
        memories = list_result.get("results", list_result if isinstance(list_result, list) else [])
        assert len(memories) > 0, "Expected at least one memory"
        memory_id = memories[-1]["id"]

        get_result = call_tool(base_url, session_id, "get_memory_by_id", {
            "memory_id": memory_id,
            "user_id": test_user_id,
        })
        assert "error" not in get_result

        update_result = call_tool(base_url, session_id, "update_memory", {
            "memory_id": memory_id,
            "content": "I play guitar on weekends",
            "user_id": test_user_id,
        })
        assert "error" not in update_result

        delete_result = call_tool(base_url, session_id, "delete_memory", {
            "memory_id": memory_id,
            "user_id": test_user_id,
        })
        assert delete_result.get("success") is True

    def test_delete_all_memories(self, base_url, session_id):
        tmp_user = f"tmp_{uuid.uuid4().hex[:8]}"
        call_tool(base_url, session_id, "add_memory", {
            "messages": "temporary memory",
            "user_id": tmp_user,
            "infer": False,
        })
        result = call_tool(base_url, session_id, "delete_all_memories", {"user_id": tmp_user})
        assert result.get("success") is True

    def test_search_memories_with_filters(self, base_url, session_id, test_user_id):
        # filters as empty dict
        result = call_tool(base_url, session_id, "search_memories", {
            "query": "hiking",
            "user_id": test_user_id,
            "limit": 5,
            "filters": {},
        })
        assert "error" not in result

        # filters as non-empty dict
        result = call_tool(base_url, session_id, "search_memories", {
            "query": "food",
            "user_id": test_user_id,
            "limit": 5,
            "filters": {"source": "chat"},
        })
        assert "error" not in result

    def test_list_memories_with_filters(self, base_url, session_id, test_user_id):
        # filters as empty dict
        result = call_tool(base_url, session_id, "list_memories", {
            "user_id": test_user_id,
            "limit": 10,
            "filters": {},
        })
        assert "error" not in result

        # filters as non-empty dict
        result = call_tool(base_url, session_id, "list_memories", {
            "user_id": test_user_id,
            "limit": 10,
            "filters": {"source": "chat"},
        })
        assert "error" not in result

    def test_search_memories_with_filters_as_string(self, base_url, session_id, test_user_id):
        """Verify string-form filters are coerced correctly (pydantic compat)."""
        result = call_tool(base_url, session_id, "search_memories", {
            "query": "hiking",
            "user_id": test_user_id,
            "limit": 5,
            "filters": "{}",
        })
        assert "error" not in result


# ---------------------------------------------------------------------------
# Tests: user profile tools
# ---------------------------------------------------------------------------

class TestUserProfileTools:

    def test_add_memory_with_profile(self, base_url, session_id, test_user_id):
        result = call_tool(base_url, session_id, "add_memory_with_profile", {
            "messages": [
                {"role": "user", "content": "My name is Alex, I am 30 years old and work as a software engineer"},
            ],
            "user_id": test_user_id,
        })
        assert "error" not in result

    def test_add_memory_with_profile_topics(self, base_url, session_id, test_user_id):
        result = call_tool(base_url, session_id, "add_memory_with_profile", {
            "messages": "I live in Shanghai and enjoy photography",
            "user_id": test_user_id,
            "profile_type": "topics",
            "custom_topics": json.dumps({
                "personal_info": {
                    "location": "city of residence",
                    "hobbies": "leisure activities",
                }
            }),
        })
        assert "error" not in result

    def test_search_memories_with_profile(self, base_url, session_id, test_user_id):
        result = call_tool(base_url, session_id, "search_memories_with_profile", {
            "query": "software engineer",
            "user_id": test_user_id,
            "add_profile": True,
        })
        assert "error" not in result

    def test_get_user_profile(self, base_url, session_id, test_user_id):
        result = call_tool(base_url, session_id, "get_user_profile", {"user_id": test_user_id})
        assert isinstance(result, dict)

    def test_list_user_profiles(self, base_url, session_id, test_user_id):
        result = call_tool(base_url, session_id, "list_user_profiles", {
            "user_id": test_user_id,
            "limit": 10,
        })
        assert "profiles" in result

    def test_delete_memory_with_profile(self, base_url, session_id, test_user_id, test_agent_id):
        add_result = call_tool(base_url, session_id, "add_memory_with_profile", {
            "messages": "I enjoy reading science fiction books",
            "user_id": test_user_id,
            "agent_id": test_agent_id,
            "infer": False,
        })
        assert "error" not in add_result

        list_result = call_tool(base_url, session_id, "list_memories", {
            "user_id": test_user_id,
            "limit": 100,
        })
        memories = list_result.get("results", list_result if isinstance(list_result, list) else [])
        assert len(memories) > 0
        memory_id = memories[-1]["id"]

        result = call_tool(base_url, session_id, "delete_memory_with_profile", {
            "memory_id": memory_id,
            "user_id": test_user_id,
            "delete_profile": False,
        })
        assert result.get("success") is True

    def test_delete_user_profile(self, base_url, session_id):
        tmp_user = f"tmp_profile_{uuid.uuid4().hex[:8]}"
        call_tool(base_url, session_id, "add_memory_with_profile", {
            "messages": "My name is Temp User",
            "user_id": tmp_user,
        })
        result = call_tool(base_url, session_id, "delete_user_profile", {"user_id": tmp_user})
        assert isinstance(result.get("success"), bool)
