import pymongo

# Connect to MongoDB
MONGO_URI = "mongodb+srv://BTI:BTI@newcluster.rk3luxk.mongodb.net/HireX?retryWrites=true&w=majority"
client = pymongo.MongoClient(MONGO_URI)
db = client["HireX"]
collection = db["resumes"]

# Dummy Data
resumes = [
    {
        "name": "Harshith J",
        "email": "harshith@example.com",
        "phone": "+91 9876543210",
        "education": "B.Tech in Computer Science",
        "skills": ["Python", "Machine Learning", "React"],
        "experience": "2 years at XYZ Corp as Software Engineer",
        "public_link": "https://example.com/resumes/harshith.jpg"
    },
    {
        "name": "Mohithkumar M S",
        "email": "mohith@example.com",
        "phone": "+91 8765432109",
        "education": "M.Tech in Data Science",
        "skills": ["Deep Learning", "TensorFlow", "Flask"],
        "experience": "3 years at ABC Ltd as Data Scientist",
        "public_link": "https://example.com/resumes/mohithkumar.jpg"
    },
    {
        "name": "Mohammed Musharraf",
        "email": "musharraf@example.com",
        "phone": "+91 7654321098",
        "education": "B.E. in Information Technology",
        "skills": ["Java", "Spring Boot", "AWS"],
        "experience": "1.5 years at PQR Solutions as Backend Developer",
        "public_link": "https://example.com/resumes/musharraf.jpg"
    }
]

# Insert Data into MongoDB
collection.insert_many(resumes)
print("✅ Dummy resumes inserted successfully!")
