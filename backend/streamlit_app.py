import streamlit as st
import requests
import json
import re
import io
import base64

# PDF and DOCX processing libraries for local text extraction
try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    import docx
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False

def extract_text_from_pdf_local(file_bytes: bytes) -> str:
    """Extract text from PDF file locally"""
    if not PDF_SUPPORT:
        return ""
    
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page_num, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        print(f"Local PDF extraction failed: {e}")
        return ""

def extract_text_from_docx_local(file_bytes: bytes) -> str:
    """Extract text from DOCX file locally"""
    if not DOCX_SUPPORT:
        return ""
    
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text
    except Exception as e:
        print(f"Local DOCX extraction failed: {e}")
        return ""

def apply_selected_improvements(resume_text: str, selected_suggestions: list) -> str:
    """
    Apply selected improvements to the resume text
    """
    enhanced_resume = resume_text
    
    for suggestion in selected_suggestions:
        suggestion = suggestion.lower()
        
        # Apply common improvement patterns
        if "add keywords" in suggestion or "include" in suggestion:
            # Extract keywords from suggestion
            keywords_match = re.search(r'include\s*[\'"]([^\'"]+)[\'"]', suggestion)
            if keywords_match:
                keywords = keywords_match.group(1)
                # Add keywords to skills section if it exists
                if "skills" in enhanced_resume.lower():
                    # Find skills section and add keywords
                    skills_pattern = r'(skills?:?.*?)(?=\n\n|\n[A-Z]|\Z)'
                    enhanced_resume = re.sub(
                        skills_pattern, 
                        rf'\1\n• {keywords}', 
                        enhanced_resume, 
                        flags=re.IGNORECASE | re.DOTALL
                    )
                else:
                    # Add skills section at the end
                    enhanced_resume += f"\n\nSKILLS\n• {keywords}"
        
        elif "use action verbs" in suggestion:
            # Replace passive phrases with action verbs
            action_verb_replacements = {
                r'\bworked on\b': 'developed',
                r'\bresponsible for\b': 'managed',
                r'\bhelped with\b': 'assisted in',
                r'\bparticipated in\b': 'contributed to',
                r'\binvolved in\b': 'engaged in'
            }
            for old, new in action_verb_replacements.items():
                enhanced_resume = re.sub(old, new, enhanced_resume, flags=re.IGNORECASE)
        
        elif "remove" in suggestion and ("personal" in suggestion or "interests" in suggestion):
            # Remove personal interests section
            enhanced_resume = re.sub(r'\n.*?(personal interests?|hobbies?|interests?:?).*?(?=\n\n|\n[A-Z]|\Z)', '', enhanced_resume, flags=re.IGNORECASE | re.DOTALL)
        
        elif "formatting" in suggestion or "headers" in suggestion:
            # Improve section headers
            header_improvements = {
                r'\bwork experience\b': 'PROFESSIONAL EXPERIENCE',
                r'\beducation\b': 'EDUCATION',
                r'\bskills\b': 'SKILLS',
                r'\bprojects\b': 'PROJECTS',
                r'\bcertifications?\b': 'CERTIFICATIONS'
            }
            for old, new in header_improvements.items():
                enhanced_resume = re.sub(old, new, enhanced_resume, flags=re.IGNORECASE)
    
    return enhanced_resume

API_URL = "http://127.0.0.1:8000"

# List of job roles for analysis
JOB_ROLES = [
    "Select a job role...",
    "Frontend Developer",
    "Backend Developer",
    "Full Stack Developer",
    "Data Scientist",
    "Machine Learning Engineer",
    "DevOps Engineer",
    "Cloud Architect",
    "AI Engineer",
    "Product Manager",
    "UX/UI Designer",
    "Mobile Developer",
    "QA Engineer",
    "Business Analyst",
    "System Administrator"
]

