import sqlite3, json, re, time, html
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timezone, timedelta
import requests
import feedparser

ROOT=Path(__file__).parent
DATA=ROOT/"data"; DATA.mkdir(exist_ok=True)
DB=DATA/"applypilot.db"; PROFILE=DATA/"profile.json"; SOURCES=DATA/"sources.json"
DEFAULT_ROLES="Business Analyst, Junior Business Analyst, Business Analyst Trainee, Associate Business Analyst, Product Analyst, Associate Product Analyst"
DEFAULT_SKILLS="SQL, Excel, Power BI, requirements analysis, documentation, stakeholder communication, KPI reporting"
HEADERS={"User-Agent":"ApplyPilot Job Finder/1.0 (personal job search app)"}

def conn():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init_db():
 with conn() as c:
  c.execute("""CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY,url TEXT UNIQUE,title TEXT,company TEXT,location TEXT,summary TEXT,published TEXT,score INTEGER DEFAULT 0,status TEXT DEFAULT 'new',created REAL)""")
  c.execute("CREATE TABLE IF NOT EXISTS questions(id INTEGER PRIMARY KEY,job_id INTEGER,question TEXT,answer TEXT DEFAULT '',status TEXT DEFAULT 'open')")
  c.execute("CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY,job_id INTEGER,event TEXT,details TEXT,created REAL)")
  c.execute("CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT)")
  c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('minimum_score','55')")
  cols={r[1] for r in c.execute("PRAGMA table_info(jobs)")}
  if "source" not in cols: c.execute("ALTER TABLE jobs ADD COLUMN source TEXT DEFAULT ''")

def get_profile(): return json.loads(PROFILE.read_text(encoding="utf-8")) if PROFILE.exists() else {}
def save_profile(p): PROFILE.write_text(json.dumps(p,indent=2,ensure_ascii=False),encoding="utf-8")
def get_sources(): return json.loads(SOURCES.read_text(encoding="utf-8")) if SOURCES.exists() else []
def save_sources(text):
 urls=[]
 for line in text.splitlines():
  u=line.strip()
  if u and urlparse(u).scheme=="https" and urlparse(u).netloc: urls.append(u)
 SOURCES.write_text(json.dumps(list(dict.fromkeys(urls)),indent=2),encoding="utf-8")
def get_setting(k,default=""):
 with conn() as c:
  r=c.execute("SELECT value FROM settings WHERE key=?",(k,)).fetchone(); return r["value"] if r else default
def set_setting(k,v):
 with conn() as c: c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",(k,v))

def clean_text(value):
 value=html.unescape(re.sub(r"<[^>]+>"," ",str(value or "")))
 return re.sub(r"\s+"," ",value).strip()

def parse_date(value):
 if not value: return None
 if isinstance(value,str) and value.strip().isdigit() and len(value.strip()) in (10,13):
  try: value=float(value.strip()); value=value/1000 if value>10_000_000_000 else value
  except Exception: pass
 if isinstance(value,(int,float)):
  try: return datetime.fromtimestamp(value,timezone.utc)
  except Exception: return None
 s=str(value).strip()
 try:
  if s.endswith("Z"): s=s[:-1]+"+00:00"
  d=datetime.fromisoformat(s)
  return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)
 except Exception: pass
 try: return datetime.strptime(s[:25],"%a, %d %b %Y %H:%M:%S").replace(tzinfo=timezone.utc)
 except Exception: return None

