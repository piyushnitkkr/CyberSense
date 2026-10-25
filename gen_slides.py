"""
CyberSense — Professional IEEE-Evaluation Presentation Generator.
Features: dark-mode design, diagram/chart visuals, minimal text, planned features clearly labelled.
Run: .venv\Scripts\python gen_slides.py
"""

from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from lxml import etree

# ── Brand palette ───────────────────────────────────────────────────────────────
C = {
    "bg_dark":    RGBColor(0x0B, 0x0F, 0x19),  # slide background
    "panel":      RGBColor(0x11, 0x18, 0x27),  # card background
    "accent":     RGBColor(0x00, 0xE5, 0xFF),  # cyan accent
    "green":      RGBColor(0x00, 0xF5, 0xA0),  # deployed green
    "gold":       RGBColor(0xFF, 0xD7, 0x00),  # planned / highlight
    "violet":     RGBColor(0xB3, 0x88, 0xFF),  # alt accent
    "white":      RGBColor(0xFF, 0xFF, 0xFF),
    "muted":      RGBColor(0x94, 0xA3, 0xB8),
    "danger":     RGBColor(0xFF, 0x52, 0x52),
}

W = Inches(13.333)
H = Inches(7.5)

prs = Presentation()
prs.slide_width = W
prs.slide_height = H


# ── Low-level helpers ────────────────────────────────────────────────────────────

def blank_slide():
    return prs.slides.add_slide(prs.slide_layouts[6])


def set_bg(slide, color: RGBColor):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_box(slide, left, top, width, height,
            fill=None, border_color=None, border_pt=0) -> object:
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        left, top, width, height
    )
    shape.line.width = Pt(border_pt) if border_pt else Pt(0)
    if border_color:
        shape.line.color.rgb = border_color
    else:
        shape.line.fill.background()
    if fill:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
    else:
        shape.fill.background()
    return shape


def add_text(slide, text, left, top, width, height,
             size=18, bold=False, italic=False, color=None,
             align=PP_ALIGN.LEFT, wrap=True):
    txb = slide.shapes.add_textbox(left, top, width, height)
    tf = txb.text_frame
    tf.word_wrap = wrap
    tf.auto_size = None
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color or C["white"]
    return txb


def add_multiline(slide, lines, left, top, width, height,
                  size=16, color=None, spacing=Pt(6)):
    txb = slide.shapes.add_textbox(left, top, width, height)
    tf = txb.text_frame
    tf.word_wrap = True
    first = True
    for line in lines:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        run = p.add_run()
        run.text = line
        run.font.size = Pt(size)
        run.font.color.rgb = color or C["white"]
        p.space_after = spacing
    return txb


def add_image(slide, img_path, left, top, width, height):
    if Path(img_path).exists():
        slide.shapes.add_picture(img_path, left, top, width, height)
    else:
        # Placeholder if image missing
        add_box(slide, left, top, width, height,
                fill=C["panel"], border_color=C["accent"], border_pt=1)
        add_text(slide, f"[Image: {Path(img_path).name}]",
                 left, top + height // 2 - Pt(10),
                 width, Pt(30), size=10, color=C["muted"], align=PP_ALIGN.CENTER)


def header_bar(slide, title, subtitle=""):
    """Top accent bar with title."""
    add_box(slide, 0, 0, W, Inches(1.1), fill=C["panel"])
    add_box(slide, 0, Inches(1.05), W, Pt(3), fill=C["accent"])
    add_text(slide, title,
             Inches(0.45), Inches(0.12), Inches(12.4), Inches(0.6),
             size=26, bold=True, color=C["accent"])
    if subtitle:
        add_text(slide, subtitle,
                 Inches(0.45), Inches(0.68), Inches(12.4), Inches(0.3),
                 size=12, color=C["muted"])


