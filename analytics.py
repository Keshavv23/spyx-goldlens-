import numpy as np
import pandas as pd

CONTRACTS = {
    "GOLDM": {"quoted_grams": 10.0, "purity": 995},
    "GOLDTEN": {"quoted_grams": 10.0, "purity": 999},
    "GOLDGUINEA": {"quoted_grams": 8.0, "purity": 999},
    "GOLDPETAL": {"quoted_grams": 1.0, "purity": 999},
}
GROUP_KEYS = ["symbol", "expiry_date"]


def normalize_prices(df):
    required = {"symbol", "settlement_price"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns for normalization: {sorted(missing)}")
    out = df.copy()
    out["symbol"] = out["symbol"].astype(str).str.strip().str.upper()
    unknown = sorted(set(out["symbol"]) - set(CONTRACTS))
    if unknown:
        raise ValueError(f"Unsupported contract symbols: {unknown}")
    grams = out["symbol"].map({k: v["quoted_grams"] for k, v in CONTRACTS.items()})
    purity = out["symbol"].map({k: v["purity"] for k, v in CONTRACTS.items()})
    out["normalized_price"] = (
        pd.to_numeric(out["settlement_price"], errors="coerce") / grams * (999 / purity)
    )
    return out


def calculate_spreads(df, window=5, threshold=2.0, min_periods=3):
    if window < 2:
        raise ValueError("window must be at least 2")
    if threshold <= 0:
        raise ValueError("threshold must be positive")
    out = normalize_prices(df)
    missing = {"trade_date", "expiry_date"} - set(out.columns)
    if missing:
        raise ValueError(f"Missing columns for spread analysis: {sorted(missing)}")
    out["trade_date"] = pd.to_datetime(out["trade_date"], errors="coerce")
    out["expiry_date"] = pd.to_datetime(out["expiry_date"], errors="coerce")
    out = out.dropna(subset=["trade_date", "expiry_date", "normalized_price"]).copy()
    out = out.sort_values(["trade_date", "expiry_date", "symbol"]).reset_index(drop=True)
    out["benchmark"] = out.groupby(["trade_date", "expiry_date"])["normalized_price"].transform("median")
    out["spread"] = out["normalized_price"] - out["benchmark"]
    out = out.sort_values(["symbol", "expiry_date", "trade_date"]).copy()
    hist = out.groupby(GROUP_KEYS, sort=False)["spread"]
    out["rolling_mean"] = hist.transform(
        lambda s: s.shift(1).rolling(window, min_periods=min_periods).mean()
    )
    out["rolling_std"] = hist.transform(
        lambda s: s.shift(1).rolling(window, min_periods=min_periods).std(ddof=0)
    )
    out["z_score"] = (out["spread"] - out["rolling_mean"]) / out["rolling_std"].where(out["rolling_std"] > 1e-12)
    out["signal"] = np.select(
        [out["z_score"] >= threshold, out["z_score"] <= -threshold],
        ["Potentially rich", "Potentially cheap"],
        default="No signal",
    )
    out["threshold"] = float(threshold)
    return out.sort_values(["trade_date", "expiry_date", "symbol"]).reset_index(drop=True)


def run_backtest(analyzed, threshold=2.0, cost_bps=10.0):
    """Simple next-observation spread diagnostic; outputs are spread units, not account P&L."""
    if threshold <= 0 or cost_bps < 0:
        raise ValueError("threshold must be positive and cost_bps non-negative")
    required = {"trade_date", "expiry_date", "symbol", "spread", "z_score", "normalized_price"}
    missing = required - set(analyzed.columns)
    if missing:
        raise ValueError(f"Missing columns for backtest: {sorted(missing)}")
    out = analyzed.sort_values(["symbol", "expiry_date", "trade_date"]).copy()
    groups = out.groupby(GROUP_KEYS, sort=False)
    # Signal at close t applies to the next observed spread change.
    out["target_position"] = np.select(
        [out["z_score"] <= -threshold, out["z_score"] >= threshold],
        [1.0, -1.0], default=0.0,
    )
    out["next_spread"] = groups["spread"].shift(-1)
    out["next_spread_change"] = out["next_spread"] - out["spread"]
    out["gross_pnl_spread_units"] = out["target_position"] * out["next_spread_change"]
    out["previous_position"] = groups["target_position"].shift(1).fillna(0.0)
    out["turnover"] = (out["target_position"] - out["previous_position"]).abs()
    out["estimated_cost_spread_units"] = (
        out["turnover"] * out["normalized_price"] * float(cost_bps) / 10000.0
    )
    out["net_pnl_spread_units"] = out["gross_pnl_spread_units"] - out["estimated_cost_spread_units"]
    out.loc[out["next_spread_change"].isna(), ["gross_pnl_spread_units", "net_pnl_spread_units"]] = np.nan
    return out.sort_values(["trade_date", "expiry_date", "symbol"]).reset_index(drop=True)


def calculate_metrics(backtest):
    valid = backtest.dropna(subset=["gross_pnl_spread_units"]).copy()
    if valid.empty:
        return {"observations": 0, "net_pnl_spread_units": 0.0,
                "positive_observations_pct": 0.0, "max_drawdown_spread_units": 0.0}
    daily = valid.groupby("trade_date")["net_pnl_spread_units"].sum().sort_index()
    equity = daily.cumsum()
    drawdown = equity - equity.cummax()
    return {
        "observations": int(len(valid)),
        "net_pnl_spread_units": float(daily.sum()),
        "positive_observations_pct": float((valid["net_pnl_spread_units"] > 0).mean() * 100),
        "max_drawdown_spread_units": float(drawdown.min()),
    }