def score_job(title,summary,location,p):
 title_l=title.lower(); text=(title+" "+summary+" "+location).lower()
 roles=[x.strip().lower() for x in p.get("roles",DEFAULT_ROLES).split(",") if x.strip()]
 skills=[x.strip().lower() for x in p.get("skills",DEFAULT_SKILLS).split(",") if x.strip()]
 # Use both user-confirmed skills and recognizable skills found in extracted resume text.
 resume=(p.get("resume_text","") or "").lower()
 known=["sql","excel","power bi","tableau","python","jira","confluence","requirements gathering","requirements analysis","user stories","acceptance criteria","stakeholder management","process mapping","agile","scrum","kpi reporting","data analysis","dashboarding","root cause analysis","gap analysis","documentation","uat","functional testing","regression testing","communication","figma","wireframing","product analytics"]
 for skill in known:
  if skill in resume and skill not in skills: skills.append(skill)
 score=15
 if any(r in title_l for r in roles): score+=45
 elif any(x in title_l for x in ["business analyst","business analysis","product analyst"]): score+=32
 elif any(x in title_l for x in ["data analyst","operations analyst","reporting analyst"]): score+=18
 score+=min(25,sum(3 for s in skills if s and s in text))
 if any(x in title_l for x in ["senior","principal","director","head of","staff","lead","manager"]): score-=30
 if any(x in title_l for x in ["junior","trainee","associate","intern","entry level","entry-level","graduate"]): score+=10
 if any(x in text for x in ["india","delhi","noida","gurugram","gurgaon","remote"]): score+=5
 return max(0,min(100,score))

def is_relevant_role(title, roles):
 t=title.lower()
 terms=[r.strip().lower() for r in roles if r.strip()]
 # Include reasonable title variants for analyst-focused searches.
 terms += ["business analyst","business analysis analyst","product analyst","associate business analyst","junior analyst"]
 return any(term in t for term in terms)

def _job(url,title,company,location,summary,published,source):
 return {"url":str(url or "").strip(),"title":clean_text(title) or "Untitled listing","company":clean_text(company),"location":clean_text(location),"summary":clean_text(summary)[:4000],"published":str(published or ""),"source":source}

def fetch_himalayas(query, country="IN", page=1):
 # Official public search endpoint; remote listings only.
 params={"q":query,"country":country,"seniority":"Entry-level","sort":"recent","page":page}
 r=requests.get("https://himalayas.app/jobs/api/search",params=params,headers=HEADERS,timeout=18); r.raise_for_status(); data=r.json()
 if isinstance(data,list): rows=data
 else: rows=data.get("jobs",data.get("data",data.get("results",[]))) if isinstance(data,dict) else []
 out=[]
 for x in rows if isinstance(rows,list) else []:
  url=x.get("applicationLink") or x.get("application_url") or x.get("url") or x.get("guid") or x.get("link")
  if not url: continue
  out.append(_job(url,x.get("title"),x.get("companyName") or x.get("company") or x.get("company_name"),x.get("location") or x.get("locationRestrictions") or "Remote",x.get("description") or x.get("excerpt") or x.get("summary"),x.get("pubDate") or x.get("published") or x.get("publicationDate") or x.get("createdAt") or x.get("created_at") or x.get("postedAt") or x.get("date"),"Himalayas"))
 return out

def fetch_arbeitnow():
 r=requests.get("https://www.arbeitnow.com/api/job-board-api",headers=HEADERS,timeout=18); r.raise_for_status(); data=r.json()
 rows=data.get("data",[]) if isinstance(data,dict) else []
 out=[]
 for x in rows:
  out.append(_job(x.get("url"),x.get("title"),x.get("company_name"),x.get("location") or ("Remote" if x.get("remote") else ""),x.get("description"),x.get("created_at") or x.get("createdAt") or x.get("publication_date") or x.get("date"),"Arbeitnow"))
 return out

def fetch_remotive(query):
 r=requests.get("https://remotive.com/api/remote-jobs",params={"search":query,"limit":100},headers=HEADERS,timeout=18); r.raise_for_status(); data=r.json()
 out=[]
 for x in data.get("jobs",[]) if isinstance(data,dict) else []:
  out.append(_job(x.get("url"),x.get("title"),x.get("company_name"),x.get("candidate_required_location") or "Remote",x.get("description"),x.get("publication_date") or x.get("publicationDate") or x.get("created_at") or x.get("date"),"Remotive"))
 return out