def footer(slide, page_num, total=10):
    add_text(slide, f"CyberSense  |  B.Tech Final Year Project  |  October 2026",
             Inches(0.4), Inches(7.15), Inches(9), Inches(0.28),
             size=8, color=C["muted"])
    add_text(slide, f"{page_num} / {total}",
             Inches(12.5), Inches(7.15), Inches(0.8), Inches(0.28),
             size=9, bold=True, color=C["muted"], align=PP_ALIGN.RIGHT)


def pill_badge(slide, text, left, top, bg_color, text_color=None):
    w, h = Inches(2.0), Inches(0.32)
    box = slide.shapes.add_shape(1, left, top, w, h)
    box.fill.solid()
    box.fill.fore_color.rgb = bg_color
    box.line.fill.background()
    tf = box.text_frame
    tf.word_wrap = False
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = text
    run.font.size = Pt(9)
    run.font.bold = True
    run.font.color.rgb = text_color or C["bg_dark"]
    return box


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 1 — Title
# ════════════════════════════════════════════════════════════════════════════════

s1 = blank_slide()
set_bg(s1, C["bg_dark"])

# Central glow rectangle
add_box(s1, Inches(1.2), Inches(1.6), Inches(10.9), Inches(4.5),
        fill=C["panel"], border_color=C["accent"], border_pt=1.5)

add_text(s1, "CYBERSENSE",
         Inches(1.5), Inches(1.85), Inches(10.3), Inches(1.1),
         size=58, bold=True, color=C["accent"], align=PP_ALIGN.CENTER)
add_text(s1, "A Domain-Specific Retrieval-Augmented Generation System",
         Inches(1.5), Inches(3.0), Inches(10.3), Inches(0.5),
         size=18, color=C["white"], align=PP_ALIGN.CENTER)
add_text(s1, "for Cybersecurity Knowledge Synthesis",
         Inches(1.5), Inches(3.45), Inches(10.3), Inches(0.4),
         size=18, color=C["white"], align=PP_ALIGN.CENTER)

add_text(s1, "Piyush Kumar  |  Department of Computer Engineering  |  B.Tech Final Year",
         Inches(1.5), Inches(4.2), Inches(10.3), Inches(0.35),
         size=12, color=C["muted"], align=PP_ALIGN.CENTER)
add_text(s1, "October 2026  |  Live: https://cybersense-api-vorj.onrender.com",
         Inches(1.5), Inches(4.55), Inches(10.3), Inches(0.3),
         size=11, color=C["muted"], align=PP_ALIGN.CENTER)

# Tag row
pill_badge(s1, "FastAPI + Qdrant Cloud", Inches(2.8), Inches(5.2), C["accent"])
pill_badge(s1, "Groq LLM Engine", Inches(5.1), Inches(5.2), C["violet"])
pill_badge(s1, "MITRE ATT&CK + CWE + OWASP", Inches(7.4), Inches(5.2), C["green"])

# Bottom accent line
add_box(s1, 0, Inches(7.2), W, Pt(4), fill=C["accent"])


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 2 — Problem Statement
# ════════════════════════════════════════════════════════════════════════════════

s2 = blank_slide()
set_bg(s2, C["bg_dark"])
header_bar(s2, "The Problem: Fragmented Cybersecurity Knowledge",
           "Why general AI tools fail for security professionals")
footer(s2, 2)

# 3 problem cards
cards = [
    ("Fragmented Sources", "MITRE ATT&CK, NVD, OWASP, CWE — scattered across\nhundreds of repositories with no unified interface.", C["danger"]),
    ("LLM Hallucinations", "General LLMs invent CVE IDs, wrong technique\nnumbers, and outdated mitigations with high confidence.", C["gold"]),
    ("No Source Citations", "Practitioners cannot verify AI answers without\ntransparent source attribution and inline citations.", C["violet"]),
]

