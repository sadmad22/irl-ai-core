from __future__ import annotations

import argparse
import json
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.research.dataforseo_account import fetch_account, pricing_summary
from agents.research.dataforseo_cost import load_project_cost
from agents.research.provider_config import (
    load_saved_environment,
    save_dataforseo_credentials,
    save_wordpress_credentials,
    wordpress_configuration_status,
)
from agents.research.wordpress_config import verify_wordpress_credentials
from scripts import web_ui

load_saved_environment()

CSS = """
:root{--n:#0f172a;--b:#2563eb;--bg:#f8fafc;--l:#e2e8f0;--m:#64748b;--ok:#15803d;--bad:#b91c1c}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--n);font:14px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
.app{display:grid;grid-template-columns:240px 1fr;min-height:100vh}.side{background:#fff;border-right:1px solid var(--l);padding:22px 16px}.brand{font-weight:850;font-size:18px;margin-bottom:28px}.brand span{color:var(--b)}
.nav{display:grid;gap:6px}.nav a{padding:11px 12px;border-radius:9px;color:#334155;text-decoration:none;font-weight:650}.nav a.active,.nav a:hover{background:#eff6ff;color:var(--b)}
.main{max-width:1280px;width:100%;margin:auto;padding:30px}.ey{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--b);font-weight:800}.title{font-size:30px;font-weight:850;margin:4px 0}.sub{color:var(--m)}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:22px 0}.card{background:#fff;border:1px solid var(--l);border-radius:14px;padding:18px;box-shadow:0 3px 12px #0f172a08}.num{font-size:28px;font-weight:850}.muted{color:var(--m);font-size:12px}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:10px 8px;border-bottom:1px solid var(--l)}th{font-size:11px;text-transform:uppercase;color:var(--m)}
.badge{display:inline-block;padding:5px 9px;border-radius:999px;font-size:11px;font-weight:750;background:#f1f5f9}.ok{background:#f0fdf4;color:var(--ok)}.bad{background:#fef2f2;color:var(--bad)}
.monitor-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:14px 0}.metric{border:1px solid var(--l);border-radius:10px;padding:13px}.metric strong{display:block;font-size:21px}.toolbar{display:flex;justify-content:space-between;gap:12px;align-items:center}.button{border:1px solid var(--l);background:#fff;border-radius:8px;padding:8px 11px;cursor:pointer;font-weight:650}.scroll{overflow:auto;max-height:360px}
.provider-actions{display:flex;gap:8px;align-items:center}.link-button{display:inline-block;border:1px solid var(--l);background:#fff;border-radius:8px;padding:8px 11px;color:var(--b);text-decoration:none;font-weight:650}.form{display:grid;gap:14px;max-width:720px}.form label{font-weight:700;font-size:13px}.form input{width:100%;margin-top:6px;border:1px solid #cbd5e1;border-radius:9px;padding:11px;background:#fff;color:var(--n)}.notice{padding:11px 13px;border-radius:9px;background:#eff6ff;color:#1e3a8a}.error{background:#fef2f2;color:var(--bad)}
iframe{width:100%;height:calc(100vh - 170px);min-height:680px;border:1px solid var(--l);border-radius:14px;background:#fff;margin-top:18px}
@media(max-width:850px){.app{grid-template-columns:1fr}.cards,.monitor-grid{grid-template-columns:1fr 1fr}.side{border-right:0;border-bottom:1px solid var(--l)}}
"""


def page(title: str, subtitle: str, active: str, body: str) -> str:
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>{CSS}</style></head><body><div class="app"><aside class="side"><div class="brand">IRL <span>AI CORE</span></div><nav class="nav"><a class="{'active' if active == 'operations' else ''}" href="/">Operations</a><a class="{'active' if active == 'production' else ''}" href="/production">Content Production</a></nav><p class="muted" style="margin-top:28px">LIVE creates WordPress drafts only.<br>Publish is intentionally unavailable.</p></aside><main class="main"><div class="ey">Insurance Review Lab</div><div class="title">{title}</div><div class="sub">{subtitle}</div>{body}</main></div></body></html>'''

OPERATIONS_HTML = page(
    "IRL AI Core Operations",
    "Control center for projects, pipeline activity, providers, costs, and WordPress draft delivery.",
    "operations",
    '''
