from huggingface_hub import InferenceClient
import os
from dotenv import load_dotenv
import time

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")

# Models that are confirmed to work with provider="auto" [citation:5][citation:8][citation:9]
MODELS_TO_TRY = [
    "mistralai/Mixtral-8x7B-Instruct-v0.1",     # Confirmed working [citation:8]
    "meta-llama/Llama-3.3-70B-Instruct",         # Confirmed working [citation:8]
    "Qwen/Qwen2.5-Coder-32B-Instruct",           # Works with provider="auto" [citation:5]
    "HuggingFaceTB/SmolLM3-3B",                   # Works even without token [citation:1]
    "Qwen/QwQ-32B"                               # Works with hf-inference [citation:9]
]

def analyze_resume(text):
    """
    Analyze resume with automatic fallback between working models
    """
    for model_id in MODELS_TO_TRY:
        try:
            print(f"Trying model: {model_id}")
            
            # CRITICAL: Use provider="auto" instead of "hf-inference"
            client = InferenceClient(
                provider="auto",  # This lets HF route to the right backend
                api_key=HF_TOKEN
            )
            
            response = client.chat.completions.create(
                model=model_id,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a resume analysis expert. Provide detailed analysis."
                    },
                    {
                        "role": "user", 
                        "content": f"""Analyze this resume and provide:
1. Professional Summary
2. Key Skills
3. Strengths
4. Weaknesses
5. ATS Score (0-100)

Resume: {text}"""
                    }
                ],
                max_tokens=1000,
                temperature=0.1
            )
            
            analysis = response.choices[0].message.content
            
            return {
                "success": True,
                "data": analysis,
                "model": model_id
            }
            
        except Exception as e:
            print(f"Model {model_id} failed: {e}")
            continue
    
    return {
        "success": False,
        "error": "All models failed",
        "message": "Could not find a working model. Please try again later."
    }