for i, (title, desc, accent) in enumerate(cards):
    lx = Inches(0.4 + i * 4.3)
    add_box(s2, lx, Inches(1.4), Inches(4.0), Inches(4.5),
            fill=C["panel"], border_color=accent, border_pt=1.5)
    add_box(s2, lx, Inches(1.4), Inches(4.0), Pt(4), fill=accent)
    add_text(s2, title,
             lx + Inches(0.15), Inches(1.6), Inches(3.7), Inches(0.5),
             size=16, bold=True, color=accent)
    add_text(s2, desc,
             lx + Inches(0.15), Inches(2.2), Inches(3.7), Inches(2.0),
             size=13, color=C["white"])

# Bottom solution banner
add_box(s2, Inches(0.4), Inches(6.3), Inches(12.5), Inches(0.85),
        fill=RGBColor(0x05, 0x15, 0x20), border_color=C["accent"], border_pt=1)
add_text(s2, "CyberSense Solution: Grounded RAG with authoritative sources + verifiable inline citations",
         Inches(0.6), Inches(6.4), Inches(12.1), Inches(0.5),
         size=14, bold=True, color=C["accent"], align=PP_ALIGN.CENTER)


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 3 — System Architecture Diagram
# ════════════════════════════════════════════════════════════════════════════════

s3 = blank_slide()
set_bg(s3, C["bg_dark"])
header_bar(s3, "System Architecture: Hybrid RAG Pipeline",
           "Five-stage processing: Safety → Retrieve → Fuse → Rerank → Generate")
footer(s3, 3)

add_image(s3, "assets/architecture_diagram.png",
          Inches(0.3), Inches(1.2), Inches(12.7), Inches(6.0))


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 4 — Knowledge Base & Data Sources
# ════════════════════════════════════════════════════════════════════════════════

s4 = blank_slide()
set_bg(s4, C["bg_dark"])
header_bar(s4, "Knowledge Base: Authoritative Cybersecurity Sources",
           "STIX 2.1 JSON • XML • Markdown — indexed into Qdrant Cloud (384-dim BGE embeddings)")
footer(s4, 4)

# 3 source cards — DEPLOYED
deployed_sources = [
    ("MITRE ATT&CK", "Enterprise + ICS + Mobile\n967+ techniques & sub-techniques\nMitigations, Detection, Data Sources\nSTIX 2.1 JSON bundles", C["green"]),
    ("MITRE CWE", "939 Software Weaknesses\nDescriptions, Platforms,\nConsequence Chains, Examples\ncwec_latest.xml (MITRE)", C["accent"]),
    ("OWASP Top 10", "2025 Edition (Latest)\n10 Critical Risk Categories\nA01-A10 with Prevention\nMarkdown Documentation", C["violet"]),
]

for i, (title, desc, accent) in enumerate(deployed_sources):
    lx = Inches(0.35 + i * 4.3)
    add_box(s4, lx, Inches(1.35), Inches(4.0), Inches(4.3),
            fill=C["panel"], border_color=accent, border_pt=1.5)
    add_text(s4, title,
             lx + Inches(0.15), Inches(1.5), Inches(3.7), Inches(0.45),
             size=18, bold=True, color=accent)
    pill_badge(s4, "DEPLOYED", lx + Inches(2.0), Inches(1.52), C["green"])
    add_text(s4, desc,
             lx + Inches(0.15), Inches(2.1), Inches(3.7), Inches(2.5),
             size=12.5, color=C["white"])

# Planned row
add_box(s4, Inches(0.35), Inches(5.85), Inches(12.6), Inches(1.3),
        fill=C["panel"], border_color=C["gold"], border_pt=1)
add_text(s4, "ROADMAP — Planned Data Sources (Next 2.5 Months)",
         Inches(0.55), Inches(5.9), Inches(5.5), Inches(0.38),
         size=12, bold=True, color=C["gold"])
planned = [
    "Drag & Drop UI (Month 1)  |  CISA KEV Live Sync (Month 1)  |  NVD CVE 2.0 API (Month 1-2)  |  CAPEC Patterns (Month 2)"
]
add_text(s4, planned[0], Inches(0.55), Inches(6.35), Inches(12.1), Inches(0.5),
         size=12, color=C["muted"])


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 5 — Live UI Screenshot
# ════════════════════════════════════════════════════════════════════════════════

