import json
import sys
import urllib.request

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
ENDPOINTS = ["/health", "/readiness", "/api/v1/projects"]


def fetch(path: str) -> tuple[int, str]:
    with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=10) as response:
        return response.status, response.read().decode("utf-8")


def main() -> int:
    failures: list[str] = []
    for endpoint in ENDPOINTS:
        try:
            status, body = fetch(endpoint)
            print(json.dumps({"endpoint": endpoint, "status": status, "ok": 200 <= status < 300, "body_preview": body[:120]}))
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{endpoint}: {exc}")
            print(json.dumps({"endpoint": endpoint, "ok": False, "error": str(exc)}))
    if failures:
        print("Smoke check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
