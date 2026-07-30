import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.check_react_router_rsc_boundary import inspect_boundary  # noqa: E402


def write_frontend(root: Path, *, dependency: str | None = None, source: str = "") -> None:
    frontend = root / "frontend"
    (frontend / "src").mkdir(parents=True)
    dependencies = {"react-router-dom": "7.18.1"}
    if dependency:
        dependencies[dependency] = "1.0.0"
    (frontend / "package.json").write_text(
        json.dumps({"dependencies": dependencies}),
        encoding="utf-8",
    )
    (frontend / "package-lock.json").write_text(
        json.dumps(
            {
                "packages": {
                    "node_modules/react-router": {"version": "7.18.1"},
                    "node_modules/react-router-dom": {"version": "7.18.1"},
                }
            }
        ),
        encoding="utf-8",
    )
    (frontend / "src" / "main.tsx").write_text(source, encoding="utf-8")


def test_current_frontend_has_no_rsc_execution_path() -> None:
    result = inspect_boundary(ROOT)

    assert result["status"] == "passed"
    assert result["architecture"] == "vite-declarative-spa"
    assert result["locked_versions"]["react-router"]
    assert result["locked_versions"]["react-router-dom"]
    assert result["rsc_dependencies"] == "absent"
    assert result["rsc_source_apis"] == "absent"


def test_rsc_dependency_fails_closed(tmp_path: Path) -> None:
    write_frontend(tmp_path, dependency="@vitejs/plugin-rsc")

    result = inspect_boundary(tmp_path)

    assert result["status"] == "failed"
    assert any("@vitejs/plugin-rsc" in error for error in result["errors"])


def test_rsc_source_api_fails_closed(tmp_path: Path) -> None:
    write_frontend(
        tmp_path,
        source='import { RSCHydratedRouter } from "react-router/dom-rsc";',
    )

    result = inspect_boundary(tmp_path)

    assert result["status"] == "failed"
    assert any("RSCHydratedRouter" in error for error in result["errors"])