<div class="cards" id="cards"></div>
<section class="card"><div class="toolbar"><div><h3 style="margin:0">Provider Control</h3><div class="muted">Runtime research provider and account health.</div></div><div class="provider-actions"><a class="link-button" href="/provider">Configure Provider</a><button class="button" id="refreshCost" type="button">Refresh DataForSEO</button></div></div><div id="provider" style="margin-top:14px"></div></section>
<section class="card" style="margin-top:18px"><div class="toolbar"><div><h3 style="margin:0">DataForSEO Account &amp; Cost Monitor</h3><div class="muted">Live balance, current spending, API pricing, and measured per-article cost.</div></div><a class="link-button" href="/provider">Manage DataForSEO</a></div><div class="monitor-grid" id="costMetrics"></div><div id="costError"></div><div class="scroll" id="pricingTable"></div></section>
<section class="card" style="margin-top:18px"><h3>Projects</h3><div id="projectsTable"></div></section>
<section class="card" style="margin-top:18px"><h3>WordPress Drafts</h3><div id="draftsTable"></div></section>
<script>
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=v=>v===null||v===undefined?'—':`$${Number(v).toFixed(4)}`;
function renderCost(a,projects){const metrics=document.getElementById('costMetrics'),error=document.getElementById('costError'),table=document.getElementById('pricingTable');if(!a.configured){metrics.innerHTML='';table.innerHTML='';error.innerHTML='<div class="notice error">DataForSEO is not configured. <a href="/provider">Configure provider credentials</a>.</div>';return}if(a.error){metrics.innerHTML='';table.innerHTML='';error.innerHTML=`<div class="notice error">${esc(a.error)}. <a href="/provider">Manage provider credentials</a>.</div>`;return}const exact=projects.filter(x=>x.dataforseo_cost&&x.dataforseo_cost.exact);const latest=exact.length?exact[0].dataforseo_cost:null;metrics.innerHTML=[['Balance',money(a.balance),'live account balance'],['Today spend',money(a.today_spend),'DataForSEO current-day spend'],['Latest article cost',latest?money(latest.cost):'—',latest?'measured from account balance delta':'no exact project cost yet'],['Measured articles',exact.length,exact.length?'projects with exact cost records':'no exact project cost records']].map(x=>`<div class="metric"><div class="muted">${x[2]}</div><strong>${x[1]}</strong><span class="muted">${x[0]}</span></div>`).join('');error.innerHTML=latest?`<div class="muted" style="margin:8px 0">Latest exact cost: ${money(latest.cost)} for ${esc(exact[0].project)}. Measurement uses the DataForSEO account-balance delta captured around that production run.</div>`:'<div class="muted" style="margin:8px 0">Exact project cost appears after a DataForSEO production run with successful before/after account-balance snapshots.</div>';const rows=(a.pricing||[]).slice(0,30);table.innerHTML=rows.length?`<table><tr><th>API</th><th>Function</th><th>Charge</th><th>Cost</th></tr>${rows.map(x=>`<tr><td>${esc(x.api)}</td><td>${esc(x.function)}</td><td>${esc(x.cost_type)}</td><td>${money(x.cost)}</td></tr>`).join('')}</table>`:'<div class="muted">No pricing records returned.</div>'}
async function load(){const r=await fetch('/api/dashboard');const d=await r.json();const m=d.metrics,p=d.provider;document.getElementById('cards').innerHTML=[['Projects',m.projects,'initialized'],['WordPress Drafts',m.drafts,'delivered + still draft'],['Draft Ready',m.draft_ready,'ready before delivery'],['Exact Cost Records',m.exact_cost_records,'measured DataForSEO project costs']].map(x=>`<div class="card"><div class="muted">${x[2]}</div><div class="num">${x[1]}</div><strong>${x[0]}</strong></div>`).join('');document.getElementById('provider').innerHTML=`<span class="badge ok">${esc(p.active)}</span> <strong>${p.dataforseo.configured?'DataForSEO connected':'DataForSEO not configured'}</strong><div class="muted" style="margin-top:8px">WordPress: ${d.wordpress.configured?'connected':'not configured'}. Credentials are stored locally with restrictive permissions and are never returned to the browser.</div>`;renderCost(d.dataforseo,d.recent_projects);document.getElementById('projectsTable').innerHTML=d.recent_projects.length?`<table><tr><th>Project</th><th>Status</th><th>Draft</th><th>Article Cost</th></tr>${d.recent_projects.map(x=>`<tr><td><strong>${esc(x.project)}</strong><div class="muted">${esc(x.keyword)}</div></td><td>${esc(x.status||'created')}</td><td>${x.post_id?'#'+esc(x.post_id):'—'}</td><td>${x.dataforseo_cost&&x.dataforseo_cost.exact?money(x.dataforseo_cost.cost):'—'}</td></tr>`).join('')}</table>`:'<div class="muted">No projects yet.';const drafts=d.recent_projects.filter(x=>x.post_id&&x.remote_status==='draft');document.getElementById('draftsTable').innerHTML=drafts.length?`<table><tr><th>Project</th><th>Post</th><th>Action</th></tr>${drafts.map(x=>`<tr><td>${esc(x.project)}</td><td>#${esc(x.post_id)}</td><td><a href="${esc(x.edit_url)}" target="_blank">Open Draft</a></td></tr>`).join('')}</table>`:'<div class="muted">No WordPress drafts recorded.</div>'}
document.getElementById('refreshCost').addEventListener('click',load);load();setInterval(load,15000);
</script>'''
)

PROVIDER_HTML = page(
    "Provider Control",
    "Configure and verify DataForSEO and WordPress credentials used by IRL AI Core.",
    "operations",
    '''
<section class="card" style="margin-top:22px"><h3>DataForSEO Configuration</h3><p class="muted">Credentials are stored only in the local <span class="mono">.irl-ai-core.env</span> file with restrictive permissions. The dashboard never displays or returns the secret values.</p><div id="status" class="notice">Checking configuration…</div><form id="providerForm" class="form"><div><label>DataForSEO Base URL<input id="base_url" value="https://api.dataforseo.com" autocomplete="url"></label></div><div><label>DataForSEO Login<input id="login" autocomplete="username" placeholder="Enter API login"></label></div><div><label>DataForSEO Password<input id="password" type="password" autocomplete="new-password" placeholder="Enter API password"></label></div><div><button class="button" type="submit">Save &amp; Verify DataForSEO</button></div></form></section>
<section class="card" style="margin-top:18px"><h3>WordPress Configuration</h3><p class="muted">WordPress credentials are stored in the same local <span class="mono">.irl-ai-core.env</span> file with restrictive permissions. The application password is never returned to the browser.</p><div id="wpStatus" class="notice">Checking configuration…</div><form id="wpForm" class="form"><div><label>WordPress Base URL<input id="wp_base_url" placeholder="https://insurancereviewlab.com" autocomplete="url"></label></div><div><label>WordPress Username<input id="wp_username" autocomplete="username" placeholder="Enter WordPress username"></label></div><div><label>WordPress Application Password<input id="wp_password" type="password" autocomplete="new-password" placeholder="Enter application password"></label></div><div><button class="button" type="submit">Save &amp; Verify WordPress</button></div></form></section>
<section class="card" style="margin-top:18px"><h3>Security</h3><div class="muted">The credential file is ignored by Git, written with mode 0600 when supported, and secret values are never included in API responses or dashboard HTML.</div></section>
<script>
const statusEl=document.getElementById('status');const wpStatusEl=document.getElementById('wpStatus');
async function refresh(){const r=await fetch('/api/providers');const p=await r.json();if(p.dataforseo.configured){statusEl.className='notice';statusEl.textContent='DataForSEO credentials are configured.'}else{statusEl.className='notice error';statusEl.textContent='DataForSEO credentials are not configured.'}if(p.wordpress.configured){wpStatusEl.className='notice';wpStatusEl.textContent='WordPress credentials are configured and available to the production pipeline.'}else{wpStatusEl.className='notice error';wpStatusEl.textContent='WordPress credentials are not configured.'}}
document.getElementById('providerForm').addEventListener('submit',async e=>{e.preventDefault();statusEl.className='notice';statusEl.textContent='Saving and verifying…';const payload={base_url:document.getElementById('base_url').value,login:document.getElementById('login').value,password:document.getElementById('password').value};try{const r=await fetch('/api/providers/dataforseo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const data=await r.json();if(!r.ok)throw new Error(data.error||'Unable to save credentials');statusEl.className=data.verified?'notice':'notice error';statusEl.textContent=data.verified?'DataForSEO connected and verified.':'Credentials saved, but verification failed. Check the credentials.';document.getElementById('password').value='';}catch(err){statusEl.className='notice error';statusEl.textContent=err.message}});
document.getElementById('wpForm').addEventListener('submit',async e=>{e.preventDefault();wpStatusEl.className='notice';wpStatusEl.textContent='Saving and verifying…';const payload={base_url:document.getElementById('wp_base_url').value,username:document.getElementById('wp_username').value,application_password:document.getElementById('wp_password').value};try{const r=await fetch('/api/providers/wordpress',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const data=await r.json();if(!r.ok)throw new Error(data.error||'Unable to save WordPress credentials');wpStatusEl.className=data.verified?'notice':'notice error';wpStatusEl.textContent=data.verified?'WordPress connected and verified.':'Credentials were not saved because verification failed.';if(data.verified)document.getElementById('wp_password').value='';}catch(err){wpStatusEl.className='notice error';wpStatusEl.textContent=err.message}});refresh();
</script>'''
)

HTML = PRODUCTION_HTML = page(
    "Content Production",
    "Create and run a new content project through the proven LIVE production workflow.",
    "production",
    '''<section class="card" style="margin-top:22px"><h3>Production Console</h3><div class="muted">New projects run through the live research and quality-gate workflow and deliver to WordPress as Draft only.</div><iframe src="/operator" title="IRL AI Core Content Production Console"></iframe></section>'''
)

class DashboardHandler(web_ui.Handler):
    server_version = "IRLAICoreDashboard/1.5"

    def _send_html(self, text: str) -> None:
        body = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._send_html(OPERATIONS_HTML)
            return
        if path == "/provider":
            self._send_html(PROVIDER_HTML)
            return
        if path == "/production":
            self._send_html(PRODUCTION_HTML)
            return
        if path == "/operator":
            self._send_html(web_ui.HTML)
            return
        if path == "/api/providers":
            load_saved_environment()
            self._send_json({**web_ui.provider_status(), "wordpress": wordpress_configuration_status()})
            return
        if path == "/api/dashboard":
            load_saved_environment()
            projects = web_ui.list_projects()
            enriched = []
            for project in projects:
                item = dict(project)
                item["dataforseo_cost"] = load_project_cost(project["project"])
                enriched.append(item)
            with web_ui.JOBS_LOCK:
                jobs = [dict(job) for job in web_ui.JOBS.values()]
            delivered = [p for p in enriched if p.get("delivery_status") == "delivered" and p.get("remote_status") == "draft"]
            draft_ready = [p for p in enriched if p.get("status") in {"draft_ready", "wordpress_draft_ready"}]
            exact_costs = [p for p in enriched if p.get("dataforseo_cost", {}).get("exact")]
            dataforseo = fetch_account()
            self._send(200, {"provider": web_ui.provider_status(), "wordpress": wordpress_configuration_status(), "dataforseo": dataforseo, "metrics": {"projects": len(enriched), "drafts": len(delivered), "draft_ready": len(draft_ready), "active_jobs": sum(1 for job in jobs if job.get("status") in {"queued", "running"}), "exact_cost_records": len(exact_costs)}, "recent_projects": enriched[:8]})
            return
        super().do_GET()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path not in {"/api/providers/dataforseo", "/api/providers/wordpress"}:
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 16384:
                raise ValueError("Invalid request size")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Invalid request payload")
            if path.endswith("/dataforseo"):
                save_dataforseo_credentials(str(payload.get("login", "")), str(payload.get("password", "")), str(payload.get("base_url", "")))
                account = fetch_account()
                self._send_json({"configured": True, "verified": not bool(account.get("error")), "error": account.get("error")})
                return
            base_url = str(payload.get("base_url", ""))
            username = str(payload.get("username", ""))
            application_password = str(payload.get("application_password", ""))
            verification = verify_wordpress_credentials(base_url, username, application_password)
            if not verification.get("verified"):
                self._send_json({"configured": False, "verified": False, "error": f"WordPress verification failed (HTTP {verification.get('status_code', 'unknown')}). Credentials were not saved."}, status=401)
                return
            save_wordpress_credentials(base_url, username, application_password)
            self._send_json({"configured": True, "verified": True, "user_id": verification.get("user_id")})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._send_json({"configured": False, "verified": False, "error": str(exc)}, status=400)
        except Exception as exc:
            self._send_json({"configured": False, "verified": False, "error": str(exc)}, status=500)


def main() -> int:
    parser = argparse.ArgumentParser(description="IRL AI Core production operations dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    load_saved_environment()
    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"IRL AI Core Dashboard: http://{args.host}:{args.port}")
    print("LIVE mode creates WordPress drafts only; publish is not supported.")
    print(f"Research provider: {web_ui.active_provider()}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())