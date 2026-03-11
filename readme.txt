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