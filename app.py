from pathlib import Path
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from data_loader import load_data
from analytics import normalize_prices, calculate_spreads, run_backtest, calculate_metrics

st.set_page_config(
    page_title="GoldLens | SPYX",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Design system ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');
:root {
  --bg: #0b1020;
  --panel: #111a2e;
  --panel2: #151f35;
  --line: #26334d;
  --text: #edf2fb;
  --muted: #91a0b8;
  --gold: #d9ad5b;
  --green: #4fd1a1;
  --red: #ff7b86;
  --blue: #78a9ff;
}
.stApp { background: var(--bg); color: var(--text); font-family: 'DM Sans', sans-serif; }
[data-testid="stHeader"] { background: rgba(11,16,32,.95); }
.block-container { padding-top: 1.7rem; padding-bottom: 3rem; max-width: 1500px; }
h1,h2,h3 { font-family: 'Space Grotesk', sans-serif !important; letter-spacing: -.03em; }
h1 { font-size: 2.1rem !important; font-weight: 700 !important; }
h2 { font-size: 1.25rem !important; font-weight: 600 !important; }
p, label, div { }
[data-testid="stSidebar"] { background: #0e1628; border-right: 1px solid var(--line); }
[data-testid="stSidebar"] * { color: var(--text); }
[data-testid="stMetric"] {
  background: linear-gradient(145deg, #141f34, #10182a);
  border: 1px solid var(--line); padding: 18px 20px; border-radius: 14px;
}
[data-testid="stMetricLabel"] { color: var(--muted) !important; font-size: .78rem !important; }
[data-testid="stMetricValue"] { color: var(--text) !important; font-family: 'Space Grotesk', sans-serif; }
[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
.stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 1px solid var(--line); }
.stTabs [data-baseweb="tab"] { background: transparent; color: var(--muted); border-radius: 8px 8px 0 0; }
.stTabs [aria-selected="true"] { color: var(--gold) !important; border-bottom: 2px solid var(--gold) !important; }
div[data-testid="stAlert"] { border-radius: 10px; }
.goldlens-brand { display:flex; align-items:center; gap:12px; margin-bottom:22px; }
.brand-mark { width:42px; height:42px; display:flex; align-items:center; justify-content:center;
  border-radius:12px; background:linear-gradient(145deg,#e4c17c,#b98535); color:#101625;
  font-family:'Space Grotesk'; font-weight:800; font-size:23px; }
.brand-title { font-family:'Space Grotesk'; font-weight:700; font-size:20px; color:#f5f7fc; }
.brand-sub { color:var(--muted); font-size:11px; letter-spacing:.13em; text-transform:uppercase; }
.hero { background:linear-gradient(115deg,#151f35 0%,#10182a 65%,#1b2335 100%);
  border:1px solid var(--line); border-radius:18px; padding:24px 26px; margin-bottom:20px; }
.eyebrow { color:var(--gold); font-size:11px; font-weight:700; letter-spacing:.17em; text-transform:uppercase; }
.hero-title { font-family:'Space Grotesk'; font-size:29px; font-weight:700; margin:7px 0 6px; color:#f5f7fc; }
.hero-copy { color:#a8b5c9; font-size:14px; max-width:760px; }
.pill { display:inline-block; padding:5px 9px; border-radius:999px; font-size:11px; font-weight:700;
  background:#342b1b; color:#e4c17c; border:1px solid #65502d; }
.section-head { display:flex; justify-content:space-between; align-items:center; margin:12px 0 10px; }
.section-note { color:var(--muted); font-size:12px; }
.panel { background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:16px 18px; }
.small-muted { color:var(--muted); font-size:12px; }
hr { border-color:var(--line) !important; }
footer { visibility:hidden; }
</style>
""", unsafe_allow_html=True)

# ---------- Data ----------
try:
    raw = load_data()
    normalized = normalize_prices(raw)
    analyzed = calculate_spreads(raw)
    backtest = run_backtest(analyzed, threshold=2.0, cost_bps=10)
except Exception as exc:
    st.error(f"Could not load or analyze the dataset: {exc}")
    st.stop()

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("""
    <div class="goldlens-brand">
      <div class="brand-mark">G</div>
      <div>
        <div class="brand-title">GoldLens</div>
        <div class="brand-sub">SPYX · Market intelligence</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("### Workspace")
    st.caption("Commodity derivatives · Gold")
    all_symbols = ["GOLD", "GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"]
    symbols = st.multiselect("Contracts", all_symbols, default=all_symbols)
    min_date = raw["trade_date"].min().date()
    max_date = raw["trade_date"].max().date()
    date_range = st.date_input("Trading period", value=(min_date, max_date),
                               min_value=min_date, max_value=max_date)
    st.divider()
    st.markdown("### Signal settings")
    threshold = st.slider("Z-score threshold", 1.0, 3.5, 2.0, 0.25)
    window = st.slider("Lookback window", 3, 10, 5)
    cost_bps = st.slider("Estimated cost (bps)", 0, 50, 10, 5)
    st.divider()
    st.markdown('<div class="small-muted">DATA MODE</div><span class="pill">SYNTHETIC DEMO DATA</span>',
                unsafe_allow_html=True)
    st.caption("No live MCX feed is connected in this build.")

if not symbols:
    st.warning("Select at least one contract from the sidebar.")
    st.stop()

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

filtered_raw = raw[
    raw["symbol"].isin(symbols)
    & raw["trade_date"].dt.date.between(start_date, end_date)
].copy()
if filtered_raw.empty:
    st.warning("No records match the selected period.")
    st.stop()

normalized = normalize_prices(filtered_raw)
analyzed = calculate_spreads(filtered_raw, window=window, threshold=threshold)
backtest = run_backtest(analyzed, threshold=threshold, cost_bps=cost_bps)
metrics = calculate_metrics(backtest)

# ---------- Header ----------
st.markdown("""
<div class="hero">
  <div class="eyebrow">Commodity derivatives intelligence</div>
  <div class="hero-title">Gold contract intelligence, without the noise.</div>
  <div class="hero-copy">Normalize cross-contract prices, inspect relative-value deviations and evaluate a
  transparent spread strategy with estimated costs. Built for research, not blind execution.</div>
</div>
""", unsafe_allow_html=True)

left, right = st.columns([4, 1])
with left:
    st.markdown("## Market overview")
    st.caption(f"{start_date:%d %b %Y} — {end_date:%d %b %Y} · {len(filtered_raw):,} valid records")
with right:
    st.markdown("<div style='text-align:right;padding-top:12px'><span class='pill'>PROTOTYPE · V1</span></div>",
                unsafe_allow_html=True)

# Metrics
signal_count = int(analyzed["signal"].isin(["Potentially rich", "Potentially cheap"]).sum())
latest_date = filtered_raw["trade_date"].max().strftime("%d %b %Y")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Contracts monitored", f"{filtered_raw['symbol'].nunique()}/4")
m2.metric("Valid observations", f"{len(filtered_raw):,}")
m3.metric("Latest data date", latest_date)
m4.metric("Threshold events", f"{signal_count:,}")

tab_overview, tab_signals, tab_backtest, tab_data = st.tabs(
    ["Overview", "Spread radar", "Strategy simulation", "Data quality"]
)

plot_template = "plotly_dark"
chart_layout = dict(
    template=plot_template,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans, sans-serif", color="#aebbd0", size=11),
    margin=dict(l=10, r=10, t=24, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    xaxis=dict(showgrid=False, zeroline=False),
    yaxis=dict(gridcolor="#26334d", zeroline=False),
)

with tab_overview:
    st.markdown("### Normalized contract prices")
    st.caption("Comparable 999-purity price basis in ₹ per gram. Each line represents a separate contract.")
    fig = px.line(
        normalized.sort_values("trade_date"),
        x="trade_date", y="normalized_price", color="symbol",
        markers=True,
        hover_data={"expiry_date": True, "settlement_price": ":,.2f", "normalized_price": ":,.2f"},
        labels={"trade_date":"Trading date", "normalized_price":"₹ / gram (999 basis)",
                "symbol":"Contract", "expiry_date":"Expiry", "settlement_price":"Settlement price"},
        color_discrete_sequence=["#d9ad5b", "#78a9ff", "#4fd1a1", "#c59cff"],
    )
    fig.update_layout(**chart_layout, height=380)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Latest contract snapshot")
    latest = normalized.sort_values("trade_date").groupby("symbol", as_index=False).tail(1)
    latest = latest[["symbol","trade_date","expiry_date","settlement_price","normalized_price","volume"]]
    latest = latest.rename(columns={
        "symbol":"Contract", "trade_date":"Trading date", "expiry_date":"Expiry",
        "settlement_price":"Settlement price", "normalized_price":"Normalized ₹/g",
        "volume":"Reported volume"
    })
    st.dataframe(latest, use_container_width=True, hide_index=True)

with tab_signals:
    st.markdown("### Relative-value deviations")
    st.caption("Z-scores compare each contract's deviation from the same-day cross-contract median against its own prior history. Rolling statistics use prior observations only.")
    fig2 = px.line(
        analyzed.sort_values("trade_date"), x="trade_date", y="z_score", color="symbol",
        markers=True,
        labels={"trade_date":"Trading date", "z_score":"Rolling z-score", "symbol":"Contract"},
        color_discrete_sequence=["#d9ad5b", "#78a9ff", "#4fd1a1", "#c59cff"],
    )
    fig2.add_hline(y=threshold, line_dash="dash", line_color="#ff7b86",
                   annotation_text=f"+{threshold:.1f} threshold")
    fig2.add_hline(y=-threshold, line_dash="dash", line_color="#4fd1a1",
                   annotation_text=f"−{threshold:.1f} threshold")
    fig2.update_layout(**chart_layout, height=370)
    st.plotly_chart(fig2, use_container_width=True)

    signals = analyzed.sort_values("trade_date", ascending=False)[
        ["trade_date","expiry_date","symbol","normalized_price","spread","z_score","signal"]
    ].copy()
    signals = signals.rename(columns={
        "trade_date":"Date", "expiry_date":"Expiry", "symbol":"Contract",
        "normalized_price":"Normalized ₹/g", "spread":"Spread vs median",
        "z_score":"Z-score", "signal":"Signal"
    })
    st.dataframe(signals, use_container_width=True, hide_index=True)
    st.caption("A signal flags a statistical deviation only. It is not proof of executable arbitrage or a recommendation to trade.")

with tab_backtest:
    st.markdown("### Historical strategy simulation")
    st.caption("Signal at close t is evaluated on the next observed spread move. Results are spread units, not account-level P&L.")
    net_pnl = float(backtest["net_pnl_spread_units"].fillna(0).sum())
    positive = float((backtest["net_pnl_spread_units"].dropna() > 0).mean() * 100) if backtest["net_pnl_spread_units"].notna().any() else 0.0
    equity = backtest.sort_values("trade_date").copy()
    equity["portfolio_curve"] = equity["net_pnl_spread_units"].fillna(0).cumsum()
    peak = equity["portfolio_curve"].cummax()
    dd = equity["portfolio_curve"] - peak
    max_dd = float(dd.min()) if len(dd) else 0.0

    b1,b2,b3 = st.columns(3)
    b1.metric("Net spread P&L", f"{net_pnl:,.2f}")
    b2.metric("Positive observations", f"{positive:.1f}%")
    b3.metric("Max drawdown", f"{max_dd:,.2f}")

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=equity["trade_date"], y=equity["portfolio_curve"],
        mode="lines", line=dict(color="#d9ad5b", width=2.5),
        fill="tozeroy", fillcolor="rgba(217,173,91,0.08)", name="Cumulative net spread P&L"
    ))
    fig3.update_layout(**chart_layout, height=330, yaxis_title="Normalized spread units")
    st.plotly_chart(fig3, use_container_width=True)

    bt_view = backtest[["trade_date","expiry_date","symbol","target_position","gross_pnl_spread_units","estimated_cost_spread_units","net_pnl_spread_units"]].copy()
    bt_view = bt_view.rename(columns={
        "trade_date":"Date", "expiry_date":"Expiry", "symbol":"Contract",
        "target_position":"Target position", "gross_pnl_spread_units":"Gross spread P&L (units)",
        "estimated_cost_spread_units":"Estimated cost (proxy units)", "net_pnl_spread_units":"Net spread P&L (units)"
    })
    st.dataframe(bt_view.sort_values("Date", ascending=False), use_container_width=True, hide_index=True)
    st.warning("This simplified backtest does not model exchange lot sizes, two-leg fills, margin, market depth, taxes or expiry settlement. Treat the output as a prototype diagnostic only.")

with tab_data:
    st.markdown("### Dataset validation")
    q1,q2,q3 = st.columns(3)
    q1.metric("Rows loaded", f"{len(raw):,}")
    q2.metric("Rows in selected view", f"{len(filtered_raw):,}")
    q3.metric("Unique trading dates", f"{filtered_raw['trade_date'].nunique():,}")

    quality = filtered_raw.groupby("symbol").agg(
        records=("trade_date","count"),
        first_date=("trade_date","min"),
        last_date=("trade_date","max"),
        missing_volume=("volume",lambda s: int(s.isna().sum())),
        expiry_count=("expiry_date","nunique"),
    ).reset_index().rename(columns={
        "symbol":"Contract", "records":"Records", "first_date":"First date",
        "last_date":"Last date", "missing_volume":"Missing volume", "expiry_count":"Distinct expiries"
    })
    st.dataframe(quality, use_container_width=True, hide_index=True)
    st.markdown("#### Data caveats")
    st.write("- Current bundled CSV is synthetic demo data.")
    st.write("- Settlement prices are not executable fill prices.")
    st.write("- The prototype tracks contract expiry explicitly and does not stitch a continuous near-month series.")

st.divider()
st.markdown(
    "<div class='small-muted'>SPYX GoldLens · Research prototype · Data shown here is synthetic unless explicitly replaced with validated MCX data.</div>",
    unsafe_allow_html=True
)
