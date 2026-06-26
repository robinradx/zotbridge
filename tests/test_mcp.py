import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from zotbridge.config import Settings
from zotbridge.mcp import run_stdio_server


class McpTests(unittest.TestCase):
    def test_initialize_echoes_supported_client_protocol_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            stdin = io.StringIO(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-03-26",
                            "capabilities": {},
                            "clientInfo": {"name": "test", "version": "0"},
                        },
                    }
                )
                + "\n"
            )
            stdout = io.StringIO()
            settings = Settings(state_dir=str(Path(tmp) / "state"))

            with patch("sys.stdin", stdin), patch("sys.stdout", stdout):
                run_stdio_server(settings)

            response = json.loads(stdout.getvalue())
            self.assertEqual(response["result"]["protocolVersion"], "2025-03-26")

    def test_tools_list_returns_available_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            stdin = io.StringIO(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "jsonrpc": "2.0",
                                "id": 1,
                                "method": "initialize",
                                "params": {
                                    "protocolVersion": "2025-11-25",
                                    "capabilities": {},
                                    "clientInfo": {"name": "test", "version": "0"},
                                },
                            }
                        ),
                        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
                        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
                    ]
                )
                + "\n"
            )
            stdout = io.StringIO()
            settings = Settings(state_dir=str(Path(tmp) / "state"))

            with patch("sys.stdin", stdin), patch("sys.stdout", stdout):
                run_stdio_server(settings)

            responses = [json.loads(line) for line in stdout.getvalue().splitlines()]
            tool_names = {tool["name"] for tool in responses[1]["result"]["tools"]}
            self.assertIn("zotero_capabilities", tool_names)
            self.assertIn("zotero_qmd_get", tool_names)
            self.assertIn("zotero_qmd_doctor", tool_names)


if __name__ == "__main__":
    unittest.main()
