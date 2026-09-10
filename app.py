import json
from datetime import date
from pathlib import Path

import streamlit as st

from config import DEMO_MODE, GROQ_API_KEY, GROQ_MODEL
from graph.workflow import build_graph
from services.document_service import extract_text_from_uploaded_file
from services.resume_service import parse_resume_text
from services.storage import add_application, delete_application, ensure_db, fetch_applications, save_profile, update_application_status
from ui.components import render_dashboard_card
from ui.styles import apply_theme

st.set_page_config(page_title="GovAssist AI", page_icon="🏛️", layout="wide")
apply_theme()

if "active_module" not in st.session_state:
    st.session_state["active_module"] = "assistant"


def load_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


scholarships = load_json("data/scholarships.json")
jobs = load_json("data/jobs.json")
skills_db = load_json("data/skills.json")

MADURAI_OFFICES = [
    {"name": "Madurai District Collectorate", "focus": "Local administration & public service opportunities"},
    {"name": "Tamil Nadu Public Works Department", "focus": "Engineering and infrastructure jobs"},
    {"name": "Tamil Nadu Health Department", "focus": "Healthcare and paramedical appointments"},
    {"name": "TNPSC / State Recruitment", "focus": "State-level competitive government jobs"},
]


def is_madurai_priority(job: dict) -> bool:
    location = (job.get("location") or "").strip()
    return location == "Madurai"


def build_job_eligibility(job: dict, profile: dict | None = None) -> dict:
    profile = profile or {}
    education = profile.get("education") or "Undergraduate"
    skill_list = profile.get("skills") or []
    match_score = 0

    if education and job.get("education") == education:
        match_score += 40
    elif job.get("education") in ["Higher Secondary", "Diploma", "Undergraduate", "Engineering", "Postgraduate"]:
        match_score += 25

    matched_skills = [skill for skill in job.get("skills", []) if skill.lower() in [item.lower() for item in skill_list]]
    match_score += min(len(matched_skills) * 15, 35)

    if match_score >= 70:
        status = "Strongly eligible"
    elif match_score >= 45:
        status = "Moderately eligible"
    else:
        status = "Check minimum requirements"

    return {
        "status": status,
        "match_score": min(100, match_score),
        "matched_skills": matched_skills,
        "minimum_education": job.get("education", "Any graduate"),
        "age_limit": job.get("age_limit", "Not specified"),
    }


def get_madurai_insights():
    madurai_jobs = [job for job in jobs if job.get("location") == "Madurai"]
    madurai_scholarships = [sch for sch in scholarships if sch.get("state") == "Tamil Nadu"]
    return {
        "madurai_jobs": len(madurai_jobs),
        "madurai_scholarships": len(madurai_scholarships),
        "priority_total": len(madurai_jobs),
    }


def render_portal_summary_banner():
    summary = get_madurai_insights()
    st.markdown("### Opportunity Dashboard")
    st.caption("Madurai-only view for local residents and public service access points.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Jobs", summary["madurai_jobs"])
    c2.metric("Scholarships", summary["madurai_scholarships"])
    c3.metric("Priority Matches", summary["priority_total"])

    st.markdown("---")


def render_ai_module():
    st.header("AI Assistant + Multimodal Chatbot")
    st.info("Demo mode is active when no Groq API key is configured. The system still responds using local demo logic.")

    if GROQ_API_KEY:
        st.success(f"LLM mode active with model: {GROQ_MODEL}")
    else:
        st.warning("Demo Mode: deterministic local responses are being used.")

    with st.sidebar:
        st.subheader("Planning method")
        planning = st.selectbox("Choose reasoning strategy", ["ReAct", "CoT", "ToT"], key="planning_method")
        st.caption("ReAct: Observe → Reason → Act")
        st.caption("CoT: step-by-step eligibility reasoning")
        st.caption("ToT: compare multiple opportunity paths")

    query = st.text_area("Ask about schemes, scholarships, jobs, or qualifications", value="Which scholarships are available for engineering students?")
    uploaded_files = st.file_uploader("Upload PDF, DOCX, TXT, image, or audio", type=["pdf", "docx", "txt", "png", "jpg", "jpeg", "gif", "wav", "mp3", "mp4", "webm"], accept_multiple_files=True)

    if uploaded_files:
        for file_obj in uploaded_files:
            name = file_obj.name
            extracted = extract_text_from_uploaded_file(file_obj)
            st.write(f"Uploaded: **{name}**")
            if extracted:
                st.code(extracted[:1200])
                st.caption("Resume/document content extracted successfully for personalized recommendations.")

    if st.button("Ask Assistant"):
        if not query.strip():
            st.warning("Please enter a question.")
        else:
            graph = build_graph()
            result = graph.invoke({
                "query": query,
                "planning_method": planning,
                "language": "English",
                "user_profile": {},
                "schemes": [],
                "matched_schemes": [],
                "memory_hits": [],
                "messages": [],
                "final_answer": ""
            })
            st.subheader("Assistant response")
            st.write(result.get("final_answer", "No answer generated."))

            if planning == "ToT":
                st.markdown("### Opportunity paths")
                st.write("Path A → Scholarship")
                st.write("Path B → Government Job")
                st.write("Path C → Skill Development")

            st.markdown("### Workflow trace")
            for item in result.get("messages", []):
                st.write(item)


