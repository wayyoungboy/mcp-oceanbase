#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
PowerMem HTTP Client

Proxy mode client that translates Memory/UserMemory method calls into HTTP requests
to a remote PowerMem server.
"""

import json
from typing import Any, Dict, List, Optional, Union

import httpx


def _messages_to_content(messages: Union[str, Dict, List]) -> str:
    """Convert messages to JSON string for HTTP API MemoryCreateRequest.content"""
    if isinstance(messages, str):
        return messages
    return json.dumps(messages, ensure_ascii=False)


class PowerMemHTTPClient:
    """
    HTTP client for core memory operations (proxy for powermem.Memory).

    Connects to a remote PowerMem server and exposes the same interface
    as the embedded Memory class used by server.py.
    """

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        headers: Dict[str, str] = {}
        if api_key:
            headers["X-API-Key"] = api_key
        self._client = httpx.Client(headers=headers, timeout=60.0)

    def _request(self, method: str, path: str, **kwargs) -> Dict:
        url = f"{self.base_url}/api/v1{path}"
        req_body = kwargs.get("json") or kwargs.get("params") or {}
        print(f"[proxy] {method} {url} | body: {json.dumps(req_body, ensure_ascii=False)[:300]}")
        response = self._client.request(method, url, **kwargs)
        print(f"[proxy] response status: {response.status_code} | body: {response.text[:500]}")
        response.raise_for_status()
        return response.json()

    def _data(self, response: Dict) -> Any:
        """Extract data from APIResponse wrapper: {"success": ..., "data": ..., ...}"""
        return response.get("data")

    def add(
        self,
        messages: Union[str, Dict, List],
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        infer: bool = True,
    ) -> Any:
        body: Dict[str, Any] = {
            "content": _messages_to_content(messages),
            "infer": infer,
        }
        if user_id is not None:
            body["user_id"] = user_id
        if agent_id is not None:
            body["agent_id"] = agent_id
        if run_id is not None:
            body["run_id"] = run_id
        if metadata is not None:
            body["metadata"] = metadata
        return self._data(self._request("POST", "/memories", json=body))

    def search(
        self,
        query: str,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        limit: int = 10,
        threshold: Optional[float] = None,
        filters: Optional[Dict] = None,
    ) -> Any:
        body: Dict[str, Any] = {"query": query, "limit": limit}
        if user_id is not None:
            body["user_id"] = user_id
        if agent_id is not None:
            body["agent_id"] = agent_id
        if run_id is not None:
            body["run_id"] = run_id
        if filters is not None:
            body["filters"] = filters
        # threshold is not supported by HTTP server, ignored in proxy mode
        data = self._data(self._request("POST", "/memories/search", json=body)) or {}
        # Normalize: PowerMem server uses 'content' field, embedded mode uses 'memory'
        # Also use _vector_similarity as score for consistency with embedded mode
        for item in data.get("results", []):
            if "content" in item and "memory" not in item:
                item["memory"] = item["content"]
            if "metadata" in item and "_vector_similarity" in item["metadata"] and item.get("score", 0) < 0.1:
                item["score"] = item["metadata"]["_vector_similarity"]
        return data

    def get(
        self,
        memory_id: Union[int, str],
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> Any:
        params: Dict[str, Any] = {}
        if user_id is not None:
            params["user_id"] = user_id
        if agent_id is not None:
            params["agent_id"] = agent_id
        return self._data(
            self._request("GET", f"/memories/{memory_id}", params=params)
        )

    def update(
        self,
        memory_id: Union[int, str],
        content: str,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Any:
        body: Dict[str, Any] = {"content": content}
        if metadata is not None:
            body["metadata"] = metadata
        return self._data(
            self._request("PUT", f"/memories/{memory_id}", json=body)
        )

    def delete(
        self,
        memory_id: Union[int, str],
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> bool:
        params: Dict[str, Any] = {}
        if user_id is not None:
            params["user_id"] = user_id
        if agent_id is not None:
            params["agent_id"] = agent_id
        self._request("DELETE", f"/memories/{memory_id}", params=params)
        return True

    def delete_all(
        self,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> bool:
        params: Dict[str, Any] = {}
        if user_id is not None:
            params["user_id"] = user_id
        if agent_id is not None:
            params["agent_id"] = agent_id
        if run_id is not None:
            params["run_id"] = run_id
        self._request("DELETE", "/system/delete-all-memories", params=params)
        return True

    def get_all(
        self,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Any:
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if user_id is not None:
            params["user_id"] = user_id
        if agent_id is not None:
            params["agent_id"] = agent_id
        if run_id is not None:
            params["run_id"] = run_id
        data = self._data(self._request("GET", "/memories", params=params)) or {}
        # HTTP server returns {"memories": [...], "total": N, ...}
        # Normalize to {"results": [...], "total": N} for consistency with search response
        if isinstance(data, dict) and "memories" in data and "results" not in data:
            data = {**data, "results": data["memories"]}
        # Normalize: 'content' -> 'memory' for consistency with embedded mode
        for item in data.get("results", []):
            if "content" in item and "memory" not in item:
                item["memory"] = item["content"]
        return data

    def close(self) -> None:
        self._client.close()


class PowerMemUserHTTPClient:
    """
    HTTP client for user profile operations (proxy for powermem.UserMemory).

    Connects to a remote PowerMem server and exposes the same interface
    as the embedded UserMemory class used by server.py.
    """

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        headers: Dict[str, str] = {}
        if api_key:
            headers["X-API-Key"] = api_key
        self._client = httpx.Client(headers=headers, timeout=60.0)

    def _request(self, method: str, path: str, **kwargs) -> Dict:
        url = f"{self.base_url}/api/v1{path}"
        req_body = kwargs.get("json") or kwargs.get("params") or {}
        print(f"[proxy:user] {method} {url} | body: {json.dumps(req_body, ensure_ascii=False)[:300]}")
        response = self._client.request(method, url, **kwargs)
        print(f"[proxy:user] response status: {response.status_code} | body: {response.text[:500]}")
        response.raise_for_status()
        return response.json()

    def _data(self, response: Dict) -> Any:
        return response.get("data")

    def add(
        self,
        messages: Union[str, Dict, List],
        user_id: str,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        infer: bool = True,
        profile_type: str = "content",
        custom_topics: Optional[str] = None,
        strict_mode: bool = False,
    ) -> Any:
        # UserProfileAddRequest.messages supports Any (str/dict/list), pass as-is
        body: Dict[str, Any] = {
            "messages": messages,
            "infer": infer,
            "profile_type": profile_type,
            "strict_mode": strict_mode,
        }
        if agent_id is not None:
            body["agent_id"] = agent_id
        if run_id is not None:
            body["run_id"] = run_id
        if metadata is not None:
            body["metadata"] = metadata
        if custom_topics is not None:
            body["custom_topics"] = custom_topics
        return self._data(
            self._request("POST", f"/users/{user_id}/profile", json=body)
        )

    def search(
        self,
        query: str,
        user_id: str,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        limit: int = 10,
        threshold: Optional[float] = None,
        filters: Optional[Dict] = None,
        add_profile: bool = True,
    ) -> Any:
        # Two sequential requests: search + get_profile (option A: both must succeed)
        search_body: Dict[str, Any] = {
            "query": query,
            "user_id": user_id,
            "limit": limit,
        }
        if agent_id is not None:
            search_body["agent_id"] = agent_id
        if run_id is not None:
            search_body["run_id"] = run_id
        if filters is not None:
            search_body["filters"] = filters

        search_result = self._data(
            self._request("POST", "/memories/search", json=search_body)
        ) or {}

        profile_result = None
        if add_profile:
            # Option A: profile request failure raises exception (propagates to caller)
            profile_result = self._data(
                self._request("GET", f"/users/{user_id}/profile")
            )

        result = dict(search_result)
        if profile_result:
            result["profile_content"] = profile_result.get("profile_content")
            result["topics"] = profile_result.get("topics")
        return result

    def profile(self, user_id: str) -> Any:
        return self._data(self._request("GET", f"/users/{user_id}/profile"))

    def profile_list(
        self,
        user_id: Optional[str] = None,
        main_topic: Optional[List[str]] = None,
        sub_topic: Optional[List[str]] = None,
        topic_value: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Any:
        # NOTE: HTTP server GET /users/profiles only supports user_id/limit/offset filtering.
        # main_topic/sub_topic/topic_value are not supported in proxy mode.
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if user_id is not None:
            params["user_id"] = user_id
        data = self._data(self._request("GET", "/users/profiles", params=params))
        # HTTP server returns {"profiles": [...], "total": n, ...}
        if isinstance(data, dict):
            return data.get("profiles", [])
        return data or []

    def delete_profile(self, user_id: str) -> bool:
        self._request("DELETE", f"/users/{user_id}/profile")
        return True

    def delete(
        self,
        memory_id: Union[int, str],
        user_id: str,
        agent_id: Optional[str] = None,
        delete_profile: bool = False,
    ) -> bool:
        params: Dict[str, Any] = {"user_id": user_id}
        if agent_id is not None:
            params["agent_id"] = agent_id
        self._request("DELETE", f"/memories/{memory_id}", params=params)
        if delete_profile:
            self._request("DELETE", f"/users/{user_id}/profile")
        return True

    def close(self) -> None:
        self._client.close()
