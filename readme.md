# AI Projects Portfolio

## AI Resume Builder with Llama-3.3-70B-Instruct

A production-ready web application that analyzes resumes using Meta's Llama-3.3-70B-Instruct model.

### Features
- Secure PostgreSQL authentication
- PDF/DOCX resume upload
- AI analysis via Hugging Face
 -Real-time ATS scoring

### Tech Stack
- Frontend: streamlit, React.js
- Backend: FastAPI (Python)
- Database: PostgreSQL
- AI: Llama-3.3-70B-Instruct
- Infrastructure: Docker

### Project commands used

py -3.11 -m venv venv
venv\Scripts\activate
To generate secret and keep it in .env file:
python generate_secret.py
To run Uvicorn:
Go to backend foleder where the main.py file is
cd backend\app
python -m uvicorn main:app --reload(wont work)
or cd backend
uvicorn app.main:app --reload


install OLLAMA: download OLLAMA 
open cmd and run :ollama pull llama3 or ollama pull mistral