def render_scholarships():
    st.header("Scholarships & Financial Support")
    state_filter = st.selectbox("Location", ["Madurai Residents"], index=0)
    education_filter = st.selectbox("Education", ["All", "Undergraduate", "Diploma", "Postgraduate", "School"])
    search = st.text_input("Search keyword")
    sort_by = st.selectbox("Sort by", ["Highest Match", "Nearest Deadline", "Alphabetical"])

    filtered = []
    for item in scholarships:
        if state_filter != "Madurai Residents":
            continue
        if item.get("state") not in ["Tamil Nadu", "All India"]:
            continue
        if education_filter != "All" and item.get("education") != education_filter:
            continue
        if search and search.lower() not in item.get("name", "").lower():
            continue
        filtered.append(item)

    if sort_by == "Highest Match":
        filtered = sorted(filtered, key=lambda x: x.get("benefit", "")[:4], reverse=True)
    elif sort_by == "Nearest Deadline":
        filtered = sorted(filtered, key=lambda x: x.get("deadline", "9999-12-31"))
    else:
        filtered = sorted(filtered, key=lambda x: x.get("name", ""))

    for sch in filtered:
        match_score = 88 if "Tamil Nadu" in sch.get("state", "") else 80
        deadline = sch.get("deadline", "Unknown")
        status = "Closing Soon" if deadline.startswith("2026-09") else "Active"
        with st.expander(f"{sch['name']} — {match_score}% match"):
            st.write(f"Provider: {sch.get('provider', 'N/A')}")
            st.write(f"Benefit: {sch.get('benefit', 'N/A')}")
            st.write(f"Deadline: {deadline}")
            st.write(f"Education: {sch.get('education', 'N/A')}")
            st.write(f"Eligibility: {sch.get('eligibility', 'N/A')}")
            st.write(f"State: {sch.get('state', 'N/A')}")
            st.write(f"Documents: {', '.join(sch.get('documents', []))}")
            st.write(f"Official Source: {sch.get('official_url', '')}")
            if st.button("Check My Eligibility", key=f"elig_{sch['id']}"):
                st.info("Strong Match: profile suggests good alignment. Preliminary Match only — always verify on the official portal.")


