# ============================================================
# dashboard/app.py
# PURPOSE: Plotly Dash interactive analytics dashboard
# RUN FROM: project root with: python dashboard/app.py
# VIEW AT: http://localhost:8050
# ============================================================

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
from datetime import datetime

# ── CONFIGURATION ──────────────────────────────────────────────
API_URL = os.getenv("API_URL", "http://localhost:8000")

# ── HELPER FUNCTION ────────────────────────────────────────────
def fetch(endpoint: str) -> list | dict:
    try:
        response = requests.get(f"{API_URL}{endpoint}", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching {endpoint}: {e}")
        return []

# ── COLOUR PALETTE ─────────────────────────────────────────────
COLORS = {
    "primary":    "#1D9E75",
    "secondary":  "#5DCAA5",
    "accent":     "#534AB7",
    "warning":    "#E8593C",
    "light":      "#E1F5EE",
    "background": "#f5f5f2",
    "card":       "#ffffff",
    "text":       "#1a1a1a",
    "muted":      "#888780",
}

CARD_STYLE = {
    "backgroundColor": COLORS["card"],
    "borderRadius": "12px",
    "padding": "20px",
    "marginBottom": "20px",
    "boxShadow": "0 1px 3px rgba(0,0,0,0.08)",
    "border": "1px solid #e5e5e0"
}

# ── INITIALISE DASH APP ────────────────────────────────────────
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="E-commerce BI Platform"
)

# ══════════════════════════════════════════════════════════════
# LAYOUT
# ══════════════════════════════════════════════════════════════

app.layout = html.Div(
    style={"backgroundColor": COLORS["background"], "minHeight": "100vh"},
    children=[

        # ── NAVIGATION BAR ─────────────────────────────────────
        dbc.Navbar(
            dbc.Container([
                dbc.Row([
                    dbc.Col(html.Span(
                        "E-commerce BI Platform",
                        style={"color": "white", "fontWeight": "600", "fontSize": "18px"}
                    )),
                    dbc.Col(html.Span(
                        f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                        style={"color": "rgba(255,255,255,0.7)", "fontSize": "12px"}
                    ), className="text-end"),
                ], className="w-100 align-items-center"),
            ], fluid=True),
            color=COLORS["primary"],
            dark=True,
        ),

        # ── TAB NAVIGATION ─────────────────────────────────────
        dbc.Container([
            dcc.Tabs(
                id="tabs",
                value="overview",
                style={"marginTop": "20px", "marginBottom": "20px"},
                colors={
                    "border": "#e5e5e0",
                    "primary": COLORS["primary"],
                    "background": COLORS["background"]
                },
                children=[
                    dcc.Tab(label="Overview",   value="overview"),
                    dcc.Tab(label="RFM",        value="rfm"),
                    dcc.Tab(label="Cohort",     value="cohort"),
                    dcc.Tab(label="Geography",  value="geo"),
                    dcc.Tab(label="Products",   value="products"),
                    dcc.Tab(label="Trends",     value="trends"),
                ]
            ),
            html.Div(id="tab-content")
        ], fluid=True, style={"padding": "0 24px"})
    ]
)


# ══════════════════════════════════════════════════════════════
# PAGE BUILDERS
# ══════════════════════════════════════════════════════════════

