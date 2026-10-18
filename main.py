import hashlib
import json
import re

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

app = FastAPI()

EMAIL = "23f3003995@ds.study.iitm.ac.in"
PROTOCOL_VERSION = "2025-03-26"

TOOLS = [
    {
        "name": "solve_challenge",
        "description": "Solve the current exam challenge using the HTTP request header.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    try:
        message = await request.json()
    except Exception:
        return JSONResponse(
            {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None},
            status_code=400
        )

    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") or {}

    # MCP notifications do not receive JSON-RPC responses.
    if method == "notifications/initialized":
        return Response(status_code=202)

    if method == "initialize":
        result = {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {
                "name": "exam-challenge-server",
                "version": "1.0.0"
            }
        }
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        })

    if method == "ping":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {}
        })

    if method == "tools/list":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": TOOLS}
        })

    if method == "tools/call":
        name = params.get("name")
        if name != "solve_challenge":
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32602, "message": "Unknown tool"}
            })

        # Read the fresh challenge from the HTTP headers, never from tool arguments.
        challenge = request.headers.get("x-exam-challenge", "")

        if not re.fullmatch(r"[0-9a-f]{32}", challenge):
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32602, "message": "Missing or invalid X-Exam-Challenge"}
            })

        digest = hashlib.sha256(
            f"{challenge}:{EMAIL}".encode("utf-8")
        ).hexdigest()[:16]

        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": digest}],
                "isError": False
            }
        })

    # A notification has no id and should not receive a JSON-RPC response.
    if request_id is None:
        return Response(status_code=202)

    return JSONResponse({
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": "Method not found"}
    })