s5 = blank_slide()
set_bg(s5, C["bg_dark"])
header_bar(s5, "User Interface: Streamlit Web Application",
           "Real-time streaming answers with collapsible verified source citations")
footer(s5, 5)

add_image(s5, "assets/ui_screenshot.png",
          Inches(0.4), Inches(1.25), Inches(12.55), Inches(5.95))


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 6 — Hybrid Retrieval Deep-Dive
# ════════════════════════════════════════════════════════════════════════════════

s6 = blank_slide()
set_bg(s6, C["bg_dark"])
header_bar(s6, "Hybrid Retrieval: Dense + Sparse + Rerank",
           "Reciprocal Rank Fusion ensures both semantic recall and exact identifier precision")
footer(s6, 6)

# Two columns
left_panel_data = [
    ("DENSE VECTOR SEARCH", C["accent"], [
        "Model: BAAI/bge-small-en-v1.5",
        "Dimension: 384-d cosine similarity",
        "Database: Qdrant Cloud (HNSW index)",
        "Top-K: 30 candidates retrieved",
        "Strength: Semantic understanding",
    ]),
    ("SPARSE BM25 SEARCH", C["violet"], [
        "Engine: rank_bm25 (in-memory)",
        "Populated: Qdrant full scroll on startup",
        "Tokenizer: regex [a-zA-Z0-9_.-]+",
        "Top-K: 30 candidates retrieved",
        "Strength: Exact ID/token matching",
    ]),
]

for i, (title, accent, points) in enumerate(left_panel_data):
    top = Inches(1.3 + i * 2.85)
    add_box(s6, Inches(0.35), top, Inches(5.8), Inches(2.6),
            fill=C["panel"], border_color=accent, border_pt=1.2)
    add_text(s6, title, Inches(0.5), top + Inches(0.1),
             Inches(5.5), Inches(0.38), size=13, bold=True, color=accent)
    add_multiline(s6, ["• " + p for p in points],
                  Inches(0.5), top + Inches(0.55), Inches(5.5), Inches(1.9),
                  size=12, color=C["white"], spacing=Pt(3))

# Centre merge arrow
add_box(s6, Inches(6.4), Inches(3.2), Inches(0.55), Inches(1.1),
        fill=C["accent"])
add_text(s6, "RRF\nk=60",
         Inches(6.35), Inches(3.3), Inches(0.65), Inches(0.8),
         size=10, bold=True, color=C["bg_dark"], align=PP_ALIGN.CENTER)

# Right panel — reranker
add_box(s6, Inches(7.2), Inches(1.3), Inches(5.75), Inches(5.6),
        fill=C["panel"], border_color=C["green"], border_pt=1.2)
add_text(s6, "FUSION & RERANKING", Inches(7.4), Inches(1.4),
         Inches(5.4), Inches(0.38), size=13, bold=True, color=C["green"])

fusion_points = [
    "RRF merges dense + sparse ranked lists",
    "Score formula: sum(1/(k + rank_i))",
    "Eliminates score-space incompatibility",
    "",
    "CROSS-ENCODER RERANKER (Optional)",
    "Model: BAAI/bge-reranker-base",
    "Evaluates (query, chunk) pairs jointly",
    "Top-8 re-scored for precision tasks",
    "Disabled on free-tier (RAM constraint)",
    "",
    "ENTITY SHORTCUT",
    "Regex: CVE-YYYY-NNNNN  |  T\\d{4}  |  CWE-NN",
    "Direct Qdrant payload filter — exact match",
    "Bypasses semantic stage for ID queries",
]
add_multiline(s6, ["  " + p if not p.isupper() and p else p for p in fusion_points],
              Inches(7.4), Inches(1.85), Inches(5.3), Inches(4.8),
              size=11.5, color=C["white"], spacing=Pt(2.5))


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 7 — Evaluation / Benchmarks
# ════════════════════════════════════════════════════════════════════════════════

