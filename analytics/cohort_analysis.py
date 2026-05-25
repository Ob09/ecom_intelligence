# ============================================================
# analytics/cohort_analysis.py
# PURPOSE: Analyse monthly cohort retention from mart_cohort
# OUTPUT:  Retention heatmap and summary saved to reports/
# RUN FROM: project root (e_com_analyser)
# ============================================================

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from analytics.db import get_engine

os.makedirs("reports", exist_ok=True)

print("="*60)
print("  COHORT RETENTION ANALYSIS")
print("="*60)

# ── LOAD DATA ──────────────────────────────────────────────────
print("\nLoading mart_cohort from Supabase...")
engine = get_engine()

df = pd.read_sql(
    "SELECT * FROM public_marts.mart_cohort ORDER BY cohort_month, months_since_first_purchase",
    engine
)

print(f"Loaded {len(df):,} cohort-month rows")
print(f"Cohorts span: {df['cohort_label'].min()} to {df['cohort_label'].max()}")

# ── BUILD RETENTION MATRIX ─────────────────────────────────────
# Pivot the data into a matrix format:
# Rows = cohort months, Columns = months since first purchase
# Values = retention rate percentage
print("\nBuilding retention matrix...")

retention_matrix = df.pivot_table(
    index="cohort_label",
    columns="months_since_first_purchase",
    values="retention_rate"
)

# Rename columns to be more readable
retention_matrix.columns = [f"Month {int(c)}" for c in retention_matrix.columns]

print("\n--- RETENTION MATRIX (%) ---")
print(retention_matrix.round(1).to_string())

# ── KEY INSIGHTS ───────────────────────────────────────────────
print("\n--- KEY INSIGHTS ---")

# Average Month 1 retention across all cohorts
# Month 1 = what % of customers came back the very next month
month1_col = "Month 1"
if month1_col in retention_matrix.columns:
    avg_month1 = retention_matrix[month1_col].mean()
    print(f"\nAverage Month 1 retention: {avg_month1:.1f}%")
    print(f"  This means on average {avg_month1:.1f}% of customers")
    print(f"  return the month after their first purchase")

# Average Month 3 retention
month3_col = "Month 3"
if month3_col in retention_matrix.columns:
    avg_month3 = retention_matrix[month3_col].mean()
    print(f"\nAverage Month 3 retention: {avg_month3:.1f}%")

# Best performing cohort at Month 1
if month1_col in retention_matrix.columns:
    best_cohort = retention_matrix[month1_col].idxmax()
    best_rate = retention_matrix[month1_col].max()
    print(f"\nBest Month 1 retention: {best_cohort} at {best_rate:.1f}%")

    worst_cohort = retention_matrix[month1_col].idxmin()
    worst_rate = retention_matrix[month1_col].min()
    print(f"Worst Month 1 retention: {worst_cohort} at {worst_rate:.1f}%")

# Cohort sizes
cohort_sizes = df[df["months_since_first_purchase"] == 0][
    ["cohort_label", "cohort_size"]
].set_index("cohort_label")

largest_cohort = cohort_sizes["cohort_size"].idxmax()
largest_size = cohort_sizes["cohort_size"].max()
print(f"\nLargest cohort: {largest_cohort} with {largest_size:,} customers")

# ── CHART: RETENTION HEATMAP ───────────────────────────────────
print("\nGenerating retention heatmap...")

fig, ax = plt.subplots(figsize=(14, 8))

# Create a colour map — dark green = high retention, light = low
cmap = mcolors.LinearSegmentedColormap.from_list(
    "retention", ["#f5f5f2", "#1D9E75"]
)

# Plot the heatmap
im = ax.imshow(
    retention_matrix.values,
    cmap=cmap,
    aspect="auto",
    vmin=0,
    vmax=100
)

# Add text labels inside each cell showing the retention rate
for i in range(len(retention_matrix.index)):
    for j in range(len(retention_matrix.columns)):
        val = retention_matrix.values[i, j]
        if not np.isnan(val):
            # Use dark text on light cells, light text on dark cells
            text_color = "white" if val > 50 else "#1a1a1a"
            ax.text(
                j, i, f"{val:.0f}%",
                ha="center", va="center",
                fontsize=8, color=text_color, fontweight="500"
            )

# Labels
ax.set_xticks(range(len(retention_matrix.columns)))
ax.set_xticklabels(retention_matrix.columns, rotation=45, ha="right")
ax.set_yticks(range(len(retention_matrix.index)))
ax.set_yticklabels(retention_matrix.index)
ax.set_title("Monthly Cohort Retention Heatmap\n(% of cohort still purchasing)", 
             fontsize=14, fontweight="bold", pad=15)
ax.set_xlabel("Months Since First Purchase")
ax.set_ylabel("Cohort (First Purchase Month)")

plt.colorbar(im, ax=ax, label="Retention Rate (%)")
plt.tight_layout()

chart_path = "reports/cohort_retention_heatmap.png"
plt.savefig(chart_path, dpi=150, bbox_inches="tight")
print(f"Chart saved to {chart_path}")

# ── CHART 2: AVERAGE RETENTION CURVE ──────────────────────────
fig2, ax2 = plt.subplots(figsize=(10, 5))

avg_retention = retention_matrix.mean()
months = range(len(avg_retention))

ax2.plot(
    months,
    avg_retention.values,
    color="#1D9E75",
    linewidth=2.5,
    marker="o",
    markersize=6
)
ax2.fill_between(months, avg_retention.values, alpha=0.15, color="#1D9E75")
ax2.set_title("Average Retention Curve Across All Cohorts",
              fontsize=13, fontweight="bold")
ax2.set_xlabel("Months Since First Purchase")
ax2.set_ylabel("Average Retention Rate (%)")
ax2.set_xticks(months)
ax2.set_xticklabels([f"M{i}" for i in months])
ax2.grid(axis="y", alpha=0.3)
ax2.yaxis.set_major_formatter(
    plt.FuncFormatter(lambda x, _: f"{x:.0f}%")
)

plt.tight_layout()
chart_path2 = "reports/cohort_retention_curve.png"
plt.savefig(chart_path2, dpi=150, bbox_inches="tight")
print(f"Chart saved to {chart_path2}")

# ── SAVE MATRIX TO CSV ─────────────────────────────────────────
csv_path = "reports/cohort_retention_matrix.csv"
retention_matrix.round(1).to_csv(csv_path)
print(f"Matrix saved to {csv_path}")

print("\n" + "="*60)
print("  COHORT ANALYSIS COMPLETE")
print("="*60 + "\n")