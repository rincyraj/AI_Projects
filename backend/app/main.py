# app/main.py
import time

from fastapi import FastAPI, Depends, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import User
from app.auth import hash_password, verify_password, create_access_token, verify_access_token
from fastapi import FastAPI,UploadFile, File
from app.routers import resume
from app.auth import get_current_user


app = FastAPI()

# app.include_router(auth.router)
app.include_router(resume.router)
# Create tables
Base.metadata.create_all(bind=engine)



# Enable CORS if frontend is on another origin
#origins = ["http://localhost:3000"]  # change if needed
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/register")
def register(email: str, password: str, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "User registered successfully"}


@app.post("/login")
def login(response: Response, email: str, password: str, db: Session = Depends(get_db)):
    start = time.time()
    user = db.query(User).filter(User.email == email).first()
    print("DB query:", time.time() - start)
    start = time.time()     
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    print("Password verify:", time.time() - start)

    access_token = create_access_token({"sub": user.email})

    # Set HTTP-only cookie
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=1800,  # 30 minutes
        secure=False,  # set True in production with HTTPS
        samesite="lax"
    )

    return {"message": "Login successful","token":access_token}


# Dependency to get current user from cookie
def get_current_user_from_cookie(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if token.startswith("Bearer "):
        token = token.split(" ")[1]

    try:
        user_email = verify_access_token(token)
        return user_email
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# # Protected route example: Resume analysis
# @app.post("/analyze_resume")
# def analyze_resume(current_user: str = Depends(get_current_user_from_cookie)):
#     # Replace this with your GENAI resume analyser logic
#     return {"user": current_user, "result": "Resume analyzed successfully"}



# @app.post("/analyze_resume")
# async def analyze_resume(
#     file: UploadFile = File(...),
#     current_user: str = Depends(get_current_user)
    
# ):
#     print("cutrrr",current_user)
#     if file.filename.endswith(".pdf"):
#         text = extract_text_from_pdf(file.file)

#     elif file.filename.endswith(".docx"):
#         text = extract_text_from_docx(file.file)

#     else:
#         raise HTTPException(status_code=400, detail="Unsupported file type")

#     result = ai_analyze_resume(text)

#     return {
#         "user": current_user,
#         "analysis": result
#     }