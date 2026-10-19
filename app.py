import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
from applypilot_core import *

st.set_page_config(page_title="ApplyPilot Job Finder", page_icon="🎯", layout="wide")
init_db()
st.title("🎯 ApplyPilot — Job Finder")
st.caption("Find recently posted jobs that match your resume, then open the original application link.")
st.info("This tool searches selected public job sources, not every job website on the internet. Some listings may not expose reliable posting dates or location eligibility.")

profile_tab, search_tab, results_tab, history_tab, settings_tab = st.tabs(["👤 Resume & preferences", "🔎 Find jobs", "📋 Matching jobs", "📈 Search history", "⚙️ Settings"])

with profile_tab:
    p=get_profile()
    st.subheader("Your resume and job preferences")
    uploaded=st.file_uploader("Upload resume (PDF, DOCX or TXT)",type=["pdf","docx","txt"])
    if uploaded:
        try:
            if uploaded.name.lower().endswith(".pdf"):
                from pypdf import PdfReader
                import io
                reader=PdfReader(io.BytesIO(uploaded.getvalue()))
                resume_text="\n".join(page.extract_text() or "" for page in reader.pages)
            elif uploaded.name.lower().endswith(".docx"):
                from docx import Document
                import io
                doc=Document(io.BytesIO(uploaded.getvalue()))
                resume_text="\n".join(par.text for par in doc.paragraphs)
            else: resume_text=uploaded.getvalue().decode("utf-8",errors="ignore")
            st.text_area("Extracted resume text (review it)",resume_text,height=180,key="resume_extract")
            st.caption("Resume parsing runs locally in this app. Check the extracted text for errors before saving.")
        except Exception as e: st.error(f"Could not read the file: {e}")
    with st.form("profile_form"):
        name=st.text_input("Full name",p.get("name",""))
        email=st.text_input("Email (optional for job search)",p.get("email",""))
        location=st.text_input("Preferred locations (comma-separated)",p.get("location","Delhi NCR, Noida, Gurugram, Remote India"))
        roles=st.text_area("Target roles (one per line or comma-separated)",p.get("roles",DEFAULT_ROLES.replace(", ","\n")),height=110)
        skills=st.text_area("Skills from your resume (comma-separated)",p.get("skills",DEFAULT_SKILLS),height=90)
        experience=st.text_area("Relevant experience / summary",p.get("experience",""),height=100)
        salary=st.text_input("Expected salary (optional)",p.get("salary","10 LPA"))
        if st.form_submit_button("Save resume details and preferences",type="primary"):
            if uploaded:
                try: extracted=resume_text
                except NameError: extracted=""
            else: extracted=p.get("resume_text","")
            save_profile(dict(name=name,email=email,location=location,roles=roles.replace("\n",","),skills=skills,experience=experience,salary=salary,resume_text=extracted,resume_filename=uploaded.name if uploaded else p.get("resume_filename","")))
            st.success("Saved. Your resume text and target-role preferences will be used for job search and matching.")
    if p.get("resume_filename"):
        st.caption(f"Previously saved resume text: {p.get('resume_filename')} (re-upload to update the extracted text).")

