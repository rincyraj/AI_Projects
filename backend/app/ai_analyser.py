from huggingface_hub import InferenceClient
import os
from dotenv import load_dotenv
import time

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")

def clean_analysis_response(response_text: str) -> str:
    """
    Clean up the AI analysis response to remove formatting issues
    """
    import re
    
    # Remove emoji prefixes that might confuse parsing
    response_text = re.sub(r'[📌🔧📍📊]\s*', '', response_text)
    
    # Remove extra colons and formatting but keep content
    response_text = re.sub(r':\*', '', response_text)
    response_text = re.sub(r'•\s*\*', '• ', response_text)
    
    # Fix malformed ATS scores like "N/A/100" -> "N/A"
    response_text = re.sub(r'N/A/\d+', 'N/A', response_text)
    
    # Basic cleanup - remove empty lines and excessive whitespace
    lines = [line.strip() for line in response_text.split('\n') if line.strip()]
    
    return '\n'.join(lines)

# Models that are confirmed to work with provider="auto" [citation:5][citation:8][citation:9]
MODELS_TO_TRY = [
    "mistralai/Mixtral-8x7B-Instruct-v0.1",     # Confirmed working [citation:8]
    "meta-llama/Llama-3.3-70B-Instruct",         # Confirmed working [citation:8]
    "Qwen/Qwen2.5-Coder-32B-Instruct",           # Works with provider="auto" [citation:5]
    "HuggingFaceTB/SmolLM3-3B",                   # Works even without token [citation:1]
    "Qwen/QwQ-32B"                               # Works with hf-inference [citation:9]
]

def _local_text_generation(prompt: str, max_length: int = 800) -> str:
    """Fallback local text generation using transformers (if installed)."""
    try:
        from transformers import pipeline
        generator = pipeline("text-generation", model="distilgpt2")
        out = generator(prompt, max_length=max_length, num_return_sequences=1)
        # generator output is a list of dicts {"generated_text": ...}
        return out[0]["generated_text"].strip()
    except Exception as e:
        raise RuntimeError(
            "Local generation failed (transformers not installed or model not available). "
            "Install transformers or ensure the model is available." + str(e)
        )


def analyze_resume(text, job_role=None):
    """
    Analyze resume with automatic fallback between working models
    Optionally provide a job_role for role-specific analysis
    """
    # Build the prompt based on whether job_role is provided
    if job_role and job_role != "Select a job role...":
        user_prompt = f"""Analyze this resume for the role of "{job_role}" and provide a structured analysis with exactly these numbered sections:

1. Professional Summary - A brief overview of the candidate's background
2. Key Skills - List the most important skills found in the resume  
3. Strengths - Highlight what makes this candidate well-suited for a {job_role} role
4. Weaknesses or Missing Skills - What skills for {job_role} are missing or could be improved
5. Skills Match - List which required {job_role} skills are present (mark present skills with ✓ and missing skills with ✗)
6. ATS Score - Give a match score (0-100) based on how well the resume matches {job_role} requirements

IMPORTANT: 
- Use the exact section numbers and names shown above
- Do not repeat section headers within the content
- Keep each section focused on its topic
- Be concise but comprehensive

Resume: {text}"""
    else:
        user_prompt = f"""Analyze this resume and provide a structured analysis with exactly these numbered sections:

1. Professional Summary
2. Key Skills  
3. Strengths
4. Weaknesses
5. ATS Score (0-100)

IMPORTANT: 
- Use the exact section numbers and names shown above
- Do not repeat section headers within the content
- Keep each section focused on its topic
- Be concise but comprehensive

Resume: {text}"""
    
    for model_id in MODELS_TO_TRY:
        try:
            print(f"Trying model: {model_id}")
            
            # CRITICAL: Use provider="auto" instead of "hf-inference"
            client = InferenceClient(
                provider="auto",  # This lets HF route to the right backend
                api_key=HF_TOKEN
            )
            
            try:
                response = client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {
                            "role": "system", 
                            "content": "You are an expert resume analyst and recruitment specialist. Provide detailed, structured analysis with exactly the numbered sections requested. Do not repeat section headers within the content. Keep each section focused and concise. Use proper formatting with bullet points where appropriate."
                        },
                        {
                            "role": "user", 
                            "content": user_prompt
                        }
                    ],
                    max_tokens=1500,
                    temperature=0.1
                )

                analysis = response.choices[0].message.content
                
                # Clean up the response to remove repeated section headers and formatting issues
                analysis = clean_analysis_response(analysis)
                
                return {
                    "success": True,
                    "data": analysis,
                    "model": model_id,
                    "job_role": job_role
                }

            except Exception as e:
                error_message = str(e)
                print(f"Model {model_id} failed: {error_message}")

                # Detect usage/credit issues and fallback to local generation
                if "402" in error_message or "Payment Required" in error_message or "out of credits" in error_message.lower():
                    print("Inference credits exhausted - falling back to local generation (if available).")
                    try:
                        local_output = _local_text_generation(user_prompt, max_length=1200)
                        return {
                            "success": True,
                            "data": local_output,
                            "model": "local-distilgpt2-fallback",
                            "job_role": job_role
                        }
                    except Exception as local_e:
                        return {
                            "success": False,
                            "error": f"Inference credits exhausted and local fallback failed: {local_e}",
                            "model": model_id,
                            "job_role": job_role
                        }

                if "model_not_supported" in error_message or "not supported" in error_message.lower():
                    # Skip unsupported models
                    continue

                # Try next model
                continue
    
def improve_resume(resume_text, job_role=None, analysis=None):
    """
    Generate resume improvement suggestions based on analysis
    """
    # Build the prompt for improvement
    if job_role and job_role != "Select a job role...":
        user_prompt = f"""Based on this resume analysis, provide specific, actionable suggestions to improve the resume for a {job_role} position:

ANALYSIS:
{analysis}

ORIGINAL RESUME:
{resume_text}

Please provide exactly this format:

IMPROVEMENT SUGGESTIONS:
1. [Specific suggestion with clear action]
2. [Specific suggestion with clear action]
3. [Specific suggestion with clear action]
... (continue with numbered list)

IMPROVED RESUME:
[Complete revised resume text with all improvements applied, properly formatted for ATS. Include ALL sections from the original resume (contact info, summary, professional experience, education, certifications, skills, etc.) but improved and optimized. Do not remove any past roles or prior experience entries; keep every job listed and improve it.] 

IMPORTANT: Make suggestions specific and actionable like:
- "Add keywords: Include 'Python', 'Django', 'REST API' in your skills section"
- "Use action verbs: Change 'Worked on projects' to 'Developed and deployed web applications'"
- "Preserve all experience: Do not drop any job or role; include every position listed in the original resume"
- "Improve formatting: Use standard section headers like 'PROFESSIONAL EXPERIENCE'"

The IMPROVED RESUME section must contain the COMPLETE revised resume - not just suggestions. Include all relevant sections from the original resume but make them better, more professional, and ATS-optimized.

Focus on {job_role} requirements and ATS optimization."""
    else:
        user_prompt = f"""Based on this resume analysis, provide specific, actionable suggestions to improve the resume:

ANALYSIS:
{analysis}

ORIGINAL RESUME:
{resume_text}

Please provide exactly this format:

IMPROVEMENT SUGGESTIONS:
1. [Specific suggestion with clear action]
2. [Specific suggestion with clear action]
3. [Specific suggestion with clear action]
... (continue with numbered list)

IMPROVED RESUME:
[Complete revised resume text with all improvements applied, properly formatted for ATS. Include ALL sections from the original resume (contact info, summary, experience, education, skills, etc.) but improved and optimized.]

IMPORTANT: Make suggestions specific and actionable like:
- "Add relevant keywords for your target industry"
- "Use action verbs: Replace passive phrases with active verbs like 'Designed', 'Developed', 'Implemented'"
- "Remove unnecessary sections: Delete personal information not relevant to job applications"
- "Improve formatting: Use consistent formatting and clear section headers"

The IMPROVED RESUME section must contain the COMPLETE revised resume - not just suggestions. Include all relevant sections from the original resume but make them better, more professional, and ATS-optimized.

Focus on ATS optimization and professional presentation."""
    
    for model_id in MODELS_TO_TRY:
        try:
            print(f"Trying model: {model_id} for resume improvement")
            
            client = InferenceClient(
                provider="auto",
                api_key=HF_TOKEN
            )
            
            try:
                response = client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {
                            "role": "system", 
                            "content": """You are an expert resume writer and ATS optimization specialist. Provide specific, actionable suggestions that are easy to implement. 

CRITICAL: The IMPROVED RESUME section must contain the COMPLETE revised resume text - not just suggestions or partial content. Include ALL sections from the original resume (contact info, summary, experience, education, skills, etc.) but improved and optimized for ATS.

Format your response exactly like this:

IMPROVEMENT SUGGESTIONS:
1. [Actionable suggestion]: [Brief explanation]
2. [Actionable suggestion]: [Brief explanation]
3. [Actionable suggestion]: [Brief explanation]
... (continue numbering)

IMPROVED RESUME:
[Complete revised resume with all suggestions implemented - this should be a full, professional resume]

Examples of good suggestions:
- "Add keywords: Include 'Python', 'Django', 'REST API' in your skills section to match job requirements"
- "Use action verbs: Change 'Worked on projects' to 'Developed and deployed web applications using Python'"
- "Remove unnecessary sections: Delete 'Personal Interests' and 'Visa Details' sections"
- "Improve formatting: Use consistent bullet points and standard section headers like 'PROFESSIONAL EXPERIENCE'"

Make each suggestion specific and immediately actionable. The IMPROVED RESUME must be complete and professional."""
                        },
                        {
                            "role": "user", 
                            "content": user_prompt
                        }
                    ],
                    max_tokens=2000,
                    temperature=0.2
                )

                improvement = response.choices[0].message.content

                return {
                    "success": True,
                    "data": improvement,
                    "model": model_id
                }

            except Exception as e:
                error_message = str(e)
                print(f"Model {model_id} failed for improvement: {error_message}")

                if "402" in error_message or "Payment Required" in error_message or "out of credits" in error_message.lower():
                    print("Inference credits exhausted - falling back to local generation (if available).")
                    try:
                        local_output = _local_text_generation(user_prompt, max_length=1800)
                        return {
                            "success": True,
                            "data": local_output,
                            "model": "local-distilgpt2-fallback"
                        }
                    except Exception as local_e:
                        return {
                            "success": False,
                            "error": f"Inference credits exhausted and local fallback failed: {local_e}",
                            "model": model_id
                        }

                if "model_not_supported" in error_message or "not supported" in error_message.lower():
                    continue

                continue
    
    return {
        "success": False,
        "error": "All models failed",
        "message": "Could not generate improvements. Please try again later."
    }