s7 = blank_slide()
set_bg(s7, C["bg_dark"])
header_bar(s7, "Evaluation Results: 60-Question Golden Benchmark",
           "CyberSense (Hybrid RAG) vs. Ungrounded General-Purpose LLM Baseline")
footer(s7, 7)

add_image(s7, "assets/benchmark_comparison.png",
          Inches(0.5), Inches(1.25), Inches(8.5), Inches(5.5))

# Stats aside
stats = [
    ("94%", "Factual Accuracy", C["green"]),
    ("98%", "Citation Grounding", C["accent"]),
    ("99%", "Guardrail Adherence", C["violet"]),
    ("91%", "Correct Abstention", C["gold"]),
    ("< 2s", "Query Latency", C["white"]),
]
for i, (val, label, col) in enumerate(stats):
    top = Inches(1.35 + i * 1.1)
    add_box(s7, Inches(9.2), top, Inches(3.8), Inches(0.95),
            fill=C["panel"], border_color=col, border_pt=1.2)
    add_text(s7, val, Inches(9.35), top + Inches(0.05),
             Inches(1.2), Inches(0.55), size=26, bold=True, color=col)
    add_text(s7, label, Inches(10.65), top + Inches(0.18),
             Inches(2.2), Inches(0.45), size=12, color=C["muted"])


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 8 — Implemented Features Summary
# ════════════════════════════════════════════════════════════════════════════════

s8 = blank_slide()
set_bg(s8, C["bg_dark"])
header_bar(s8, "What's Built & Deployed",
           "All core MVP components are live in production — zero infrastructure cost")
footer(s8, 8)

implemented = [
    "Hybrid RAG: Dense (Qdrant) + Sparse (BM25) + RRF Fusion",
    "MITRE ATT&CK Enterprise + ICS + Mobile (967+ techniques with mitigations)",
    "MITRE CWE Weaknesses (939 entries, full weakness chain data)",
    "OWASP Top 10 2025 (A01-A10 risk categories)",
    "Safety Guardrails: Exploit refusal + prompt injection sanitization",
    "Inline Citation Validation (every factual claim source-mapped)",
    "Real-time Streaming via Server-Sent Events (SSE)",
    "Entity Extraction Fast-Path (CVE, CWE, T-code regex filters)",
    "Admin API: BM25 rebuild, ingestion triggers, document CRUD",
    "Full CI/CD: GitHub Actions, Ruff linting, Black formatting, Pytest (35 tests)",
]

for i, item in enumerate(implemented):
    lx = Inches(0.45) if i < 5 else Inches(6.85)
    top = Inches(1.3 + (i % 5) * 1.06)
    add_box(s8, lx, top, Inches(6.1), Inches(0.9),
            fill=C["panel"], border_color=C["green"], border_pt=1)
    add_box(s8, lx, top, Pt(5), Inches(0.9), fill=C["green"])
    add_text(s8, item,
             lx + Inches(0.12), top + Inches(0.17), Inches(5.85), Inches(0.5),
             size=12, color=C["white"])
    pill_badge(s8, "LIVE", lx + Inches(4.85), top + Inches(0.3), C["green"])


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 9 — 2.5-Month Roadmap
# ════════════════════════════════════════════════════════════════════════════════

s9 = blank_slide()
set_bg(s9, C["bg_dark"])
header_bar(s9, "2.5-Month Development Roadmap (10-Week Sprint Plan)",
           "Structured milestones for the next evaluation cycle")
footer(s9, 9)

add_image(s9, "assets/roadmap_gantt.png",
          Inches(0.35), Inches(1.2), Inches(12.65), Inches(5.15))

