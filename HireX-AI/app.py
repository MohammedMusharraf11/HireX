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
    prompt = f"""
    Extract ONLY the candidate's full name from the following resume text.
    If no name is found, return 'Unknown'.

    Resume Text:
    {resume_text}
    """
    response = model.generate_content(prompt)
    time.sleep(3)  
    return response.text.strip()

def extract_skills_from_jd(job_description):
    """Extract technical skills from job description."""
    response = model.generate_content(f"Extract ONLY technical skills as comma-separated values: {job_description}")
    time.sleep(3)
    return [s.strip() for s in response.text.split(",")]

def extract_ats_factors(resume_text):
    """Extract skills, experience, certifications, and projects for ATS scoring."""
    prompt = f"""
    Extract key job-related details from the resume:
    
    Resume: 
    {resume_text}

    Output format:
    Skills: (comma-separated list)
    Experience: (summary of relevant job experiences)
    Certifications: (comma-separated list)
    Projects: (brief descriptions)
    """
    response = model.generate_content(prompt)
    time.sleep(3)  

    output = response.text.strip()

    skills_match = re.search(r"Skills:\s*(.*)", output, re.IGNORECASE)
    experience_match = re.search(r"Experience:\s*(.*)", output, re.IGNORECASE)
    certifications_match = re.search(r"Certifications:\s*(.*)", output, re.IGNORECASE)
    projects_match = re.search(r"Projects:\s*(.*)", output, re.IGNORECASE)

    skills = skills_match.group(1).strip() if skills_match else ""
    experience = experience_match.group(1).strip() if experience_match else ""
    certifications = certifications_match.group(1).strip() if certifications_match else ""
    projects = projects_match.group(1).strip() if projects_match else ""

    return skills, experience, certifications, projects


def calculate_ats_score(jd_skills, resume_skills, experience, certifications, projects):
    """Calculate an ATS score based on job relevance."""
    jd_skills_set = set([s.lower() for s in jd_skills])
    resume_skills_set = set([s.lower() for s in resume_skills.split(",")])

    skill_match_score = len(jd_skills_set & resume_skills_set) / max(len(jd_skills_set), 1) * 50  
    experience_score = 20 if experience else 0  
    certs_score = min(len(certifications.split(",")) * 5, 10)  
    project_score = min(len(projects.split(",")) * 5, 20)  

    total_score = skill_match_score + experience_score + certs_score + project_score  
    return round(total_score, 2)

def evaluate_resume(job_desc, resume_text, jd_skills):
    """Use Gemini to score a resume, give an ATS score, and provide reasons."""
    resume_skills, experience, certifications, projects = extract_ats_factors(resume_text)
    ats_score = calculate_ats_score(jd_skills, resume_skills, experience, certifications, projects)

    prompt = f"""
    Job Description:
    {job_desc}

    Candidate's Resume:
    {resume_text}

    ATS Score: {ats_score}

    Evaluate this resume for job relevance, considering skills, experience, projects, and certifications.
    Provide structured output:
    SCORE: (1-10)
    REASON: (Why is the candidate a good/bad fit?)
    """
    response = model.generate_content(prompt)
    time.sleep(3)  

    output = response.text.strip()

    score_match = re.search(r"SCORE:\s*([\d.]+)", output)
    reason_match = re.search(r"REASON:\s*(.*)", output, re.DOTALL)

    ai_score = float(score_match.group(1)) if score_match else 0.0
    reason = reason_match.group(1).strip() if reason_match else "Invalid AI response."

    final_score = (0.7 * ai_score) + (0.3 * ats_score)  

    return final_score, reason, ats_score

# Streamlit UI
st.title("🚀 Advanced AI Resume Screening System")

# Upload Job Description
job_desc_file = st.file_uploader("Upload Job Description (TXT or PDF)", type=["txt", "pdf"])

if job_desc_file:
    job_desc_text = extract_text_from_pdf(job_desc_file) if job_desc_file.type == "application/pdf" else job_desc_file.read().decode("utf-8")
    st.text_area("Extracted Job Description:", job_desc_text, height=150)
    skills = extract_skills_from_jd(job_desc_text)
    st.write("### Extracted Skills:", skills)

# Process Resumes from "src" Directory
resume_dir = "src"
resume_files = [os.path.join(resume_dir, f) for f in os.listdir(resume_dir) if f.endswith(".pdf")]

if resume_files:
    ranked_resumes = []

    for resume_path in resume_files:
        text = extract_text_from_pdf(resume_path)
        candidate_name = extract_name_from_resume(text)

        if not contains_email(text):
            st.warning(f"❌ {candidate_name} rejected: No email found.")
            continue

        final_score, reason, ats_score = evaluate_resume(job_desc_text, text, skills)
        ranked_resumes.append((candidate_name, final_score, ats_score, reason))

    # Sort by score
    ranked_resumes.sort(key=lambda x: x[1], reverse=True)

    # Display results
    if ranked_resumes:
        st.write("### 🏆 Final Ranked Candidates:")
        for idx, (name, final_score, ats_score, reason) in enumerate(ranked_resumes):
            st.write(f"**{idx+1}. {name}** (Final Score: {final_score:.2f} | ATS Score: {ats_score:.2f})")
            st.write(f"📌 **Reason:** {reason}")
            st.write("---")