st.set_page_config(
    page_title="AI Resume Analyzer",
    page_icon="📄",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #667eea;
        text-align: center;
        margin-bottom: 2rem;
    }
    .analysis-section {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        border-left: 5px solid #667eea;
    }
    .section-title {
        color: #333;
        font-size: 1.3rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    .skill-tag {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        display: inline-block;
        margin: 0.2rem;
        font-size: 0.9rem;
    }
    .score-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        font-size: 2rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-header'>📄 AI Resume Analyzer</h1>", unsafe_allow_html=True)

# Initialize session state for analysis result if not exists
if "analysis_result" not in st.session_state:
    st.session_state["analysis_result"] = None

# ============================================
# DEFINE HELPER FUNCTIONS FIRST (BEFORE THEY'RE USED)
# ============================================

def display_section(section_name, content_lines):
    """Helper function to display formatted sections"""
    if not content_lines:
        return
        
    content = " ".join(content_lines).strip()
    
    if section_name == "ATS Score":
        # Extract score number - look for the actual score (not section numbers)
        # Priority: "score around X", "score of X", "X out of 100", or highest number
        score_patterns = [
            r'score around (\d+)',  # "score around 85"
            r'score of (\d+)',      # "score of 85" 
            r'(\d+) out of 100',    # "85 out of 100"
            r'(\d+)/100',           # "85/100"
        ]
        
        score = "N/A"
        for pattern in score_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                score = match.group(1)
                break
        
        # If no specific pattern found, find all numbers and take the highest reasonable score (10-100)
        if score == "N/A":
            all_numbers = re.findall(r'\b(\d{1,3})\b', content)
            valid_scores = [int(num) for num in all_numbers if 10 <= int(num) <= 100]
            if valid_scores:
                score = str(max(valid_scores))  # Take the highest valid score
        
        st.markdown(f"<div class='score-box'>{score}/100</div>", unsafe_allow_html=True)
        st.markdown(f"**{section_name}**")
        st.write(content)
    
    elif section_name == "Key Skills":
        st.markdown(f"### 🔧 {section_name}")
        # Extract skills (look for bullet points)
        skills = re.findall(r'[\*\•]\s*([^\*\•\n]+)', content)
        if skills:
            skills_html = "".join([f'<span class="skill-tag">{skill.strip()}</span>' for skill in skills])
            st.markdown(f"<div>{skills_html}</div>", unsafe_allow_html=True)
        else:
            # If no bullet points, split by commas
            skills = [s.strip() for s in content.split(',') if s.strip()]
            if skills:
                skills_html = "".join([f'<span class="skill-tag">{skill}</span>' for skill in skills])
                st.markdown(f"<div>{skills_html}</div>", unsafe_allow_html=True)
            else:
                st.write(content)
    
    else:
        st.markdown(f"### 📌 {section_name}")
        # Format bullet points
        if '*' in content or '•' in content:
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('*') or line.startswith('•'):
                    st.markdown(f"• {line[1:].strip()}")
                elif line:
                    st.markdown(line)
        else:
            st.write(content)
    
    st.markdown("---")

def improve_resume():
    """Function to improve the resume based on analysis"""
    if "analysis_result" not in st.session_state or st.session_state["analysis_result"] is None:
        st.error("❌ No analysis result found. Please analyze a resume first.")
        return
    
    result = st.session_state["analysis_result"]
    job_role = result.get("job_role", None)
    
    # Get the original resume text (we need to store it during upload)
    if "original_resume_text" not in st.session_state:
        st.error("❌ Original resume text not found. Please re-upload and analyze your resume.")
        return
    
    original_text = st.session_state["original_resume_text"]
    
    with st.spinner("🤖 AI is generating resume improvements... This may take a moment."):
        try:
            # Call the improvement endpoint
            response = requests.post(
                f"{API_URL}/improve_resume",
                json={
                    "resume_text": original_text,
                    "job_role": job_role,
                    "analysis": result.get("data", ""),
                    "format": "json"  # Get JSON first for display
                },
                headers={
                    "Authorization": f"Bearer {st.session_state.get('token', '')}"
                },
                timeout=180  # Longer timeout for improvement
            )
            
            if response.status_code == 200:
                improvement_result = response.json()
                if improvement_result.get("success"):
                    # Store improvement result
                    st.session_state["improvement_result"] = improvement_result
                    
                    # Show success and scroll to results
                    st.success("✅ Resume improvement suggestions generated!")
                    st.rerun()
                else:
                    st.error(f"❌ Improvement failed: {improvement_result.get('message', 'Unknown error')}")
            else:
                st.error(f"❌ Improvement failed: {response.text}")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

def download_improved_resume_pdf(resume_text=None):
    """Download the improved resume as PDF"""
    if "analysis_result" not in st.session_state or st.session_state["analysis_result"] is None:
        st.error("❌ No analysis result found.")
        return
    
    if "original_resume_text" not in st.session_state:
        st.error("❌ Original resume text not found.")
        return
    
    result = st.session_state["analysis_result"]
    job_role = result.get("job_role", None)
    
    # Use provided resume text or fall back to original
    text_to_use = resume_text if resume_text else st.session_state["original_resume_text"]
    
    with st.spinner("📄 Generating PDF..."):
        try:
            # Call the improvement endpoint with PDF format
            response = requests.post(
                f"{API_URL}/improve_resume",
                json={
                    "resume_text": text_to_use,
                    "job_role": job_role,
                    "analysis": result.get("data", ""),
                    "format": "pdf"
                },
                headers={
                    "Authorization": f"Bearer {st.session_state.get('token', '')}"
                },
                timeout=180
            )
            
            if response.status_code == 200:
                # Return the PDF data
                return response.content
            else:
                st.error(f"❌ PDF generation failed: {response.text}")
                return None
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            return None

# ============================================
# MAIN APP LAYOUT
# ============================================

# Create two columns for layout
col1, col2 = st.columns([1, 1])

with col1:
    # -------------------
    # LOGIN / REGISTER SECTION
    # -------------------
    # Create tabs for Login and Register
    auth_tab1, auth_tab2 = st.tabs(["🔐 Login", "📝 Register"])
    
    with auth_tab1:
        # LOGIN FORM
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="Enter your email", key="login_email")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")
            login_button = st.form_submit_button("Login", use_container_width=True)
            
            if login_button:
                with st.spinner("Logging in..."):
                    try:
                        response = requests.post(
                            f"{API_URL}/login",
                            params={"email": email, "password": password},
                            timeout=30
                        )
                        
                        if response.status_code == 200:
                            token = response.json()["token"]
                            st.session_state["token"] = token
                            st.success("✅ Login successful!")
                            st.rerun()
                        else:
                            st.error(f"❌ Login failed: {response.text}")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
    
    with auth_tab2:
        # REGISTER FORM
        with st.form("register_form"):
            reg_email = st.text_input("Email", placeholder="Enter your email", key="register_email")
            reg_password = st.text_input("Password", type="password", placeholder="Enter your password", key="register_password")
            reg_confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password", key="confirm_password")
            register_button = st.form_submit_button("Register", use_container_width=True)
            
            if register_button:
                if not reg_email or not reg_password:
                    st.error("❌ Please fill in all fields")
                elif reg_password != reg_confirm_password:
                    st.error("❌ Passwords do not match")
                else:
                    with st.spinner("Creating account..."):
                        try:
                            response = requests.post(
                                f"{API_URL}/register",
                                params={"email": reg_email, "password": reg_password},
                                timeout=30
                            )
                            
                            if response.status_code == 200:
                                st.success("✅ Registration successful! Please login with your credentials.")
                            else:
                                st.error(f"❌ Registration failed: {response.text}")
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
    
    # Show login status
    if "token" in st.session_state:
        st.success("✅ You are logged in")
        if st.button("Logout", use_container_width=True):
            # Clear all session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

