from __future__ import annotations
import os
from agents.research.wordpress_draft_delivery_client import WordPressConnection, deliver_wordpress_draft


def main() -> None:
    required = ("WORDPRESS_BASE_URL", "WORDPRESS_USERNAME", "WORDPRESS_APPLICATION_PASSWORD")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise SystemExit("Missing required environment variables: " + ", ".join(missing))

    connection = WordPressConnection.from_env()
    delivery = {
        "delivery_id": "live_smoke_test",
        "platform": "wordpress",
        "lifecycle_stage": "wordpress_draft_ready",
        "request_payload": {
            "title": "IRL AI Core — WordPress Draft Smoke Test",
            "content": "Temporary smoke-test draft created by IRL AI Core. Review and delete it after verification.",
            "status": "draft",
        },
        "evidence_refs": ["live_smoke_test"],
    }

    result = deliver_wordpress_draft(delivery=delivery, connection=connection)
    if result.get("status") != "draft" or result.get("remote_status") != "draft":
        raise SystemExit("FAIL: WordPress did not confirm status=draft")

    print("LIVE WORDPRESS DRAFT SMOKE TEST: PASS")
    print(f"post_id={result['post_id']}")
    print(f"status={result['status']}")
    print(f"remote_status={result['remote_status']}")
    print(f"edit_url={result.get('edit_url')}")


if __name__ == "__main__":
    main()
