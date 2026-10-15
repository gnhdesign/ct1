"""Minimal client for driving a running SolidCraft app over MCP.

Start the app first:  solidcraft --control 7878
Usage from shell:
    python sc.py list_commands '{"filter": "sketch"}'
    python sc.py execute '{"command": "solid.box", "params": {...}}'
    python sc.py batch commands.json
Usage from Python:
    from sc import Session
    with Session() as s:
        s.call("execute", command="solid.box", params={...})
"""

import json
import os
import subprocess
import sys

CLI = os.environ.get("SOLIDCRAFT_CLI", r"C:\Program\SolidCraft\solidcraft-cli.exe")
ADDR = os.environ.get("SOLIDCRAFT_ADDR", "127.0.0.1:7878")
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


class Session:
    def __init__(self, cli=CLI, addr=ADDR, allow_path=PROJECT_DIR):
        args = [cli, "mcp", "--connect", addr]
        if allow_path:
            args += ["--allow-path", allow_path]
        self.proc = subprocess.Popen(
            args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, encoding="utf-8", bufsize=1,
        )
        self._id = 0
        self._rpc("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "ct1", "version": "1"},
        })
        self._notify("notifications/initialized")

    def _notify(self, method):
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method}) + "\n")
        self.proc.stdin.flush()

    def _rpc(self, method, params=None):
        self._id += 1
        msg = {"jsonrpc": "2.0", "id": self._id, "method": method}
        if params is not None:
            msg["params"] = params
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("SolidCraft MCP server closed the connection")
            resp = json.loads(line)
            if resp.get("id") == self._id:
                break
        if "error" in resp:
            raise RuntimeError(f"{method}: {resp['error']}")
        return resp["result"]

    def call(self, tool, **arguments):
        """Call an MCP tool; returns parsed JSON text content where possible."""
        result = self._rpc("tools/call", {"name": tool, "arguments": arguments})
        out = []
        for item in result.get("content", []):
            if item.get("type") == "text":
                try:
                    out.append(json.loads(item["text"]))
                except json.JSONDecodeError:
                    out.append(item["text"])
            else:
                out.append({"type": item.get("type")})
        out = out[0] if len(out) == 1 else out
        if result.get("isError"):
            raise RuntimeError(f"{tool} failed: {out}")
        return out

    def execute(self, command, verbose=False, **params):
        return self.call("execute", command=command, params=params, verbose=verbose)

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


if __name__ == "__main__":
    tool = sys.argv[1]
    arg = sys.argv[2] if len(sys.argv) > 2 else "{}"
    if os.path.isfile(arg):
        with open(arg, encoding="utf-8") as f:
            arg = f.read()
    with Session() as s:
        try:
            res = s.call(tool, **json.loads(arg))
        except RuntimeError as e:
            print(e)
            sys.exit(1)
    print(json.dumps(res, indent=1) if not isinstance(res, str) else res)
