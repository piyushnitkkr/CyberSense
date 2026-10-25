import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

colors = {
    'primary': RGBColor(51, 102, 204),
    'secondary': RGBColor(102, 153, 204),
    'text': RGBColor(33, 33, 33),
    'subtitle': RGBColor(102, 102, 102),
}

def add_slide(title, bullets, notes=""):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Title
    tb = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.7), Inches(1.0))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.text = title
    p = tf.paragraphs[0]
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = colors['primary']

    # Bullets
    if bullets:
        tb2 = slide.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(11.7), Inches(5.2))
        tf2 = tb2.text_frame
        tf2.word_wrap = True
        for b in bullets:
            p2 = tf2.add_paragraph()
            p2.text = b
            p2.font.size = Pt(18)
            p2.font.color.rgb = colors['text']
            p2.space_after = Pt(8)

    if notes:
        slide.notes_slide.notes_text_frame.text = notes

    return slide

# 1. Title Slide
s1 = prs.slides.add_slide(prs.slide_layouts[6])
tb = s1.shapes.add_textbox(Inches(1), Inches(2), Inches(11.333), Inches(3))
tf = tb.text_frame
tf.text = "CYBERSENSE\nA Cybersecurity RAG Assistant for Academic Research"
tf.paragraphs[0].font.size = Pt(44)
tf.paragraphs[0].font.bold = True
tf.paragraphs[0].font.color.rgb = colors['primary']
tf.paragraphs[0].alignment = PP_ALIGN.CENTER
s1.notes_slide.notes_text_frame.text = "Welcome to CyberSense presentation."

# Section 1
add_slide("Section 1: Problem Identification & Objectives", [
    "Problem Identification:",
    "  - Cybersecurity knowledge is vast and rapidly evolving",
    "  - Practitioners struggle to find accurate, contextual answers quickly",
    "  - Traditional keyword search returns fragmented or irrelevant results",
    "  - Security documentation scattered across multiple repositories",
    "",
    "Project Objectives:",
    "  - Build a cybersecurity RAG chatbot for academic and practical use",
    "  - Integrate authoritative sources (MITRE ATT&CK, CWE, OWASP)",
    "  - Implement hybrid retrieval (dense vector + sparse BM25)",
    "  - Provide cited, hallucination-resistant answers with zero cost deployment"
], "Covering problem identification and project objectives.")

add_slide("Project Scope & Target Users", [
    "In Scope:",
    "  - Cybersecurity knowledge synthesis & RAG architecture",
    "  - MITRE ATT&CK (867 tech), CWE (939 weak), OWASP Top 10 ingestion",
    "  - FastAPI backend, Streamlit UI, Qdrant vector DB, Groq LLM",
    "",
    "Out of Scope:",
    "  - Real-time threat intelligence feeds",
    "  - Automated exploit generation or offensive payloads",
    "",
    "Target Users:",
    "  - Security researchers, students, and defenders needing grounded answers"
], "Defining project scope and target audience.")

# Section 2
add_slide("Section 2: Literature Review & Foundations", [
    "RAG (Retrieval-Augmented Generation):",
    "  - Introduced by Lewis et al. (2020, NeurIPS)",
    "  - Combines parametric LLMs with non-parametric external memory",
    "  - Core advantage: Reduces hallucinations via strict source grounding",
    "",
    "Related Security AI Systems:",
    "  - IBM Security QRadar / Microsoft Copilot for Security / Google Chronicle",
    "  - Most commercial systems are proprietary and lack open citation transparency",
    "  - CyberSense provides an open academic alternative with verifiable inline citations"
], "Discussing RAG literature and related work.")

add_slide("Embedding & Retrieval Technologies", [
    "Embedding Models:",
    "  - Sentence-BERT (SBERT) architecture (Reimers & Gurevych, ICLR 2020)",
    "  - all-MiniLM-L6-v2 (384-dimensional dense vectors)",
    "  - BAAI/bge-small-en-v1.5 optimized for retrieval",
    "",
    "Retrieval Architecture:",
    "  - Dense Vector Search (Qdrant Cloud HNSW index)",
    "  - Sparse Lexical Search (BM25 inverted index with regex ID short-circuit)",
    "  - Reciprocal Rank Fusion (RRF) + cross-encoder reranking"
], "Technical review of embeddings and hybrid retrieval.")

