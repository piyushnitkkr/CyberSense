"""
Generate updated 2.5-month Roadmap Gantt Chart for CyberSense.
Includes realistic, achievable features with Drag & Drop Ingestion UI as planned.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from pathlib import Path

# Styling
plt.style.use("dark_background")
fig, ax = plt.subplots(figsize=(12, 6.2), dpi=300)
fig.patch.set_facecolor("#0B0F19")
ax.set_facecolor("#111827")

# Tasks: (Task Name, Start Week, Duration Weeks, Category/Color)
tasks = [
    ("Drag & Drop Ingestion UI (PDF/DOCX/MD)", 1, 2.5, "#00E5FF", "Month 1"),
    ("CISA KEV Live Vulnerability Sync", 2, 2.5, "#38BDF8", "Month 1"),
    ("NVD CVE 2.0 API Lookup Integration", 3.5, 2.5, "#818CF8", "Month 1-2"),
    ("CAPEC Attack Pattern Knowledge Base", 5, 2.5, "#A78BFA", "Month 2"),
    ("Graph-Based Threat Entity Mapping", 6, 2.5, "#F472B6", "Month 2"),
    ("RAGAS Automated Evaluation Pipeline", 7.5, 2.0, "#FBBF24", "Month 2-2.5"),
    ("Automated SOC Threat Report Export", 8.5, 1.5, "#00F5A0", "Month 2.5"),
]

y_positions = np.arange(len(tasks))

# Draw task bars
for idx, (name, start, dur, color, phase) in enumerate(tasks):
    # Bar shadow
    ax.barh(idx, dur, left=start, height=0.48, color=color, alpha=0.9,
            edgecolor="#FFFFFF", linewidth=0.8, zorder=3)
    # Milestone marker at end
    ax.plot(start + dur, idx, marker="D", markersize=6, color="#FFFFFF",
            markeredgecolor=color, markeredgewidth=1.5, zorder=4)
    # Text label inside or next to bar
    ax.text(start + 0.15, idx, f"{name} ({phase})",
            va="center", ha="left", color="#0B0F19", fontsize=9.5, fontweight="bold", zorder=5)

# Formatting axes
ax.set_yticks(y_positions)
ax.set_yticklabels([t[0] for t in tasks], fontsize=10, fontweight="600", color="#E2E8F0")
ax.invert_yaxis()  # Top-down order

# X-axis: Weeks 1 to 10
ax.set_xlim(0.8, 10.5)
ax.set_xticks(range(1, 11))
ax.set_xticklabels([f"Week {w}" for w in range(1, 11)], fontsize=9.5, color="#94A3B8")

# Gridlines
ax.grid(axis="x", linestyle="--", alpha=0.25, color="#64748B", zorder=1)

# Phase vertical background bands
# Month 1: Weeks 1-4
ax.axvspan(0.8, 4.5, color="#00E5FF", alpha=0.04, zorder=0)
ax.text(2.6, -0.6, "MONTH 1: INGESTION & DATA FEEDS", color="#00E5FF",
        fontsize=9, fontweight="bold", ha="center")

# Month 2: Weeks 4.5-8.5
ax.axvspan(4.5, 8.5, color="#A78BFA", alpha=0.04, zorder=0)
ax.text(6.5, -0.6, "MONTH 2: KNOWLEDGE GRAPH & EVAL", color="#A78BFA",
        fontsize=9, fontweight="bold", ha="center")

# Month 2.5: Weeks 8.5-10.5
ax.axvspan(8.5, 10.5, color="#00F5A0", alpha=0.04, zorder=0)
ax.text(9.5, -0.6, "MONTH 2.5: SOC EXPORT", color="#00F5A0",
        fontsize=9, fontweight="bold", ha="center")

# Title and headers
ax.set_title("CyberSense: 2.5-Month (10-Week) Realistic Development Roadmap",
             fontsize=13, fontweight="bold", color="#F8FAFC", pad=28)
ax.set_xlabel("Implementation Sprints (10-Week Timeline)", fontsize=10, color="#94A3B8", labelpad=10)

# Borders
for spine in ax.spines.values():
    spine.set_color("#334155")
    spine.set_linewidth(1.0)

plt.tight_layout()
out_path = Path("assets/roadmap_gantt.png")
out_path.parent.mkdir(exist_ok=True)
plt.savefig(out_path, dpi=300, facecolor=fig.get_facecolor(), bbox_inches="tight")
print(f"SUCCESS: Saved updated Gantt chart to {out_path}")
