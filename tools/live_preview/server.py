from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
RESEARCH_ROOT = ROOT / "research"

ARTIFACTS = {
    "Research Report": "research-report.json",
    "Decision": "decision.json",
    "Content Strategy": "content-strategy.json",
    "Article Configuration": None,
    "Semantic SEO": None,
    "Article Structure": None,
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


def _project_payload(project: str) -> dict[str, object]:
    project_dir = RESEARCH_ROOT / project
    if not project_dir.is_dir():
        raise FileNotFoundError(project)

    items: list[dict[str, object]] = []
    for label, filename in ARTIFACTS.items():
        path = _find_artifact(project, filename) if filename else None
        items.append(
            {
                "name": label,
                "status": "available" if path else "not_available",
                "filename": filename,
                "data": _load_json(path) if path else None,
            }
        )

    return {
        "project": project,
        "artifact_count": sum(item["status"] == "available" for item in items),
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
.pipeline{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:28px 0}.node{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px}.node b{display:block;font-size:13px}.ok{color:#15803d;font-size:12px;margin-top:7px}.pending{color:#64748b;font-size:12px;margin-top:7px}
.panel{background:#fff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden}.panel-head{padding:16px 18px;border-bottom:1px solid #e2e8f0;font-weight:700;display:flex;justify-content:space-between}.json{margin:0;padding:20px;overflow:auto;max-height:65vh;background:#f8fafc;font:12px/1.6 ui-monospace,SFMono-Regular,monospace;white-space:pre-wrap}.meta{font-size:12px;color:#64748b}
@media(max-width:760px){.app{grid-template-columns:1fr}aside{position:relative;height:auto}.top{display:block}}
</style>
</head>
<body>
<div class="app"><aside><div class="brand">IRL AI Core</div><div class="sub">Live Preview MVP · read-only</div><div id="nav"></div></aside>
<main><div class="top"><div><div class="eyebrow">Live Preview</div><h1 class="title" id="projectTitle">Loading…</h1><div class="meta" id="summary"></div></div><div class="badge">READ ONLY</div></div>
<div class="pipeline" id="pipeline"></div><section class="panel"><div class="panel-head"><span id="panelTitle">Artifact</span><span class="meta" id="filename"></span></div><pre class="json" id="json">Loading…</pre></section></main></div>
<script>
const stages=['Research Report','Decision','Content Strategy','Article Configuration','Semantic SEO','Article Structure','Article Draft','SEO Validation','Publication'];
let state;
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
async function init(){const r=await fetch('/api/project/expat-health-insurance');if(!r.ok)throw Error(await r.text());state=await r.json();document.querySelector('#projectTitle').textContent=state.project;document.querySelector('#summary').textContent=`${state.artifact_count} artifacts available in research/${state.project}/`;render();select(stages[0])}
function render(){const map=new Map(state.artifacts.map(x=>[x.name,x]));document.querySelector('#pipeline').innerHTML=stages.map(x=>{const a=map.get(x);return `<div class="node"><b>${esc(x)}</b><div class="${a?.status==='available'?'ok':'pending'}">${a?.status==='available'?'✓ Available':'○ Not materialized'}</div></div>`}).join('');document.querySelector('#nav').innerHTML=stages.map(x=>`<button data-stage="${esc(x)}">${esc(x)}</button>`).join('');document.querySelectorAll('#nav button').forEach(b=>b.onclick=()=>select(b.dataset.stage))}
function select(name){const a=state.artifacts.find(x=>x.name===name);document.querySelectorAll('#nav button').forEach(b=>b.classList.toggle('active',b.dataset.stage===name));document.querySelector('#panelTitle').textContent=name;document.querySelector('#filename').textContent=a?.filename||'';document.querySelector('#json').textContent=a?.data?JSON.stringify(a.data,null,2):'No artifact is materialized for this stage yet.'}
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
            self._send(200, "application/json; charset=utf-8", json.dumps(payload, indent=2).encode("utf-8"))
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
