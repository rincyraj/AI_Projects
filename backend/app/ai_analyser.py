from huggingface_hub import InferenceClient
import os
from dotenv import load_dotenv
import re

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")

# Initialize client once
client = InferenceClient(
    provider="auto",
    api_key=HF_TOKEN
)

# Models to try
MODELS_TO_TRY = [
    "mistralai/Mixtral-8x7B-Instruct-v0.1",
    "meta-llama/Llama-3.3-70B-Instruct",
    "Qwen/Qwen2.5-Coder-32B-Instruct",
    "HuggingFaceTB/SmolLM3-3B",
    "Qwen/QwQ-32B"
]


def clean_analysis_response(response_text: str) -> str:
    """
    Clean AI response formatting
    """
    if not response_text:
        return ""

    response_text = re.sub(r'[📌🔧📍📊]\s*', '', response_text)
    response_text = re.sub(r':\*', '', response_text)
    response_text = re.sub(r'N/A/\d+', 'N/A', response_text)

    lines = [line.strip() for line in response_text.split('\n') if line.strip()]
    return "\n".join(lines)


def analyze_resume(text, job_role=None):
    """
    Analyze resume using HuggingFace models with fallback
    """

    # Prevent very large prompts
    text = text[:8000]

    if job_role:
        user_prompt = f"""
Analyze this resume for the role of "{job_role}" and provide:

1. Professional Summary
2. Key Skills
3. Strengths
4. Weaknesses or Missing Skills
5. Skills Match
6. ATS Score (0-100)

Resume:
{text}
"""
    else:
        user_prompt = f"""
Analyze this resume and provide:

1. Professional Summary
2. Key Skills
3. Strengths
4. Weaknesses
5. ATS Score (0-100)

Resume:
{text}
"""

    for model_id in MODELS_TO_TRY:

        print(f"Trying model: {model_id}")

        try:

            response = client.chat.completions.create(
                model=model_id,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional resume analyst."
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                max_tokens=1200,
                temperature=0.2
            )

            if not response or not response.choices:
                continue

            analysis = response.choices[0].message.content

            analysis = clean_analysis_response(analysis)

            return {
                "success": True,
                "data": analysis,
                "model": model_id,
                "job_role": job_role
            }

        except Exception as e:

            error_message = str(e)
            print(f"{model_id} failed: {error_message}")

            # Skip unsupported models
            if "not supported" in error_message.lower():
                continue

            # Skip credit issues
            if "402" in error_message or "credit" in error_message.lower():
                continue

    return {
        "success": False,
        "error": "All models failed"
    }


def improve_resume(resume_text, job_role=None, analysis=None):
    """
    Generate resume improvement suggestions
    """

    resume_text = resume_text[:8000]

    user_prompt = f"""
Improve this resume based on the analysis.

Analysis:
{analysis}

Original Resume:
{resume_text}

Provide:

1. Improvement Suggestions
2. Fully Improved Resume
"""

    for model_id in MODELS_TO_TRY:

        try:

            print(f"Trying model: {model_id}")

            response = client.chat.completions.create(
                model=model_id,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert resume writer."
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                max_tokens=1500,
                temperature=0.2
            )

            if not response or not response.choices:
                continue

            improvement = response.choices[0].message.content

            return {
                "success": True,
                "data": improvement,
                "model": model_id
            }

        except Exception as e:

            error_message = str(e)
            print(f"{model_id} failed: {error_message}")

            if "not supported" in error_message.lower():
                continue

            if "credit" in error_message.lower():
                continue

    return {
        "success": False,
        "error": "All models failed"
    }