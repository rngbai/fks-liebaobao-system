import os

import uvicorn


def run() -> None:
    host = os.environ.get("RECHARGE_VERIFY_HOST", "0.0.0.0")
    port = int(os.environ.get("RECHARGE_VERIFY_PORT", "5000"))
    uvicorn.run(
        "fastapi_app:app",
        host=host,
        port=port,
        reload=False,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    run()
