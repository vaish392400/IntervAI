# app.py code....
import streamlit as st
import os
import json
from dotenv import load_dotenv
from datetime import datetime
import google.generativeai as genai

# loading environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-2.0-flash")

if not GEMINI_API_KEY:
    st.error("Missing GEMINI_API_KEY in .env file.")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)

# UI SETUP
st.set_page_config(page_title="intervAI — AI Interview Agent", page_icon="🤖", layout="wide")

# STYLING
st.markdown("""
<style>
html, body, .stApp {
    background-color:#0d0d0d !important;
    color:white !important;
    width:100% !important;
    height:100% !important;
}
.block-container {
    max-width: 100% !important;
    padding-left: 40px !important;
    padding-right: 40px !important;
}
@media (max-width: 768px) {
    .block-container {
        padding-left: 15px !important;
        padding-right: 15px !important;
    }
}
.chat-card { background:#1a1a1a; padding:18px; border-radius:14px; margin-bottom:16px; border:1px solid #333; }
.question { font-size:1.1rem; font-weight:700; color:white; margin-bottom:10px; }
.stRadio label { font-size:1rem; color:white !important; }
.section-title { font-size:1.4rem; font-weight:700; margin-top:25px; color:#4ade80; }
.line { border-bottom:1px solid #333; margin-bottom:20px; }
.small-muted { color:#9ca3af; font-size:0.9rem; }
</style>
""", unsafe_allow_html=True)

# ROLE VALIDATION
def is_valid_role(text: str) -> bool:
    """Uses Gemini to check whether the given text is a real job role."""
    check_prompt = f"""
Is "{text}" a valid professional job role?

Answer ONLY using this JSON:
{{
 "valid": true/false
}}

A job role means a profession (Example: Data Scientist, Accountant, Nurse).
If it's greeting, random text, nonsense, names, or not a profession → valid=false.
"""
    try:
        response = model.generate_content(check_prompt)
        t = response.text.strip()
        data = json.loads(t[t.find("{"): t.rfind("}")+1])
        return data.get("valid", False)
    except:
        return False


# GEMINI INTERACTIONS
def generate_mcqs(role, n_domain=10, n_comm=10):
    prompt = f"""
Generate {n_domain} TECHNICAL MCQs and {n_comm} COMMUNICATION MCQs
for the job role "{role}".

Return ONLY JSON:
{{
 "domain":[{{"q":"question","options":["A","B","C","D"],"answer":0}}],
 "communication":[{{"q":"question","options":["A","B","C","D"],"answer":0}}]
}}
"""
    response = model.generate_content(prompt)
    text = response.text.strip()
    return json.loads(text[text.find("{"): text.rfind("}")+1])

def evaluate_answers(role, domain_qs, comm_qs, answers):
    all_qs = domain_qs + comm_qs
    payload = {
        "questions":[ {"index":i,"q":q["q"],"options":q["options"],"correct":q["answer"]} for i, q in enumerate(all_qs) ],
        "candidate_answers":[ answers.get(f"q_{i}", None) for i in range(len(all_qs)) ]
    }

    prompt = f"""
Evaluate for role {role}. Return EXACT JSON:
{{
 "scores":{{"total":int,"technical":int,"communication":int}},
 "per_question":[{{"index":int,"selected":int,"correct":int,"correct_bool":true}}],
 "summary":"text",
 "strengths":"text",
 "improvements":"text"
}}
"""
    response = model.generate_content(prompt + json.dumps(payload))
    text = response.text.strip()
    return json.loads(text[text.find("{"): text.rfind("}")+1])


# SESSION STATE INITIALIZATION
if "state" not in st.session_state:
    st.session_state.state = "home"
if "role" not in st.session_state:
    st.session_state.role = ""
if "mcqs" not in st.session_state:
    st.session_state.mcqs = None
if "answers" not in st.session_state:
    st.session_state.answers = {}
if "evaluation" not in st.session_state:
    st.session_state.evaluation = None


