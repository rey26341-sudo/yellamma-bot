#!/bin/bash
set -e

echo "=== Turn 1: greeting ==="
RESP=$(curl -s -X POST http://localhost:8002/chat -H "Content-Type: application/json" -d '{"business_id":"salon","message":"hi"}')
echo "$RESP"
SID=$(python3 -c "import sys,json; print(json.loads(sys.argv[1])['session_id'])" "$RESP")
echo "Captured session_id: $SID"
echo

echo "=== Turn 2: book appointment ==="
RESP=$(curl -s -X POST http://localhost:8002/chat -H "Content-Type: application/json" -d "{\"business_id\":\"salon\",\"message\":\"book appointment\",\"session_id\":\"$SID\"}")
echo "$RESP"
echo

echo "=== Turn 3: give name ==="
RESP=$(curl -s -X POST http://localhost:8002/chat -H "Content-Type: application/json" -d "{\"business_id\":\"salon\",\"message\":\"Renganayaki\",\"session_id\":\"$SID\"}")
echo "$RESP"
echo

echo "=== Turn 4: give phone ==="
RESP=$(curl -s -X POST http://localhost:8002/chat -H "Content-Type: application/json" -d "{\"business_id\":\"salon\",\"message\":\"9876543210\",\"session_id\":\"$SID\"}")
echo "$RESP"
echo

echo "=== Turn 5: give date ==="
RESP=$(curl -s -X POST http://localhost:8002/chat -H "Content-Type: application/json" -d "{\"business_id\":\"salon\",\"message\":\"next Monday\",\"session_id\":\"$SID\"}")
echo "$RESP"
echo

echo "=== Turn 6: give time ==="
RESP=$(curl -s -X POST http://localhost:8002/chat -H "Content-Type: application/json" -d "{\"business_id\":\"salon\",\"message\":\"2 PM\",\"session_id\":\"$SID\"}")
echo "$RESP"