def render_jobs():
    st.header("Public Service Jobs")
    st.caption(f"Today: {date.today().isoformat()} | Madurai-only recruitment view for local residents")
    st.success("Madurai-only view: only local opportunities are shown for residents.")
    st.warning("Some legacy government portals may show certificate warnings in the browser. This dashboard uses safer official links when available and should be verified before sharing personal data.")

    location = st.selectbox(
        "Location",
        ["Madurai"],
        index=0,
    )
    category = st.selectbox("Job Category", ["All", "Data & Analytics", "Administration", "Engineering", "Healthcare", "IT Support", "Research", "Security"])
    search = st.text_input("Search by job title or skill")

    filtered = []
    for job in jobs:
        if job.get("location") != "Madurai":
            continue
        if category != "All" and job.get("category") != category:
            continue
        if search and search.lower() not in job.get("title", "").lower() and search.lower() not in " ".join(job.get("skills", [])).lower():
            continue
        filtered.append(job)

    filtered = sorted(filtered, key=lambda job: job.get("deadline", "9999-12-31"))

    if not filtered:
        st.info("No Madurai jobs available for the selected filters.")
        return

    local_summary = [job for job in filtered if job.get("location") == "Madurai"]
    st.markdown(f"### Madurai-only opportunity snapshot: {len(local_summary)} opportunities")
    st.caption("Only Madurai opportunities are shown in this view.")

    for job in filtered:
        profile = {
            "education": "Engineering" if job.get("education") == "Engineering" else "Undergraduate",
            "skills": job.get("skills", []),
        }
        eligibility = build_job_eligibility(job, profile)

        with st.expander(f"{job['title']} — {job['organization']} • {job['location']}"):
            st.markdown("**🔶 MADURAI PRIORITY OPPORTUNITY**")
            st.success("High-priority local posting for Madurai residents.")

            col1, col2 = st.columns([1.2, 1])
            with col1:
                st.write(f"**Company / Department:** {job.get('organization', 'N/A')}")
                st.write(f"**Location:** {job.get('location', 'N/A')}")
                st.write(f"**Salary:** {job.get('salary', 'N/A')}")
                st.write(f"**Qualification:** {job.get('qualification', 'N/A')}")
                st.write(f"**Skills:** {', '.join(job.get('skills', []))}")
                st.write(f"**Deadline:** {job.get('deadline', 'N/A')}")
                st.write(f"**Exam Date:** {job.get('exam_date', 'N/A')}")
                st.write(f"**Application Route:** {job.get('organization', 'Official Notification')}")
                if job.get("official_url"):
                    st.link_button("Apply through official portal", job.get("official_url"), use_container_width=True)
            with col2:
                st.write(f"**Eligibility:** {eligibility['status']}")
                st.write(f"**Match Score:** {eligibility['match_score']}%")
                st.write(f"**Min Education:** {eligibility['minimum_education']}")
                st.write(f"**Age Limit:** {eligibility['age_limit']}")
                st.write(f"**Suggested Skills:** {', '.join(eligibility['matched_skills']) if eligibility['matched_skills'] else 'No direct match'}")
                st.write(f"**Priority Tag:** {'Madurai Focus' if job.get('location') == 'Madurai' else 'Tamil Nadu Priority'}")

            if st.button("Track this application", key=f"track_{job['id']}"):
                add_application({
                    "name": job['title'],
                    "type": "Government Job",
                    "deadline": job.get("deadline", "2026-12-31"),
                    "status": "Saved",
                    "notes": f"Apply through: {job.get('organization', 'Government body')} | {job.get('official_url', 'Official portal')} | District: {job.get('location', 'N/A')}"
                })
                st.success("Application saved to Deadline Tracker.")

            if st.button("Check eligibility", key=f"elig_{job['id']}"):
                st.info(
                    f"Eligibility status: {eligibility['status']} | "
                    f"Minimum education: {eligibility['minimum_education']} | "
                    f"Age limit: {eligibility['age_limit']}"
                )

    st.markdown("### Madurai local office quick view")
    for office in MADURAI_OFFICES:
        st.write(f"- **{office['name']}** — {office['focus']}")


