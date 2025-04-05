import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import re
import os
import time
import json

# Load API Key securely
GEMINI_API_KEY = "AIzaSyBw9qlfSD4LBiZpAQEf0jaUCd70Z_fnkB8" # Ensure you set this in your environment
if not GEMINI_API_KEY:
    st.error("Missing API key. Set GEMINI_API_KEY as an environment variable.")
    st.stop()

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro-latest')

# Directory for resumes
SRC_DIR = "src"

# Weights for scoring
WEIGHTS = {
    'skills_match': 0.40,
    'experience': 0.30,
    'education': 0.15,
    'certifications': 0.10,
    'ats_score': 0.05
}

def process_pdf(file_path):
    """Extract text from a PDF file"""
    try:
        doc = fitz.open(file_path)
        text = "\n".join([page.get_text("text") for page in doc])
        return text.strip()
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def extract_name(resume_text):
    """Extract candidate's name from the resume using AI"""
    prompt = f"""
    Extract the candidate's full name from this resume. Return ONLY the name without any other text.
    
    Resume Content:
    {resume_text[:5000]}
    
    Candidate's Name:
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip().replace('"', '') or "Unknown Candidate"
    except Exception as e:
        return "Unknown Candidate"

def analyze_resume(job_desc, resume_text):
    """Analyze resume using Gemini AI"""
    prompt = f"""
    Analyze this resume for a software engineering position. Return STRICT JSON:
    {{
        "breakdown": {{
            "skills_match": 0-1,
            "experience": 0-1,
            "education": 0-1,
            "certifications": 0-1,
            "projects": 0-1
        }},
        "ats_score": 0-100,
        "skill_validation": {{
            "unverified_claims": ["list of skills without supporting evidence"],
            "verified_skills": ["skills with project/work evidence"]
        }},
        "red_flags": ["typos", "irrelevant info", "skill exaggerations"],
        "summary": "detailed analysis"
    }}

    Job Requirements:
    {job_desc}

    Resume Content:
    {resume_text[:15000]}

    Evaluation Rules:
    1. Education score based on relevance, not just presence.
    2. Skills without project/work evidence get 50% penalty.
    3. Deduct 0.1 for each red flag.
    4. ATS score based on: sections, keywords, readability.
    """
    
    try:
        response = model.generate_content(prompt)
        time.sleep(5)  # Rate limit handling
        
        json_str = response.text.strip().replace('```json', '').replace('```', '').strip()
        analysis = json.loads(json_str)

        # Calculate final weighted score
        base_score = min(100, sum(
            analysis.get(key, 0) * WEIGHTS[key] * 100 for key in WEIGHTS if key != 'ats_score'
        ) + analysis.get('ats_score', 0))

        # Apply penalty for red flags
        penalty = len(analysis.get('red_flags', [])) * 0.1 * 100
        final_score = max(0, base_score - penalty)

        return {
            **analysis,
            "final_score": round(final_score, 1),
            "score_breakdown": {
                "base_score": round(base_score, 1),
                "penalties": round(penalty, 1)
            }
        }
    
    except Exception as e:
        return {"error": str(e)}

def main():
    st.title("AI Resume Analyzer")
    
    # Input job description
    job_desc = st.text_area("Paste Job Description", height=200)

    if st.button("Analyze Resumes") and job_desc:
        if not os.path.exists(SRC_DIR):
            st.error(f"Directory {SRC_DIR} not found!")
            return
            
        pdf_files = [f for f in os.listdir(SRC_DIR) if f.lower().endswith('.pdf')]
        if not pdf_files:
            st.error("No PDF files found in src directory")
            return
            
        results = []
        with st.spinner("Processing resumes..."):
            for pdf_file in pdf_files:
                try:
                    file_path = os.path.join(SRC_DIR, pdf_file)
                    resume_text = process_pdf(file_path)

                    if not resume_text:
                        st.warning(f"Skipping {pdf_file}: Empty or unreadable PDF")
                        continue

                    # Extract candidate name
                    candidate_name = extract_name(resume_text)

                    # Analyze resume
                    analysis = analyze_resume(job_desc, resume_text)
                    analysis["name"] = candidate_name

                    results.append(analysis)
                    time.sleep(3)  # Rate limit protection
                    
                except Exception as e:
                    st.error(f"Error processing {pdf_file}: {str(e)}")

        # Store results in session state
        st.session_state.results = sorted(results, key=lambda x: x['final_score'], reverse=True)

    # Display results
    if 'results' in st.session_state:
        st.header("Top Candidates")
        
        for idx, res in enumerate(st.session_state.results):
            with st.expander(f"{idx+1}. {res['name']} ({res['final_score']}/100)"):
                st.write(f"**Verdict:** {res.get('verdict', 'Unknown')}")
                st.write(f"**Base Score:** {res['score_breakdown']['base_score']}")
                st.write(f"**Penalties:** -{res['score_breakdown']['penalties']}")
                
                st.write("**Skill Validation:**")
                st.write("Verified Skills:", ", ".join(res['skill_validation'].get('verified_skills', [])))
                st.write("Unverified Claims:", ", ".join(res['skill_validation'].get('unverified_claims', [])))
        
                st.write("**ATS Score:**", res.get('ats_score', 0))
                st.write("**Red Flags:**", ", ".join(res.get('red_flags', [])) if res.get('red_flags') else "None")
        
                st.write("**Detailed Breakdown:**")
                for category, score in res.get('breakdown', {}).items():
                    st.write(f"- {category.title()}: {score * 100:.1f}%")

if __name__ == "__main__":
    main()