def build_overview():
    kpis    = fetch("/kpis")
    monthly = fetch("/revenue/monthly")
    df      = pd.DataFrame(monthly)

    # ── KPI CARDS ──────────────────────────────────────────────
    def kpi_card(title, value, subtitle="", color=COLORS["primary"]):
        return html.Div(style={**CARD_STYLE, "textAlign": "center",
                               "borderTop": f"3px solid {color}"}, children=[
            html.P(title, style={"color": COLORS["muted"],
                                 "fontSize": "12px", "margin": "0",
                                 "textTransform": "uppercase",
                                 "letterSpacing": "0.5px"}),
            html.H3(value, style={"color": COLORS["text"],
                                  "fontWeight": "700",
                                  "margin": "8px 0 4px",
                                  "fontSize": "24px"}),
            html.P(subtitle, style={"color": COLORS["muted"],
                                    "fontSize": "11px", "margin": "0"}),
        ])

    cards = dbc.Row([
        dbc.Col(kpi_card("Total Revenue",
                         f"R${kpis.get('total_revenue', 0):,.0f}",
                         "All delivered orders",
                         COLORS["primary"]), width=2),
        dbc.Col(kpi_card("Total Orders",
                         f"{kpis.get('total_orders', 0):,}",
                         "Delivered orders",
                         COLORS["secondary"]), width=2),
        dbc.Col(kpi_card("Unique Customers",
                         f"{kpis.get('total_customers', 0):,}",
                         "Distinct buyers",
                         COLORS["accent"]), width=2),
        dbc.Col(kpi_card("Avg Order Value",
                         f"R${kpis.get('avg_order_value', 0):,.2f}",
                         "Per order",
                         COLORS["primary"]), width=2),
        dbc.Col(kpi_card("Avg Fulfilment",
                         f"{kpis.get('avg_fulfilment_days', 0):.1f} days",
                         "Purchase to delivery",
                         COLORS["warning"]), width=2),
        dbc.Col(kpi_card("On-time Delivery",
                         f"{kpis.get('pct_on_time', 0):.1f}%",
                         "Delivered by estimate",
                         COLORS["secondary"]), width=2),
    ], className="mb-3")

    if not df.empty:
        # ── DATE RANGE FILTER ──────────────────────────────────
        # Filter out very early low-revenue months for cleaner charts
        df_clean = df[df["total_revenue"] > 50000].copy()

        # ── MONTHLY REVENUE CHART ──────────────────────────────
        fig_revenue = px.bar(
            df,
            x="year_month",
            y="total_revenue",
            title="Monthly Revenue (R$)",
            color_discrete_sequence=[COLORS["primary"]],
            labels={"year_month": "Month", "total_revenue": "Revenue (R$)"}
        )
        # Annotate Black Friday
        fig_revenue.add_annotation(
            x="2017-11", y=1153528,
            text="Black Friday",
            showarrow=True,
            arrowhead=2,
            arrowcolor=COLORS["warning"],
            font=dict(color=COLORS["warning"], size=11),
            ax=40, ay=-40
        )
        fig_revenue.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            font_color=COLORS["text"], showlegend=False,
            margin=dict(t=50, b=60, l=60, r=20),
            xaxis_tickangle=45
        )

        # ── AOV CHART — filter out near-zero months ────────────
        fig_aov = px.line(
            df_clean,
            x="year_month",
            y="avg_order_value",
            title="Average Order Value (R$)",
            color_discrete_sequence=[COLORS["accent"]],
            labels={"year_month": "Month", "avg_order_value": "AOV (R$)"},
            markers=True
        )
        fig_aov.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            font_color=COLORS["text"], showlegend=False,
            margin=dict(t=50, b=60, l=60, r=20),
            xaxis_tickangle=45,
            yaxis_range=[100, 220]
        )
    else:
        fig_revenue = go.Figure()
        fig_aov     = go.Figure()

    return html.Div([
        cards,
        dbc.Row([
            dbc.Col(html.Div(style=CARD_STYLE, children=[
                dcc.Graph(figure=fig_revenue, config={"displayModeBar": False})
            ]), width=8),
            dbc.Col(html.Div(style=CARD_STYLE, children=[
                dcc.Graph(figure=fig_aov, config={"displayModeBar": False})
            ]), width=4),
        ])
    ])


