from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
RESEARCH_ROOT = ROOT / "research"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.research.article_configuration import build_article_config
from agents.research.semantic_seo import build_semantic_seo

ARTIFACTS = {
    "Research Report": "research-report.json",
    "Decision": "decision.json",
    "Content Brief": "content-brief.json",
    "Content Strategy": "content-strategy.json",
    "Article Configuration": None,
    "Semantic SEO": None,
    "Article Structure": None,
    "SERP Analysis": None,
    "Article Draft": "article-draft.json",
    "SEO Validation": "seo-validation.json",
    "Publication": "publication.json",
}


def _load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _find_artifact(project: str, filename: str) -> Path | None:
    path = RESEARCH_ROOT / project / filename
    return path if path.is_file() else None


def _materialized(project: str, label: str) -> dict[str, object] | None:
    filename = ARTIFACTS.get(label)
    if not filename:
        return None
    path = _find_artifact(project, filename)
    if not path:
        return None
    return {
        "name": label,
        "status": "available",
        "source": "materialized_artifact",
        "filename": filename,
        "data": _load_json(path),
    }


def _computed_contract(project: str, label: str) -> dict[str, object]:
    """Resolve a contract through its real Core builder without persisting it."""
    brief_path = _find_artifact(project, "content-brief.json")
    strategy_path = _find_artifact(project, "content-strategy.json")
    if label == "Article Configuration":
        if not brief_path:
            return {"name": label, "status": "blocked", "source": "core_contract", "reason": "content-brief.json is required"}
        brief = _load_json(brief_path)
        report_path = _find_artifact(project, "research-report.json")
        report = _load_json(report_path) if report_path else {}
        metadata = report.get("metadata", {}) if isinstance(report, dict) else {}
        country = metadata.get("country") if isinstance(metadata, dict) else None
        if not isinstance(country, str) or not country.strip():
            return {
                "name": label,
                "status": "blocked",
                "source": "core_contract",
                "reason": "Article Config requires an explicit target_country; no country is present in the current upstream artifacts",
            }
        try:
            data = build_article_config(content_brief=brief, target_country=country)
        except (TypeError, ValueError) as exc:
            return {"name": label, "status": "blocked", "source": "core_contract", "reason": str(exc)}
        return {"name": label, "status": "computed", "source": "core_contract", "data": data}

    if label == "Semantic SEO":
        if not strategy_path:
            return {"name": label, "status": "blocked", "source": "core_contract", "reason": "content-strategy.json is required"}
        strategy = _load_json(strategy_path)
        try:
            data = build_semantic_seo(content_strategy=strategy)
        except (TypeError, ValueError) as exc:
            return {"name": label, "status": "blocked", "source": "core_contract", "reason": str(exc)}
        return {"name": label, "status": "computed", "source": "core_contract", "data": data}

    if label == "Article Structure":
        return {
            "name": label,
            "status": "blocked",
            "source": "core_contract",
            "reason": "The Article Structure builder requires an explicit structure policy; no such policy is materialized upstream",
        }

    if label == "SERP Analysis":
        return {
            "name": label,
            "status": "blocked",
            "source": "core_contract",
            "reason": "SERP Analysis requires an injected SERP provider and an article_config_ready contract; the read-only Preview does not create providers or network access",
        }

    raise KeyError(label)


def _project_payload(project: str) -> dict[str, object]:
    project_dir = RESEARCH_ROOT / project
    if not project_dir.is_dir():
        raise FileNotFoundError(project)

    items: list[dict[str, object]] = []
    for label in ARTIFACTS:
        item = _materialized(project, label)
        if item is None and label in {"Article Configuration", "Semantic SEO", "Article Structure", "SERP Analysis"}:
            item = _computed_contract(project, label)
        if item is None:
            item = {"name": label, "status": "not_available", "source": "materialized_artifact", "filename": ARTIFACTS[label]}
        items.append(item)

    return {
        "project": project,
        "artifact_count": sum(item["status"] in {"available", "computed"} for item in items),
        "artifacts": items,
    }


HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>IRL AI Core — Live Preview</title>
<style>
:root{font-family:Inter,ui-sans-serif,system-ui,sans-serif;color:#0f172a;background:#f8fafc}
*{box-sizing:border-box}body{margin:0}.app{display:grid;grid-template-columns:290px 1fr;min-height:100vh}
aside{background:#0f172a;color:#fff;padding:24px;position:sticky;top:0;height:100vh}.brand{font-size:20px;font-weight:750}.sub{font-size:12px;opacity:.65;margin:6px 0 24px}
button{display:block;width:100%;text-align:left;border:0;border-radius:8px;background:transparent;color:#e2e8f0;padding:10px 12px;margin:3px 0;cursor:pointer}button:hover,button.active{background:#1e293b;color:#fff}
main{padding:32px;max-width:1200px;width:100%;margin:auto}.top{display:flex;justify-content:space-between;gap:16px;align-items:flex-start}.eyebrow{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#64748b}.title{font-size:32px;margin:5px 0}.badge{background:#dcfce7;color:#166534;padding:6px 10px;border-radius:999px;font-size:12px;font-weight:650}
.pipeline{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:28px 0}.node{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px}.node b{display:block;font-size:13px}.ok{color:#15803d;font-size:12px;margin-top:7px}.computed{color:#1d4ed8;font-size:12px;margin-top:7px}.blocked{color:#b45309;font-size:12px;margin-top:7px}.pending{color:#64748b;font-size:12px;margin-top:7px}
.panel{background:#fff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden}.panel-head{padding:16px 18px;border-bottom:1px solid #e2e8f0;font-weight:700;display:flex;justify-content:space-between;gap:16px}.json{margin:0;padding:20px;overflow:auto;max-height:65vh;background:#f8fafc;font:12px/1.6 ui-monospace,SFMono-Regular,monospace;white-space:pre-wrap}.meta{font-size:12px;color:#64748b}.reason{margin:0 20px 20px;padding:12px;border-left:3px solid #f59e0b;background:#fffbeb;color:#78350f;font-size:13px;line-height:1.5}
@media(max-width:760px){.app{grid-template-columns:1fr}aside{position:relative;height:auto}.top{display:block}}
</style>
</head>
<body>
<div class="app"><aside><div class="brand">IRL AI Core</div><div class="sub">Live Preview MVP · read-only</div><div id="nav"></div></aside>
<main><div class="top"><div><div class="eyebrow">Live Preview</div><h1 class="title" id="projectTitle">Loading…</h1><div class="meta" id="summary"></div></div><div class="badge">READ ONLY</div></div>
<div class="pipeline" id="pipeline"></div><section class="panel"><div class="panel-head"><span id="panelTitle">Artifact</span><span class="meta" id="filename"></span></div><div id="reason"></div><pre class="json" id="json">Loading…</pre></section></main></div>
<script>
const stages=['Research Report','Decision','Content Brief','Content Strategy','Article Configuration','Semantic SEO','Article Structure','SERP Analysis','Article Draft','SEO Validation','Publication'];
let state;
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
async function init(){const r=await fetch('/api/project/expat-health-insurance');if(!r.ok)throw Error(await r.text());state=await r.json();document.querySelector('#projectTitle').textContent=state.project;document.querySelector('#summary').textContent=`${state.artifact_count} stages available or computed from current contracts`;render();select(stages[0])}
function statusText(a){if(a?.status==='available')return '✓ Available';if(a?.status==='computed')return '⚡ Computed from Core contract';if(a?.status==='blocked')return '△ Blocked by contract input';return '○ Not available'}
function render(){const map=new Map(state.artifacts.map(x=>[x.name,x]));document.querySelector('#pipeline').innerHTML=stages.map(x=>{const a=map.get(x);const cls=a?.status||'pending';return `<div class="node"><b>${esc(x)}</b><div class="${cls}">${statusText(a)}</div></div>`}).join('');document.querySelector('#nav').innerHTML=stages.map(x=>`<button data-stage="${esc(x)}">${esc(x)}</button>`).join('');document.querySelectorAll('#nav button').forEach(b=>b.onclick=()=>select(b.dataset.stage))}
function select(name){const a=state.artifacts.find(x=>x.name===name);document.querySelectorAll('#nav button').forEach(b=>b.classList.toggle('active',b.dataset.stage===name));document.querySelector('#panelTitle').textContent=name;document.querySelector('#filename').textContent=a?.filename||'';const reason=document.querySelector('#reason');reason.innerHTML=a?.reason?`<div class="reason"><strong>Why this stage is blocked:</strong> ${esc(a.reason)}</div>`:'';document.querySelector('#json').textContent=a?.data?JSON.stringify(a.data,null,2):'No contract output is available for this stage yet.'}
init().catch(e=>document.querySelector('#json').textContent=e.message);
</script></body></html>"""


class PreviewHandler(BaseHTTPRequestHandler):
    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send(200, "text/html; charset=utf-8", HTML.encode("utf-8"))
            return
        if parsed.path == "/api/project/expat-health-insurance":
            try:
                payload = _project_payload("expat-health-insurance")
            except FileNotFoundError:
                self._send(404, "text/plain; charset=utf-8", b"Project not found")
                return
            self._send(200, "application/json; charset=utf-8", json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8"))
            return
        self._send(404, "text/plain; charset=utf-8", b"Not found")

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only IRL AI Core live preview")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), PreviewHandler)
    print(f"IRL AI Core Live Preview: http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
