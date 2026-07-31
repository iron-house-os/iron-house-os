from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from dataclasses import replace

from ops.agent.iron_house_agent.dashboard import create_dashboard_server
from ops.agent.iron_house_agent.store import JobStore


def test_dashboard_is_read_only_and_does_not_expose_prompts(settings) -> None:
    settings = replace(settings, dashboard_port=0)
    store = JobStore(settings.database_path)
    store.initialize()
    store.enqueue(
        project_key="test-project",
        role="documentation",
        issue_number=107,
        title="Document test",
        prompt="Private task instructions that must not appear in dashboard JSON.",
    )
    server = create_dashboard_server(
        settings,
        store,
        state_provider=lambda: {
            "generated_at": "2026-07-31T00:00:00+00:00",
            "production_locked": True,
            "agent_roles": [],
            "repositories": [],
            **store.snapshot(),
        },
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with urllib.request.urlopen(f"{base_url}/api/state") as response:
            payload = json.load(response)
        assert payload["production_locked"] is True
        assert "prompt" not in payload["queue"][0]

        request = urllib.request.Request(f"{base_url}/api/state", method="POST")
        try:
            urllib.request.urlopen(request)
            raise AssertionError("POST unexpectedly succeeded")
        except urllib.error.HTTPError as error:
            assert error.code == 405
    finally:
        server.shutdown()
        thread.join(timeout=5)
