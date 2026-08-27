from __future__ import annotations

import argparse
import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
RESEARCH_ROOT = ROOT / "research"
if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))

from agents.research.content_research_pipeline import run_content_research_to_wordpress_draft

JOBS: dict[str, dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()
PROJECT_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,79}$")
PROVIDERS = ("dataforseo", "mock")
GATES = (
    ("research_sufficiency", "Research Sufficiency"),
    ("article_draft_quality", "Article Draft Quality"),
    ("claim_audit", "Claim Audit"),
    ("seo_strategy", "SEO Strategy"),
    ("seo_validation", "SEO Validation"),
    ("editorial_review", "Editorial Review"),
    ("publication", "Publication Gate"),
    ("publisher", "Publisher"),
    ("wordpress_draft_delivery", "WordPress Draft"),
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def active_provider() -> str:
    value = os.getenv("IRL_RESEARCH_PROVIDER", "dataforseo").strip().lower()
    return value if value in PROVIDERS else "dataforseo"


def provider_status() -> dict[str, Any]:
    login_set = bool(os.getenv("DATAFORSEO_LOGIN", "").strip())
    password_set = bool(os.getenv("DATAFORSEO_PASSWORD", "").strip())
    return {
        "active": active_provider(),
        "options": list(PROVIDERS),
        "dataforseo": {
            "configured": login_set and password_set,
            "login_configured": login_set,
            "password_configured": password_set,
            "base_url": os.getenv("DATAFORSEO_BASE_URL", "https://api.dataforseo.com").strip().rstrip("/"),
        },
        "mock": {"configured": True},
    }


def project_info(project: str) -> dict[str, Any]:
    root = RESEARCH_ROOT / project
    metadata = load_json(root / "metadata.json") if (root / "metadata.json").exists() else {}
    keyword = load_json(root / "keyword.json") if (root / "keyword.json").exists() else {}
    return {"project": project, "keyword": keyword.get("keyword", ""), "language": keyword.get("language", ""), "country": keyword.get("country", ""), "status": metadata.get("status", "")}


def list_projects() -> list[dict[str, Any]]:
    if not RESEARCH_ROOT.exists():
        return []
    return [project_info(p.name) for p in sorted(RESEARCH_ROOT.iterdir()) if p.is_dir() and (p / "keyword.json").exists()]


def create_or_validate_project(project: str, keyword: str, language: str, country: str) -> None:
    if not PROJECT_RE.fullmatch(project):
        raise ValueError("Project name must use lowercase letters, numbers, and hyphens (2-80 chars).")
    if not keyword.strip():
        raise ValueError("Keyword is required.")
    if not language.strip() or not country.strip():
        raise ValueError("Language and country are required.")
    root = RESEARCH_ROOT / project
    root.mkdir(parents=True, exist_ok=True)
    keyword_path = root / "keyword.json"
    metadata_path = root / "metadata.json"
    if keyword_path.exists():
        existing = load_json(keyword_path)
        if str(existing.get("keyword", "")).strip().lower() != keyword.strip().lower():
            raise ValueError("This project already exists with a different keyword.")
        return
    keyword_path.write_text(json.dumps({"keyword": keyword.strip(), "search_volume": 0, "difficulty": 0, "cpc": 0, "trend": [], "language": language.strip(), "country": country.strip()}, indent=4, ensure_ascii=False), encoding="utf-8")
    metadata_path.write_text(json.dumps({"id": "", "keyword": keyword.strip(), "language": language.strip(), "country": country.strip(), "created_at": now(), "updated_at": now(), "version": "1.0", "status": "created", "project_name": project}, indent=4, ensure_ascii=False), encoding="utf-8")


def gate_status(artifact: Any) -> str:
    if not isinstance(artifact, dict):
        return "pending"
    return str(artifact.get("outcome") or artifact.get("gate_status") or artifact.get("lifecycle_stage") or "ready")


def public_result(result: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {"gates": {}}
    for key, _label in GATES:
        output["gates"][key] = gate_status(result.get(key))
    live = result.get("wordpress_draft_delivery_result")
    if isinstance(live, dict):
        output["live"] = {"post_id": live.get("post_id"), "status": live.get("status"), "edit_url": live.get("edit_url")}
    return output


def run_job(job_id: str, project: str, deliver: bool, provider: str) -> None:
    with JOBS_LOCK:
        JOBS[job_id].update(status="running", started_at=now())
    try:
        result = run_content_research_to_wordpress_draft(project, deliver=deliver, provider=provider)
        live = result.get("wordpress_draft_delivery_result")
        with JOBS_LOCK:
            JOBS[job_id].update(status="completed", finished_at=now(), result=public_result(result), post_id=live.get("post_id") if isinstance(live, dict) else None, provider=provider, error=None)
    except Exception as exc:
        with JOBS_LOCK:
            JOBS[job_id].update(status="failed", finished_at=now(), provider=provider, error=str(exc))


HTML = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>IRL AI Core</title>
<style>
:root{--navy:#0f172a;--blue:#2563eb;--bg:#f8fafc;--line:#e2e8f0;--muted:#64748b;--ok:#15803d;--bad:#b91c1c;--amber:#b45309}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--navy);font:14px/1.5 Inter,system-ui,-apple-system,Segoe UI,sans-serif}.app{display:grid;grid-template-columns:250px 1fr;min-height:100vh}.side{background:#fff;border-right:1px solid var(--line);padding:22px 16px}.brand{font-weight:800;font-size:18px;margin-bottom:24px}.brand span{color:var(--blue)}.nav{display:grid;gap:6px}.nav button{border:0;background:transparent;text-align:left;padding:10px 12px;border-radius:9px;color:#334155;cursor:pointer}.nav button.active,.nav button:hover{background:#eff6ff;color:var(--blue)}.main{max-width:1180px;width:100%;margin:auto;padding:32px}.top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:24px}.eyebrow{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--blue);font-weight:700}.title{font-size:30px;font-weight:800;margin:5px 0}.sub{color:var(--muted)}.grid{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(320px,.9fr);gap:18px}.card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:20px;box-shadow:0 3px 12px #0f172a08}.card h2{font-size:16px;margin:0 0 16px}.form{display:grid;gap:13px}.row{display:grid;grid-template-columns:1fr 1fr;gap:12px}label{font-weight:650;font-size:13px}input,select{width:100%;margin-top:6px;border:1px solid #cbd5e1;border-radius:9px;padding:11px;background:#fff;color:var(--navy);outline:none}input:focus,select:focus{border-color:var(--blue);box-shadow:0 0 0 3px #2563eb18}.actions{display:flex;gap:10px;align-items:center;margin-top:4px}.primary{border:0;border-radius:9px;background:var(--blue);color:#fff;padding:11px 16px;font-weight:750;cursor:pointer}.primary:disabled{opacity:.55;cursor:wait}.secondary{border:1px solid var(--line);background:#fff;border-radius:9px;padding:10px 14px;cursor:pointer}.mode{display:flex;gap:9px;align-items:flex-start;padding:12px;background:#f8fafc;border:1px solid var(--line);border-radius:9px}.mode input{width:auto;margin:3px 0}.mode strong{display:block}.mode small{color:var(--muted)}.gates{display:grid;gap:8px}.gate{display:flex;justify-content:space-between;align-items:center;border:1px solid var(--line);border-radius:9px;padding:10px 12px}.state{font-size:12px;font-weight:750}.ok{color:var(--ok)}.pending{color:var(--muted)}.bad{color:var(--bad)}.amber{color:var(--amber)}.project{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--line)}.project:last-child{border-bottom:0}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}.live{margin-top:15px;padding:14px;border-radius:10px;background:#f0fdf4;border:1px solid #bbf7d0}.live a{color:var(--blue);font-weight:700}.notice{padding:11px 13px;border-radius:9px;background:#eff6ff;color:#1e3a8a;margin-bottom:14px}.error{background:#fef2f2;color:var(--bad)}.provider{display:grid;grid-template-columns:1fr auto;gap:12px;align-items:center}.badge{padding:5px 9px;border-radius:999px;font-size:11px;font-weight:750}.badge.ok{background:#f0fdf4}.badge.bad{background:#fef2f2}.provider-note{margin-top:8px;color:var(--muted);font-size:12px}.secret{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}@media(max-width:850px){.app{grid-template-columns:1fr}.side{display:none}.main{padding:18px}.grid{grid-template-columns:1fr}.row{grid-template-columns:1fr}.provider{grid-template-columns:1fr}}
</style></head><body><div class="app"><aside class="side"><div class="brand">IRL <span>AI CORE</span></div><div class="nav"><button class="active">New Project</button><button onclick="loadProjects()">Projects</button></div><div style="margin-top:28px;color:#94a3b8;font-size:11px">Production operator console</div></aside><main class="main"><div class="top"><div><div class="eyebrow">Insurance Review Lab</div><div class="title">Content Production</div><div class="sub">Run the research-to-WordPress workflow from one screen.</div></div><div class="mono" id="health">● ready</div></div><div id="notice"></div>
<section class="card" style="margin-bottom:18px"><h2>Research Provider</h2><div class="provider"><div><label>Provider used for keyword metrics + SERP</label><select id="provider"><option value="dataforseo">DataForSEO — LIVE research</option><option value="mock">Mock — testing only</option></select><div class="provider-note" id="providerNote">Credentials are read only from the production environment; they are never stored in the UI or project files.</div></div><span class="badge" id="providerBadge">Checking…</span></div></section>
<div class="grid"><section class="card"><h2>New Content Project</h2><form id="runForm" class="form"><div><label>Project name</label><input id="project" required pattern="[a-z0-9][a-z0-9-]{1,79}" placeholder="e.g. nurse-insurance"></div><div><label>Primary keyword</label><input id="keyword" required placeholder="e.g. nurse malpractice insurance"></div><div class="row"><div><label>Language</label><select id="language"><option value="en">English</option></select></div><div><label>Country</label><select id="country"><option value="US">United States</option></select></div></div><div class="mode"><input id="deliver" type="checkbox" checked><div><strong>LIVE WordPress Draft</strong><small>Runs the production path. WordPress delivery is restricted to status=draft; this UI has no publish action.</small></div></div><div class="actions"><button class="primary" id="run" type="submit">Run Project</button><button class="secondary" type="button" onclick="loadProjects()">Refresh</button></div></form></section><section class="card"><h2>Pipeline Status</h2><div class="gates" id="gates">Start a project to see its gates.</div><div id="live"></div></section></div><section class="card" style="margin-top:18px"><h2>Existing Projects</h2><div id="projects">Loading…</div></section></main></div>
<script>
const labels={research_sufficiency:'Research Sufficiency',article_draft_quality:'Article Draft Quality',claim_audit:'Claim Audit',seo_strategy:'SEO Strategy',seo_validation:'SEO Validation',editorial_review:'Editorial Review',publication:'Publication Gate',publisher:'Publisher',wordpress_draft_delivery:'WordPress Draft'};
function cls(s){if(['passed','approved','allowed','publisher_ready','wordpress_draft_ready','research_complete','present'].includes(s))return'ok';if(['failed','blocked','needs_revision','insufficient'].includes(s))return'bad';return'pending'}
function renderGates(g){document.getElementById('gates').innerHTML=Object.entries(labels).map(([k,l])=>`<div class="gate"><span>${l}</span><span class="state ${cls(g?.[k])}">${g?.[k]||'pending'}</span></div>`).join('')}
function showNotice(text,bad=false){const n=document.getElementById('notice');n.className=bad?'notice error':'notice';n.textContent=text}
async function loadProviders(){const r=await fetch('/api/providers');const p=await r.json();document.getElementById('provider').value=p.active;const badge=document.getElementById('providerBadge');const configured=p.dataforseo.configured;badge.textContent=p.active==='dataforseo'?(configured?'DataForSEO connected':'DataForSEO not configured'):'Mock active';badge.className='badge '+(p.active==='dataforseo'&& !configured?'bad':'ok');document.getElementById('providerNote').textContent=p.active==='dataforseo'&&!configured?'DataForSEO is selected but DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD are missing in this production shell. Set them as environment variables, then restart the UI.':'Credentials are read from environment variables only; they are never displayed or stored by the UI.'}
async function loadProjects(){const r=await fetch('/api/projects');const data=await r.json();document.getElementById('projects').innerHTML=data.projects.length?data.projects.map(p=>`<div class="project"><div><strong>${p.project}</strong><div class="sub">${p.keyword}</div></div><span class="mono">${p.status||'ready'}</span></div>`).join(''):'No projects yet.'}
async function pollJob(id){const r=await fetch('/api/jobs/'+id);const j=await r.json();if(j.status==='running'||j.status==='queued'){showNotice(`Pipeline is running with ${j.provider}…`);return setTimeout(()=>pollJob(id),1000)}if(j.status==='failed'){showNotice(j.error||'Pipeline failed.',true);document.getElementById('run').disabled=false;return}showNotice(`Pipeline completed using ${j.provider}.`);renderGates(j.result?.gates||{});if(j.result?.live){document.getElementById('live').innerHTML=`<div class="live"><strong>LIVE WordPress Draft</strong><br>Post ID: <span class="mono">${j.result.live.post_id}</span><br>Status: <strong>${j.result.live.status}</strong><br>${j.result.live.edit_url?`<a href="${j.result.live.edit_url}" target="_blank" rel="noopener">Open Draft</a>`:''}</div>`}document.getElementById('run').disabled=false;loadProjects()}
document.getElementById('runForm').addEventListener('submit',async e=>{e.preventDefault();document.getElementById('run').disabled=true;document.getElementById('live').innerHTML='';renderGates({});const provider=document.getElementById('provider').value;const p=await fetch('/api/providers').then(r=>r.json());if(provider==='dataforseo'&&!p.dataforseo.configured){showNotice('DataForSEO is selected but credentials are not configured in the production environment.',true);document.getElementById('run').disabled=false;return}showNotice('Starting pipeline…');const payload={project:document.getElementById('project').value.trim(),keyword:document.getElementById('keyword').value.trim(),language:document.getElementById('language').value,country:document.getElementById('country').value,deliver:document.getElementById('deliver').checked,provider};const r=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const j=await r.json();if(!r.ok){showNotice(j.error||'Could not start project.',true);document.getElementById('run').disabled=false;return}pollJob(j.job_id)});loadProviders();loadProjects();
</script></body></html>'''


class Handler(BaseHTTPRequestHandler):
    server_version = "IRLAICoreUI/1.1"

    def _send(self, status: int, payload: Any, content_type: str = "application/json") -> None:
        body = payload if isinstance(payload, bytes) else (json.dumps(payload, ensure_ascii=False).encode("utf-8") if content_type == "application/json" else str(payload).encode("utf-8"))
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, HTML, "text/html")
            return
        if path == "/api/projects":
            self._send(200, {"projects": list_projects()})
            return
        if path == "/api/providers":
            self._send(200, provider_status())
            return
        if path.startswith("/api/jobs/"):
            job_id = path.rsplit("/", 1)[-1]
            with JOBS_LOCK:
                job = dict(JOBS.get(job_id, {}))
            if not job:
                self._send(404, {"error": "Job not found"})
            else:
                self._send(200, job)
            return
        self._send(404, {"error": "Not found"})

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/run":
            self._send(404, {"error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 20_000:
                raise ValueError("Request too large")
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            project = str(data.get("project", "")).strip()
            keyword = str(data.get("keyword", "")).strip()
            language = str(data.get("language", "en")).strip()
            country = str(data.get("country", "US")).strip()
            deliver = bool(data.get("deliver", True))
            provider = str(data.get("provider", active_provider())).strip().lower()
            if provider not in PROVIDERS:
                raise ValueError(f"Unsupported provider: {provider}")
            if provider == "dataforseo" and not provider_status()["dataforseo"]["configured"]:
                raise ValueError("DataForSEO credentials are not configured in the production environment.")
            create_or_validate_project(project, keyword, language, country)
            job_id = uuid.uuid4().hex[:16]
            with JOBS_LOCK:
                JOBS[job_id] = {"job_id": job_id, "project": project, "status": "queued", "created_at": now(), "deliver": deliver, "provider": provider}
            threading.Thread(target=run_job, args=(job_id, project, deliver, provider), daemon=True).start()
            self._send(202, {"job_id": job_id, "status": "queued", "provider": provider})
        except Exception as exc:
            self._send(400, {"error": str(exc)})

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[IRL AI CORE UI] {self.address_string()} - {fmt % args}")


def main() -> int:
    parser = argparse.ArgumentParser(description="IRL AI Core operator web UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"IRL AI Core UI: http://{args.host}:{args.port}")
    print("LIVE mode creates WordPress drafts only; publish is not supported by this UI.")
    print(f"Research provider: {active_provider()}")
    print(f"DataForSEO configured: {provider_status()['dataforseo']['configured']}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