with search_tab:
    p=get_profile()
    st.subheader("Find jobs posted recently")
    role_defaults=[x.strip() for x in p.get("roles",DEFAULT_ROLES).replace("\n",",").split(",") if x.strip()]
    c1,c2,c3=st.columns(3)
    with c1:
        date_choice=st.selectbox("Posted within",["Last 24 hours","Today (UTC date)","Last 7 days","Last 30 days"],index=2)
        days={"Last 24 hours":1,"Today (UTC date)":0,"Last 7 days":7,"Last 30 days":30}[date_choice]
    with c2:
        locations=st.text_input("Locations",p.get("location","Delhi NCR, Noida, Gurugram, Remote India"))
        max_results=st.selectbox("Maximum results to import",[50,100,200,300],index=2)
    with c3:
        min_score=st.slider("Minimum resume match score",0,100,int(get_setting("minimum_score","35")))
        include_related=st.checkbox("Include related analyst roles",value=False)
    all_roles=["Business Analyst","Junior Business Analyst","Business Analyst Trainee","Associate Business Analyst","Product Analyst","Associate Product Analyst","Data Analyst","Reporting Analyst","Business Systems Analyst"]
    role_options=list(dict.fromkeys(all_roles+role_defaults))
    default_roles=[r for r in role_options if r in role_defaults] if role_defaults else all_roles
    # Include the full analyst role set by default so changing a resume does not silently keep the search restricted to BA only.
    default_roles=list(dict.fromkeys(default_roles + ["Business Analyst","Junior Business Analyst","Business Analyst Trainee","Associate Business Analyst","Product Analyst","Associate Product Analyst","Data Analyst","Reporting Analyst"]))
    chosen=st.multiselect("Roles to search",options=role_options,default=[r for r in default_roles if r in role_options])
    st.caption("Resume and target roles are separate settings: uploading a Product Analyst resume updates the resume text only after you save the profile. Select the roles you want to search below; multiple roles can be selected.")
    st.markdown("**Sources:** Himalayas (remote roles), Remotive (remote roles), Arbeitnow (public job board API). Results are deduplicated by application URL.")
    st.markdown("#### More job boards")
    st.caption("Unstop and Wellfound are included as quick-search links. They open in your browser; their listings are not imported automatically because this build has no authorized integration for those boards.")
    import urllib.parse
    role_query = " OR ".join(chosen[:5]) if chosen else "Business Analyst OR Product Analyst"
    unstop_query = urllib.parse.quote_plus(f'site:unstop.com/jobs ({role_query})')
    wellfound_query = urllib.parse.quote_plus(f'site:wellfound.com/jobs ({role_query})')
    ext1, ext2, ext3, ext4 = st.columns(4)
    with ext1:
        st.link_button("Unstop jobs ↗", "https://unstop.com/jobs", use_container_width=True)
    with ext2:
        st.link_button("Search Unstop roles ↗", f"https://www.google.com/search?q={unstop_query}&tbs=qdr:w", use_container_width=True)
    with ext3:
        st.link_button("Wellfound jobs ↗", "https://wellfound.com/jobs", use_container_width=True)
    with ext4:
        st.link_button("Search Wellfound roles ↗", f"https://www.google.com/search?q={wellfound_query}&tbs=qdr:w", use_container_width=True)
    sources=[]
    s1,s2,s3=st.columns(3)
    with s1:
        if st.checkbox("Himalayas",value=True): sources.append("Himalayas")
    with s2:
        if st.checkbox("Remotive",value=True): sources.append("Remotive")
    with s3:
        if st.checkbox("Arbeitnow",value=True): sources.append("Arbeitnow")
    if st.button("🔍 Search recent jobs",type="primary",use_container_width=True):
        if not chosen:
            st.error("Choose at least one role first.")
        elif not sources:
            st.error("Choose at least one job source.")
        else:
            # Persist the latest role/location choices for future runs.
            p.update({"roles":", ".join(chosen),"location":locations})
            save_profile(p)
            with st.spinner("Searching public job sources, checking posting dates, and removing duplicates…"):
                result=search_jobs(chosen,days=days,locations=locations,max_results=max_results,sources=sources)
            st.session_state["last_search_result"]=result
            st.session_state["last_search_days"]=days
            st.session_state["last_search_score"]=min_score
            st.session_state["last_search_time"]=datetime.now(timezone.utc).isoformat()
            st.success(f"Search complete: {result['added']} new recent jobs added. {result['skipped']} listings skipped.")
            if result.get("source_counts"):
                st.write("**Records received from each source:** " + " · ".join(f"{k}: {v}" for k,v in result["source_counts"].items()))
            if result.get("reasons"):
                with st.expander("Why listings were skipped"):
                    st.json(result["reasons"])
            if result["errors"]: st.warning("Some sources could not be reached:\n\n"+"\n".join(result["errors"][:8]))
            if result["added"] == 0:
                st.warning("No listings passed the current role, posting-date and location checks. Expand the date range or location, or inspect source errors and skip reasons above.")
            st.rerun()
    if "last_search_result" in st.session_state:
        r=st.session_state["last_search_result"]
        st.caption(f"Last search scanned {r['scanned']} source records. Last search time: {st.session_state.get('last_search_time','')}")