with col2:
    # -------------------
    # RESUME UPLOAD SECTION
    # -------------------
    st.markdown("### 📤 Upload Resume & Select Role")
    
    # Job role selector
    selected_role = st.selectbox(
        "Select Target Job Role",
        JOB_ROLES,
        help="Choose the job role you want to match your resume against"
    )
    
    uploaded_file = st.file_uploader(
        "Choose a file (PDF or DOCX)",
        type=["pdf", "docx"],
        help="Upload your resume in PDF or DOCX format"
    )
    
    # Show file info if uploaded
    if uploaded_file is not None:
        st.caption(f"📎 File: {uploaded_file.name} ({uploaded_file.type}, {uploaded_file.size} bytes)")
    
    analyze_button = st.button("🚀 Analyze Resume", use_container_width=True, type="primary")
    
    if analyze_button:
        token = st.session_state.get("token")
        
        if not token:
            st.warning("⚠️ Please login first")
        elif not uploaded_file:
            st.warning("⚠️ Please upload a resume")
        elif selected_role == "Select a job role...":
            st.warning("⚠️ Please select a job role")
        else:
            # Extract text locally for improvement feature
            file_bytes = uploaded_file.getvalue()
            filename = uploaded_file.name.lower()
            
            original_text = ""
            if filename.endswith('.pdf'):
                original_text = extract_text_from_pdf_local(file_bytes)
            elif filename.endswith('.docx'):
                original_text = extract_text_from_docx_local(file_bytes)
            
            if original_text:
                st.session_state["original_resume_text"] = original_text
            
            # Prepare file for upload
            files = {
                "file": (uploaded_file.name, file_bytes, uploaded_file.type)
            }
            
            headers = {
                "Authorization": f"Bearer {token}"
            }
            
            with st.spinner("🤖 AI is analyzing your resume... This may take a moment."):
                try:
                    # Use the main endpoint for file uploads (not _json)
                    response = requests.post(
                        f"{API_URL}/analyze_resume",  # Changed from analyze_resume_json
                        files=files,
                        headers=headers,
                        params={"job_role": selected_role},
                        timeout=120  # Increased timeout for larger files
                    )
                    
                    if response.status_code == 200:
                        # Check if response is JSON or HTML
                        content_type = response.headers.get("content-type", "")
                        
                        if "application/json" in content_type:
                            result = response.json()
                            st.session_state["analysis_result"] = result
                            # Clear any previous improvement results when new analysis is done
                            if "improvement_result" in st.session_state:
                                del st.session_state["improvement_result"]
                            st.success("✅ Analysis complete!")
                            st.rerun()
                        else:
                            # It's HTML - display directly
                            st.session_state["analysis_result"] = None
                            st.markdown("### 📊 Analysis Results")
                            st.components.v1.html(response.text, height=800, scrolling=True)
                    else:
                        st.error(f"❌ Analysis failed: {response.text}")
                except requests.exceptions.Timeout:
                    st.error("❌ Request timed out. The file might be too large.")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