def build_rfm():
    segments = fetch("/rfm/segments")
    dist     = fetch("/rfm/distribution")

    df_seg  = pd.DataFrame(segments)
    df_dist = pd.DataFrame(dist)

    if not df_seg.empty:
        df_seg = df_seg.sort_values("customer_count", ascending=True)

        # Colour mapping per segment
        color_map = {
            "Champions":           COLORS["primary"],
            "Loyal Customers":     COLORS["secondary"],
            "Potential Loyalists": COLORS["secondary"],
            "At Risk":             COLORS["warning"],
            "Cannot Lose Them":    COLORS["warning"],
            "Lost":                COLORS["warning"],
            "Hibernating":         "#B4B2A9",
            "Promising":           "#B4B2A9",
            "New Customers":       COLORS["accent"],
            "Needs Attention":     "#F5A623",
            "Others":              "#CCCCCC",
        }
        df_seg["color"] = df_seg["customer_segment"].map(color_map).fillna("#B4B2A9")

        # Customers chart — fixed margins so labels are not cut off
        fig_customers = go.Figure(go.Bar(
            x=df_seg["customer_count"],
            y=df_seg["customer_segment"],
            orientation="h",
            marker_color=df_seg["color"],
            text=df_seg["customer_count"].apply(lambda x: f"{x:,}"),
            textposition="outside",
            cliponaxis=False
        ))
        fig_customers.update_layout(
            title="Customers per Segment",
            plot_bgcolor="white", paper_bgcolor="white",
            font_color=COLORS["text"], showlegend=False,
            margin=dict(t=50, b=40, l=160, r=100),
            height=420,
            xaxis=dict(range=[0, df_seg["customer_count"].max() * 1.25])
        )

        # Revenue chart — fixed margins
        df_seg2 = df_seg.sort_values("total_revenue", ascending=True)
        df_seg2["color2"] = df_seg2["customer_segment"].map(color_map).fillna("#B4B2A9")

        fig_revenue = go.Figure(go.Bar(
            x=df_seg2["total_revenue"],
            y=df_seg2["customer_segment"],
            orientation="h",
            marker_color=df_seg2["color2"],
            text=df_seg2["total_revenue"].apply(lambda x: f"R${x:,.0f}"),
            textposition="outside",
            cliponaxis=False
        ))
        fig_revenue.update_layout(
            title="Revenue per Segment (R$)",
            plot_bgcolor="white", paper_bgcolor="white",
            font_color=COLORS["text"], showlegend=False,
            margin=dict(t=50, b=40, l=160, r=140),
            height=420,
            xaxis=dict(range=[0, df_seg2["total_revenue"].max() * 1.35])
        )
    else:
        fig_customers = go.Figure()
        fig_revenue   = go.Figure()

    if not df_dist.empty:
        fig_dist = px.bar(
            df_dist,
            x="rfm_score",
            y="customer_count",
            title="RFM Score Distribution (3=worst, 15=best)",
            color_discrete_sequence=[COLORS["accent"]],
            labels={"rfm_score": "RFM Score",
                    "customer_count": "Number of Customers"},
            text="customer_count"
        )
        fig_dist.update_traces(texttemplate="%{text:,}", textposition="outside")
        fig_dist.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            font_color=COLORS["text"], showlegend=False,
            margin=dict(t=50, b=40, l=60, r=20),
            yaxis=dict(range=[0, df_dist["customer_count"].max() * 1.15])
        )
    else:
        fig_dist = go.Figure()

    # Insight card
    insight = html.Div(
        style={**CARD_STYLE, "backgroundColor": COLORS["light"],
               "borderLeft": f"4px solid {COLORS['primary']}"},
        children=[
            html.H6("Key Insight", style={"color": COLORS["primary"],
                                          "fontWeight": "600"}),
            html.P(
                "Champions represent 10.2% of customers but generate 23.4% of revenue. "
                "Average Champion spend (R$377) is 2.4x the platform average (R$160). "
                "The At Risk segment represents customers with high historical value "
                "who have gone quiet — priority targets for win-back campaigns.",
                style={"color": COLORS["text"], "margin": "0", "fontSize": "14px"}
            )
        ]
    )

    return html.Div([
        dbc.Row([
            dbc.Col(html.Div(style=CARD_STYLE, children=[
                dcc.Graph(figure=fig_customers, config={"displayModeBar": False})
            ]), width=6),
            dbc.Col(html.Div(style=CARD_STYLE, children=[
                dcc.Graph(figure=fig_revenue, config={"displayModeBar": False})
            ]), width=6),
        ]),
        dbc.Row([
            dbc.Col(html.Div(style=CARD_STYLE, children=[
                dcc.Graph(figure=fig_dist, config={"displayModeBar": False})
            ]), width=8),
            dbc.Col(insight, width=4),
        ])
    ])


