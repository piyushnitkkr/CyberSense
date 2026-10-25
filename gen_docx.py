from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document()

# Title
title = doc.add_heading('CYBERSENSE: A Cybersecurity RAG Assistant for Academic Research', 0)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('Project Evaluation Report & Documentation\nDepartment of Computer Engineering | October 2026')
run.font.size = Pt(14)
run.font.color.rgb = RGBColor(102, 102, 102)

doc.add_heading('Executive Summary', level=1)
doc.add_paragraph(
    'CyberSense is an enterprise-grade Retrieval-Augmented Generation (RAG) assistant built specifically '
    'for cybersecurity engineering, incident response, and vulnerability analysis. It synthesizes knowledge '
    'across authoritative cybersecurity repositories—including MITRE ATT&CK Enterprise (867 techniques), '
    'MITRE CWE (939 weaknesses), and OWASP Top 10 2025—providing grounded, fact-checked answers with '
    'verified inline citations and hallucination-resistant abstention.'
)

doc.add_heading('1. Problem Identification and Objectives', level=1)
doc.add_paragraph(
    'Cybersecurity knowledge is vast, fragmented, and rapidly evolving across multiple official repositories. '
    'Security professionals and students struggle to find accurate, contextual answers quickly. Traditional keyword '
    'search engines fail because security queries require semantic understanding, domain-specific terminology, '
    'and precise identifier lookups (CVE, CWE, T* IDs). CyberSense bridges this gap by providing an AI-powered '
    'RAG assistant that ingests authoritative datasets and returns cited, verified answers.'
)
doc.add_paragraph('Key Objectives:\n'
    '1. Integrate authoritative cybersecurity data sources (MITRE ATT&CK, CWE, OWASP Top 10).\n'
    '2. Implement a hybrid retrieval pipeline combining dense vector embeddings (Qdrant) and sparse BM25 search.\n'
    '3. Ensure zero hallucination through strict grounding and citation validation.\n'
    '4. Deploy a scalable, zero-cost cloud architecture (Render.com + Qdrant Cloud + Groq Cloud).')

doc.add_heading('2. Literature Review and Related Work', level=1)
doc.add_paragraph(
    'Retrieval-Augmented Generation (RAG), introduced by Lewis et al. (2020), combines parametric language models '
    'with non-parametric external memory. In cybersecurity, related tools include MITRE ATT&CK Navigator, MITRE ATLAS, '
    'and commercial SIEM assistants like Microsoft Copilot for Security and IBM QRadar. However, most commercial tools '
    'are proprietary and opaque. CyberSense provides an open academic alternative with transparent citation grounding.'
)

doc.add_heading('3. Methodology and Work Plan', level=1)
doc.add_paragraph(
    'CyberSense implements an advanced multi-stage RAG pipeline:\n'
    '- Query Pipeline: Rewrite query using conversation history + entity extraction (CVE/CWE/ATT&CK IDs).\n'
    '- Dual Retrieval: Dense search in Qdrant (384-dim all-MiniLM-L6-v2) + sparse BM25 search.\n'
    '- Fusion & Rerank: Reciprocal Rank Fusion (RRF) + cross-encoder reranker (ms-marco-MiniLM-L-6-v2).\n'
    '- Generation: Groq LLM inference with strict citation verification.'
)

doc.add_heading('4. Progress Achieved', level=1)
doc.add_paragraph(
    'All core deliverables are complete:\n'
    '- 867 MITRE ATT&CK techniques successfully ingested (STIX 2.1 JSON).\n'
    '- 939 MITRE CWE weaknesses indexed.\n'
    '- OWASP Top 10 2025 categories loaded.\n'
    '- Live cloud deployment active on Render.com and Qdrant Cloud.\n'
    '- Evaluation benchmark (60-question golden set) passing successfully.'
)

doc.add_heading('5. Future Work and Timeline', level=1)
doc.add_paragraph(
    '- Short-term (1-3 months): CAPEC attack pattern integration, CISA KEV catalog, multi-turn conversation memory.\n'
    '- Medium-term (3-6 months): NIST SP 800-53 control mapping, full CVE database integration.\n'
    '- Long-term (6-12 months): Custom fine-tuned security LLM and enterprise SIEM integration.'
)

