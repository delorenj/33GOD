"""Protocol proof against the installed executable; Python stdlib only."""
import json
import selectors
import subprocess

process = subprocess.Popen(
    ["codegraph-voyage-mcp", "--transport", "stdio"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
)
assert process.stdin is not None and process.stdout is not None
selector = selectors.DefaultSelector()
selector.register(process.stdout, selectors.EVENT_READ)


def send(message):
    process.stdin.write(json.dumps(message) + "\n")
    process.stdin.flush()


def receive(expected_id):
    assert selector.select(15), "MCP response timed out"
    response = json.loads(process.stdout.readline())
    assert response.get("id") == expected_id and "error" not in response, response
    return response["result"]


try:
    send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2024-11-05", "capabilities": {},
        "clientInfo": {"name": "g5-smoke", "version": "1"},
    }})
    result = receive(1)
    assert result["serverInfo"]["name"] == "codegraph-voyage", result
    print("MCP initialize:", json.dumps(result["serverInfo"]), flush=True)
    send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    names = sorted(tool["name"] for tool in receive(2)["tools"])
    assert names == ["explore", "index", "search", "semantic_candidates", "status"], names
    print("MCP tools/list:", ", ".join(names), flush=True)
    process.stdin.close()
    assert process.wait(timeout=15) == 0
    print("MCP EOF: exit 0")
finally:
    if process.poll() is None:
        process.kill()
        process.wait()
    selector.close()