def build_cohort():
    cohort = fetch("/cohort")
    df = pd.DataFrame(cohort)

    if not df.empty:
        matrix = df.pivot_table(
            index="cohort_label",
            columns="months_since_first_purchase",
            values="retention_rate"
        )

        fig = go.Figure(go.Heatmap(
            z=matrix.values,
            x=[f"Month {int(c)}" for c in matrix.columns],
            y=matrix.index.tolist(),
            colorscale=[[0, "#f5f5f2"], [1, COLORS["primary"]]],
            text=[[f"{v:.1f}%" if not pd.isna(v) else ""
                   for v in row] for row in matrix.values],
            texttemplate="%{text}",
            textfont={"size": 9},
            showscale=True,
            zmin=0, zmax=100,
        ))
        fig.update_layout(
            title="Monthly Cohort Retention Heatmap (% of cohort still purchasing)",
            plot_bgcolor="white", paper_bgcolor="white",
            font_color=COLORS["text"],
            height=620,
            margin=dict(t=60, b=80, l=90, r=40),
            xaxis_title="Months Since First Purchase",
            yaxis_title="Cohort (First Purchase Month)"
        )
    else:
        fig = go.Figure()

    insight = html.Div(
        style={**CARD_STYLE, "backgroundColor": COLORS["light"],
               "borderLeft": f"4px solid {COLORS['primary']}"},
        children=[
            html.H6("Key Insight — Single Purchase Marketplace",
                    style={"color": COLORS["primary"], "fontWeight": "600"}),
            html.P(
                "Near-zero retention after Month 0 (under 1% average) confirms Olist "
                "is entirely acquisition-driven. Almost no customer returns after their "
                "first purchase. Every revenue target requires finding new customers. "
                "Marketing investment should focus exclusively on acquisition channels "
                "rather than retention or CRM tools.",
                style={"color": COLORS["text"], "margin": "0", "fontSize": "14px"}
            )
        ]
    )

    return html.Div([
        html.Div(style=CARD_STYLE, children=[
            dcc.Graph(figure=fig, config={"displayModeBar": False})
        ]),
        insight
    ])


def build_geo():
    geo = fetch("/geo")
    df  = pd.DataFrame(geo)

    if not df.empty:

        # ── TREEMAP — better than map for state comparison ─────
        fig_treemap = px.treemap(
            df,
            path=["customer_state"],
            values="total_revenue",
            color="total_revenue",
            color_continuous_scale=[[0, COLORS["light"]], [1, COLORS["primary"]]],
            title="Revenue by Brazilian State (size = revenue)",
            hover_data={"total_orders": True, "avg_order_value": True}
        )
        fig_treemap.update_traces(
            textinfo="label+value",
            texttemplate="<b>%{label}</b><br>R$%{value:,.0f}",
        )
        fig_treemap.update_layout(
            paper_bgcolor="white",
            font_color=COLORS["text"],
            height=460,
            margin=dict(t=50, b=20, l=10, r=10),
            coloraxis_showscale=False
        )

        # ── TOP 10 STATES BAR CHART ────────────────────────────
        fig_bar = px.bar(
            df.head(10),
            x="customer_state",
            y="total_revenue",
            title="Top 10 States by Revenue",
            color="avg_fulfilment_days",
            color_continuous_scale=[[0, COLORS["secondary"]], [1, COLORS["warning"]]],
            labels={"customer_state": "State",
                    "total_revenue": "Total Revenue (R$)",
                    "avg_fulfilment_days": "Avg Delivery Days"},
            text="total_revenue"
        )
        fig_bar.update_traces(
            texttemplate="R$%{text:,.0f}",
            textposition="outside"
        )
        fig_bar.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            font_color=COLORS["text"],
            margin=dict(t=50, b=50, l=60, r=20),
            yaxis=dict(range=[0, df["total_revenue"].max() * 1.15]),
            coloraxis_colorbar_title="Delivery Days"
        )

        # ── FULFILMENT BY STATE ────────────────────────────────
        fig_delivery = px.bar(
            df.sort_values("avg_fulfilment_days", ascending=False).head(10),
            x="customer_state",
            y="avg_fulfilment_days",
            title="Top 10 States — Avg Delivery Days (higher = slower)",
            color="avg_fulfilment_days",
            color_continuous_scale=[[0, COLORS["secondary"]], [1, COLORS["warning"]]],
            labels={"customer_state": "State",
                    "avg_fulfilment_days": "Avg Delivery Days"}
        )
        fig_delivery.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            font_color=COLORS["text"],
            margin=dict(t=50, b=50, l=60, r=20),
            showlegend=False,
            coloraxis_showscale=False
        )

    else:
        fig_treemap  = go.Figure()
        fig_bar      = go.Figure()
        fig_delivery = go.Figure()

    return html.Div([
        dbc.Row([
            dbc.Col(html.Div(style=CARD_STYLE, children=[
                dcc.Graph(figure=fig_treemap, config={"displayModeBar": False})
            ]), width=6),
            dbc.Col(html.Div(style=CARD_STYLE, children=[
                dcc.Graph(figure=fig_bar, config={"displayModeBar": False})
            ]), width=6),
        ]),
        dbc.Row([
            dbc.Col(html.Div(style=CARD_STYLE, children=[
                dcc.Graph(figure=fig_delivery, config={"displayModeBar": False})
            ]), width=12),
        ])
    ])


