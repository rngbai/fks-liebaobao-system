from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi_app import app


def main() -> None:
    client = TestClient(app)

    health = client.get("/api/recharge/health")
    assert health.status_code == 200, health.text
    health_payload = health.json()
    assert health_payload["ok"] is True, health_payload
    assert health_payload["data"]["adminPath"] == "/admin/", health_payload

    auth_check = client.get("/api/manage/auth-check")
    assert auth_check.status_code == 401, auth_check.text
    auth_payload = auth_check.json()
    assert auth_payload["ok"] is False, auth_payload

    print("fastapi smoke assertions passed")


if __name__ == "__main__":
    main()