doc.add_heading('6. Viva Voce Questions & Answers (20+ Q&A)', level=1)
viva_qs = [
    ("Q1: What is RAG and why is it needed in cybersecurity?", "Retrieval-Augmented Generation combines LLMs with external knowledge bases. Cybersecurity data changes daily and requires precise factual grounding; pure LLMs hallucinate CVE details or outdated mitigation steps."),
    ("Q2: Why use hybrid retrieval instead of just vector search?", "Dense vector search captures semantic similarity but often misses exact identifier matches (like CVE-2021-44228 or CWE-79). BM25 sparse search ensures exact token matching. Combining them via Reciprocal Rank Fusion (RRF) provides the best of both worlds."),
    ("Q3: How many MITRE ATT&CK techniques did you ingest?", "We ingested 867 Enterprise ATT&CK techniques from the official STIX 2.1 JSON repository, parsed into structured document chunks."),
    ("Q4: Which vector database did you use and why?", "We used Qdrant Cloud (Free Tier) because it offers high-performance HNSW indexing, native metadata filtering, and a scroll API used to rebuild the in-memory BM25 index."),
    ("Q5: How does CyberSense prevent hallucinations?", "Through strict grounding: retrieved chunks must exceed relevance criteria, and the prompt instructs the model to abstain ('I couldn't find relevant information') if context lacks the answer."),
    ("Q6: Explain the query rewriting process.", "When chat history is present, an LLM prompt rewrites the follow-up question into a standalone query while preserving security acronyms and technical terms."),
    ("Q7: What embedding model is used?", "all-MiniLM-L6-v2 from sentence-transformers, producing 384-dimensional dense vectors balanced for speed and accuracy."),
    ("Q8: How are security entity IDs handled?", "Regex entity extraction identifies CVEs, CWEs, and ATT&CK IDs (e.g. T1059) and performs direct ID filtering in Qdrant, guaranteeing exact matches appear at the top of results."),
    ("Q9: What is the role of the cross-encoder reranker?", "A cross-encoder (ms-marco-MiniLM-L-6-v2) evaluates query-chunk pairs jointly to provide fine-grained relevance scoring before passing top chunks to the LLM."),
    ("Q10: How is the system deployed on free cloud tiers?", "FastAPI backend is hosted on Render.com, vector storage on Qdrant Cloud, and LLM inference on Groq Cloud—achieving 100% free production deployment."),
    ("Q11: What safety guardrails are implemented?", "Guardrails block prompt injection attempts and refuse prompts requesting functional exploit scripts, malware payloads, or unauthorized attack instructions."),
    ("Q12: How are citations formatted in responses?", "Every factual claim includes inline citation tags [1], [2] mapping to source documents with deep links and excerpt cards."),
    ("Q13: What is the purpose of BM25 rebuilds?", "BM25 is an in-memory sparse index. When new documents or uploads are added, the index is rebuilt by scrolling all points from Qdrant."),
    ("Q14: How does file upload work?", "Users can upload PDF, DOCX, MD, TXT, or HTML files. The app extracts text, chunks it, embeds it, and indexes it for immediate retrieval in private sessions."),
    ("Q15: What is the evaluation benchmark size?", "A 60-question golden set covering exact-ID lookups, conceptual explanations, multi-document comparisons, and unanswerable abstention tests."),
    ("Q16: What database is used for session tracking?", "SQLite with SQLAlchemy async session management stores document records and ingestion run metadata."),
    ("Q17: Why did you choose FastAPI over Flask or Django?", "FastAPI provides asynchronous support, automatic OpenAPI/Swagger documentation, Pydantic validation, and high performance ideal for streaming SSE responses."),
    ("Q18: What are the latency benchmarks?", "Cold cache query latency is under 2 seconds; warm cache latency is under 1 second."),
    ("Q19: What datasets are planned for future versions?", "CAPEC (Common Attack Pattern Enumeration and Classification) and CISA KEV (Known Exploited Vulnerabilities)."),
    ("Q20: How does CyberSense comply with responsible AI guidelines?", "It enforces defensive-only usage, refusing offensive exploitation while supporting security analysis, hardening, and education.")
]

for q, a in viva_qs:
    doc.add_heading(q, level=2)
    doc.add_paragraph(a)

doc.add_heading('7. Email Draft for Supervisor Submission', level=1)
doc.add_paragraph(
    "Subject: CyberSense Project Report and Presentation Submission\n\n"
    "Respected Professor / Supervisor,\n\n"
    "I am pleased to submit the project evaluation report and presentation for 'CyberSense: A Cybersecurity RAG Assistant for Academic Research'.\n\n"
    "Project Highlights:\n"
    "- Fully functional RAG assistant integrating MITRE ATT&CK (867 techniques), CWE, and OWASP Top 10.\n"
    "- Advanced hybrid retrieval pipeline (Dense Qdrant + Sparse BM25 + RRF + Cross-Encoder Reranker).\n"
    "- Live zero-cost cloud deployment (Render.com + Qdrant Cloud + Groq Cloud).\n"
    "- Comprehensive evaluation benchmark (60-question golden set) and 20+ viva Q&A.\n\n"
    "Attached Files:\n"
    "1. CyberSense_Presentation.pptx (11 professional evaluation slides)\n"
    "2. CyberSense_Report.docx (Complete academic project report)\n\n"
    "Thank you for your continuous guidance and support throughout this project.\n\n"
    "Sincerely,\n"
    "CyberSense Project Team"
)

doc.save('CyberSense_Report.docx')
print("SUCCESS: CyberSense_Report.docx fully updated with all sections and viva Q&A.")