# MAIN HEADER
st.markdown("<h1 style='text-align:center;'>🤖 intervAI — AI Interview Agent</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:#9ca3af;'>Enter ANY job role. AI will generate 20 MCQs & evaluate you.</p>", unsafe_allow_html=True)
st.markdown("---")


# HOME PAGE
if st.session_state.state == "home":
    with st.form("role_form"):
        role = st.text_input("Enter Job Role (e.g. Software Engineer, Data Scientist)")
        start = st.form_submit_button("Start Interview")

    if start:

        if not role.strip():
            st.warning("Please enter a job role.")
        else:
            # -------------------- VALIDATION ADDED HERE --------------------
            if not is_valid_role(role.strip()):
                st.error("❌ Please enter a valid job role (profession).")
                st.stop()
            # --------------------------------------------------------------

            st.session_state.role = role.strip()
            st.session_state.state = "generating"
            st.rerun()


# GENERATING
if st.session_state.state == "generating":
    st.info(f"Generating MCQs for **{st.session_state.role}**...")
    data = generate_mcqs(st.session_state.role)
    st.session_state.mcqs = data
    st.session_state.state = "test"
    st.rerun()


# TEST
if st.session_state.state == "test":
    domain = st.session_state.mcqs["domain"]
    comm = st.session_state.mcqs["communication"]

    st.subheader(f"Role: {st.session_state.role}")
    st.markdown("<div class='small-muted'>10 Technical + 10 Communication MCQs.</div>", unsafe_allow_html=True)

    with st.form("mcq_form"):
        st.markdown("<div class='section-title'>SECTION 1 — TECHNICAL QUESTIONS</div>", unsafe_allow_html=True)
        st.markdown("<div class='line'></div>", unsafe_allow_html=True)

        for i, q in enumerate(domain):
            st.markdown(f"<div class='chat-card'><div class='question'>Q{i+1}. {q['q']}</div></div>", unsafe_allow_html=True)
            key = f"q_{i}"
            st.session_state.answers[key] = st.radio("", list(range(4)), format_func=lambda x, o=q["options"]: o[x], key=key, index=None)

        st.markdown("<div class='section-title'>SECTION 2 — COMMUNICATION SKILLS</div>", unsafe_allow_html=True)
        st.markdown("<div class='line'></div>", unsafe_allow_html=True)

        offset = len(domain)
        for j, q in enumerate(comm):
            idx = offset + j
            st.markdown(f"<div class='chat-card'><div class='question'>Q{idx+1}. {q['q']}</div></div>", unsafe_allow_html=True)
            key = f"q_{idx}"
            st.session_state.answers[key] = st.radio("", list(range(4)), format_func=lambda x, o=q["options"]: o[x], key=key, index=None)

        submit = st.form_submit_button("Submit Test")

    if submit:
        st.session_state.state = "evaluating"
        st.rerun()


# EVALUATION
if st.session_state.state == "evaluating":
    st.info("Evaluating answers...")
    ev = evaluate_answers(
        st.session_state.role,
        st.session_state.mcqs["domain"],
        st.session_state.mcqs["communication"],
        st.session_state.answers
    )
    st.session_state.evaluation = ev
    st.session_state.state = "result"
    st.rerun()


# RESULTS
if st.session_state.state == "result":
    ev = st.session_state.evaluation
    scores = ev["scores"]

    st.success("Test submitted successfully!")
    st.header("📊 Score Summary")
    st.metric("Total Score", f"{scores['total']} / 20")
    st.metric("Technical", f"{scores['technical']} / 10")
    st.metric("Communication", f"{scores['communication']} / 10")

    st.subheader("⭐ Summary")
    st.write(ev["summary"])

    st.subheader("💪 Strengths")
    st.write(ev["strengths"])

    st.subheader("📉 Improvements")
    st.write(ev["improvements"])

    if st.button("Retake / Try Another Role"):
        st.session_state.state = "home"
        st.session_state.role = ""
        st.session_state.answers = {}
        st.session_state.mcqs = None
        st.session_state.evaluation = None
        st.rerun()