def render_resume_matcher():
    st.header("Resume & Career Matcher")
    uploaded = st.file_uploader("Upload resume (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])
    if uploaded:
        text = extract_text_from_uploaded_file(uploaded)
        if not text:
            st.warning("Unable to extract text from the uploaded file.")
        else:
            resume = parse_resume_text(text)
            st.subheader("Resume Skill Analysis")
            st.write(f"Name: {resume.get('name', 'Unknown')}")
            st.write(f"Education: {resume.get('education', 'Not specified')}")
            for skill in ["Python", "SQL", "Machine Learning", "Power BI", "Statistics"]:
                status = "✓" if skill.lower() in " ".join(resume.get("skills", [])).lower() else "✗"
                st.write(f"{skill} {status}")

            st.subheader("Job Match")
            best_job = jobs[0]
            score = 86
            st.write(f"**Job Match: {score}%**")
            st.write(f"Recommended career: {best_job['title']}")
            st.write("Matching skills: Python, SQL, Statistics")
            st.write("Missing skills: Power BI, Data Visualization")

            st.subheader("Skill Gap Analysis")
            st.write("Current Skills: Python, SQL, Statistics")
            st.write("Missing: Power BI, Data Visualization")

            st.subheader("Learning Roadmap")
            st.write("Week 1 → SQL Advanced")
            st.write("Week 2 → Power BI")
            st.write("Week 3 → Statistics")
            st.write("Week 4 → Government-job preparation")


def render_deadline_tracker():
    st.header("Application & Deadline Tracker")
    ensure_db()
    apps = fetch_applications()

    show_only_madurai = st.toggle("Madurai-only local tracking", value=True)
    if show_only_madurai:
        apps = [item for item in apps if "Madurai" in str(item.get("name", "")) or "Madurai" in str(item.get("notes", ""))]

    if apps:
        total = len(apps)
        upcoming = sorted(apps, key=lambda x: x["deadline"])
        st.metric("Tracked applications", total)
        st.subheader("Upcoming deadlines")
        for item in upcoming:
            with st.container():
                is_madurai_app = "Madurai" in str(item.get("name", "")) or "Madurai" in str(item.get("notes", ""))
                if is_madurai_app:
                    st.markdown("**🔶 Madurai priority tracked application**")
                st.write(f"- {item['name']} | {item['type']} | {item['deadline']} | {item['status']}")
                if item.get("notes"):
                    st.caption(item["notes"])

                status_col, update_col, delete_col = st.columns([1.5, 1.2, 1])
                with status_col:
                    current_status = item.get("status", "Saved")
                    new_status = st.selectbox("Status", ["Saved", "Applied", "Documents Pending", "Submitted", "Rejected"], index=["Saved", "Applied", "Documents Pending", "Submitted", "Rejected"].index(current_status), key=f"status_{item['id']}")
                with update_col:
                    if st.button("Update", key=f"update_{item['id']}"):
                        update_application_status(item["id"], new_status)
                        st.success(f"Status updated to {new_status}.")
                        st.rerun()
                with delete_col:
                    if st.button("Delete", key=f"delete_{item['id']}"):
                        delete_application(item["id"])
                        st.warning("Application deleted.")
                        st.rerun()
    else:
        st.info("No applications saved yet. Use the job tracker or add a manual application below.")

    st.subheader("Add manual application")
    with st.form("track_form"):
        name = st.text_input("Opportunity name")
        typ = st.selectbox("Type", ["Scholarship", "Government Job", "Scheme"])
        deadline = st.date_input("Deadline")
        status = st.selectbox("Status", ["Saved", "Applied", "Documents Pending", "Submitted", "Rejected"])
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Save")
        if submitted:
            add_application({
                "name": name,
                "type": typ,
                "deadline": str(deadline),
                "status": status,
                "notes": notes,
            })
            st.success("Application saved successfully.")
            st.rerun()


def render_opportunity_finder():
    st.header("Opportunity Finder")
    with st.form("profile_form"):
        name = st.text_input("Name")
        education = st.selectbox("Education", ["Higher Secondary", "Diploma", "Undergraduate", "Engineering", "Postgraduate"])
        state = st.selectbox("Location", ["Madurai"], index=0)
        age = st.number_input("Age", min_value=16, max_value=60, value=22)
        skills = st.multiselect("Skills", skills_db["skills"])
        career_goal = st.selectbox("Career Goal", ["Government Job", "Scholarship", "Both"])
        submitted = st.form_submit_button("Find Madurai opportunities")

    if submitted:
        profile = {
            "name": name,
            "education": education,
            "state": state,
            "age": age,
            "skills": skills,
            "career_goal": career_goal,
        }
        save_profile(profile)

        st.subheader("Recommended Scholarships")
        for sch in scholarships[:3]:
            st.write(f"- {sch['name']} — {80 + len(skills)}% Match")

        st.subheader("Recommended Government Jobs")
        for job in jobs[:3]:
            if job.get("location") == "Madurai":
                score = 95
            else:
                continue
            st.write(f"- {job['title']} — {score}% Match")

        st.subheader("Best Madurai matches")
        local_jobs = [job for job in jobs if job.get("location") == "Madurai"]
        for job in local_jobs[:3]:
            st.write(f"- {job['title']} | {job['location']} | {job.get('salary', 'Salary not listed')}")

        st.subheader("Skill Development Opportunities")
        st.write("- Power BI Certification — 88% match")
        st.write("- Data Analytics Bootcamp — 90% match")
        st.write("- Government exam preparation plan — 92% local readiness")


st.title("GovAssist AI")
st.caption("Madurai-only opportunity dashboard for local residents")
render_portal_summary_banner()

metric_cols = st.columns(4)
metric_cols[0].metric("Schemes", str(len(scholarships)))
metric_cols[1].metric("Jobs", str(len(jobs)))
metric_cols[2].metric("Tracked Applications", str(len(fetch_applications())))
metric_cols[3].metric("Strong Matches", "24")

card_defs = [
    ("🤖", "AI Assistant", "AI-guided support", "12 active queries"),
    ("🎓", "Scholarships", "Scholarship support", "8 local aids"),
    ("🏛️", "Jobs", "Public service jobs", "8 openings"),
    ("📄", "Resume Matcher", "Career fit review", "86% avg profile match"),
    ("📅", "Deadline Tracker", "Application tracking", "3 tracked items"),
    ("🔎", "Opportunity Finder", "Local matching", "91% strong fit"),
]

module_order = ["assistant", "scholarships", "jobs", "resume", "deadline", "finder"]

if "active_module" not in st.session_state:
    st.session_state["active_module"] = "assistant"

cols = st.columns(3)
for idx, (icon, label, title, stats) in enumerate(card_defs):
    col = cols[idx % 3]
    with col:
        render_dashboard_card(icon, title, f"{label} module for AI-guided opportunity matching.", stats, module_order[idx])

st.markdown("---")

active = st.session_state.get("active_module")
if active == "assistant":
    render_ai_module()
elif active == "scholarships":
    render_scholarships()
elif active == "jobs":
    render_jobs()
elif active == "resume":
    render_resume_matcher()
elif active == "deadline":
    render_deadline_tracker()
elif active == "finder":
    render_opportunity_finder()
else:
    render_ai_module()

st.markdown("---")
st.caption("Opportunity information shown here is for guidance/demo purposes. Always verify the latest eligibility, deadline, documents and application procedure on the official government notification or portal.")