def _store_job(j,p):
 url=j["url"]
 if not url.startswith("https://"): return False
 score=score_job(j["title"],j["summary"],j["location"],p)
 with conn() as c:
  try:
   c.execute("INSERT INTO jobs(url,title,company,location,summary,published,score,status,created,source) VALUES(?,?,?,?,?,?,?,?,?,?)",(url,j["title"],j["company"],j["location"],j["summary"],j["published"],score,"new",time.time(),j.get("source","")))
   jid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
   c.execute("INSERT INTO history(job_id,event,details,created) VALUES(?,?,?,?)",(jid,"discovered",f"Imported from {j.get('source','job source')}",time.time()))
   return True
  except sqlite3.IntegrityError: return False

def search_jobs(roles, days=7, locations="India, Delhi NCR, Noida, Gurugram, Remote", max_results=200, sources=None):
 """Search public APIs, retain diagnostics explaining why listings were excluded."""
 p=get_profile(); role_list=[r.strip() for r in roles if r.strip()]
 if not role_list: role_list=[x.strip() for x in DEFAULT_ROLES.split(",")]
 sources=sources or ["Himalayas","Remotive","Arbeitnow"]
 all_jobs=[]; errors=[]; source_counts={}
 for role in role_list[:8]:
  if "Himalayas" in sources:
   # Search multiple pages so a single small first page does not cap the results.
   for page in range(1, 4):
    try:
     rows=fetch_himalayas(role,country="IN",page=page); all_jobs.extend(rows); source_counts["Himalayas"]=source_counts.get("Himalayas",0)+len(rows)
     if not rows: break
    except Exception as e:
     errors.append(f"Himalayas ({role}, page {page}): {str(e)[:180]}")
     break
  if "Remotive" in sources:
   try:
    rows=fetch_remotive(role); all_jobs.extend(rows); source_counts["Remotive"]=source_counts.get("Remotive",0)+len(rows)
   except Exception as e: errors.append(f"Remotive ({role}): {str(e)[:180]}")
 if "Arbeitnow" in sources:
  try:
   rows=fetch_arbeitnow(); all_jobs.extend(rows); source_counts["Arbeitnow"]=len(rows)
  except Exception as e: errors.append(f"Arbeitnow: {str(e)[:180]}")
 now=datetime.now(timezone.utc)
 cutoff=now.replace(hour=0,minute=0,second=0,microsecond=0) if int(days)==0 else now-timedelta(days=int(days))
 seen=set(); added=0; skipped=0; scanned=0
 reasons={"duplicate_or_missing_url":0,"role_mismatch":0,"outside_date_range":0,"location_mismatch":0,"already_saved":0}
 loc_terms=[x.strip().lower() for x in locations.split(",") if x.strip()]
 for j in all_jobs:
  scanned+=1; url=j["url"]
  if not url or url in seen: skipped+=1; reasons["duplicate_or_missing_url"]+=1; continue
  seen.add(url)
  if not is_relevant_role(j["title"],role_list): skipped+=1; reasons["role_mismatch"]+=1; continue
  published=parse_date(j["published"])
  # For date-filtered searches, do not silently treat unknown dates as recent.
  if not published or published<cutoff or published>now+timedelta(days=1): skipped+=1; reasons["outside_date_range"]+=1; continue
  hay=(j["location"]+" "+j["summary"]).lower()
  if loc_terms and not any(term in hay for term in loc_terms) and not any(x in hay for x in ["remote","worldwide","anywhere"]):
   if j["source"]!="Himalayas": skipped+=1; reasons["location_mismatch"]+=1; continue
  if _store_job(j,p): added+=1
  else: skipped+=1; reasons["already_saved"]+=1
  if added>=max_results: break
 return {"added":added,"skipped":skipped,"scanned":scanned,"errors":errors,"source_counts":source_counts,"reasons":reasons,"cutoff":cutoff.isoformat()}