def build_products():
    products = fetch("/products")
    payments = fetch("/payments")

    df    = pd.DataFrame(products)
    df_p  = pd.DataFrame(payments)

    if not df.empty:
        fig_revenue = px.bar(
            df.head(15).sort_values("total_revenue"),
            x="total_revenue",
            y="category_name",
            orientation="h",
            title="Top 15 Categories by Revenue",
            color_discrete_sequence=[COLORS["primary"]],
            labels={"total_revenue": "Revenue (R$)", "category_name": "Category"},
            text="total_revenue"
        )
        fig_revenue.update_traces(
            texttemplate="R$%{text:,.0f}",
            textposition="outside",
            cliponaxis=False
        )
        fig_revenue.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            font_color=COLORS["text"], showlegend=False,
            height=520,
            margin=dict(t=50, b=40, l=200, r=120),
            xaxis=dict(range=[0, df["total_revenue"].max() * 1.2])
        )

        fig_reviews = px.scatter(
            df,
            x="total_revenue",
            y="avg_review_score",
            size="total_orders",
            hover_name="category_name",
            title="Revenue vs Review Score (bubble size = order volume)",
            color="avg_review_score",
            color_continuous_scale=[[0, COLORS["warning"]], [1, COLORS["primary"]]],
            labels={"total_revenue": "Total Revenue (R$)",
                    "avg_review_score": "Avg Review Score (1-5)",
                    "total_orders": "Total Orders"}
        )
        fig_reviews.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            font_color=COLORS["text"], showlegend=False,
            margin=dict(t=50, b=50, l=60, r=20),
            coloraxis_showscale=False,
            yaxis=dict(range=[2.5, 5.2])
        )
    else:
        fig_revenue = go.Figure()
        fig_reviews = go.Figure()

    if not df_p.empty:
        fig_payment = px.pie(
            df_p,
            values="order_count",
            names="payment_type",
            title="Orders by Payment Method",
            color_discrete_sequence=[COLORS["primary"], COLORS["secondary"],
                                     COLORS["accent"], "#F5A623"],
            hole=0.4
        )
        fig_payment.update_traces(
            textposition="outside",
            texttemplate="<b>%{label}</b><br>%{percent}"
        )
        fig_payment.update_layout(
            paper_bgcolor="white",
            font_color=COLORS["text"],
            margin=dict(t=50, b=20, l=20, r=20),
            showlegend=False
        )
    else:
        fig_payment = go.Figure()

    return html.Div([
        dbc.Row([
            dbc.Col(html.Div(style=CARD_STYLE, children=[
                dcc.Graph(figure=fig_revenue, config={"displayModeBar": False})
            ]), width=7),
            dbc.Col([
                html.Div(style=CARD_STYLE, children=[
                    dcc.Graph(figure=fig_payment, config={"displayModeBar": False})
                ]),
            ], width=5),
        ]),
        dbc.Row([
            dbc.Col(html.Div(style=CARD_STYLE, children=[
                dcc.Graph(figure=fig_reviews, config={"displayModeBar": False})
            ]), width=12),
        ])
    ])


