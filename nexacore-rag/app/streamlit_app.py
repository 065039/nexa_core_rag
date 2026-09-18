"""
NexaCore AI: web Q&A interface (works on desktop and mobile browsers).

Run:
    streamlit run app/streamlit_app.py --server.address 0.0.0.0 --server.port 8501
"""
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.access import load_roles, role_names  # noqa: E402
from src.config import settings  # noqa: E402
from src.rag import NexaCoreRAG  # noqa: E402

AUDIT_LOG = ROOT / "logs" / "audit.jsonl"
DEPT_LABELS = {"All": "All departments", "Customer_Service": "Customer Service"}
SAMPLE_QUESTIONS = [
    "How many days of unused leave can I carry forward?",
    "Who approves a purchase of INR 3 lakh?",
    "What is the process for onboarding a new vendor?",
    "What is the deadline for submitting expense claims?",
    "What are the response and resolution times for a P1 issue?",
]

st.set_page_config(page_title="NexaCore AI", page_icon="📚", layout="centered")
st.markdown("""
<style>
  .block-container {padding-top: 1.5rem; padding-bottom: 5rem; max-width: 820px;}
  .src-meta {font-size: 0.8rem; opacity: 0.75;}
  .dept-chip {display:inline-block; padding:2px 10px; margin:2px 4px 2px 0; border-radius:12px;
              background: rgba(49,120,198,0.15); font-size:0.8rem;}
  @media (max-width: 640px) {
    .block-container {padding-left: 0.8rem; padding-right: 0.8rem;}
    h1 {font-size: 1.6rem !important;}
    div.stButton > button {width: 100%; min-height: 2.8rem;}
  }
</style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner="Loading knowledge base...")
def get_engine() -> NexaCoreRAG:
    return NexaCoreRAG()


@st.cache_data
def load_catalog() -> list:
    path = settings.converted_dir / "catalog.json"
    return json.loads(path.read_text()) if path.exists() else []


def audit(resp, feedback=None) -> None:
    """Governance: record who asked what, what was retrieved, and the outcome (no answer text stored)."""
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    row = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "role": resp.role,
           "department_filter": resp.department_filter, "question": resp.question, "status": resp.status,
           "retrieved": [s.source_file for s in resp.sources], "cited": [s.sid for s in resp.sources if s.cited],
           "model": resp.model, "total_ms": resp.total_ms, "feedback": feedback}
    with AUDIT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")


def render_response(resp, show_all_sources: bool) -> None:
    if resp.status == "answered":
        st.markdown(resp.answer)
    elif resp.status == "restricted":
        st.warning(resp.answer, icon="🔒")
    else:
        st.info(resp.answer, icon="🔎")

    if resp.status == "answered" and resp.departments:
        chips = "".join(f'<span class="dept-chip">{DEPT_LABELS.get(d, d)}</span>' for d in resp.departments)
        st.markdown(f"<div>Answer drawn from: {chips}</div>", unsafe_allow_html=True)

    shown = resp.sources if show_all_sources else [s for s in resp.sources if s.cited]
    if shown:
        with st.expander(f"Sources ({len(shown)})"):
            for s in shown:
                badge = " · superseded" if s.status == "superseded" else ""
                lock = " · restricted" if s.access_level == "restricted" else ""
                st.markdown(f"**[{s.sid}] {s.title}** v{s.version}{badge}{lock}  \n"
                            f"<span class='src-meta'>{DEPT_LABELS.get(s.department, s.department)} · "
                            f"{s.source_file} · {s.section} · relevance {s.score:.2f}</span>",
                            unsafe_allow_html=True)
                snippet = re.sub(r"^#{1,6}\s*(.+)$", r"**\1**", s.text[:600], flags=re.M)
                st.caption(snippet + ("..." if len(s.text) > 600 else ""))
    st.caption(f"{resp.model} · retrieval {resp.retrieval_ms:.0f} ms · generation {resp.generation_ms:.0f} ms"
               + (" · cached" if resp.cache_hit else ""))


# ----------------------------------------------------------------------------- sidebar
roles = role_names()
with st.sidebar:
    st.header("Settings")
    role = st.selectbox("Your role", roles, index=roles.index(load_roles().get("default_role", roles[0])),
                        help="Restricted documents are only searched for roles that own them.")
    dept_options = ["All"] + list(settings.departments)
    department = st.selectbox("Department", dept_options, format_func=lambda d: DEPT_LABELS.get(d, d))
    include_superseded = st.toggle("Include superseded versions", value=False,
                                   help="Turn on to compare old and new policy versions.")
    show_all_sources = st.toggle("Show all retrieved chunks", value=False)
    if st.button("Clear conversation"):
        st.session_state.history = []

    catalog = load_catalog()
    if catalog:
        st.divider()
        st.subheader("Knowledge base")
        c1, c2 = st.columns(2)
        c1.metric("Documents", len(catalog))
        c2.metric("Departments", len({c["department"] for c in catalog}))
        by_dept = Counter(DEPT_LABELS.get(c["department"], c["department"]) for c in catalog)
        by_type = Counter(c["file_type"] for c in catalog)
        st.caption("By department: " + ", ".join(f"{k} {v}" for k, v in sorted(by_dept.items())))
        st.caption("By format: " + ", ".join(f"{k} {v}" for k, v in sorted(by_type.items())))
    st.caption("Parser: Docling · Framework: LlamaIndex · Vector DB: Qdrant · "
               f"Embeddings: {settings.embed_model} · LLM: Ollama Cloud")

# ----------------------------------------------------------------------------- main
st.title("NexaCore AI")
st.caption("Ask about HR, Finance, IT, Procurement, Legal and Customer Service policies. "
           "Answers come only from company documents, with sources.")

if "history" not in st.session_state:
    st.session_state.history = []

pending = None
if not st.session_state.history:
    st.markdown("**Try one of these:**")
    for i, q in enumerate(SAMPLE_QUESTIONS):
        if st.button(q, key=f"sample_{i}"):
            pending = q

for item in st.session_state.history:
    with st.chat_message("user"):
        st.markdown(item.question)
        st.caption(f"{item.role} · {DEPT_LABELS.get(item.department_filter, item.department_filter)}")
    with st.chat_message("assistant"):
        render_response(item, show_all_sources)

question = st.chat_input("Ask a question about company policies...") or pending
if question:
    with st.chat_message("user"):
        st.markdown(question)
        st.caption(f"{role} · {DEPT_LABELS.get(department, department)}")
    with st.chat_message("assistant"):
        with st.spinner("Searching departmental documents..."):
            try:
                resp = get_engine().answer(question, role=role, department=department,
                                           include_superseded=include_superseded)
            except Exception as exc:  # show a friendly error instead of a stack trace
                st.error(f"Something went wrong while answering: {exc}. "
                         "If Ollama Cloud is rate-limiting, wait a minute and try again.")
                st.stop()
        render_response(resp, show_all_sources)
    audit(resp)
    st.session_state.history.append(resp)
