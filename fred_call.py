"""Call one tool on FRED's MCP server from the command line.

For FRED-arm runs from a session that could not load the `fred` MCP server:
    python fred_call.py list
    python fred_call.py <tool-name> '<json arguments>'
"""
import json
import sys
import urllib.request

from fred_auth import access_token

URL = "https://mcp.stlouisfed.org/"


def rpc(method, params, session=None, rid=1):
    body = {"jsonrpc": "2.0", "method": method, "params": params}
    if rid is not None:
        body["id"] = rid
    headers = {
        "Authorization": "Bearer " + access_token(),
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session:
        headers["Mcp-Session-Id"] = session
    req = urllib.request.Request(URL, json.dumps(body).encode(), headers)
    with urllib.request.urlopen(req, timeout=120) as r:
        sid = r.headers.get("Mcp-Session-Id") or session
        text = r.read().decode("utf-8", "replace")
    if rid is None:
        return None, sid
    if text.lstrip().startswith("{"):
        return json.loads(text), sid
    # Server-sent events: take the last data line that parses.
    msg = None
    for line in text.splitlines():
        if line.startswith("data:"):
            try:
                msg = json.loads(line[5:].strip())
            except ValueError:
                pass
    return msg, sid


def main():
    init, sid = rpc("initialize", {
        "protocolVersion": "2025-06-18", "capabilities": {},
        "clientInfo": {"name": "fredcheck", "version": "1"}})
    rpc("notifications/initialized", {}, sid, rid=None)
    if len(sys.argv) < 2 or sys.argv[1] == "list":
        res, _ = rpc("tools/list", {}, sid, rid=2)
        for t in res["result"]["tools"]:
            print(json.dumps({"name": t["name"], "description": t.get("description", ""),
                              "input": t.get("inputSchema", {})}))
        return
    args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    res, _ = rpc("tools/call", {"name": sys.argv[1], "arguments": args}, sid, rid=2)
    if "error" in res:
        print(json.dumps(res["error"]))
        return
    for part in res["result"].get("content", []):
        print(part.get("text", json.dumps(part)))


if __name__ == "__main__":
    main()
