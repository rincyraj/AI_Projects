from fastapi import APIRouter, Request, HTTPException, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response
from app.ai_analyser import analyze_resume, improve_resume
import asyncio
import re
import json
import io
from typing import Optional

# PDF generation
try:
    import reportlab
    PDF_REPORTLAB_SUPPORT = True
    print("ReportLab imported successfully")
except ImportError as e:
    PDF_REPORTLAB_SUPPORT = False
    print(f"Warning: reportlab not installed. PDF generation disabled. Error: {e}")

# PDF processing libraries
try:
    import PyPDF2
    PDF_PROCESSING_SUPPORT = True
except ImportError:
    PDF_PROCESSING_SUPPORT = False
    print("Warning: PyPDF2 not installed. PDF support disabled.")

try:
    import pdfplumber
    PDFPLUMBER_SUPPORT = True
except ImportError:
    PDFPLUMBER_SUPPORT = False
    print("Warning: pdfplumber not installed. Using PyPDF2 as fallback.")

# DOCX processing library
try:
    import docx
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False
    print("Warning: python-docx not installed. DOCX support disabled.")

router = APIRouter()

def generate_resume_pdf(resume_text: str, filename: str = "improved_resume.pdf") -> bytes:
    """Generate a PDF from resume text"""
    if not PDF_REPORTLAB_SUPPORT:
        raise HTTPException(status_code=500, detail="PDF generation not available. Please install reportlab.")
    
    try:
        # Import reportlab modules locally to ensure they're available
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
        styles = getSampleStyleSheet()
        
        # Create custom styles
        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            leading=14,
            fontName='Helvetica'
        )
        
        story = []
        
        # Split resume into lines and process
        lines = resume_text.split('\n')
        current_section = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if it's a section header (all caps or ends with colon)
            if (line.isupper() and len(line) > 3) or (line.endswith(':') and len(line) > 3):
                # Add previous section content
                if current_section:
                    section_text = '<br/>'.join(current_section)
                    story.append(Paragraph(section_text, normal_style))
                    story.append(Spacer(1, 12))
                    current_section = []
                
                # Add section header
                story.append(Paragraph(line, section_style))
            
            elif line.startswith('-') or line.startswith('•') or line.startswith('*'):
                # Bullet point
                current_section.append(f"• {line[1:].strip()}")
            
            else:
                # Regular text
                current_section.append(line)
        
        # Add remaining content
        if current_section:
            section_text = '<br/>'.join(current_section)
            story.append(Paragraph(section_text, normal_style))
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF file"""
    text = ""
    
    # Try pdfplumber first (better formatting)
    if PDFPLUMBER_SUPPORT:
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            if text.strip():
                print(f"Successfully extracted {len(text)} characters using pdfplumber")
                return text
        except Exception as e:
            print(f"pdfplumber extraction failed: {e}")
    
    # Fallback to PyPDF2
    if PDF_PROCESSING_SUPPORT:
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            if text.strip():
                print(f"Successfully extracted {len(text)} characters using PyPDF2")
                return text
        except Exception as e:
            print(f"PyPDF2 extraction failed: {e}")
    
    return text

def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX file"""
    if not DOCX_SUPPORT:
        return ""
    
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        print(f"Successfully extracted {len(text)} characters from DOCX")
        return text
    except Exception as e:
        print(f"DOCX extraction failed: {e}")
        return ""