# Sprint summary boxes
sprints = [
    ("Month 1", "Drag & Drop UI + CISA KEV Live Sync", C["accent"]),
    ("Month 1-2", "NVD CVE 2.0 API + Threat Graph Links", C["gold"]),
    ("Month 2", "CAPEC Patterns + RAGAS Eval Suite", C["violet"]),
    ("Month 2.5", "Automated SOC Threat Report Export", C["green"]),
]
for i, (month, desc, col) in enumerate(sprints):
    lx = Inches(0.35 + i * 3.25)
    add_box(s9, lx, Inches(6.5), Inches(3.05), Inches(0.75),
            fill=C["panel"], border_color=col, border_pt=1)
    add_text(s9, f"{month}: {desc}", lx + Inches(0.1), Inches(6.55),
             Inches(2.85), Inches(0.55), size=10, bold=True, color=col)


# ════════════════════════════════════════════════════════════════════════════════
# SLIDE 10 — Conclusion
# ════════════════════════════════════════════════════════════════════════════════

s10 = blank_slide()
set_bg(s10, C["bg_dark"])
header_bar(s10, "Conclusion & Project Status",
           "CyberSense: Production-ready Cybersecurity RAG — Zero-cost Cloud Deployment")
footer(s10, 10)

# Left: summary
add_box(s10, Inches(0.35), Inches(1.25), Inches(7.5), Inches(5.8),
        fill=C["panel"], border_color=C["accent"], border_pt=1)
add_text(s10, "What CyberSense Achieves",
         Inches(0.55), Inches(1.35), Inches(7.1), Inches(0.42),
         size=15, bold=True, color=C["accent"])

summary_pts = [
    "Grounds every answer in authoritative sources (ATT&CK, CWE, OWASP)",
    "Eliminates LLM hallucinations through strict retrieval grounding",
    "Provides verifiable inline citations for every factual claim",
    "Hybrid retrieval for both semantic understanding + exact ID matching",
    "Fully deployed at zero cost: Render + Qdrant Cloud + Groq Cloud",
    "35 unit/integration tests, ruff-linted, black-formatted codebase",
    "94% factual accuracy vs. 58% for ungrounded LLM baseline",
]
add_multiline(s10, ["  + " + p for p in summary_pts],
              Inches(0.55), Inches(1.9), Inches(7.1), Inches(4.8),
              size=13, color=C["white"], spacing=Pt(10))

# Right: status indicators
add_box(s10, Inches(8.1), Inches(1.25), Inches(4.85), Inches(5.8),
        fill=C["panel"], border_color=C["green"], border_pt=1)
add_text(s10, "Project Status",
         Inches(8.3), Inches(1.35), Inches(4.5), Inches(0.42),
         size=15, bold=True, color=C["green"])

status_items = [
    ("MVP", "COMPLETE & DEPLOYED", C["green"]),
    ("Tests", "35/35 PASSING", C["green"]),
    ("CI/CD", "GITHUB ACTIONS OK", C["green"]),
    ("Linting", "RUFF + BLACK CLEAN", C["green"]),
    ("Drag & Drop UI", "PLANNED — MONTH 1", C["gold"]),
    ("KEV & CVE Sync", "PLANNED — MONTH 1-2", C["gold"]),
    ("SOC Export", "PLANNED — MONTH 2.5", C["gold"]),
]
for i, (label, val, col) in enumerate(status_items):
    top = Inches(1.9 + i * 0.72)
    add_text(s10, label + ":", Inches(8.3), top,
             Inches(1.6), Inches(0.4), size=11, bold=True, color=C["muted"])
    add_text(s10, val, Inches(9.95), top,
             Inches(2.8), Inches(0.4), size=11, bold=True, color=col)

# Footer URL bar
add_box(s10, Inches(0.35), Inches(7.05), Inches(12.6), Inches(0.3),
        fill=C["panel"])
add_text(s10,
         "https://cybersense-api-vorj.onrender.com  |  "
         "GitHub: github.com/piyushnitkkr/CyberSense",
         Inches(0.5), Inches(7.06), Inches(12.3), Inches(0.28),
         size=9, color=C["muted"], align=PP_ALIGN.CENTER)


# ── Save ─────────────────────────────────────────────────────────────────────────

prs.save("CyberSense_Final_Presentation.pptx")
print("SUCCESS: CyberSense_Final_Presentation.pptx saved (10 slides).")