def discover(urls,limit=100):
 added=skipped=0; errors=[]; p=get_profile()
 for url in urls:
  url=url.strip()
  if not url: continue
  parsed=urlparse(url)
  if parsed.scheme!="https" or not parsed.netloc: errors.append("Skipped invalid/non-HTTPS feed: "+url[:80]); continue
  try:
   req=requests.get(url,headers=HEADERS,timeout=12); req.raise_for_status(); feed=feedparser.parse(req.content)
   for e in feed.entries:
    if added>=limit: return added,skipped,errors
    link=(e.get("link") or "").strip()
    if not link.startswith("https://"): skipped+=1; continue
    j=_job(link,e.get("title"),e.get("author"),e.get("location") or "",e.get("summary"),e.get("published"),"RSS/Atom")
    if _store_job(j,p): added+=1
    else: skipped+=1
  except Exception as ex: errors.append(f"{url}: {str(ex)[:150]}")
 return added,skipped,errors

def get_jobs(include_applied=True):
 query = "SELECT * FROM jobs" + ("" if include_applied else " WHERE status NOT IN ('applied_manually','applied')") + " ORDER BY score DESC,created DESC"
 with conn() as c: return [dict(r) for r in c.execute(query)]
def get_questions():
 with conn() as c: return [dict(r) for r in c.execute("SELECT * FROM questions WHERE status='open' ORDER BY id DESC")]
def save_answer(qid,answer):
 with conn() as c: c.execute("UPDATE questions SET answer=?,status='answered' WHERE id=?",(answer,qid))
def get_draft(jid):
 with conn() as c:
  r=c.execute("SELECT details FROM history WHERE job_id=? AND event='draft' ORDER BY id DESC LIMIT 1",(jid,)).fetchone(); return r["details"] if r else ""
def prepare(jid):
 with conn() as c: job=c.execute("SELECT * FROM jobs WHERE id=?",(jid,)).fetchone()
 if not job: return {"missing":[]}
 p=get_profile(); required={"full name":p.get("name",""),"email":p.get("email",""),"verified experience":p.get("experience","")}
 missing=[k for k,v in required.items() if not str(v).strip()]
 draft=("APPLICATION DRAFT\n\n" f"Role: {job['title']}\nCompany: {job['company']}\nListing: {job['url']}\n\nDear Hiring Team,\n\nI am interested in the {job['title']} position. " f"My relevant background: {p.get('experience','[Add verified experience]')}\n\nRelevant skills: {p.get('skills','[Add verified skills]')}\n\nThank you for your consideration.\n{p.get('name','[Your name]')}")
 with conn() as c:
  c.execute("UPDATE jobs SET status=? WHERE id=?",("needs_answers" if missing else "prepared",jid))
  c.execute("INSERT INTO history(job_id,event,details,created) VALUES(?,?,?,?)",(jid,"draft",draft,time.time()))
  c.execute("INSERT INTO history(job_id,event,details,created) VALUES(?,?,?,?)",(jid,"prepared","Missing fields: "+", ".join(missing),time.time()))
  for m in missing: c.execute("INSERT INTO questions(job_id,question,status) VALUES(?,?,?)",(jid,"Please provide verified "+m,"open"))
 return {"missing":missing}
def set_status(jid,status):
 with conn() as c:
  c.execute("UPDATE jobs SET status=? WHERE id=?",(status,jid)); c.execute("INSERT INTO history(job_id,event,details,created) VALUES(?,?,?,?)",(jid,status,"Status updated manually",time.time()))
def get_history():
 with conn() as c: return [dict(r) for r in c.execute("SELECT h.id,h.job_id,j.title,h.event,h.details,h.created FROM history h LEFT JOIN jobs j ON j.id=h.job_id ORDER BY h.id DESC LIMIT 500")]
