import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from pptx import Presentation
from pptx.util import Inches, Pt, Cm
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
import datetime

# Configure presentation for professional academic evaluation
prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# Professional color scheme
colors = {
    'primary': RGBColor(51, 102, 204),
    'secondary': RGBColor(102, 153, 204),
    'accent': RGBColor(255, 204, 51),
    'dark': RGBColor(51, 51, 51),
    'light': RGBColor(240, 240, 240),
    'text': RGBColor(33, 33, 33),
    'subtitle': RGBColor(102, 102, 102),
    'code_bg': RGBColor(245, 245, 245),
}

def add_title_slide(title, subtitle=""):
    slide_layout = prs.slide_layouts[6]  # blank
    slide = prs.slides.add_slide(slide_layout)
    title_box = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(11), Inches(3))
    tf = title_box.text_frame
    tf.text = f"{title}\n{subtitle}"
    p = tf.paragraphs[0]
    p.font.size = Pt(44)
    p.font.bold = True
    p.font.color.rgb = colors['primary']
    p.alignment = PP_ALIGN.CENTER
    return slide

def add_content_slide(title, bullets, notes=""):
    slide_layout = prs.slide_layouts[6]  # blank
    slide = prs.slides.add_slide(slide_layout)

    # Title
    title_box = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(11), Inches(2.5))
    tf = title_box.text_frame
    tf.text = title
    p = tf.paragraphs[0]
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = colors['primary']
    p.alignment = PP_ALIGN.CENTER

    # Bullets
    if bullets:
        col = slide.shapes.add_textbox(Inches(1.5), Inches(4.5), Inches(9), Inches(2.5))
        tf = col.text_frame
        tf.word_wrap = True
        for bullet in bullets:
            p = tf.add_paragraph()
            p.text = bullet
            p.font.size = Pt(18)
            p.font.color.rgb = colors['text']
            p.alignment = PP_ALIGN.CENTER

    # Notes
    if notes:
        note_box = slide.shapes.add_textbox(Inches(1.5), Inches(8.5), Inches(9), Inches(1.5))
        tf = note_box.text_frame
        tf.word_wrap = True
        for line in notes.split('\n'):
            p = tf.add_paragraph()
            p.text = line[:200]  # truncate long lines
            p.font.size = Pt(14)
            p.font.color.rgb = colors['subtitle']
            p.alignment = PP_ALIGN.CENTER

    return slide

# Section 1: Problem Identification & Objectives
section1 = add_title_slide(
    "Section 1: Problem Identification & Objectives",
    "Understanding the need for CyberSense and defining its goals"
)
for b in [
    "Problem Identification:",
    "  • Cybersecurity knowledge is vast and rapidly evolving",
    "  • Practitioners struggle to find accurate, contextual answers quickly",
    "  • Traditional search returns fragmented or irrelevant results",
    "  • Security documentation is scattered across multiple repositories",
    "  • Root cause: Gap between available knowledge and actionable answers",
    "Secondary Objectives:",
    "  • Integrate authoritative data sources (MITRE, OWASP)",
    "  • Implement hybrid retrieval: dense vector + sparse BM25",
    "  • Provide cited, hallucination-resistant answers",
    "  • Deploy scalable cloud architecture",
]:
    section1.add_content_slide(b, None)

# Section 2: Literature Review
section2 = add_title_slide(
    "Section 2: Literature Review",
    "Foundational research and related work in cybersecurity AI"
)
for b in [
    "RAG Fundamentals:",
    "  • Retrieval-Augmented Generation, Lewis et al. (2020, NeurIPS)",
    "  • Hybrid of parametric LLMs and non-parametric memory",
    "  • Key insight: Grounding reduces hallucination through external knowledge",
    "",
    "Related Work in Cybersecurity AI:",
    "  • IBM Security QRadar: SIEM with AI-powered analytics",
    "  • Microsoft Copilot for Security: Enterprise security copilot",
    "  • Chronicle: SecOps analytics platform",
    "  • MITRE ATT&CK Navigator: Visualization and annotation tool",
    "  • CAPEC: Attack pattern catalog",
    "  • CWE: Common Weakness Enumeration database",
],
    notes=(
        "Several existing systems leverage AI for cybersecurity. MITRE's ATT&CK framework "
        "has spawned derivative tools including ATT&CK Navigator for visualization and MITRE ATLAS "
        "for evaluating AI system security. Commercial solutions like IBM QRadar, Microsoft Copilot for "
        "Security, and Google Chronicle integrate AI for threat detection and analysis. However, "
        "most are proprietary and lack transparency in their retrieval grounding mechanisms. "
        "CyberSense fills this gap with an open, academic approach emphasizing verifiable citations."
    ),
]
section2.add_content_slide(b, notes)