# -------------------
# DISPLAY RESULTS (for JSON responses)
# -------------------
if st.session_state["analysis_result"] is not None:
    st.markdown("---")
    
    result = st.session_state["analysis_result"]
    job_role = result.get("job_role", None)
    
    if job_role and job_role != "Select a job role...":
        st.markdown(f"## 📊 Analysis Results for **{job_role}**")
        st.info(f"📍 Resume analyzed for: **{job_role}** role")
    else:
        st.markdown("## 📊 Analysis Results")
    
    # Check if analysis was successful
    if result.get("success"):
        analysis_text = result.get("data", "")
        model_used = result.get("model", "Unknown")
        
        # Debug: Check if we have analysis text
        if not analysis_text or analysis_text.strip() == "":
            st.error("❌ No analysis content received from AI model")
            st.info("This might be due to API issues or the model not responding. Try again.")
          
        
        # Parse the analysis text into sections
        sections = analysis_text.split('\n')
        
        # Create tabs for different views
        tab1, tab2 = st.tabs(["📋 Formatted View", "📝 Raw Analysis"])
        
        with tab1:
            # Debug: Show raw analysis first
            with st.expander("🔍 Debug: Raw Analysis Response", expanded=False):
                st.code(analysis_text, language="text")
            
            # Parse and display in formatted way
            current_section = ""
            current_content = []
            
            for line in sections:
                line = line.strip()
                if not line:
                    continue
                
                # More flexible section header detection - look for numbered sections or standalone headers
                if re.match(r'^1\.', line) or (line.lower().startswith('professional summary') and not current_section):
                    if current_section:
                        display_section(current_section, current_content)
                    current_section = "Professional Summary"
                    cleaned = re.sub(r'^1\.\s*', '', line)
                    cleaned = re.sub(r'^Professional Summary\s*', '', cleaned, flags=re.IGNORECASE)
                    current_content = [cleaned] if cleaned else []
                elif re.match(r'^2\.', line) or (line.lower().startswith('key skills') and not current_section):
                    if current_section:
                        display_section(current_section, current_content)
                    current_section = "Key Skills"
                    cleaned = re.sub(r'^2\.\s*', '', line)
                    cleaned = re.sub(r'^Key Skills\s*', '', cleaned, flags=re.IGNORECASE)
                    current_content = [cleaned] if cleaned else []
                elif re.match(r'^3\.', line) or (line.lower().startswith('strengths') and not current_section):
                    if current_section:
                        display_section(current_section, current_content)
                    current_section = "Strengths"
                    cleaned = re.sub(r'^3\.\s*', '', line)
                    cleaned = re.sub(r'^Strengths\s*', '', cleaned, flags=re.IGNORECASE)
                    current_content = [cleaned] if cleaned else []
                elif re.match(r'^4\.', line) or ((line.lower().startswith('weaknesses') or line.lower().startswith('missing skills')) and not current_section):
                    if current_section:
                        display_section(current_section, current_content)
                    current_section = "Weaknesses or Missing Skills"
                    cleaned = re.sub(r'^4\.\s*', '', line)
                    cleaned = re.sub(r'^(Weaknesses|Missing Skills|Weaknesses or Missing Skills)\s*', '', cleaned, flags=re.IGNORECASE)
                    current_content = [cleaned] if cleaned else []
                elif re.match(r'^5\.', line) or (line.lower().startswith('skills match') and not current_section):
                    if current_section:
                        display_section(current_section, current_content)
                    current_section = "Skills Match"
                    cleaned = re.sub(r'^5\.\s*', '', line)
                    cleaned = re.sub(r'^Skills Match\s*', '', cleaned, flags=re.IGNORECASE)
                    current_content = [cleaned] if cleaned else []
                elif re.match(r'^[56]\.', line) or (line.lower().startswith('ats score') and not current_section):
                    if current_section:
                        display_section(current_section, current_content)
                    current_section = "ATS Score"
                    cleaned = re.sub(r'^[56]\.\s*', '', line)
                    cleaned = re.sub(r'^ATS Score\s*', '', cleaned, flags=re.IGNORECASE)
                    current_content = [cleaned] if cleaned else []
                else:
                    # Add content to current section if we have one active
                    if current_section and line:
                        current_content.append(line)
            
            # Display last section
            if current_section:
                display_section(current_section, current_content)
            
            # Check if any sections were parsed - if not, show raw analysis
            sections_parsed = bool(current_section)
            if not sections_parsed:
                st.warning("⚠️ Unable to parse analysis into sections. Check the Raw Analysis tab for the full response.")
                with st.expander("📄 Raw Analysis (Formatted View)", expanded=True):
                    st.text_area("Raw Analysis", analysis_text, height=300)
        
        with tab2:
            # Show raw analysis text
            st.text_area("Raw Analysis Output", analysis_text, height=400)
        
        # Show model info
        st.info(f"🤖 Analysis powered by: **{model_used}**")
        
        # Add download button
        st.download_button(
            label="📥 Download Analysis",
            data=analysis_text,
            file_name="resume_analysis.txt",
            mime="text/plain"
        )
        
        # Add resume improvement button
        if st.button("✨ Improve Resume", use_container_width=True, type="secondary"):
            improve_resume()
        
        # Add clear button
        if st.button("🔄 Clear Results"):
            st.session_state["analysis_result"] = None
            if "improvement_result" in st.session_state:
                del st.session_state["improvement_result"]
            if "original_resume_text" in st.session_state:
                del st.session_state["original_resume_text"]
            st.rerun()
    else:
        st.error(f"❌ Analysis failed: {result.get('message', 'Unknown error')}")

