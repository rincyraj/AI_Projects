import streamlit as st
import requests
import json
import re

API_URL = "http://127.0.0.1:8000"

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
        # Extract score number
        score_match = re.search(r'(\d+)', content)
        score = score_match.group(1) if score_match else "N/A"
        
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

# ============================================
# MAIN APP LAYOUT
# ============================================

# Create two columns for layout
col1, col2 = st.columns([1, 1])

with col1:
    # -------------------
    # LOGIN SECTION
    # -------------------
    st.markdown("### 🔐 Login")
    
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="Enter your email")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
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
    
    # Show login status
    if "token" in st.session_state:
        st.success("✅ You are logged in")
        if st.button("Logout", use_container_width=True):
            del st.session_state["token"]
            st.session_state["analysis_result"] = None
            st.rerun()

with col2:
    # -------------------
    # RESUME UPLOAD SECTION
    # -------------------
    st.markdown("### 📤 Upload Resume")
    
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
        else:
            # Prepare file for upload
            files = {
                "file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
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
                        timeout=120  # Increased timeout for larger files
                    )
                    
                    if response.status_code == 200:
                        # Check if response is JSON or HTML
                        content_type = response.headers.get("content-type", "")
                        
                        if "application/json" in content_type:
                            result = response.json()
                            st.session_state["analysis_result"] = result
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
    st.markdown("## 📊 Analysis Results")
    
    result = st.session_state["analysis_result"]
    
    # Check if analysis was successful
    if result.get("success"):
        analysis_text = result.get("data", "")
        model_used = result.get("model", "Unknown")
        
        # Parse the analysis text into sections
        sections = analysis_text.split('\n')
        
        current_section = ""
        current_content = []
        
        # Create tabs for different views
        tab1, tab2 = st.tabs(["📋 Formatted View", "📝 Raw Analysis"])
        
        with tab1:
            # Parse and display in formatted way
            for line in sections:
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith("1.") or "Professional Summary" in line:
                    if current_section:
                        display_section(current_section, current_content)
                    current_section = "Professional Summary"
                    # Clean the line
                    cleaned = re.sub(r'^1\.\s*', '', line)
                    cleaned = re.sub(r'Professional Summary\s*', '', cleaned)
                    current_content = [cleaned] if cleaned else []
                elif line.startswith("2.") or "Key Skills" in line:
                    if current_section:
                        display_section(current_section, current_content)
                    current_section = "Key Skills"
                    cleaned = re.sub(r'^2\.\s*', '', line)
                    cleaned = re.sub(r'Key Skills\s*', '', cleaned)
                    current_content = [cleaned] if cleaned else []
                elif line.startswith("3.") or "Strengths" in line:
                    if current_section:
                        display_section(current_section, current_content)
                    current_section = "Strengths"
                    cleaned = re.sub(r'^3\.\s*', '', line)
                    cleaned = re.sub(r'Strengths\s*', '', cleaned)
                    current_content = [cleaned] if cleaned else []
                elif line.startswith("4.") or "Weaknesses" in line:
                    if current_section:
                        display_section(current_section, current_content)
                    current_section = "Weaknesses"
                    cleaned = re.sub(r'^4\.\s*', '', line)
                    cleaned = re.sub(r'Weaknesses\s*', '', cleaned)
                    current_content = [cleaned] if cleaned else []
                elif line.startswith("5.") or "ATS Score" in line:
                    if current_section:
                        display_section(current_section, current_content)
                    current_section = "ATS Score"
                    cleaned = re.sub(r'^5\.\s*', '', line)
                    cleaned = re.sub(r'ATS Score\s*', '', cleaned)
                    current_content = [cleaned] if cleaned else []
                else:
                    if line and not line.startswith(('1.', '2.', '3.', '4.', '5.')):
                        current_content.append(line)
            
            # Display last section
            if current_section:
                display_section(current_section, current_content)
        
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
        
        # Add clear button
        if st.button("🔄 Clear Results"):
            st.session_state["analysis_result"] = None
            st.rerun()
    else:
        st.error(f"❌ Analysis failed: {result.get('message', 'Unknown error')}")