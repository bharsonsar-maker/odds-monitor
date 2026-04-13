"""
============================================================
  ODDS MONITOR DASHBOARD  —  dashboard.py
  Streamlit web app — deploy free on streamlit.io
  Shows charts, accuracy, P&L simulation, history
============================================================
  Run locally:  streamlit run dashboard.py
  Deploy:       push to GitHub → connect on streamlit.io
============================================================
"""

import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client
from datetime import datetime, timedelta

# ── page config ────────────────────────────────────────────
st.set_page_config(
    page_title="Odds Monitor",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── custom CSS ─────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap');
  html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
  h1, h2, h3 { font-family: 'DM Mono', monospace !important; letter-spacing: -0.02em; }
  .metric-card {
    background: #0e1117; border: 1px solid #1e2530;
    border-radius: 12px; padding: 20px 24px; margin-bottom: 12px;
  }
  .metric-label { font-size: 11px; color: #4a5568; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px; }
  .metric-value { font-family: 'DM Mono', monospace; font-size: 28px; font-weight: 500; color: #e2e8f0; }
  .metric-sub   { font-size: 12px; color: #4a5568; margin-top: 4px; }
  .opp-card {
    background: #0a1f16; border: 1px solid #1D9E75;
    border-radius: 10px; padding: 16px 20px; margin-bottom: 10px;
  }
  .stDataFrame { border-radius: 10px; overflow: hidden; }
  div[data-testid="stMetric"] { background: #0e1117; border-radius: 10px; padding: 16px; border: 1px solid #1e2530; }
</style>
""", unsafe_allow_html=True)

# ── supabase connection ────────────────────────────────────
@st.cache_resource
def get_db():
    url = os.getenv("SUPABASE_URL", st.secrets.get("SUPABASE_URL", ""))
    key = os.getenv("SUPABASE_KEY", st.secrets.get("SUPABASE_KEY", ""))
    return create_client(url, key)

@st.cache_data(ttl=300)   # cache for 5 minutes
def load_opportunities():
    try:
        db   = get_db()
        rows = db.table("opportunities").select("*").order("spotted_at", desc=True).limit(500).execute()
        df   = pd.DataFrame(rows.data)
        if df.empty:
            return df
        df["spotted_at"]    = pd.to_datetime(df["spotted_at"])
        df["commence_time"] = pd.to_datetime(df["commence_time"])
        df["date"]          = df["spotted_at"].dt.date
        df["won"]           = df["result"].isin(["home_win", "away_win"])
        df["lost"]          = df["result"] == "draw"
        df["pending"]       = df["result"].isna()
        return df
    except Exception as e:
        st.error(f"DB connection failed: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_scans():
    try:
        db   = get_db()
        since = (datetime.utcnow() - timedelta(days=30)).isoformat()
        rows  = db.table("scans").select("scanned_at,league,is_opportunity").gte("scanned_at", since).execute()
        df    = pd.DataFrame(rows.data)
        if df.empty:
            return df
        df["scanned_at"] = pd.to_datetime(df["scanned_at"])
        df["date"]       = df["scanned_at"].dt.date
        return df
    except Exception:
        return pd.DataFrame()

# ── generate demo data if DB is empty ─────────────────────
def demo_opportunities():
    import numpy as np
    np.random.seed(42)
    n   = 60
    now = datetime.utcnow()
    results = np.random.choice(["home_win","away_win","draw",None], n, p=[0.42,0.38,0.12,0.08])
    data = []
    for i in range(n):
        ho = round(2.05 + np.random.exponential(0.4), 2)
        ao = round(2.05 + np.random.exponential(0.35), 2)
        res = results[i]
        ap  = None
        if res == "home_win":   ap = round(5000 * ho - 10000)
        elif res == "away_win": ap = round(5000 * ao - 10000)
        elif res == "draw":     ap = -10000
        data.append({
            "match_id":      f"match_{i}",
            "home_team":     np.random.choice(["Bayern","Real Madrid","Man City","Barcelona","PSG","Arsenal","Juventus","Inter"]),
            "away_team":     np.random.choice(["Dortmund","Atletico","Liverpool","Napoli","Porto","Ajax","Lazio","Milan"]),
            "league":        np.random.choice(["Champions League","Premier League","La Liga","Serie A","Bundesliga"]),
            "home_odds":     ho,
            "away_odds":     ao,
            "draw_odds":     round(3.0 + np.random.normal(0, 0.3), 2),
            "profit_if_home_wins": round(5000 * ho - 10000),
            "profit_if_away_wins": round(5000 * ao - 10000),
            "loss_if_draw":  -10000,
            "spotted_at":    now - timedelta(days=int(np.random.uniform(0, 30)), hours=int(np.random.uniform(0,24))),
            "result":        res,
            "actual_profit": ap,
            "date":          (now - timedelta(days=int(np.random.uniform(0,30)))).date(),
            "won":           res in ["home_win","away_win"],
            "lost":          res == "draw",
            "pending":       res is None,
        })
    return pd.DataFrame(data)

# ══════════════════════════════════════════════════════════
#   MAIN APP
# ══════════════════════════════════════════════════════════

st.markdown("## 📊 odds monitor dashboard")
st.markdown("*real-time tracking of both-teams-above-2x opportunities*")
st.divider()

# load data
df = load_opportunities()
using_demo = df.empty
if using_demo:
    st.info("No database connected — showing demo data. Connect Supabase to see real data.")
    df = demo_opportunities()

scans_df = load_scans()

# ── sidebar filters ────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filters")
    days_back = st.slider("Days to show", 7, 90, 30)
    leagues   = ["All"] + sorted(df["league"].unique().tolist())
    sel_league = st.selectbox("League", leagues)
    show_pending = st.checkbox("Include pending (no result yet)", True)

cutoff = datetime.utcnow() - timedelta(days=days_back)
fdf = df[df["spotted_at"] >= cutoff]
if sel_league != "All":
    fdf = fdf[fdf["league"] == sel_league]
if not show_pending:
    fdf = fdf[~fdf["pending"]]

resolved = fdf[~fdf["pending"]]

# ── top metrics ────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)

total_opps  = len(fdf)
wins        = int(fdf["won"].sum())
draws       = int(fdf["lost"].sum())
pending     = int(fdf["pending"].sum())
win_rate    = (wins / (wins + draws) * 100) if (wins + draws) > 0 else 0
total_pl    = resolved["actual_profit"].sum() if not resolved.empty else 0

c1.metric("Opportunities spotted", total_opps)
c2.metric("Won (no draw)", wins, f"{win_rate:.0f}% win rate")
c3.metric("Lost to draw", draws)
c4.metric("Pending results", pending)
c5.metric("Simulated P&L", f"${total_pl:,.0f}", delta_color="normal" if total_pl >= 0 else "inverse")

st.divider()

# ── row 1: opportunity timeline + league breakdown ─────────
col_a, col_b = st.columns([2, 1])

with col_a:
    st.markdown("#### opportunities per day")
    daily = fdf.groupby("date").size().reset_index(name="count")
    fig   = px.bar(daily, x="date", y="count",
                   color_discrete_sequence=["#1D9E75"])
    fig.update_layout(
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font_color="#a0aec0", margin=dict(l=0,r=0,t=10,b=0),
        xaxis=dict(showgrid=False, color="#4a5568"),
        yaxis=dict(showgrid=True, gridcolor="#1e2530", color="#4a5568"),
        height=220,
    )
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.markdown("#### by league")
    by_league = fdf.groupby("league").size().reset_index(name="count").sort_values("count", ascending=True)
    fig2 = px.bar(by_league, x="count", y="league", orientation="h",
                  color_discrete_sequence=["#5DCAA5"])
    fig2.update_layout(
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font_color="#a0aec0", margin=dict(l=0,r=0,t=10,b=0),
        xaxis=dict(showgrid=False, color="#4a5568"),
        yaxis=dict(showgrid=False, color="#4a5568", title=""),
        height=220,
    )
    st.plotly_chart(fig2, use_container_width=True)

# ── row 2: simulated P&L curve + odds distribution ─────────
col_c, col_d = st.columns([2, 1])

with col_c:
    st.markdown("#### simulated cumulative P&L (if you bet every opportunity)")
    if not resolved.empty:
        r2 = resolved.sort_values("spotted_at").copy()
        r2["cumulative_pl"] = r2["actual_profit"].cumsum()
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=r2["spotted_at"], y=r2["cumulative_pl"],
            fill="tozeroy",
            fillcolor="rgba(29,158,117,0.15)",
            line=dict(color="#1D9E75", width=2),
            name="Cumulative P&L"
        ))
        fig3.add_hline(y=0, line_dash="dot", line_color="#4a5568")
        fig3.update_layout(
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
            font_color="#a0aec0", margin=dict(l=0,r=0,t=10,b=0),
            xaxis=dict(showgrid=False, color="#4a5568"),
            yaxis=dict(showgrid=True, gridcolor="#1e2530", color="#4a5568", tickprefix="$"),
            showlegend=False, height=240,
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No resolved matches yet to plot P&L.")

with col_d:
    st.markdown("#### result breakdown")
    if not resolved.empty:
        labels = ["Home/Away win", "Draw (loss)"]
        values = [wins, draws]
        fig4 = go.Figure(go.Pie(
            labels=labels, values=values, hole=0.6,
            marker_colors=["#1D9E75", "#E24B4A"],
            textinfo="percent+label",
            textfont_size=12,
        ))
        fig4.update_layout(
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
            font_color="#a0aec0", margin=dict(l=0,r=0,t=10,b=20),
            showlegend=False, height=240,
        )
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("No resolved matches yet.")

# ── row 3: odds scatter ─────────────────────────────────────
st.markdown("#### odds landscape — each dot is one opportunity")
fig5 = px.scatter(
    fdf, x="home_odds", y="away_odds",
    color="result",
    color_discrete_map={
        "home_win": "#1D9E75",
        "away_win": "#5DCAA5",
        "draw":     "#E24B4A",
        None:       "#4a5568",
    },
    hover_data=["home_team", "away_team", "league", "spotted_at"],
    labels={"home_odds": "Home team odds (x)", "away_odds": "Away team odds (x)"},
)
fig5.add_vline(x=2.0, line_dash="dot", line_color="#4a5568", annotation_text="2x threshold")
fig5.add_hline(y=2.0, line_dash="dot", line_color="#4a5568")
fig5.update_layout(
    plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
    font_color="#a0aec0", margin=dict(l=0,r=0,t=10,b=0),
    xaxis=dict(showgrid=True, gridcolor="#1e2530", color="#4a5568"),
    yaxis=dict(showgrid=True, gridcolor="#1e2530", color="#4a5568"),
    height=300,
)
st.plotly_chart(fig5, use_container_width=True)

# ── row 4: full history table ───────────────────────────────
st.markdown("#### full opportunity log")
display_cols = ["spotted_at","home_team","away_team","league",
                "home_odds","away_odds","draw_odds",
                "profit_if_home_wins","profit_if_away_wins","result","actual_profit"]
show_df = fdf[[c for c in display_cols if c in fdf.columns]].copy()
show_df["spotted_at"] = show_df["spotted_at"].dt.strftime("%Y-%m-%d %H:%M")

def color_result(val):
    if val in ["home_win","away_win"]: return "color: #1D9E75"
    if val == "draw":                  return "color: #E24B4A"
    return "color: #4a5568"

st.dataframe(
    show_df.style.applymap(color_result, subset=["result"]),
    use_container_width=True,
    height=350,
)

# ── footer ─────────────────────────────────────────────────
st.divider()
st.markdown(
    "<p style='text-align:center;color:#4a5568;font-size:12px'>"
    "Odds Monitor · Data refreshes every 5 min · "
    f"{'Demo mode' if using_demo else 'Live data'}"
    "</p>",
    unsafe_allow_html=True
)