def format_analysis_as_html(analysis_data):
    """Convert the analysis text into beautiful HTML"""
    
    analysis_text = analysis_data.get("data", "")
    
    if not analysis_text:
        return "<div>No analysis data available</div>"
    
    # Parse the sections (they come with numbers 1., 2., etc.)
    sections = re.split(r'\n\d+\.\s+', analysis_text)
    
    # Remove empty first section if present
    if sections and sections[0].strip() == "":
        sections = sections[1:]
    
    # Section titles
    section_titles = [
        "Professional Summary",
        "Key Skills", 
        "Strengths",
        "Weaknesses",
        "ATS Score"
    ]
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                margin: 0;
                padding: 20px;
                min-height: 100vh;
            }
            .report-container {
                max-width: 900px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            .header h1 {
                margin: 0;
                font-size: 2.5em;
            }
            .content {
                padding: 40px;
            }
            .section {
                margin-bottom: 30px;
                padding: 25px;
                background: #f8f9fa;
                border-radius: 15px;
                border-left: 5px solid #667eea;
            }
            .section h2 {
                color: #333;
                margin-top: 0;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .skill-tag {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 6px 12px;
                margin: 4px;
                border-radius: 20px;
                display: inline-block;
                font-size: 0.9em;
            }
            .score-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                margin-bottom: 15px;
            }
            .score-number {
                font-size: 3em;
                font-weight: bold;
            }
            .bullet-list {
                list-style: none;
                padding: 0;
            }
            .bullet-list li {
                padding: 5px 0 5px 20px;
                position: relative;
            }
            .bullet-list li:before {
                content: "•";
                color: #667eea;
                font-weight: bold;
                position: absolute;
                left: 0;
            }
            .footer {
                text-align: center;
                padding: 20px;
                background: #f1f1f1;
                color: #666;
            }
        </style>
    </head>
    <body>
        <div class="report-container">
            <div class="header">
                <h1>📄 Resume Analysis Report</h1>
            </div>
            <div class="content">
    """
    
    # Add each section
    for i, section_content in enumerate(sections):
        if i < len(section_titles):
            content = section_content.strip()
            
            if "ATS Score" in section_titles[i]:
                # Extract score
                score_match = re.search(r'(\d+)', content)
                score = score_match.group(1) if score_match else "N/A"
                
                html += f"""
                <div class="section">
                    <h2>📊 {section_titles[i]}</h2>
                    <div class="score-card">
                        <div class="score-number">{score}/100</div>
                    </div>
                    <div>{content}</div>
                </div>
                """
            elif "Key Skills" in section_titles[i]:
                # Format skills as tags
                skills = re.findall(r'[\*\•]\s*([^\*\•\n]+)', content)
                if skills:
                    skills_html = "".join([f'<span class="skill-tag">{s.strip()}</span>' for s in skills])
                    html += f"""
                    <div class="section">
                        <h2>🔧 {section_titles[i]}</h2>
                        <div>{skills_html}</div>
                    </div>
                    """
                else:
                    html += f"""
                    <div class="section">
                        <h2>🔧 {section_titles[i]}</h2>
                        <div>{content}</div>
                    </div>
                    """
            else:
                # Check for bullet points
                if '*' in content or '•' in content:
                    lines = content.split('\n')
                    list_items = []
                    for line in lines:
                        if line.strip().startswith('*') or line.strip().startswith('•'):
                            list_items.append(f'<li>{line.strip()[1:].strip()}</li>')
                        elif line.strip():
                            list_items.append(f'<li>{line.strip()}</li>')
                    
                    if list_items:
                        html += f"""
                        <div class="section">
                            <h2>📌 {section_titles[i]}</h2>
                            <ul class="bullet-list">{''.join(list_items)}</ul>
                        </div>
                        """
                    else:
                        html += f"""
                        <div class="section">
                            <h2>📌 {section_titles[i]}</h2>
                            <div>{content}</div>
                        </div>
                        """
                else:
                    html += f"""
                    <div class="section">
                        <h2>📌 {section_titles[i]}</h2>
                        <div>{content}</div>
                    </div>
                    """
    
    # Add model info
    model_name = analysis_data.get("model", "AI Model")
    html += f"""
                <div style="text-align: center; color: #666; margin-top: 20px;">
                    <small>Powered by: {model_name}</small>
                </div>
            </div>
            <div class="footer">
                AI Resume Analyzer
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

@router.post("/analyze_resume")
async def analyze_resume_upload(
    request: Request,
    file: UploadFile = File(...),
    job_role: Optional[str] = None
):
    """Main endpoint for file upload with PDF/DOCX support"""
    try:
        # Read the uploaded file
        file_bytes = await file.read()
        filename = file.filename.lower()
        
        print(f"Processing file: {filename}, size: {len(file_bytes)} bytes")
        
        # Extract text based on file type
        text = ""
        if filename.endswith('.pdf'):
            if not (PDF_PROCESSING_SUPPORT or PDFPLUMBER_SUPPORT):
                return JSONResponse(
                    content={"success": False, "error": "PDF support not installed. Please install PyPDF2 or pdfplumber."},
                    status_code=500
                )
            text = extract_text_from_pdf(file_bytes)
        elif filename.endswith('.docx'):
            if not DOCX_SUPPORT:
                return JSONResponse(
                    content={"success": False, "error": "DOCX support not installed. Please install python-docx."},
                    status_code=500
                )
            text = extract_text_from_docx(file_bytes)
        else:
            return JSONResponse(
                content={"success": False, "error": "Unsupported file type. Please upload PDF or DOCX."},
                status_code=400
            )
        
        # Check if text was extracted
        if not text or len(text.strip()) < 50:
            return JSONResponse(
                content={"success": False, "error": "Could not extract enough text from the file. The file might be scanned or image-based."},
                status_code=400
            )
        
        print(f"Extracted {len(text)} characters of text")
        
        # Call your existing analyze_resume function with job_role
        result = await asyncio.to_thread(analyze_resume, text, job_role)
        
        # Check if request accepts HTML (browser) or JSON (API)
        accept_header = request.headers.get("accept", "")
        if "text/html" in accept_header:
            # Return formatted HTML for browsers
            if not result.get("success"):
                return HTMLResponse(
                    content=f"<h2 style='color: red;'>Error: {result.get('message', 'Analysis failed')}</h2>",
                    status_code=500
                )
            return HTMLResponse(content=format_analysis_as_html(result))
        else:
            # Return JSON for API clients
            return JSONResponse(content=result)
        
    except Exception as e:
        print(f"Error in analyze_resume_upload: {str(e)}")
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )

@router.post("/analyze_resume_json")
async def analyze_resume_json(request: Request):
    """Endpoint for JSON/text input (kept for compatibility)"""
    try:
        # Get the request body
        body = await request.body()
        
        # Try to parse JSON
        try:
            data = await request.json()
        except:
            try:
                text = body.decode('utf-8')
                data = {"resume_text": text}
            except:
                text = body.decode('utf-8', errors='ignore')
                data = {"resume_text": text}
        
        text = data.get("resume_text", "")
        if not text and isinstance(data, str):
            text = data
        
        if not text:
            raise HTTPException(status_code=400, detail="No resume text provided")
        
        # Call your existing analyze_resume function
        result = await asyncio.to_thread(analyze_resume, text)
        
        # Return JSON
        return JSONResponse(content=result)
        
    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )

@router.post("/improve_resume")
async def improve_resume_endpoint(request: Request):
    """Endpoint for resume improvement suggestions"""
    try:
        # Get the request body
        body = await request.json()
        
        resume_text = body.get("resume_text", "")
        job_role = body.get("job_role")
        analysis = body.get("analysis", "")
        format_type = body.get("format", "json")  # json or pdf
        
        if not resume_text:
            raise HTTPException(status_code=400, detail="No resume text provided")
        
        # Call the improvement function
        result = await asyncio.to_thread(improve_resume, resume_text, job_role, analysis)
        
        if format_type == "pdf":
            # Extract improved resume content from the result
            full_text = result.get("data", "")
            print(f"Full text length: {len(full_text)}")
            print(f"Format requested: {format_type}")
            
            # Find the IMPROVED RESUME section (use last occurrence to capture full output)
            improved_resume_start = full_text.upper().rfind("IMPROVED RESUME")
            print(f"IMPROVED RESUME start position: {improved_resume_start}")
            
            if improved_resume_start != -1:
                improved_resume_text = full_text[improved_resume_start:]
                # Remove the header line
                improved_resume_text = improved_resume_text.split('\n', 1)[1] if '\n' in improved_resume_text else improved_resume_text
            else:
                improved_resume_text = full_text
            
            # If the improved resume looks significantly shorter than the original, fallback to original
            if len(improved_resume_text.strip()) < max(300, int(len(resume_text) * 0.6)):
                print(f"Improved resume appears too short ({len(improved_resume_text)} chars) compared to original ({len(resume_text)} chars). Using original resume.")
                improved_resume_text = resume_text
            
            print(f"Final resume text length: {len(improved_resume_text)}")
            print(f"First 300 chars: {improved_resume_text[:300]}")
            
            # Generate PDF
            pdf_data = generate_resume_pdf(improved_resume_text.strip())
            
            return Response(
                content=pdf_data,
                media_type="application/pdf",
                headers={"Content-Disposition": "attachment; filename=improved_resume.pdf"}
            )
        else:
            # Return JSON
            return JSONResponse(content=result)
        
    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )