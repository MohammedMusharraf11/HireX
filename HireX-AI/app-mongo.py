import streamlit as st
import fitz  # PyMuPDF for PDF text extraction
import pymongo
import requests
import google.generativeai as genai
from io import BytesIO
from PIL import Image
import re
import time

# MongoDB Setup
MONGO_URI = "mongodb+srv://BTI:BTI@newcluster.rk3luxk.mongodb.net/HireX?retryWrites=true&w=majority"  # Replace with your new MongoDB URI
DB_NAME = "HireX"
COLLECTION_NAME = "resumes"
FILTERED_COLLECTION = "filtered_candidates"

client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]
filtered_collection = db[FILTERED_COLLECTION]

# Gemini API Setup
GEMINI_API_KEY = "AIzaSyBw9qlfSD4LBiZpAQEf0jaUCd70Z_fnkB8"  # Replace with your new API key
genai.configure(api_key=GEMINI_API_KEY)
vision_model = genai.GenerativeModel("gemini-2.0-flash")
text_model = genai.GenerativeModel("gemini-2.0-flash")


def extract_text_from_pdf(pdf_file):
    """Extract text from a PDF file using PyMuPDF."""
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text = "\n".join([page.get_text("text") for page in doc])
    return text if text.strip() else "⚠ No text found in the PDF."


def fetch_candidates():
    """Fetch candidate resumes from MongoDB."""
    return list(collection.find())


def extract_text_from_image(image_url):
    """Convert image URL to bytes and extract text using Gemini Vision API."""
    response = requests.get(image_url)
    image = Image.open(BytesIO(response.content))
    
    if image.format not in ["JPEG", "PNG"]:
        return "Unsupported Image Format"
    
    gemini_response = vision_model.generate_content([image])
    return gemini_response.text if gemini_response.text else "Text Extraction Failed"


def evaluate_candidate(candidate, job_description):
    """Evaluate the candidate using Gemini for skill assessment and scoring."""
    resume_text = extract_text_from_image(candidate["public_link"])
    
    prompt = f"""
    You are an expert in resume screening. Analyze the following resume based on the provided job description.
    Assign a score out of 10 based on the relevance of the candidate's experience, projects, and skills.
    Highlight strengths and weaknesses.
    
    Job Description: {job_description}
    
    Resume Text: {resume_text}
    
    Response format:
    SCORE: (out of 10)
    PROS: (good aspects of the candidate)
    CONS: (areas for improvement)
    """
    
    response = text_model.generate_content(prompt)
    time.sleep(3)
    
    score_match = re.search(r"SCORE:\s*(\d+)", response.text)
    pros_match = re.search(r"PROS:\s*(.*)", response.text, re.DOTALL)
    cons_match = re.search(r"CONS:\s*(.*)", response.text, re.DOTALL)
    
    final_score = int(score_match.group(1)) if score_match else 0
    pros = pros_match.group(1).strip() if pros_match else "N/A"
    cons = cons_match.group(1).strip() if cons_match else "N/A"
    
    return final_score, pros, cons


def store_filtered_candidate(candidate, final_score, pros, cons):
    """Store the filtered candidate in MongoDB."""
    filtered_collection.insert_one({
        "name": candidate["name"],
        "email": candidate["email"],
        "final_score": final_score,
        "pros": pros,
        "cons": cons
    })


# Streamlit UI
st.title("🚀 AI-Powered Resume Screening")

# ✅ Upload Job Description
job_desc_file = st.file_uploader("📂 Upload Job Description (TXT or PDF)", type=["txt", "pdf"])

job_desc_text = ""
if job_desc_file:
    if job_desc_file.type == "application/pdf":
        job_desc_text = extract_text_from_pdf(job_desc_file)
    else:
        job_desc_text = job_desc_file.read().decode("utf-8")
    
    st.text_area("📄 Extracted Job Description:", job_desc_text, height=200)

# ✅ Fetch Candidates
if job_desc_text:
    st.write("🔄 Fetching candidates...")
    candidates = fetch_candidates()
    
    if candidates:
        st.write(f"✅ Successfully fetched {len(candidates)} candidates.")

        filtered_candidates = []
        for candidate in candidates:
            st.write(f"🔍 Evaluating {candidate['name']}...")
            final_score, pros, cons = evaluate_candidate(candidate, job_desc_text)
            st.write(f"**{candidate['name']}** - Final Score: {final_score}/10")

            if final_score > 5:  # Threshold for filtering
                store_filtered_candidate(candidate, final_score, pros, cons)
                filtered_candidates.append((candidate["name"], final_score, pros, cons))
        
        # ✅ Display Filtered Candidates
        if filtered_candidates:
            st.write("### 🎯 Top Candidates:")
            for name, score, pros, cons in filtered_candidates:
                st.write(f"**{name}** (Score: {score}/10)")
                st.write(f"✅ **Pros:** {pros}")
                st.write(f"❌ **Cons:** {cons}")
                st.write("---")
        else:
            st.warning("❌ No candidates passed the screening threshold.")
    else:
        st.warning("⚠ No candidates found in the database.")
