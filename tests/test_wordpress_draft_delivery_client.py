from __future__ import annotations
import json
from agents.research.wordpress_draft_delivery_client import WordPressConnection, deliver_wordpress_draft

def delivery():
    return {"delivery_id":"wp_draft_1","platform":"wordpress","lifecycle_stage":"wordpress_draft_ready","request_payload":{"title":"Test","content":"Body","status":"draft"},"evidence_refs":["e1"]}

def connection():
    return WordPressConnection("https://example.com","editor","app-password")

class Response:
    def __init__(self, data): self.data=data
    def read(self): return json.dumps(self.data).encode()

def test_creates_wordpress_draft_and_returns_remote_id():
    seen={}
    def transport(req, timeout):
        seen["method"]=req.method; seen["body"]=json.loads(req.data); seen["auth"]=req.headers["Authorization"]
        return Response({"id":123,"status":"draft","link":"https://example.com/?p=123"})
    result=deliver_wordpress_draft(delivery=delivery(),connection=connection(),transport=transport)
    assert result["post_id"]==123 and result["status"]=="draft" and result["delivery_status"]=="delivered"
    assert seen["method"]=="POST" and seen["body"]["status"]=="draft"
    assert seen["auth"].startswith("Basic ")

def test_rejects_publish_payload_before_network():
    d=delivery(); d["request_payload"]["status"]="publish"
    called=[]
    try: deliver_wordpress_draft(delivery=d,connection=connection(),transport=lambda *_: called.append(1))
    except ValueError: pass
    else: raise AssertionError("expected ValueError")
    assert called==[]

def test_rejects_non_wordpress_delivery():
    d=delivery(); d["platform"]="other"
    try: deliver_wordpress_draft(delivery=d,connection=connection(),transport=lambda *_: None)
    except ValueError: pass
    else: raise AssertionError("expected ValueError")

def test_rejects_non_draft_remote_response():
    try: deliver_wordpress_draft(delivery=delivery(),connection=connection(),transport=lambda *_: Response({"id":123,"status":"publish"}))
    except RuntimeError as exc: assert "immutable draft" in str(exc)
    else: raise AssertionError("expected RuntimeError")

def test_missing_post_id_is_rejected():
    try: deliver_wordpress_draft(delivery=delivery(),connection=connection(),transport=lambda *_: Response({"status":"draft"}))
    except RuntimeError as exc: assert "post id" in str(exc)
    else: raise AssertionError("expected RuntimeError")

def test_no_credentials_in_error_contract():
    try: deliver_wordpress_draft(delivery=delivery(),connection=None,transport=None)
    except ValueError as exc:
        text=str(exc); assert "app-password" in text and "editor" not in text
