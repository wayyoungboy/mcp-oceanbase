#!/bin/bash
# PowerMem MCP Test Script
# Usage:
#   ./test_mcp.sh                        # streamable-http, localhost:8000
#   ./test_mcp.sh sse                    # SSE mode
#   ./test_mcp.sh streamable-http 8001   # 指定端口

MODE=${1:-streamable-http}
HOST=${2:-localhost}
PORT=${3:-8000}
BASE_URL="http://${HOST}:${PORT}"

# ============================================================
# 可修改的请求参数
# ============================================================
ADD_MESSAGES="我喜欢去旅游"
ADD_USER_ID="1"
ADD_AGENT_ID="agent_01"
ADD_RUN_ID="task_01"

SEARCH_QUERY="用户喜欢旅游吗"
SEARCH_USER_ID="1"
SEARCH_AGENT_ID="agent_01"
SEARCH_RUN_ID="task_01"
SEARCH_THRESHOLD="0.1"
SEARCH_LIMIT="10"
# ============================================================

echo "======================================"
echo " PowerMem MCP Test"
echo " Mode: $MODE  URL: $BASE_URL/mcp"
echo "======================================"

# ---------- streamable-http ----------
if [ "$MODE" = "streamable-http" ]; then

  echo ""
  echo "[1/4] Initialize..."
  INIT_RESP=$(curl -s -D /tmp/mcp_headers.txt -X POST "${BASE_URL}/mcp" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":0}')
  SESSION_ID=$(grep -i "mcp-session-id" /tmp/mcp_headers.txt | awk '{print $2}' | tr -d '\r')
  echo "  Session ID: $SESSION_ID"
  echo "  Response: $INIT_RESP" | python3 -c "import sys,json; d=sys.stdin.read(); print('  OK' if 'protocolVersion' in d else '  FAIL: '+d)"

  echo ""
  echo "[2/4] Initialized notification..."
  curl -s -X POST "${BASE_URL}/mcp" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -H "Mcp-Session-Id: $SESSION_ID" \
    -d '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}' > /dev/null
  echo "  Sent"

  echo ""
  echo "[3/4] Add Memory..."
  ADD_BODY=$(printf '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"add_memory","arguments":{"messages":"%s","user_id":"%s","agent_id":"%s","run_id":"%s","infer":"true"}},"id":1}' \
    "$ADD_MESSAGES" "$ADD_USER_ID" "$ADD_AGENT_ID" "$ADD_RUN_ID")
  ADD_RESP=$(curl -s -X POST "${BASE_URL}/mcp" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -H "Mcp-Session-Id: $SESSION_ID" \
    -d "$ADD_BODY")
  echo "  $ADD_RESP" | python3 -c "
import sys, json, re
raw = sys.stdin.read()
m = re.search(r'data: ({.*})', raw)
if m:
    d = json.loads(m.group(1))
    if 'error' in d:
        print('  FAIL:', d['error'])
    else:
        text = d.get('result',{}).get('content',[{}])[0].get('text','')
        r = json.loads(text) if text else {}
        results = r.get('results', [])
        for item in results:
            print('  event:', item.get('event'), '| memory:', item.get('memory'))
        if not results:
            print('  No results (may be NONE/dedup)')
else:
    print(' ', raw)
"

  echo ""
  echo "[4/4] Search Memories..."
  SEARCH_BODY=$(printf '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"search_memories","arguments":{"query":"%s","user_id":"%s","agent_id":"%s","run_id":"%s","limit":"%s","threshold":"%s","filters":"{}"}},"id":2}' \
    "$SEARCH_QUERY" "$SEARCH_USER_ID" "$SEARCH_AGENT_ID" "$SEARCH_RUN_ID" "$SEARCH_LIMIT" "$SEARCH_THRESHOLD")
  SEARCH_RESP=$(curl -s -X POST "${BASE_URL}/mcp" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -H "Mcp-Session-Id: $SESSION_ID" \
    -d "$SEARCH_BODY")
  echo "  $SEARCH_RESP" | python3 -c "
import sys, json, re
raw = sys.stdin.read()
m = re.search(r'data: ({.*})', raw)
if m:
    d = json.loads(m.group(1))
    if 'error' in d:
        print('  FAIL:', d['error'])
    else:
        text = d.get('result',{}).get('content',[{}])[0].get('text','')
        r = json.loads(text) if text else {}
        results = r.get('results', [])
        if results:
            for item in results:
                print('  memory:', item.get('memory'), '| score:', round(item.get('score',0),4))
        else:
            print('  No results returned')
else:
    print(' ', raw)
"

# ---------- SSE ----------
elif [ "$MODE" = "sse" ]; then

  SSE_LOG="/tmp/sse_test_stream.log"
  rm -f "$SSE_LOG"

  echo ""
  echo "[1/5] Opening SSE connection..."
  curl -s -N "${BASE_URL}/mcp" -H "Accept: text/event-stream" > "$SSE_LOG" 2>&1 &
  SSE_PID=$!
  sleep 1
  SESSION_ID=$(grep -o 'session_id=[a-f0-9]*' "$SSE_LOG" | head -1 | cut -d= -f2)
  echo "  Session ID: $SESSION_ID"

  MSG_URL="${BASE_URL}/messages/?session_id=${SESSION_ID}"

  echo ""
  echo "[2/5] Initialize..."
  curl -s -X POST "$MSG_URL" -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":0}' > /dev/null
  curl -s -X POST "$MSG_URL" -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}' > /dev/null
  sleep 1
  echo "  Done"

  echo ""
  echo "[3/5] Add Memory..."
  ADD_BODY=$(printf '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"add_memory","arguments":{"messages":"%s","user_id":"%s","agent_id":"%s","run_id":"%s","infer":"true"}},"id":1}' \
    "$ADD_MESSAGES" "$ADD_USER_ID" "$ADD_AGENT_ID" "$ADD_RUN_ID")
  curl -s -X POST "$MSG_URL" -H "Content-Type: application/json" -d "$ADD_BODY" > /dev/null
  echo -n "  Waiting for add response"
  for i in $(seq 1 120); do
    sleep 1
    echo -n "."
    if grep -q '"id":1' "$SSE_LOG" 2>/dev/null; then echo " done (${i}s)"; break; fi
    if [ $i -eq 120 ]; then echo " timeout!"; fi
  done

  echo ""
  echo "[4/5] Search Memories..."
  SEARCH_BODY=$(printf '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"search_memories","arguments":{"query":"%s","user_id":"%s","agent_id":"%s","run_id":"%s","limit":"%s","threshold":"%s","filters":"{}"}},"id":2}' \
    "$SEARCH_QUERY" "$SEARCH_USER_ID" "$SEARCH_AGENT_ID" "$SEARCH_RUN_ID" "$SEARCH_LIMIT" "$SEARCH_THRESHOLD")
  curl -s -X POST "$MSG_URL" -H "Content-Type: application/json" -d "$SEARCH_BODY" > /dev/null
  echo -n "  Waiting for search response"
  for i in $(seq 1 60); do
    sleep 1
    echo -n "."
    if grep -q '"id":2' "$SSE_LOG" 2>/dev/null; then echo " done (${i}s)"; break; fi
    if [ $i -eq 60 ]; then echo " timeout!"; fi
  done

  kill $SSE_PID 2>/dev/null

  echo ""
  echo "[5/5] Results from SSE stream:"
  python3 -c "