# Section 3
add_slide("Section 3: Methodology & Architecture", [
    "End-to-End Pipeline:",
    "  1. User Query -> Safety Guardrails (Refuse exploits, sanitize injection)",
    "  2. Query Pipeline -> Rewriting (history) + Entity Extraction (CVE/CWE/ATT&CK)",
    "  3. Hybrid Retrieval -> Dense (Qdrant) + Sparse (BM25)",
    "  4. Fusion & Rerank -> Reciprocal Rank Fusion + Cross-Encoder",
    "  5. Generation -> Groq LLM prompt assembly with citation validation",
    "",
    "Data Ingestion Pipeline:",
    "  - STIX 2.1 JSON (ATT&CK 867 tech) + XML (CWE 939 weak) + Markdown (OWASP)",
    "  - 500-token chunking with overlap -> Qdrant upsert -> BM25 index rebuild"
], "Detailed walkthrough of methodology and architecture.")

add_slide("Work Plan & Technology Stack", [
    "Execution Phases:",
    "  - Phase 1 (Weeks 1-2): Architecture design & FastAPI backend setup",
    "  - Phase 2 (Weeks 3-4): Qdrant vector store & BM25 sparse index integration",
    "  - Phase 3 (Weeks 5-6): Hybrid retrieval, RRF fusion, and LLM integration",
    "  - Phase 4 (Weeks 7-8): Streamlit UI, cloud deployment, and evaluation",
    "",
    "Technology Stack:",
    "  - Backend: FastAPI (Python 3.11), SQLAlchemy, Qdrant client",
    "  - Frontend: Streamlit (web UI)",
    "  - Infrastructure: Render.com (API) + Qdrant Cloud + Groq Cloud (Free Tier)"
], "Work plan timeline and technology stack.")

# Section 4
add_slide("Section 4: Progress Achieved", [
    "Key Deliverables Completed:",
    "  - Hybrid retrieval pipeline fully operational (Dense + Sparse + RRF)",
    "  - Cross-encoder reranker integrated for high precision",
    "  - MITRE ATT&CK Enterprise (867 techniques) successfully indexed",
    "  - MITRE CWE (939 weaknesses) and OWASP Top 10 2025 ingested",
    "  - Safety guardrails active (exploit refusal & injection sanitization)",
    "  - Streamlit UI deployed with expandable source citation cards",
    "  - Live cloud deployment on Render.com and Qdrant Cloud",
    "  - 60-question evaluation test suite passing successfully"
], "Review of progress achieved and deployed features.")

add_slide("Performance Metrics & Benchmarks", [
    "Dataset Statistics:",
    "  - 867 ATT&CK techniques | 939 CWE weaknesses | 10 OWASP categories",
    "  - Total knowledge base: 3,600+ structured chunks in Qdrant",
    "",
    "System Performance:",
    "  - Average query latency: < 2.0s (cold cache), < 1.0s (warm cache)",
    "  - Retrieval accuracy: > 85% on evaluation golden set",
    "  - Abstention rate: ~12% on unanswerable queries (hallucination prevention)"
], "Quantitative metrics and benchmark results.")

# Section 5
add_slide("Section 5: Future Work & Timeline", [
    "Short-Term Roadmap (1-3 months):",
    "  - Integrate CAPEC (Common Attack Pattern Enumeration and Classification)",
    "  - Add CISA KEV (Known Exploited Vulnerabilities catalog)",
    "  - Implement multi-turn conversation memory",
    "",
    "Medium & Long-Term Vision (3-12 months):",
    "  - NIST SP 800-53 security control mapping",
    "  - Full CVE database integration with automated vulnerability triage",
    "  - Custom fine-tuned security LLM and enterprise SIEM integration"
], "Future work roadmap and long-term vision.")

add_slide("Conclusion & Readiness", [
    "Project Summary:",
    "  - CyberSense successfully implements an enterprise-grade cybersecurity RAG",
    "  - Solves fragmentation and hallucination issues in security research",
    "  - Fully functional, zero-cost cloud deployment",
    "  - Comprehensive academic report and presentation prepared",
    "",
    "Status:",
    "  - MVP Complete | Tested | Deployed | Ready for College Evaluation"
], "Concluding remarks and project status.")

# Save
prs.save("CyberSense_Presentation.pptx")
print("SUCCESS: CyberSense_Presentation.pptx created successfully with 11 slides.")
