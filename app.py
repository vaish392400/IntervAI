# app.py (Gemini Version with VALIDATION)
import streamlit as st
import os
import json
from dotenv import load_dotenv
from datetime import datetime
import google.generativeai as genai

# -------------------- LOAD ENV --------------------
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-2.0-flash")

if not GEMINI_API_KEY:
    st.error("Missing GEMINI_API_KEY in .env file.")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)


# -------------------- UI SETUP --------------------
st.set_page_config(page_title="intervAI — AI Interview Agent", page_icon="🤖", layout="wide")

st.markdown("""
<style>

html, body, .stApp {
    background-color:#0d0d0d !important;
    color:white !important;
    width:100% !important;
    height:100% !important;
    margin:0 !important;
    padding:0 !important;
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

.chat-card { 
    background:#1a1a1a; 
    color:white;
    border-radius:14px; 
    padding:18px; 
    margin-bottom:16px; 
    border:1px solid #333;
}

.question { 
    font-weight:700; 
    margin-bottom:10px;
    font-size:1.1rem;
    color:white;
}

.stRadio label {
    color:white !important;
    font-size:1rem;
}

.section-title {
    font-size:1.4rem;
    font-weight:700;
    margin-top:25px;
    margin-bottom:5px;
    color:#4ade80;
}

.line {
    border-bottom:1px solid #333;
    margin-bottom:20px;
}

.small-muted { 
    color:#9ca3af; 
    font-size:0.9rem; 
}

</style>
""", unsafe_allow_html=True)


# -------------------- ROLE VALIDATION --------------------
def is_valid_role(text: str) -> bool:
    """Uses Gemini to check whether the text is a valid job role."""

    validate_prompt = f"""
Is "{text}" a valid professional job role?

Job role = A real profession like: Data Scientist, Accountant, Software Engineer, Doctor, Nurse, Teacher.

Invalid = random words, greetings, names, slang, sentences, nonsense.

Return ONLY JSON:
{{
 "valid": true/false
}}
"""

    try:
        res = model.generate_content(validate_prompt)
        t = res.text.strip()

        obj = json.loads(t[t.find("{"): t.rfind("}")+1])
        return obj.get("valid", False)

    except:
        return False


# -------------------- GEMINI FUNCTIONS --------------------
def generate_mcqs(role, n_domain=10, n_comm=10):
    prompt = f"""
Generate {n_domain} TECHNICAL MCQs and {n_comm} COMMUNICATION MCQs
for the job role "{role}".

Return ONLY valid JSON:
{{
 "domain": [
   {{"q": "question text", "options": ["A","B","C","D"], "answer": 0}}
 ],
 "communication": [
   {{"q": "question text", "options": ["A","B","C","D"], "answer": 0}}
 ]
}}
"""
    res = model.generate_content(prompt)
    text = res.text.strip()

    try:
        return json.loads(text)
    except:
        start = text.find("{")
        end = text.rfind("}")
        return json.loads(text[start:end+1])


def evaluate_answers(role, domain_qs, comm_qs, answers):
    all_qs = domain_qs + comm_qs

    tech_correct = 0
    comm_correct = 0
    tech_attempted = 0
    comm_attempted = 0

    for i, q in enumerate(all_qs):
        selected = answers.get(f"q_{i}", None)
        correct = q["answer"]

        if selected is not None:
            if i < len(domain_qs):
                tech_attempted += 1
            else:
                comm_attempted += 1

        if selected == correct:
            if i < len(domain_qs):
                tech_correct += 1
            else:
                comm_correct += 1

    total = tech_correct + comm_correct

    # ---------------- TEXT LOGIC ----------------

    # If user attempted nothing
    if tech_attempted == 0 and comm_attempted == 0:
        return {
            "scores": {
                "technical": 0,
                "communication": 0,
                "total": 0
            },
            "summary": "You did not attempt any questions.",
            "strengths": "No strengths detected because no questions were answered.",
            "improvements": "Please attempt the questions to receive proper feedback."
        }

    # If user scored very low
    if total <= 5:
        strengths = "You attempted the test, which is a good start."
        improvements = (
            "Try revising fundamentals for this job role. Practice more MCQs "
            "to strengthen your basic understanding."
        )

    # Medium score
    elif 6 <= total <= 14:
        strengths = (
            "You have moderate understanding. Some answers show that you know "
            "important concepts."
        )
        improvements = (
            "Focus on weak areas and revisit key concepts. Try to improve accuracy "
            "by practicing domain-related questions."
        )

    # High score
    else:
        strengths = (
            "Strong understanding of the subject. Your answers show clarity "
            "and confidence in multiple areas."
        )
        improvements = (
            "Keep refining your skills. Work on small gaps to reach expert level."
        )

    summary = f"You scored {total}/20 with {tech_correct}/10 in technical skills and {comm_correct}/10 in communication skills."

    return {
        "scores": {
            "technical": tech_correct,
            "communication": comm_correct,
            "total": total
        },
        "summary": summary,
        "strengths": strengths,
        "improvements": improvements
    }


# -------------------- SESSION STATE --------------------
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


# -------------------- HEADER --------------------
st.markdown("<h1 style='text-align:center;'>🤖 intervAI — AI Interview Agent</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:#9ca3af;'>Enter ANY job role. AI will generate 20 MCQs & evaluate you.</p>", unsafe_allow_html=True)
st.markdown("---")


# -------------------- HOME PAGE --------------------
if st.session_state.state == "home":

    with st.form("role_form"):
        role = st.text_input("Enter Job Role (e.g. Software Engineer, Data Scientist)")
        start = st.form_submit_button("Start Interview")

    if start:

        if not role.strip():
            st.warning("Please enter a job role.")
        else:
            # ⚠️ VALIDATION ADDED HERE
            if not is_valid_role(role.strip()):
                st.error("❌ Invalid job role! Enter a real profession.")
                st.stop()

            st.session_state.role = role.strip()
            st.session_state.state = "generating"
            st.rerun()


# -------------------- GENERATING MCQS --------------------
if st.session_state.state == "generating":
    st.info(f"Generating 20 MCQs for **{st.session_state.role}** ...")
    data = generate_mcqs(st.session_state.role)
    st.session_state.mcqs = data
    st.session_state.state = "test"
    st.rerun()


# -------------------- TEST PAGE --------------------
if st.session_state.state == "test":
    domain = st.session_state.mcqs["domain"]
    comm = st.session_state.mcqs["communication"]

    st.subheader(f"Role: {st.session_state.role}")
    st.markdown("<div class='small-muted'>10 Technical + 10 Communication questions.</div>", unsafe_allow_html=True)

    with st.form("mcq_form"):

        st.markdown("<div class='section-title'>SECTION 1 — TECHNICAL QUESTIONS</div>", unsafe_allow_html=True)
        st.markdown("<div class='line'></div>", unsafe_allow_html=True)

        for i, q in enumerate(domain):
            st.markdown(f"<div class='chat-card'><div class='question'>Q{i+1}. {q['q']}</div></div>", unsafe_allow_html=True)
            key = f"q_{i}"
            st.session_state.answers[key] = st.radio("", list(range(4)),
                format_func=lambda x, opts=q["options"]: opts[x], key=key, index=None)

        st.markdown("<div class='section-title'>SECTION 2 — COMMUNICATION SKILLS</div>", unsafe_allow_html=True)
        st.markdown("<div class='line'></div>", unsafe_allow_html=True)

        offset = len(domain)
        for j, q in enumerate(comm):
            idx = offset + j
            st.markdown(f"<div class='chat-card'><div class='question'>Q{idx+1}. {q['q']}</div></div>", unsafe_allow_html=True)
            key = f"q_{idx}"
            st.session_state.answers[key] = st.radio("", list(range(4)),
                format_func=lambda x, opts=q["options"]: opts[x], key=key, index=None)

        submit = st.form_submit_button("Submit Test")

    if submit:
        st.session_state.state = "evaluating"
        st.rerun()


# -------------------- EVALUATION --------------------
if st.session_state.state == "evaluating":
    st.info("Evaluating results...")
    ev = evaluate_answers(
        st.session_state.role,
        st.session_state.mcqs["domain"],
        st.session_state.mcqs["communication"],
        st.session_state.answers
    )
    st.session_state.evaluation = ev
    st.session_state.state = "result"
    st.rerun()


# -------------------- RESULTS --------------------
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
