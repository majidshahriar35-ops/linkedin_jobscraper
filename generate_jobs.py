"""
LinkedIn Jobs Daily Scraper
Calls Apify → curious_coder/linkedin-jobs-scraper → generates index.html for GitHub Pages
"""

import os
import sys
import time
import json
import requests
from datetime import datetime, timezone
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
APIFY_TOKEN   = os.environ["APIFY_TOKEN"]
ACTOR_ID      = "curious_coder~linkedin-jobs-scraper"
OUTPUT_DIR    = Path("out")

SEARCH_URLS = [
    "https://www.linkedin.com/jobs/search/?keywords=data%20scientist&f_E=2&f_TPR=r86400&position=1&pageNum=0",
    "https://www.linkedin.com/jobs/search/?keywords=machine%20learning%20engineer&f_E=2&f_TPR=r86400&position=1&pageNum=0",
    "https://www.linkedin.com/jobs/search/?keywords=AI%20engineer&f_E=2&f_TPR=r86400&position=1&pageNum=0",
]

ACTOR_INPUT = {
    "count": 100,
    "scrapeCompany": False,
    "urls": SEARCH_URLS,
}

# ── Apify helpers ─────────────────────────────────────────────────────────────
def run_actor() -> tuple[str, str]:
    """Start the actor run. Returns (run_id, dataset_id)."""
    print("▶ Starting Apify actor run...")
    url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs"
    r = requests.post(url, params={"token": APIFY_TOKEN}, json=ACTOR_INPUT, timeout=30)
    r.raise_for_status()
    data = r.json()["data"]
    print(f"  Run ID:     {data['id']}")
    print(f"  Dataset ID: {data['defaultDatasetId']}")
    return data["id"], data["defaultDatasetId"]


def wait_for_run(run_id: str, timeout: int = 360, poll: int = 15) -> None:
    """Poll until run succeeds or raises on failure/timeout."""
    url = f"https://api.apify.com/v2/actor-runs/{run_id}"
    for elapsed in range(0, timeout, poll):
        r = requests.get(url, params={"token": APIFY_TOKEN}, timeout=15)
        r.raise_for_status()
        status = r.json()["data"]["status"]
        print(f"  [{elapsed:>3}s] status = {status}")
        if status == "SUCCEEDED":
            return
        if status in ("FAILED", "ABORTED", "TIMED-OUT"):
            raise RuntimeError(f"Actor run ended with status: {status}")
        time.sleep(poll)
    raise TimeoutError("Actor run did not finish within timeout")


def fetch_dataset(dataset_id: str) -> list[dict]:
    """Download all items from a completed dataset."""
    print("⬇ Fetching dataset items...")
    url = f"https://api.apify.com/v2/datasets/{dataset_id}/items"
    r = requests.get(url, params={"token": APIFY_TOKEN, "limit": 500}, timeout=30)
    r.raise_for_status()
    items = r.json()
    print(f"  {len(items)} raw items received")
    return items


# ── Data helpers ──────────────────────────────────────────────────────────────
def parse_salary(job: dict) -> str:
    if job.get("salary"):
        return job["salary"]
    breakdown = job.get("salaryInsights", {}).get("compensationBreakdown", [])
    if not breakdown:
        return ""
    b = breakdown[0]
    lo, hi = b.get("minSalary"), b.get("maxSalary")
    period = b.get("payPeriod", "")
    if not (lo and hi):
        return ""
    if period == "YEARLY":
        return f"${float(lo)/1000:.0f}k–${float(hi)/1000:.0f}k/yr"
    return f"${float(lo):.0f}–${float(hi):.0f}/hr"