with results_tab:
    st.subheader("Your matching jobs")
    show_applied=st.checkbox("Show jobs already marked as applied",value=False)
    jobs=get_jobs(include_applied=show_applied)
    if not jobs:
        st.info("No jobs saved yet. Go to Find jobs and run a search.")
    else:
        p=get_profile()
        a,b,c=st.columns(3)
        with a: title_query=st.text_input("Search job title or company",placeholder="Business Analyst")
        with b: score_filter=st.slider("Minimum score",0,100,int(get_setting("minimum_score","35")),key="results_score")
        with c: days_filter=st.selectbox("Posting date",["Any saved job","Last 24 hours","Last 7 days","Last 30 days"],index=2)
        days_map={"Any saved job":None,"Last 24 hours":1,"Last 7 days":7,"Last 30 days":30}
        cutoff=datetime.now(timezone.utc)-__import__('datetime').timedelta(days=days_map[days_filter]) if days_map[days_filter] else None
        filtered=[]
        for j in jobs:
            text=" ".join(str(j.get(k) or "") for k in ["title","company","location","summary"]).lower()
            if title_query and title_query.lower() not in text: continue
            if int(j.get("score") or 0)<score_filter: continue
            if cutoff:
                d=parse_date(j.get("published"))
                if not d or d<cutoff: continue
            filtered.append(j)
        st.write(f"**{len(filtered)} jobs match your filters** out of {len(jobs)} available saved jobs" + (" (including applied jobs)." if show_applied else " (applied jobs are hidden)."))
        if filtered:
            for j in filtered:
                with st.container(border=True):
                    left,right=st.columns([5,1])
                    with left:
                        st.markdown(f"### [{j['title']}]({j['url']})")
                        st.write(f"**{j.get('company') or 'Company not specified'}** · {j.get('location') or 'Location not specified'}")
                        d=parse_date(j.get("published")); st.caption(f"Posted: {d.strftime('%d %b %Y %H:%M UTC') if d else 'Date not verified'} · Source: {j.get('source') or 'RSS/other'}")
                    with right:
                        st.metric("Match",f"{int(j.get('score') or 0)}/100")
                        st.link_button("Apply / view job ↗",j["url"],use_container_width=True)
                    if j.get("summary"):
                        with st.expander("Job details / matching context"):
                            st.write(j["summary"][:2500])
                            pskills=[x.strip().lower() for x in p.get("skills","").split(",") if x.strip()]
                            hay=(j.get("title","")+" "+j.get("summary","")).lower()
                            matches=[s for s in pskills if s in hay]
                            st.write("**Skills found in listing:** "+(", ".join(matches) if matches else "No saved skills were detected in the available listing text."))
                            st.caption("The score is a heuristic match indicator, not a probability of being hired.")
                    if j.get("status") in ("applied_manually", "applied"):
                        st.success("Already marked as applied — hidden from the default results list.")
                    else:
                        st.caption("When you have actually applied, mark the listing below; it will disappear from the default results list.")
                        if st.button("Mark as applied",key=f"applied_{j['id']}"):
                            set_status(j['id'],"applied_manually"); st.success("Marked as applied and removed from the default list."); st.rerun()
        else: st.warning("No saved jobs match these filters. Try a wider date range or lower score threshold.")

with history_tab:
    st.subheader("Search and application history")
    hist=get_history()
    if hist: st.dataframe(pd.DataFrame(hist),use_container_width=True,hide_index=True)
    else: st.info("History appears after jobs are discovered or statuses are updated.")

with settings_tab:
    st.subheader("Settings")
    score=st.slider("Default minimum score",0,100,int(get_setting("minimum_score","35")),key="default_score")
    if st.button("Save default score"):
        set_setting("minimum_score",str(score)); st.success("Saved.")
    st.write("**Data and privacy:** Your saved profile and database remain in this app's local data folder. Resume text is stored locally if you save it.")
    st.write("**Sources and limitations:** Search uses selected public APIs. It cannot guarantee every vacancy across all job sites; some boards may omit posting dates, hide jobs behind login, or restrict access.")
    st.markdown("Sources: [Himalayas](https://himalayas.app), [Remotive](https://remotive.com), [Arbeitnow](https://www.arbeitnow.com), [Unstop](https://unstop.com/jobs), [Wellfound](https://wellfound.com/jobs). Unstop and Wellfound are currently quick-search links, not automatically imported APIs. Open the original listing to apply; this app does not auto-submit applications.")