import json, re
with open('$SSE_LOG') as f:
    content = f.read()
for m in re.finditer(r'data: ({.*})', content):
    d = json.loads(m.group(1))
    rid = d.get('id')
    if rid == 0:
        print('  [initialize] OK')
    elif rid == 1:
        text = d.get('result',{}).get('content',[{}])[0].get('text','')
        r = json.loads(text) if text else {}
        if isinstance(r, list):
            if r:
                for item in r:
                    print('  [add] event:', item.get('event') if isinstance(item, dict) else item, '| memory:', item.get('memory','') if isinstance(item, dict) else '')
            else:
                print('  [add] No action (dedup/NONE)')
        else:
            results = r.get('results', []) if isinstance(r, dict) else []
            if results:
                for item in results:
                    print('  [add] event:', item.get('event'), '| memory:', item.get('memory'))
            else:
                print('  [add] No action (dedup/NONE)')
    elif rid == 2:
        text = d.get('result',{}).get('content',[{}])[0].get('text','')
        r = json.loads(text) if text else {}
        results = r.get('results',[])
        if results:
            for item in results:
                print('  [search] memory:', item.get('memory'), '| score:', round(item.get('score',0),4))
        else:
            print('  [search] No results')
"

else
  echo "Unknown mode: $MODE"
  echo "Usage: $0 [streamable-http|sse] [host] [port]"
  exit 1
fi

echo ""
echo "======================================"
echo " Done"
echo "======================================"
