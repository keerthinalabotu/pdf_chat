import PyPDF2
import re
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import logging
from openai import OpenAI
import os
from time import sleep
from pdf_reader import PaperProcessor as PDFProcessor

@dataclass
class Formula:
    latex: str
    explanation: str
    context: str
    location: Dict[str, int]

@dataclass
class Reference:
    title: str
    authors: List[str]
    year: str
    citation_context: str

@dataclass
class Section:
    title: str
    content: str
    start_page: int
    end_page: int

@dataclass
class Paper:
    title: str
    authors: List[str]
    abstract: str
    sections: List[Section]
    formulas: List[Formula]
    # references: List[Reference]
    full_text: str

class PaperProcessor:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        Initialize the paper processor with OpenAI API key.
        
        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-3.5-turbo)
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.pdf_processor = PDFProcessor()

    def _get_completion(self, prompt: str, temperature: float = 0.2) -> str:
        """
        Get completion from OpenAI API with retry logic.
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a helpful research assistant analyzing academic papers."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature
                )
                return response.choices[0].message.content
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                self.logger.warning(f"API call failed, attempt {attempt + 1}/{max_retries}: {e}")
                sleep(2 ** attempt)  # Exponential backoff

    # def extract_text_from_pdf(self, pdf_path: str) -> str:
    #     """Extract text content from PDF."""
    #     try:
    #         with open(pdf_path, 'rb') as file:
    #             reader = PyPDF2.PdfReader(file)
    #             text = ""
    #             for page in reader.pages:
    #                 text += page.extract_text() + "\n"
    #         return text
    #     except Exception as e:
    #         self.logger.error(f"Error extracting text from PDF: {e}")
    #         raise

    # def extract_latex_formulas(self, text: str) -> List[Formula]:
    #     """Extract LaTeX formulas from text."""
    #     formula_patterns = [
    #         r'\$\$(.*?)\$\$',
    #         r'\$(.*?)\$',
    #         r'\\begin\{equation\}(.*?)\\end\{equation\}',
    #         r'\\begin\{align\*?\}(.*?)\\end\{align\*?\}'
    #     ]
        
    #     formulas = []
    #     for pattern in formula_patterns:
    #         matches = re.finditer(pattern, text, re.DOTALL)
    #         for match in matches:
    #             latex = match.group(1)
    #             # Get surrounding context
    #             start = max(0, match.start() - 100)
    #             end = min(len(text), match.end() + 100)
    #             context = text[start:end]
                
    #             explanation = self.explain_formula(latex, context)
                
    #             formulas.append(Formula(
    #                 latex=latex,
    #                 explanation=explanation,
    #                 context=context,
    #                 location={"page": 0, "position": match.start()}
    #             ))
        
    #     return formulas

    def explain_formula(self, latex: str, context: str) -> str:
        """Explain a LaTeX formula in natural language."""
        prompt = f"""
        Given this LaTeX formula: {latex}
        And its surrounding context: {context}
        
        Explain what this formula represents in clear, natural language. 
        Focus on:
        1. What the variables represent
        2. The relationship it describes
        3. Its significance in the paper's context
        
        Explanation:
        """
        
        return self._get_completion(prompt)

    def extract_sections(self, text: str) -> List[Section]:
        """Extract main sections from the paper."""
        section_patterns = [
            r'\n(?:#{1,6}|[1-9]\.)\s*(.*?)\n',
            r'\n(?:Abstract|Introduction|Methods|Results|Discussion|Conclusion)s?\b'
        ]
        
        sections = []
        current_section = None
        current_content = []
        
        for line in text.split('\n'):
            is_header = any(re.match(pattern, '\n' + line, re.I) for pattern in section_patterns)
            
            if is_header:
                if current_section:
                    sections.append(Section(
                        title=current_section,
                        content='\n'.join(current_content),
                        start_page=0,
                        end_page=0
                    ))
                current_section = line.strip()
                current_content = []
            elif current_section:
                current_content.append(line)
        
        if current_section:
            sections.append(Section(
                title=current_section,
                content='\n'.join(current_content),
                start_page=0,
                end_page=0
            ))
        
        return sections

    def summarize_section(self, section: Section) -> str:
        """Generate a summary of a section."""
        prompt = f"""
        Summarize this section of a research paper:
        Title: {section.title}
        Content: {section.content[:2000]}  # Increased context length for GPT
        
        Provide a concise summary focusing on:
        1. Main points
        2. Key findings or arguments
        3. Significance to the overall paper
        
        Summary:
        """
        
        return self._get_completion(prompt)

    def extract_references(self, text: str) -> List[Reference]:
        """Extract references from the paper."""
        # Look for references section
        references_section = re.split(r'\n(?:References|Bibliography)\s*\n', text, flags=re.I)[-1]
        
        # Basic reference pattern
        reference_pattern = r'\[([\d]+)\](.*?)(?=\[[\d]+\]|\Z)'
        references = []
        
        for match in re.finditer(reference_pattern, references_section, re.DOTALL):
            ref_text = match.group(2).strip()
            
            # Use GPT to parse reference
            prompt = f"""
            Parse this reference into structured data:
            {ref_text}
            
            Return only a JSON object with these fields:
            - title
            - authors (as list)
            - year
            """
            
            try:
                parsed = json.loads(self._get_completion(prompt))
                references.append(Reference(
                    title=parsed.get('title', ''),
                    authors=parsed.get('authors', []),
                    year=parsed.get('year', ''),
                    citation_context=ref_text
                ))
            except json.JSONDecodeError:
                self.logger.warning(f"Failed to parse reference: {ref_text}")
                continue
                
        return references

    def chat_with_paper(self, paper: Paper, query: str) -> str:
        """Enable interactive chat about the paper's contents."""
        context = f"""
        Title: {paper.title}
        Authors: {', '.join(paper.authors)}
        Abstract: {paper.abstract}
        
        Full text: {paper.full_text[:2000]}  # Include part of the full text for context
        
        Based on this research paper, answer the following question:
        {query}
        
        Use specific information from the paper to support your answer.
        If the answer isn't directly addressed in the paper, say so.
        """
        
        return self._get_completion(context, temperature=0.3)

    def process_paper(self, pdf_path: str) -> Paper:
        """Process a research paper and return structured information."""
        # Extract text using the PDF processor
        text = self.pdf_processor.extract_text_from_pdf(pdf_path)
        
        # Extract formulas using the PDF processor
        formulas = self.pdf_processor.extract_latex_formulas(text)
        
        # Extract components
        sections = self.extract_sections(text)
        references = self.extract_references(text)
        
        # Extract title and abstract
        title = sections[0].title if sections else ""
        abstract = next((s.content for s in sections if 'abstract' in s.title.lower()), "")
        
        # Use GPT to extract authors
        authors_prompt = f"Extract the authors from this paper title and first page:\n{text[:1000]}\nReturn only a JSON array of author names."
        try:
            authors = json.loads(self._get_completion(authors_prompt))
        except json.JSONDecodeError:
            authors = []
        
        paper = Paper(
            title=title,
            authors=authors,
            abstract=abstract,
            sections=sections,
            formulas=formulas,
            # references=references,
            full_text=text
        )
        
        return paper

    def save_paper_analysis(self, paper: Paper, output_path: str):
        """Save the paper analysis to a JSON file."""
        try:
            with open(output_path, 'w') as f:
                json.dump(asdict(paper), f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving paper analysis: {e}")
            raise

# Example usage
if __name__ == "__main__":
    # Get API key from environment variable
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Please set OPENAI_API_KEY environment variable")
    
    processor = PaperProcessor(api_key)
    
    # Example paper processing
    pdf_path = "Lu_Adaptive_Object_Detection_CVPR_2016_paper.pdf"
    try:
        paper = processor.process_paper(pdf_path)
        
        # Save analysis
        processor.save_paper_analysis(paper, "paper_analysis.json")
        
        # Example chat interaction
        question = "What are the main findings of this paper?"
        answer = processor.chat_with_paper(paper, question)
        print(f"Q: {question}\nA: {answer}")
        
    except Exception as e:
        logging.error(f"Error processing paper: {e}")