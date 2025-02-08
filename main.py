from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, Dict
import os
import tempfile
from pdf_reader import PaperProcessor
from analyzer import Paper, PaperProcessor
import json
import requests
from urllib.parse import urlparse

app = FastAPI(
    title="Paper Analysis API",
    description="API for analyzing academic papers and chatting about them",
    version="1.0.0"
)

# Configure CORS for the Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["chrome-extension://*"],  # Allow Chrome extensions
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get API key from environment
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("Please set OPENAI_API_KEY environment variable")

# Initialize the paper processor
processor = PaperProcessor(api_key)

# Global storage for papers (in a real app, this would be a database)
papers_cache: Dict[str, Paper] = {}

class ChatRequest(BaseModel):
    paper_id: str
    message: str

class AnalyzeRequest(BaseModel):
    url: str

@app.post("/upload")
async def upload_paper(file: UploadFile = File(...)):
    """
    Upload and process a PDF paper
    """
    try:
        print(f"Receiving file: {file.filename}")  # Debug log
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
            print(f"Saved to temporary file: {tmp_path}")  # Debug log

        try:
            # Process the paper
            paper = processor.process_paper(tmp_path)
            
            # Generate paper ID and store in cache
            paper_id = str(hash(paper.title))
            papers_cache[paper_id] = paper
            
            print(f"Processed paper. ID: {paper_id}, Title: {paper.title}")  # Debug log
            print(f"Papers in cache: {list(papers_cache.keys())}")  # Debug log

            return {
                "success": True,
                "paper_id": paper_id,
                "title": paper.title,
                "authors": paper.authors,
                "abstract": paper.abstract
            }
        finally:
            # Clean up temporary file
            os.unlink(tmp_path)
            
    except Exception as e:
        print(f"Error processing paper: {str(e)}")  # Debug log
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Chat with a processed paper
    """
    try:
        print(f"Chat request received. Paper ID: {request.paper_id}")  # Debug log
        print(f"Available papers: {list(papers_cache.keys())}")  # Debug log
        
        if request.paper_id not in papers_cache:
            raise HTTPException(
                status_code=404,
                detail=f"Paper not found. Available IDs: {list(papers_cache.keys())}"
            )

        paper = papers_cache[request.paper_id]
        print(f"Found paper: {paper.title}")  # Debug log
        
        response = processor.chat_with_paper(paper, request.message)
        print(f"Generated response for: {request.message}")  # Debug log

        return {
            "success": True,
            "response": response,
            "paper_id": request.paper_id
        }
    except Exception as e:
        print(f"Chat error: {str(e)}")  # Debug log
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/analyze")
async def analyze_paper(request: AnalyzeRequest):
    """
    Analyze a paper from a URL
    """
    try:
        url = request.url
        parsed_url = urlparse(url)
        
        # Handle different paper repositories
        if 'arxiv.org' in parsed_url.netloc:
            # Handle arXiv URLs
            # Convert to PDF URL if needed
            if 'pdf' not in url:
                paper_id = url.split('/')[-1]
                url = f'https://arxiv.org/pdf/{paper_id}.pdf'
        
        # Download the PDF
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise exception for bad status codes
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            for chunk in response.iter_content(chunk_size=8192):
                tmp_file.write(chunk)
            tmp_path = tmp_file.name

        try:
            # Process the paper using existing PaperProcessor
            paper = processor.process_paper(tmp_path)
            
            # Generate paper ID and store in cache
            paper_id = str(hash(paper.title))
            papers_cache[paper_id] = paper

            return {
                "success": True,
                "paper_id": paper_id,
                "title": paper.title,
                "authors": paper.authors,
                "abstract": paper.abstract
            }
        finally:
            # Clean up temp file
            os.unlink(tmp_path)
            
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to download PDF: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/paper/{paper_id}")
async def get_paper(paper_id: str):
    """
    Get processed paper information
    """
    if paper_id not in papers_cache:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    paper = papers_cache[paper_id]
    return {
        "success": True,
        "paper": {
            "title": paper.title,
            "authors": paper.authors,
            "abstract": paper.abstract,
            "sections": [{"title": s.title, "content": s.content} for s in paper.sections],
            "formulas": [{"latex": f.latex, "explanation": f.explanation} for f in paper.formulas]
        }
    }

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with basic API information"""
    return """
    <html>
        <head>
            <title>Paper Analysis API</title>
        </head>
        <body>
            <h1>Paper Analysis API</h1>
            <p>Available endpoints:</p>
            <ul>
                <li><a href="/docs">/docs</a> - API documentation</li>
                <li>/upload - Upload and analyze PDF</li>
                <li>/chat - Chat about analyzed papers</li>
                <li>/paper/{paper_id} - Get paper information</li>
            </ul>
        </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)