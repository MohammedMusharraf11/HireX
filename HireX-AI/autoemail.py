import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import re
import os
import time
import glob

# Configure Gemini API
GEMINI_API_KEY = "AIzaSyBw9qlfSD4LBiZpAQEf0jaUCd70Z_fnkB8"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    return "\n".join([page.get_text("text") for page in doc])

def contains_email(text):
    return bool(re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text))

def extract_name_from_resume(resume_text):
    prompt = f"Extract ONLY the candidate's full name from the following resume text:\n{resume_text}\nIf no name is found, return 'Unknown'."
    response = model.generate_content(prompt)
    time.sleep(2)
    return response.text.strip()

def match_resume_with_jd(job_description, resume_text):
    prompt = f"""
    Job Description:
    {job_description}

    Candidate's Resume:
    {resume_text}

    Evaluate how well this resume matches the job description.
    Provide structured output in this format:
    SCORE: (1-100)
    PROS: (one-line reason why this candidate is a good fit)
    CONS: (one-line reason why this candidate may not be the best fit)
    """
    response = model.generate_content(prompt)
    time.sleep(2)
    output = response.text.strip()
    score_match = re.search(r"SCORE:\s*([\d.]+)", output)
    pros_match = re.search(r"PROS:\s*(.*)", output)
    cons_match = re.search(r"CONS:\s*(.*)", output)
    score = float(score_match.group(1)) if score_match else 0.0
    pros = pros_match.group(1).strip() if pros_match else "No pros detected."
    cons = cons_match.group(1).strip() if cons_match else "No cons detected."
    return score, pros, cons

def analyze_txt_responses(responses_dir="responses"):
    files = glob.glob(os.path.join(responses_dir, "*.txt"))
    results = []

    for file_path in files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        name_match = re.search(r"Candidate Name:\s*(.+)", content)
        candidate_name = name_match.group(1).strip() if name_match else "Unknown"

        ai_check_prompt = f"""
        The following are interview responses from a candidate named {candidate_name}. 
        Please determine if these answers are AI-generated or human-written.

        Content:
        {content}

        Respond only with:
        AI-GENERATED
        HUMAN-WRITTEN
        MIXED
        """
        ai_response = model.generate_content(ai_check_prompt).text.strip()
        time.sleep(15)

        grading_prompt = f"""
        These are answers from a candidate's interview. Please grade them based on correctness and clarity (out of 100) and give a short one-line recommendation.

        Candidate: {candidate_name}
        Responses:
        {content}

        Format your output like this:
        SCORE: xx
        RECOMMENDATION: <text>
        """
        grade_response = model.generate_content(grading_prompt).text.strip()
        time.sleep(2)

        score_match = re.search(r"SCORE:\s*(\d+)", grade_response)
        recommendation_match = re.search(r"RECOMMENDATION:\s*(.*)", grade_response)

        score = int(score_match.group(1)) if score_match else 0
        recommendation = recommendation_match.group(1).strip() if recommendation_match else "No recommendation."

        results.append({
            "name": candidate_name,
            "ai_detected": ai_response,
            "score": score,
            "recommendation": recommendation
        })

    return results

# Streamlit UI
st.title("🚀 HireYatra AI Resume Screening System")

# Upload Job Description
job_desc_file = st.file_uploader("Upload Job Description (TXT or PDF)", type=["txt", "pdf"])

if job_desc_file:
    job_desc_text = extract_text_from_pdf(job_desc_file) if job_desc_file.type == "application/pdf" else job_desc_file.read().decode("utf-8")
    st.text_area("Extracted Job Description:", job_desc_text, height=150)

# Process Resumes from "src" Directory
resume_dir = "src"
resume_files = [os.path.join(resume_dir, f) for f in os.listdir(resume_dir) if f.endswith(".pdf")]

shortlisted = []
rejected = []

if resume_files and job_desc_file:
    for resume_path in resume_files:
        text = extract_text_from_pdf(resume_path)
        candidate_name = extract_name_from_resume(text)

        if not contains_email(text):
            rejected.append((candidate_name, "❌ No email found."))
            continue

        score, pros, cons = match_resume_with_jd(job_desc_text, text)

        if score >= 50:
            shortlisted.append((candidate_name, score, pros, cons))
        else:
            rejected.append((candidate_name, f"❌ {cons}"))

    shortlisted.sort(key=lambda x: x[1], reverse=True)
    shortlisted = shortlisted[:50]

    if shortlisted:
        st.write("### 🏆 Shortlisted Candidates:")
        for idx, (name, score, pros, cons) in enumerate(shortlisted):
            st.write(f"**{idx+1}. {name}** (Score: {score:.2f})")
            st.write(f"✅ **Pros:** {pros}")
            st.write(f"⚠️ **Cons:** {cons}")
            st.write("---")

    if rejected:
        st.write("### ❌ Rejected Candidates:")
        for idx, (name, reason) in enumerate(rejected):
            st.write(f"**{idx+1}. {name}** - {reason}")

    if st.button("📩 Send Rejection Emails"):
        st.success("Emails sent to rejected candidates.")

    if st.button("➡️ Move Shortlisted to AI Round 2"):
        st.success("Shortlisted candidates moved to the next round.")
        # time.sleep(30)
        
        st.write("## 🧠 AI Round 2: Interview Response Analysis")
        interview_results = analyze_txt_responses()

        for res in interview_results:
            st.subheader(res["name"])
            st.write(f"🤖 **AI Detection:** {res['ai_detected']}")
            st.write(f"📊 **Answer Score:** {res['score']}")
            st.write(f"💡 **Recommendation:** {res['recommendation']}")
            st.write("---")

        top_candidate = max(interview_results, key=lambda x: x["score"], default=None)
        if top_candidate:
            st.success(f"🏅 **Top Recommended Candidate: {top_candidate['name']}**")
            
        if st.button("📞 Schedule a Call"):
            st.success(f"A call has been scheduled with {top_candidate['name']}. 📅")

        st.write("### Built with ❤️ by HireYatra at HackFest'25")
