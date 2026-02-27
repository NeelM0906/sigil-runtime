from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path

from bomba_sr.runtime.sisters import SisterRegistry
from bomba_sr.storage.db import RuntimeDB
from bomba_sr.subagents.orchestrator import SubAgentOrchestrator
from bomba_sr.subagents.protocol import SubAgentProtocol


def _worker(run_id, task, protocol):
    protocol.progress(run_id, 20, summary="boot")
    time.sleep(0.2)
    return {"summary": f"done:{task.goal}", "runtime_ms": 5, "token_usage": {"input": 1, "output": 1}}


class SisterRegistryTests(unittest.TestCase):
    def test_missing_config_graceful(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = RuntimeDB(Path(td) / "runtime.db")
            protocol = SubAgentProtocol(db)
            orchestrator = SubAgentOrchestrator(protocol=protocol, default_worker=_worker, max_workers=1)
            registry = SisterRegistry(
                config_path=Path(td) / "missing-sisters.json",
                orchestrator=orchestrator,
                protocol=protocol,
            )
            self.assertEqual(registry.list_sisters(), [])

    def test_load_spawn_and_stop(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sisters_path = root / "sisters.json"
            sisters_path.write_text(
                json.dumps(
                    {
                        "sisters": [
                            {
                                "sister_id": "forge",
                                "display_name": "Sai Forge",
                                "emoji": "sword",
                                "tenant_id": "tenant-forge",
                                "workspace_root": str(root / "forge"),
                                "model_id": "anthropic/claude-sonnet-4",
                                "role": "Runs tournaments",
                                "auto_start": False,
                                "heartbeat_enabled": False,
                                "cron_tasks": [],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            db = RuntimeDB(root / "runtime.db")
            protocol = SubAgentProtocol(db)
            orchestrator = SubAgentOrchestrator(protocol=protocol, default_worker=_worker, max_workers=1)
            registry = SisterRegistry(config_path=sisters_path, orchestrator=orchestrator, protocol=protocol)

            listed = registry.list_sisters()
            self.assertEqual(len(listed), 1)
            self.assertEqual(listed[0]["sister_id"], "forge")

            start = registry.spawn_sister("forge")
            self.assertTrue(start["started"])
            self.assertTrue(start["run_id"])

            stop = registry.stop_sister("forge")
            self.assertEqual(stop["sister_id"], "forge")
            self.assertIn("stopped", stop)

    def test_rejects_workspace_outside_base(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            prime_root = root / "workspaces" / "prime"
            prime_root.mkdir(parents=True)
            sisters_path = prime_root / "sisters.json"
            sisters_path.write_text(
                json.dumps(
                    {
                        "sisters": [
                            {
                                "sister_id": "forge",
                                "display_name": "Sai Forge",
                                "tenant_id": "tenant-forge",
                                "workspace_root": "/etc",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            db = RuntimeDB(root / "runtime.db")
            protocol = SubAgentProtocol(db)
            orchestrator = SubAgentOrchestrator(protocol=protocol, default_worker=_worker, max_workers=1)
            registry = SisterRegistry(config_path=sisters_path, orchestrator=orchestrator, protocol=protocol)
            self.assertEqual(registry.list_sisters(), [])


if __name__ == "__main__":
    unittest.main()