# -------------------
# DISPLAY IMPROVEMENT RESULTS
# -------------------
if "improvement_result" in st.session_state and st.session_state["improvement_result"] is not None:
    st.markdown("---")
    st.markdown("## ✨ Resume Improvement Suggestions")
    
    improvement_result = st.session_state["improvement_result"]
    
    if improvement_result.get("success"):
        improvement_text = improvement_result.get("data", "")
        model_used = improvement_result.get("model", "Unknown")
        
        # Create tabs for improvement view
        imp_tab1, imp_tab2 = st.tabs(["📝 Improvement Suggestions", "📄 Improved Resume"])
        
        with imp_tab1:
            # Parse and display improvement suggestions
            sections = improvement_text.split('\n')
            current_section = ""
            current_content = []
            suggestions_content = ""
            improved_resume_content = ""
            
            for line in sections:
                line = line.strip()
                if not line:
                    continue
                    
                if "IMPROVEMENT SUGGESTIONS" in line.upper():
                    if current_section:
                        display_section(current_section, current_content)
                    current_section = "Improvement Suggestions"
                    current_content = []
                elif "IMPROVED RESUME" in line.upper():
                    if current_section:
                        display_section(current_section, current_content)
                    current_section = "Improved Resume"
                    current_content = []
                else:
                    if line:
                        current_content.append(line)
                        # Collect content for downloads
                        if current_section == "Improvement Suggestions":
                            suggestions_content += line + "\n"
                        elif current_section == "Improved Resume":
                            improved_resume_content += line + "\n"
            
            # Display last section
            if current_section:
                display_section(current_section, current_content)
            
            # Add quick action checklist
            if suggestions_content:
                st.markdown("---")
                st.markdown("### ✅ Quick Action Checklist")
                st.markdown("*Check the improvements you want to apply to your resume*")
                
                # Parse suggestions and create checkboxes
                suggestions_lines = [line.strip() for line in suggestions_content.split('\n') if line.strip() and line[0].isdigit()]
                
                # Initialize session state for selected suggestions if not exists
                if "selected_suggestions" not in st.session_state:
                    st.session_state.selected_suggestions = []
                
                selected_suggestions = []
                
                for i, suggestion in enumerate(suggestions_lines[:10]):  # Limit to first 10 suggestions
                    if suggestion and len(suggestion) > 3:
                        # Extract the main action from the suggestion
                        if ':' in suggestion:
                            action = suggestion.split(':', 1)[0].strip()
                            details = suggestion.split(':', 1)[1].strip()
                        else:
                            action = suggestion[:50] + "..." if len(suggestion) > 50 else suggestion
                            details = ""
                        
                        # Create checkbox with unique key
                        checkbox_key = f"suggestion_{i}_{hash(suggestion)}"
                        is_checked = st.checkbox(
                            f"✅ {action}", 
                            key=checkbox_key,
                            help=details if details else action
                        )
                        
                        if is_checked:
                            selected_suggestions.append(suggestion)
                
                # Store selected suggestions in session state
                st.session_state.selected_suggestions = selected_suggestions
                
                # Show selected count
                if selected_suggestions:
                    st.success(f"📋 {len(selected_suggestions)} improvement(s) selected")
                    
                    # Add button to apply selected improvements
                    if st.button("🚀 Apply Selected Improvements", type="primary"):
                        with st.spinner("Applying improvements..."):
                            # Get the current improved resume or original if no improved version
                            base_resume = improved_resume_content.strip() if improved_resume_content.strip() else st.session_state.get("original_resume_text", "")
                            
                            # Apply selected improvements
                            enhanced_resume = apply_selected_improvements(base_resume, selected_suggestions)
                            
                            # Store the enhanced resume
                            st.session_state["manually_enhanced_resume"] = enhanced_resume
                            
                            st.success("✅ Improvements applied successfully!")
                            st.rerun()
                else:
                    st.info("💡 Select improvements above to apply them to your resume")
        
        with imp_tab2:
            # Show the improved resume text
            # Priority: manually enhanced > AI improved > original
            display_resume = ""
            if "manually_enhanced_resume" in st.session_state:
                display_resume = st.session_state["manually_enhanced_resume"]
                st.info("📝 Showing resume with your selected improvements applied")
            elif improved_resume_content:
                display_resume = improved_resume_content.strip()
            else:
                display_resume = improvement_text
            
            st.text_area("Improved Resume Content", display_resume, height=400)
            
            # Show before/after comparison if we have original text
            if "original_resume_text" in st.session_state:
                st.markdown("---")
                st.markdown("### 🔄 Before/After Comparison")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**📄 Original Resume**")
                    st.text_area(
                        "Original", 
                        st.session_state["original_resume_text"][:1000] + "..." if len(st.session_state["original_resume_text"]) > 1000 else st.session_state["original_resume_text"],
                        height=300,
                        disabled=True
                    )
                
                with col2:
                    st.markdown("**✨ Enhanced Resume**")
                    enhanced_preview = display_resume[:1000] + "..." if len(display_resume) > 1000 else display_resume
                    st.text_area(
                        "Enhanced", 
                        enhanced_preview,
                        height=300,
                        disabled=True
                    )
        
        # Show model info
        st.info(f"🤖 Improvements powered by: **{model_used}**")
        
        # Add download buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.download_button(
                label="📥 Download Suggestions",
                data=suggestions_content.strip() if suggestions_content else improvement_text,
                file_name="resume_improvement_suggestions.txt",
                mime="text/plain",
                use_container_width=True
            )
        
        with col2:
            st.download_button(
                label="📄 Download as TXT",
                data=display_resume,
                file_name="improved_resume.txt",
                mime="text/plain",
                use_container_width=True
            )
        
        with col3:
            # PDF download button
            if st.button("📕 Download as PDF", use_container_width=True, key="pdf_download_btn"):
                # Use the display_resume for PDF generation
                pdf_data = download_improved_resume_pdf(display_resume)
                if pdf_data:
                    # Create a download link using HTML
                    b64_pdf = base64.b64encode(pdf_data).decode()
                    href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="improved_resume.pdf" style="text-decoration: none;"><button style="background-color: #FF6B6B; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; width: 100%;">📕 Download PDF Now</button></a>'
                    st.markdown(href, unsafe_allow_html=True)
                else:
                    st.error("Failed to generate PDF")
        
        # Add clear improvement button
        if st.button("🔄 Clear Improvements"):
            del st.session_state["improvement_result"]
            st.rerun()
    else:
        st.error(f"❌ Improvement failed: {improvement_result.get('message', 'Unknown error')}")