from pathlib import Path
import pandas as pd

# Put the downloaded MCX Bhavcopy in the project's data/ folder.
DATA_FILE = Path(__file__).parent / "data" / "BhavCopyDateWise_19102026.csv"
VALID_SYMBOLS = {"GOLD", "GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"}

def load_data(file_path=DATA_FILE):
    """Load either GoldLens normalized CSVs or the MCX BhavCopyDateWise format."""
    path = Path(file_path)
    if not path.exists():
        fallback = Path(__file__).parent / "data" / "sample_bhavcopy.csv"
        if fallback.exists():
            path = fallback
        else:
            raise FileNotFoundError(f"Dataset not found: {path}")

    df = pd.read_csv(path)
    # MCX BhavCopyDateWise format: clean whitespace from headings and symbols.
    df.columns = [str(c).strip() for c in df.columns]
    if {"Date", "Instrument Name", "Symbol", "Expiry Date", "Close"}.issubset(df.columns):
        df["Symbol"] = df["Symbol"].astype(str).str.strip().str.upper()
        # In this BhavCopy, Instrument Name identifies the derivative family (OPTFUT).
        # Futures are identified by Option Type '-' and Strike Price 0; exclude option rows.
        if "Option Type" in df.columns and "Strike Price" in df.columns:
            is_future = (
                df["Option Type"].astype(str).str.strip().eq("-")
                & pd.to_numeric(df["Strike Price"], errors="coerce").fillna(-1).eq(0)
            )
            df = df[is_future].copy()
        df = df[df["Symbol"].isin(VALID_SYMBOLS)].copy()
        out = pd.DataFrame({
            "trade_date": pd.to_datetime(df["Date"], errors="coerce", dayfirst=True),
            "expiry_date": pd.to_datetime(df["Expiry Date"], errors="coerce", format="%d%b%Y"),
            "symbol": df["Symbol"],
            "settlement_price": pd.to_numeric(df["Close"], errors="coerce"),
            "volume": pd.to_numeric(df.get("Volume(Lots)", 0), errors="coerce"),
            "open": pd.to_numeric(df.get("Open"), errors="coerce"),
            "high": pd.to_numeric(df.get("High"), errors="coerce"),
            "low": pd.to_numeric(df.get("Low"), errors="coerce"),
            "previous_close": pd.to_numeric(df.get("Previous Close"), errors="coerce"),
            "open_interest": pd.to_numeric(df.get("Open Interest(Lots)"), errors="coerce"),
            "source_instrument": df["Instrument Name"].astype(str).str.strip(),
        })
    else:
        # Existing normalized GoldLens format.
        required = {"trade_date", "expiry_date", "symbol", "settlement_price", "volume"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(
                f"Unsupported CSV format. Missing required columns: {sorted(missing)}. "
                "Expected GoldLens columns or MCX BhavCopyDateWise columns."
            )
        out = df.copy()
        out["trade_date"] = pd.to_datetime(out["trade_date"], errors="coerce")
        out["expiry_date"] = pd.to_datetime(out["expiry_date"], errors="coerce")
        out["settlement_price"] = pd.to_numeric(out["settlement_price"], errors="coerce")
        out["volume"] = pd.to_numeric(out["volume"], errors="coerce")
        out["symbol"] = out["symbol"].astype(str).str.strip().str.upper()

    bad_date = out["trade_date"].isna() | out["expiry_date"].isna()
    bad_price = out["settlement_price"].isna() | (out["settlement_price"] <= 0)
    bad_symbol = ~out["symbol"].isin(VALID_SYMBOLS)
    bad_expiry = out["expiry_date"] < out["trade_date"]
    total = len(out)
    valid = ~(bad_date | bad_price | bad_symbol | bad_expiry)
    out = out.loc[valid].copy()
    duplicate_count = int(out.duplicated(["trade_date", "expiry_date", "symbol"], keep="last").sum())
    out = out.drop_duplicates(["trade_date", "expiry_date", "symbol"], keep="last")
    report = {
        "input_rows": int(total),
        "invalid_dates": int(bad_date.sum()),
        "invalid_prices": int(bad_price.sum()),
        "unsupported_symbols": int(bad_symbol.sum()),
        "expiry_before_trade_date": int(bad_expiry.sum()),
        "duplicate_rows_removed": duplicate_count,
        "valid_rows": int(len(out)),
        "rejected_rows": int(total - len(out)),
    }
    if out.empty:
        raise ValueError("No valid gold futures rows remain after data-quality checks.")
    out = out.sort_values(["trade_date", "expiry_date", "symbol"]).reset_index(drop=True)
    out.attrs["quality_report"] = report
    out.attrs["source_file"] = path.name
    return out