def build_trends():
    """
    Revenue trends page replacing the straight-line forecast.
    Shows moving average, month-over-month growth, and
    year-over-year comparison — all far more insightful.
    """
    monthly = fetch("/revenue/monthly")
    df = pd.DataFrame(monthly)

    if df.empty:
        return html.Div("No data available")

    # Filter out very early low-revenue months
    df = df[df["total_revenue"] > 50000].copy()
    df["ds"] = pd.to_datetime(df["year_month"] + "-01")

    # ── 3-MONTH MOVING AVERAGE ─────────────────────────────────
    df["moving_avg_3m"] = df["total_revenue"].rolling(window=3).mean()

    fig_ma = go.Figure()

    # Actual revenue bars
    fig_ma.add_trace(go.Bar(
        x=df["year_month"],
        y=df["total_revenue"],
        name="Monthly Revenue",
        marker_color=COLORS["secondary"],
        opacity=0.7
    ))

    # 3-month moving average line
    fig_ma.add_trace(go.Scatter(
        x=df["year_month"],
        y=df["moving_avg_3m"],
        name="3-Month Moving Average",
        line=dict(color=COLORS["primary"], width=3),
        mode="lines"
    ))

    # Black Friday annotation
    fig_ma.add_annotation(
        x="2017-11", y=1153528,
        text="⭐ Black Friday",
        showarrow=True, arrowhead=2,
        arrowcolor=COLORS["warning"],
        font=dict(color=COLORS["warning"], size=11),
        ax=50, ay=-50
    )

    fig_ma.update_layout(
        title="Monthly Revenue with 3-Month Moving Average",
        plot_bgcolor="white", paper_bgcolor="white",
        font_color=COLORS["text"],
        margin=dict(t=60, b=60, l=60, r=20),
        xaxis_tickangle=45,
        legend=dict(orientation="h", yanchor="bottom",
                    y=1.02, xanchor="right", x=1),
        yaxis_title="Revenue (R$)",
        xaxis_title="Month"
    )

    # ── MONTH OVER MONTH GROWTH RATE ──────────────────────────
    df["mom_growth"] = df["total_revenue"].pct_change() * 100

    colors_growth = [
        COLORS["primary"] if x >= 0 else COLORS["warning"]
        for x in df["mom_growth"].fillna(0)
    ]

    fig_growth = go.Figure(go.Bar(
        x=df["year_month"],
        y=df["mom_growth"],
        marker_color=colors_growth,
        text=df["mom_growth"].apply(
            lambda x: f"{x:+.1f}%" if not pd.isna(x) else ""
        ),
        textposition="outside",
        cliponaxis=False,
        name="MoM Growth"
    ))
    fig_growth.add_hline(y=0, line_dash="dash",
                         line_color=COLORS["muted"], opacity=0.5)
    fig_growth.update_layout(
        title="Month-over-Month Revenue Growth Rate (%)",
        plot_bgcolor="white", paper_bgcolor="white",
        font_color=COLORS["text"],
        margin=dict(t=60, b=60, l=60, r=20),
        xaxis_tickangle=45,
        showlegend=False,
        yaxis_title="Growth (%)",
        xaxis_title="Month"
    )

    # ── YEAR OVER YEAR COMPARISON 2017 vs 2018 ────────────────
    df["year"]  = df["ds"].dt.year
    df["month"] = df["ds"].dt.month

    df_2017 = df[df["year"] == 2017][["month", "total_revenue"]].rename(
        columns={"total_revenue": "revenue_2017"}
    )
    df_2018 = df[df["year"] == 2018][["month", "total_revenue"]].rename(
        columns={"total_revenue": "revenue_2018"}
    )
    df_yoy = df_2017.merge(df_2018, on="month", how="inner")

    month_names = {1:"Jan", 2:"Feb", 3:"Mar", 4:"Apr", 5:"May",
                   6:"Jun", 7:"Jul", 8:"Aug", 9:"Sep", 10:"Oct",
                   11:"Nov", 12:"Dec"}
    df_yoy["month_name"] = df_yoy["month"].map(month_names)

    fig_yoy = go.Figure()
    fig_yoy.add_trace(go.Bar(
        x=df_yoy["month_name"],
        y=df_yoy["revenue_2017"],
        name="2017",
        marker_color=COLORS["secondary"],
        opacity=0.8
    ))
    fig_yoy.add_trace(go.Bar(
        x=df_yoy["month_name"],
        y=df_yoy["revenue_2018"],
        name="2018",
        marker_color=COLORS["primary"]
    ))
    fig_yoy.update_layout(
        title="Year-over-Year Revenue Comparison (2017 vs 2018)",
        plot_bgcolor="white", paper_bgcolor="white",
        font_color=COLORS["text"],
        barmode="group",
        margin=dict(t=60, b=50, l=60, r=20),
        legend=dict(orientation="h", yanchor="bottom",
                    y=1.02, xanchor="right", x=1),
        yaxis_title="Revenue (R$)",
        xaxis_title="Month"
    )

    insight = html.Div(
        style={**CARD_STYLE, "backgroundColor": COLORS["light"],
               "borderLeft": f"4px solid {COLORS['primary']}"},
        children=[
            html.H6("Key Insights", style={"color": COLORS["primary"],
                                           "fontWeight": "600"}),
            html.Ul([
                html.Li("Revenue grew from R$127k (Jan 2017) to R$1.13M (Nov 2017) "
                        "in 10 months — 791% growth in the first year",
                        style={"fontSize": "13px", "marginBottom": "6px"}),
                html.Li("November 2017 Black Friday spike: +53.6% month-over-month "
                        "— the single biggest growth event in the dataset",
                        style={"fontSize": "13px", "marginBottom": "6px"}),
                html.Li("Platform stabilised at R$1M/month through 2018 — "
                        "transitioning from hypergrowth to steady state",
                        style={"fontSize": "13px", "marginBottom": "6px"}),
                html.Li("2018 revenue consistently above 2017 for all comparable months "
                        "— confirming sustained year-over-year growth",
                        style={"fontSize": "13px"}),
            ], style={"margin": "0", "paddingLeft": "16px",
                      "color": COLORS["text"]})
        ]
    )

    return html.Div([
        dbc.Row([
            dbc.Col(html.Div(style=CARD_STYLE, children=[
                dcc.Graph(figure=fig_ma, config={"displayModeBar": False})
            ]), width=12),
        ]),
        dbc.Row([
            dbc.Col(html.Div(style=CARD_STYLE, children=[
                dcc.Graph(figure=fig_growth, config={"displayModeBar": False})
            ]), width=6),
            dbc.Col(html.Div(style=CARD_STYLE, children=[
                dcc.Graph(figure=fig_yoy, config={"displayModeBar": False})
            ]), width=6),
        ]),
        insight
    ])


# ══════════════════════════════════════════════════════════════
# CALLBACK
# ══════════════════════════════════════════════════════════════

@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "value")
)
def render_tab(tab):
    if tab == "overview": return build_overview()
    if tab == "rfm":      return build_rfm()
    if tab == "cohort":   return build_cohort()
    if tab == "geo":      return build_geo()
    if tab == "products": return build_products()
    if tab == "trends":   return build_trends()
    return html.Div("Page not found")


# ══════════════════════════════════════════════════════════════
# RUN
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.run(debug=True, port=8050)