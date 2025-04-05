import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import re
import os
import time

# Configure Gemini API
GEMINI_API_KEY = "AIzaSyBw9qlfSD4LBiZpAQEf0jaUCd70Z_fnkB8"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file."""
    doc = fitz.open(pdf_path)
    text = "\n".join([page.get_text("text") for page in doc])
    return text

def contains_email(text):
    """Check if the text contains an email ID."""
    return bool(re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text))

def extract_name_from_resume(resume_text):
    """Extract the candidate's full name from the resume."""
    prompt = f"Extract ONLY the candidate's full name from the following resume text:\n{resume_text}\nIf no name is found, return 'Unknown'."
    response = model.generate_content(prompt)
    time.sleep(2)
    return response.text.strip()

def match_resume_with_jd(job_description, resume_text):
    """Use Gemini to compare resumes with the job description and return a score, pros, and cons."""
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

# Streamlit UI
st.title("🚀 AI Resume Screening System")

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

    # Sort shortlisted candidates by score
    shortlisted.sort(key=lambda x: x[1], reverse=True)
    shortlisted = shortlisted[:50]  # Keep only top 50

    # Display Shortlisted Candidates
    if shortlisted:
        st.write("### 🏆 Shortlisted Candidates:")
        for idx, (name, score, pros, cons) in enumerate(shortlisted):
            st.write(f"**{idx+1}. {name}** (Score: {score:.2f})")
            st.write(f"✅ **Pros:** {pros}")
            st.write(f"⚠️ **Cons:** {cons}")
            st.write("---")

    # Display Rejected Candidates
    if rejected:
        st.write("### ❌ Rejected Candidates:")
        for idx, (name, reason) in enumerate(rejected):
            st.write(f"**{idx+1}. {name}** - {reason}")

    # Send Emails (Dummy Buttons)
    if st.button("📩 Send Rejection Emails"):
        st.success("Emails sent to rejected candidates.")

    if st.button("➡️ Move Shortlisted to AI Round 2"):
        st.success("Shortlisted candidates moved to the next round.")