# Section 3: Methodology & Work Plan
section3 = add_title_slide(
    "Section 3: Methodology & Work Plan",
    "How we built CyberSense — architecture, pipeline, and phases"
)
for b in [
    "Architecture Overview:",
    "  • User Query → Safety Guardrails → Query Pipeline → Dual Retriever → RRF Fusion → Reranker → LLM → Cited Response",
    "",
    "Hybrid Retrieval Methodology:",
    "  • Dense Retrieval: 384-dim embeddings via all-MiniLM-L6-v2 in Qdrant",
    "  • Sparse Retrieval: BM25 inverted index with regex short-circuiting for exact IDs",
    "  • Reciprocal Rank Fusion merges both result sets with entity-matched priority",
    "",
    "Ingestion Pipeline:",
    "  • Load from STIX 2.1 JSON/XML/MD from MITRE ATT&CK, CWE, OWASP Top 10",
    "  • Chunk into 500-token segments with overlap",
    "  • Embed and upsert into Qdrant",
    "  • Rebuild BM25 index post-ingestion",
    "",
    "Work Plan Timeline:",
    "  • Phase 1 (Weeks 1-2): Project setup, FastAPI scaffolding",
    "  • Phase 2 (Weeks 3-4): Vector store integration, BM25 implementation",
    "  • Phase 3 (Weeks 5-6): Hybrid retrieval, reranker, Streamlit UI",
    "  • Phase 4 (Weeks 7-8): Cloud deployment, testing, evaluation",
    "  • Future: CAPEC/CISA KEV integration, multi-turn conversations, custom LLM",
],
    notes=(
        "The project was executed in four phases over 8 weeks. Phase 1 established the development "
        "environment and backend scaffolding. Phase 2 integrated Qdrant for vector storage and implemented "
        "BM25 sparse retrieval along with the initial ingestion pipeline. Phase 3 brought together "
        "the hybrid retrieval system, cross-encoder reranker, and Streamlit UI. Phase 4 focused on "
        "live cloud deployment on Render and Qdrant Cloud, followed by comprehensive testing "
        "with a 60-question evaluation benchmark. The presentation demonstrates the system's "
        "complete functionality and readiness for college evaluation."
    ),
]
section3.add_content_slide(b, notes)

# Section 4: Progress Achieved
section4 = add_title_slide(
    "Section 4: Progress Achieved",
    "What has been built and the results so far"
)
for b in [
    "Key Features Delivered:",
    "  • Hybrid retrieval: Dense (Qdrant) + Sparse (BM25) + RRF fusion ✓",
    "  • Cross-encoder reranker for fine-grained relevance scoring ✓",
    "  • MITRE ATT&CK ingestion: 867 techniques indexed ✓",
    "  • CWE ingestion: 939 weaknesses with relationship mapping ✓",
    "  • OWASP Top 10 2025 integration with 10 categories ✓",
    "  • Safety guardrails: exploit refusal + prompt injection sanitization ✓",
    "  • Cited responses with inline references [1], [2] ✓",
    "  • Streamlit UI with source filtering and citation cards ✓",
    "  • Cloud deployment on Render.com + Qdrant Cloud free tier ✓",
    "  • Evaluation benchmark: 60-question test suite passing ✓",
],
    notes=(
        "All core features are complete and operational. The hybrid retrieval system combining "
        "dense vector search in Qdrant with in-memory BM25 and Reciprocal Rank Fusion is fully "
        "functional. All three data sources are integrated: MITRE ATT&CK with 867 techniques, "
        "CWE with 939 weaknesses, and OWASP Top 10. The system is live on Render and Qdrant "
        "Cloud's free tier. The evaluation benchmark with 60 questions demonstrates strong "
        "performance metrics. Documentation is complete and ready for submission."
    ),
]
section4.add_content_slide(b, notes)

# Section 5: Future Work & Timeline
section5 = add_title_slide(
    "Section 5: Future Work & Timeline",
    "Next steps and long-term vision for CyberSense"
)
for b in [
    "Short-term (1-3 months):",
    "  • Add CAPEC attack pattern database",
    "  • Integrate CISA KEV (Known Exploited Vulnerabilities) list",
    "  • Implement query expansion using security ontologies",
    "  • Add multi-turn conversation memory",
    "",
    "Medium-term (3-6 months):",
    "  • NIST SP 800-53 control mapping",
    "  • Full CVE database integration",
    "  • Vulnerability prioritization pipeline",
    "  • Performance optimization (embedding quantization)",
    "",
    "Long-term (6-12 months):",
    "  • Custom fine-tuned security LLM",
    "  • Automated report generation",
    "  • Integration with enterprise SIEM systems",
    "  • CVE-to-ATT&CK mapping graph",
],
    notes=(
        "Our roadmap spans three horizons. Short term (1-3 months) focuses on expanding data "
        "sources with CAPEC and CISA KEV, adding multi-turn conversation memory, and optimizing "
        "performance through embedding quantization. Medium term (3-6 months) targets NIST 800-53 "
        "control mapping, full CVE database integration, vulnerability prioritization, and "
        "performance optimizations. Long term (6-12 months) includes custom fine-tuned security "
        "LLM, automated compliance reporting, and enterprise SIEM integration."
    ),
]
section5.add_content_slide(b, notes)

# Conclusion
conclusion = add_title_slide(
    "Conclusion",
    "CyberSense successfully delivers a grounded, cited RAG system for cybersecurity"
)
for b in [
    "✅ Successfully delivered:",
    "  • A grounded, cited RAG system specifically designed for cybersecurity knowledge synthesis",
    "  • Integration of 3 authoritative knowledge sources (MITRE ATT&CK, CWE, OWASP)",
    "  • Scalable free-tier cloud deployment",
    "  • Academic-quality evaluation and documentation",
    "\nReady for college evaluation!",
],
    notes=(
        "In conclusion, CyberSense successfully delivers a sophisticated RAG system tailored "
        "for cybersecurity knowledge. We have integrated three authoritative sources, built a "
        "hybrid retrieval pipeline with cross-encoder reranking, deployed on free-tier cloud "
        "infrastructure, and completed a rigorous evaluation benchmark. The MVP is complete, "
        "the system is production-ready, and all documentation is prepared for your college "
        "evaluation submission."
    )
)

# Save
prs.save("CyberSense_Presentation.pptx")
print(f"[SUCCESS] Presentation created successfully!")
print(f"Total slides: {len(prs.slides)}")
print(f"Saved to: CyberSense_Presentation.pptx")