def normalize(raw: list[dict]) -> list[dict]:
    """Deduplicate by job ID and normalise fields."""
    seen, jobs = set(), []
    for j in raw:
        jid = j.get("id", "")
        if jid in seen:
            continue
        seen.add(jid)

        try:
            applicants = int(str(j.get("applicantsCount", "0")).replace("+", "").strip())
        except (ValueError, TypeError):
            applicants = 0

        try:
            posted = datetime.fromisoformat(
                j.get("postedAt", "").replace("Z", "+00:00")
            ).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            posted = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        jobs.append({
            "title":      j.get("title", "").strip(),
            "company":    j.get("companyName", "").strip(),
            "location":   j.get("location", "").strip(),
            "type":       j.get("employmentType", "") or "Other",
            "level":      j.get("seniorityLevel", "") or "Not Applicable",
            "salary":     parse_salary(j),
            "applicants": applicants,
            "posted":     posted,
            "remote":     1 if j.get("workRemoteAllowed") else 0,
            "link":       j.get("link", "#"),
        })

    print(f"  {len(jobs)} unique jobs after deduplication")
    return jobs


# ── HTML generation ───────────────────────────────────────────────────────────
HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>LinkedIn Jobs — AI/ML · Data Science · Entry Level · USA</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<style>
:root{--bg:#0d0f13;--surface:#13161c;--border:#1f2330;--border2:#2a2f3d;--text:#c9d1e0;--muted:#5a6378;--accent:#7c6fff;--accent2:#4db8ff;--green:#22c55e;--amber:#f59e0b;--red:#ef4444;--pink:#ec4899;--cyan:#38bdf8;--row:#181c26;}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--bg);color:var(--text);font-family:'Space Grotesk',sans-serif;font-size:14px;min-height:100vh;padding-bottom:60px;}
.header{background:linear-gradient(135deg,#0d0f13,#111420);border-bottom:1px solid var(--border);padding:28px 32px 24px;position:relative;overflow:hidden;}
.header::before{content:'';position:absolute;inset:0;background:radial-gradient(ellipse 60% 80% at 80% 20%,rgba(124,111,255,.08),transparent 60%),radial-gradient(ellipse 40% 60% at 10% 90%,rgba(77,184,255,.05),transparent 60%);pointer-events:none;}
.hi{position:relative;max-width:1700px;margin:0 auto;}
.badge{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;padding:4px 10px;border-radius:4px;letter-spacing:.08em;text-transform:uppercase;display:inline-block;margin-bottom:10px;}
h1{font-size:clamp(18px,2.5vw,26px);font-weight:700;color:#fff;letter-spacing:-.02em;}
h1 span{color:var(--accent2);}
.sub{font-size:14px;font-weight:400;color:var(--muted);margin-top:4px;}
.meta{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted);margin-top:8px;display:flex;gap:18px;flex-wrap:wrap;}
.meta b{color:var(--accent);}
.pills{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px;}
.pill{font-family:'JetBrains Mono',monospace;font-size:11px;padding:4px 12px;border-radius:20px;border:1px solid;font-weight:500;}
.pg{border-color:var(--green);color:var(--green);background:rgba(34,197,94,.08);}
.pa{border-color:var(--amber);color:var(--amber);background:rgba(245,158,11,.08);}
.pb{border-color:var(--accent2);color:var(--accent2);background:rgba(77,184,255,.08);}
.pp{border-color:var(--accent);color:var(--accent);background:rgba(124,111,255,.08);}
.ctrl{max-width:1700px;margin:20px auto 0;padding:0 32px;display:grid;grid-template-columns:1fr repeat(4,auto);gap:10px;align-items:center;}
.sw{position:relative;}
.sw input{width:100%;background:var(--surface);border:1px solid var(--border2);border-radius:8px;color:var(--text);font-family:'JetBrains Mono',monospace;font-size:13px;padding:10px 14px 10px 38px;outline:none;transition:border-color .2s;}
.sw input::placeholder{color:var(--muted);}
.sw input:focus{border-color:var(--accent);}
.si{position:absolute;left:12px;top:50%;transform:translateY(-50%);color:var(--muted);pointer-events:none;}
select{background:var(--surface);border:1px solid var(--border2);border-radius:8px;color:var(--text);font-family:'JetBrains Mono',monospace;font-size:12px;padding:10px 28px 10px 12px;outline:none;cursor:pointer;appearance:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%235a6378'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 10px center;transition:border-color .2s;}
select:focus{border-color:var(--accent);}
.tw{max-width:1700px;margin:16px auto 0;padding:0 32px;overflow-x:auto;}
table{width:100%;border-collapse:collapse;font-size:13px;}
thead th{background:var(--surface);border:1px solid var(--border);padding:10px 12px;text-align:left;font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);cursor:pointer;user-select:none;white-space:nowrap;transition:color .15s,background .15s;position:sticky;top:0;z-index:2;}
thead th:hover{color:var(--text);background:var(--border);}
.sa{margin-left:4px;opacity:.4;font-size:9px;}
th.sorted .sa{opacity:1;color:var(--accent);}
tbody tr{border-bottom:1px solid var(--border);transition:background .12s;}
tbody tr:hover{background:var(--row);}
td{padding:10px 12px;vertical-align:middle;border-left:1px solid var(--border);border-right:1px solid var(--border);}
td:first-child{color:var(--muted);font-family:'JetBrains Mono',monospace;font-size:11px;width:40px;text-align:center;}
.jt a{color:var(--accent2);text-decoration:none;font-weight:500;line-height:1.3;transition:color .15s;}
.jt a:hover{color:#fff;text-decoration:underline;}
.tag{display:inline-block;font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px;border:1px solid;white-space:nowrap;letter-spacing:.04em;}
.tft{color:var(--green);border-color:rgba(34,197,94,.4);background:rgba(34,197,94,.07);}
.tct{color:var(--amber);border-color:rgba(245,158,11,.4);background:rgba(245,158,11,.07);}
.tpt{color:var(--accent);border-color:rgba(124,111,255,.4);background:rgba(124,111,255,.07);}
.tvt{color:var(--pink);border-color:rgba(236,72,153,.4);background:rgba(236,72,153,.07);}
.tit{color:var(--cyan);border-color:rgba(56,189,248,.4);background:rgba(56,189,248,.07);}
.tot{color:var(--muted);border-color:var(--border2);background:transparent;}
.lt{display:inline-block;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--muted);border:1px solid var(--border2);padding:2px 7px;border-radius:4px;white-space:nowrap;}
.le{color:var(--green);border-color:rgba(34,197,94,.3);background:rgba(34,197,94,.05);}
.sal{font-family:'JetBrains Mono',monospace;font-size:11px;color:#f9d56e;white-space:nowrap;}
.salna{color:var(--muted);font-size:11px;font-family:'JetBrains Mono',monospace;}
.ap{font-family:'JetBrains Mono',monospace;font-size:12px;white-space:nowrap;}
.ap.hot{color:var(--red);font-weight:700;}
.po{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted);white-space:nowrap;}
.co{font-weight:500;color:var(--text);}
.lo{color:var(--muted);font-size:12px;white-space:nowrap;}
.bv{display:inline-block;font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;padding:4px 10px;border-radius:5px;background:rgba(124,111,255,.12);border:1px solid rgba(124,111,255,.3);color:var(--accent);text-decoration:none;white-space:nowrap;transition:background .15s,border-color .15s,color .15s;letter-spacing:.04em;}
.bv:hover{background:rgba(124,111,255,.25);border-color:var(--accent);color:#fff;}
.footer{max-width:1700px;margin:20px auto 0;padding:0 32px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;}
.fs{font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--muted);}
.fs b{color:var(--accent2);}
#nr{text-align:center;padding:60px 20px;color:var(--muted);font-family:'JetBrains Mono',monospace;font-size:14px;display:none;}
@media(max-width:900px){.ctrl{grid-template-columns:1fr 1fr;}.sw{grid-column:1/-1;}.header,.tw,.ctrl,.footer{padding-left:16px;padding-right:16px;}}
</style>
</head>
<body>
<div class="header">
  <div class="hi">
    <div class="badge">&#9889; Auto-refreshed daily via GitHub Actions</div>
    <h1>LinkedIn Jobs &middot; <span>Data Scientist &middot; ML Engineer &middot; AI Engineer</span></h1>
    <div class="sub">Entry Level / Early Career &middot; United States &middot; Last 24 Hours</div>
    <div class="meta">
      <span>Actor: <b>curious_coder/linkedin-jobs-scraper</b></span>
      <span>Queries: <b>data scientist &middot; ML engineer &middot; AI engineer</b></span>
      <span>Filters: <b>f_E=2 &middot; f_TPR=r86400</b></span>
    </div>
    <div class="pills">
      <span class="pill pb" id="pt">&#9632; total</span>
      <span class="pill pg" id="pf">&#9632; full-time</span>
      <span class="pill pa" id="pc">&#9632; contract</span>
      <span class="pill pp" id="ph">&#9632; &#128293; hot (200+ apps)</span>
    </div>
  </div>
</div>

<div class="ctrl">
  <div class="sw"><span class="si">&#128269;</span><input type="text" id="q" placeholder="Filter by title, company, or location&hellip;" autocomplete="off"/></div>
  <select id="ft"><option value="">All Types</option><option>Full-time</option><option>Contract</option><option>Part-time</option><option>Internship</option><option>Volunteer</option></select>
  <select id="fl"><option value="">All Levels</option><option value="Entry level">Entry Level</option><option value="Not Applicable">Not Specified</option></select>
  <select id="fs"><option value="">All Salaries</option><option value="y">Has Salary</option><option value="n">No Salary</option></select>
  <select id="fr"><option value="">Remote &amp; On-site</option><option value="1">Remote Only</option><option value="0">On-site Only</option></select>
</div>

<div class="tw">
  <table id="tbl">
    <thead><tr>
      <th data-col="idx">#<span class="sa">&#8597;</span></th>
      <th data-col="title">Job Title<span class="sa">&#8597;</span></th>
      <th data-col="company">Company<span class="sa">&#8597;</span></th>
      <th data-col="location">Location<span class="sa">&#8597;</span></th>
      <th data-col="type">Type<span class="sa">&#8597;</span></th>
      <th data-col="level">Level<span class="sa">&#8597;</span></th>
      <th data-col="salary">Salary<span class="sa">&#8597;</span></th>
      <th data-col="applicants">Applicants<span class="sa">&#8597;</span></th>
      <th data-col="posted">Posted<span class="sa">&#8597;</span></th>
      <th>Link</th>
    </tr></thead>
    <tbody id="tb"></tbody>
  </table>
  <div id="nr">No results match your filters.</div>
</div>

<div class="footer">
  <div class="fs">Showing <b id="sc">0</b> of <b id="tc">0</b> jobs</div>
  <div class="fs">Fetched on <b>FETCH_DATE_PLACEHOLDER</b> &middot; Apify &middot; curious_coder/linkedin-jobs-scraper</div>
</div>

<script>
const J=JOBS_JSON_PLACEHOLDER;
function tc(t){return{'Full-time':'tft','Contract':'tct','Part-time':'tpt','Volunteer':'tvt','Internship':'tit'}[t]||'tot';}
function lc(l){return l==='Entry level'?'lt le':'lt';}
let sc=null,sd=1;
function render(){
  const tb=document.getElementById('tb');
  tb.innerHTML='';
  const q=(document.getElementById('q').value||'').toLowerCase();
  const ft=document.getElementById('ft').value;
  const fl=document.getElementById('fl').value;
  const fs=document.getElementById('fs').value;
  const fr=document.getElementById('fr').value;
  let f=J.filter(j=>{
    const txt=(j.title+' '+j.company+' '+j.location).toLowerCase();
    if(q&&!txt.includes(q))return false;
    if(ft&&j.type!==ft)return false;
    if(fl&&j.level!==fl)return false;
    if(fs==='y'&&!j.salary)return false;
    if(fs==='n'&&j.salary)return false;
    if(fr==='1'&&!j.remote)return false;
    if(fr==='0'&&j.remote)return false;
    return true;
  });
  if(sc){
    f.sort((a,b)=>{
      let av=a[sc],bv=b[sc];
      if(sc==='applicants'){av=+av;bv=+bv;}
      if(sc==='idx'){av=J.indexOf(a);bv=J.indexOf(b);}
      return av<bv?-sd:av>bv?sd:0;
    });
  }
  document.getElementById('sc').textContent=f.length;
  document.getElementById('tc').textContent=J.length;
  document.getElementById('nr').style.display=f.length?'none':'block';
  document.getElementById('tbl').style.display=f.length?'':'none';
  f.forEach(j=>{
    const n=J.indexOf(j)+1;
    const hot=j.applicants>=200;
    const tr=document.createElement('tr');
    tr.innerHTML='<td>'+n+'</td>'
      +'<td class="jt"><a href="'+j.link+'" target="_blank" rel="noopener">'+j.title+'</a></td>'
      +'<td class="co">'+j.company+'</td>'
      +'<td class="lo">'+j.location+'</td>'
      +'<td><span class="tag '+tc(j.type)+'">'+j.type+'</span></td>'
      +'<td><span class="'+lc(j.level)+'">'+j.level+'</span></td>'
      +'<td>'+(j.salary?'<span class="sal">'+j.salary+'</span>':'<span class="salna">&#8212;</span>')+'</td>'
      +'<td>'+(hot?'<span class="ap hot">200+ &#128293;</span>':'<span class="ap">'+j.applicants+'</span>')+'</td>'
      +'<td><span class="po">'+j.posted+'</span></td>'
      +'<td><a href="'+j.link+'" target="_blank" rel="noopener" class="bv">View &#8594;</a></td>';
    tb.appendChild(tr);
  });
  const total=J.length,ftc=J.filter(x=>x.type==='Full-time').length,ctc=J.filter(x=>x.type==='Contract').length,hot=J.filter(x=>x.applicants>=200).length;
  document.getElementById('pt').textContent=total+' total jobs';
  document.getElementById('pf').textContent=ftc+' full-time';
  document.getElementById('pc').textContent=ctc+' contract';
  document.getElementById('ph').textContent=hot+' \uD83D\uDD25 hot (200+ apps)';
}
document.querySelectorAll('thead th[data-col]').forEach(th=>{
  th.addEventListener('click',()=>{
    const col=th.dataset.col;
    sd=sc===col?-sd:1;
    sc=col;
    document.querySelectorAll('thead th').forEach(h=>h.classList.remove('sorted'));
    th.classList.add('sorted');
    th.querySelector('.sa').textContent=sd===1?'\u2191':'\u2193';
    render();
  });
});
['q','ft','fl','fs','fr'].forEach(id=>{
  const el=document.getElementById(id);
  el.addEventListener('input',render);
  el.addEventListener('change',render);
});
render();
</script>
</body>
</html>
"""


def generate_html(jobs: list[dict], fetch_date: str) -> str:
    jobs_json = json.dumps(jobs, ensure_ascii=False, separators=(",", ":"))
    return (
        HTML
        .replace("JOBS_JSON_PLACEHOLDER", jobs_json)
        .replace("FETCH_DATE_PLACEHOLDER", fetch_date)
    )


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    fetch_date = datetime.now(timezone.utc).strftime("%B %d, %Y")

    # 1. Run actor
    run_id, dataset_id = run_actor()

    # 2. Wait for completion
    print("⏳ Waiting for actor to finish...")
    wait_for_run(run_id)
    print("✅ Actor run succeeded")

    # 3. Fetch & normalize dataset
    raw = fetch_dataset(dataset_id)
    jobs = normalize(raw)

    if not jobs:
        print("⚠️  No jobs returned — writing empty dashboard anyway")

    # 4. Write HTML
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / "index.html"
    html = generate_html(jobs, fetch_date)
    html = html.encode("utf-8", errors="replace").decode("utf-8")
    out_path.write_text(html, encoding="utf-8")
    print(f"✅ Dashboard written → {out_path}  ({out_path.stat().st_size // 1024} KB)")
    print(f"   {len(jobs)} jobs · fetched {fetch_date}")


if __name__ == "__main__":
    main()
