#!/bin/bash
# PowerMem Server Direct API Test Script
# Usage:
#   ./test_powermem_server.sh                        # localhost:18765
#   ./test_powermem_server.sh 192.168.1.100 8000     # 指定 host:port
#   ./test_powermem_server.sh localhost 8000 my_key  # 带 API Key

HOST=${1:-localhost}
PORT=${2:-18765}
API_KEY=${3:-}
BASE_URL="http://${HOST}:${PORT}/api/v1"

# ============================================================
# 可修改的请求参数
# ============================================================
USER_ID="1"
AGENT_ID="agent_01"
RUN_ID="task_01"
ADD_CONTENT="我喜欢去旅游"
SEARCH_QUERY="用户喜欢旅游吗"
# ============================================================

# 构造通用 curl header
CURL_OPTS=(-s -H "Content-Type: application/json")
[ -n "$API_KEY" ] && CURL_OPTS+=(-H "X-API-Key: $API_KEY")

echo "======================================"
echo " PowerMem Server Direct API Test"
echo " URL: $BASE_URL"
echo " API Key: ${API_KEY:-<none>}"
echo "======================================"

pretty() {
  python3 -c "import sys,json; d=sys.stdin.read(); print(json.dumps(json.loads(d), ensure_ascii=False, indent=2))" 2>/dev/null || cat
}

# ---------- ADD ----------
echo ""
echo "[1] POST /memories (add)"
RESP=$(curl "${CURL_OPTS[@]}" -X POST "${BASE_URL}/memories" \
  -d "$(printf '{"content":"%s","user_id":"%s","agent_id":"%s","run_id":"%s","infer":true}' \
    "$ADD_CONTENT" "$USER_ID" "$AGENT_ID" "$RUN_ID")")
echo "$RESP" | pretty
SUCCESS=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('success',''))" 2>/dev/null)
if [ "$SUCCESS" = "True" ] || [ "$SUCCESS" = "true" ]; then
  echo "  => ADD OK"
else
  echo "  => ADD FAILED"
fi

# ---------- SEARCH ----------
echo ""
echo "[2] POST /memories/search"
RESP=$(curl "${CURL_OPTS[@]}" -X POST "${BASE_URL}/memories/search" \
  -d "$(printf '{"query":"%s","user_id":"%s","agent_id":"%s","run_id":"%s","limit":10}' \
    "$SEARCH_QUERY" "$USER_ID" "$AGENT_ID" "$RUN_ID")")
echo "$RESP" | pretty
COUNT=$(echo "$RESP" | python3 -c "
import sys,json
d=json.load(sys.stdin)
results = d.get('data',{}).get('results',[])
print(len(results))
for r in results:
    print('  content:', r.get('content', r.get('memory','')), '| score:', r.get('score',''), '| vector_sim:', r.get('metadata',{}).get('_vector_similarity',''))
" 2>/dev/null)
echo "  => results: $COUNT"

# ---------- LIST ----------
echo ""
echo "[3] GET /memories (list)"
RESP=$(curl "${CURL_OPTS[@]}" -X GET \
  "${BASE_URL}/memories?user_id=${USER_ID}&agent_id=${AGENT_ID}&run_id=${RUN_ID}&limit=10")
echo "$RESP" | pretty
echo "$RESP" | python3 -c "
import sys,json
d=json.load(sys.stdin)
memories = d.get('data',{}).get('memories',[])
print('  => total:', d.get('data',{}).get('total', len(memories)))
for m in memories:
    print('  id:', m.get('id'), '| content:', m.get('content', m.get('memory','')))
" 2>/dev/null

echo ""
echo "======================================"
echo " Done"
echo "======================================"
