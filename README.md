# SPYX GoldLens — Advanced Prototype

## Run on Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

Open the local URL shown in the terminal, usually http://localhost:8501.

## Core files
- `app.py`: dashboard
- `analytics.py`: normalization, spread calculations, no-look-ahead rolling statistics, simplified simulation
- `data_loader.py`: CSV validation and data-quality report
- `data/sample_bhavcopy.csv`: synthetic demonstration dataset
- `requirements.txt`: dependencies

## Improvements in this version
- Validates columns, dates, prices, contract symbols, expiry order and duplicates.
- Rolling statistics use prior observations only.
- Backtest threshold follows the dashboard setting.
- A signal at time t is evaluated against the next observed spread change.
- Cross-contract benchmark is calculated before the dashboard display filter.
- Data-quality report is surfaced in the dashboard.

## Limitations
The included data is synthetic, not actual MCX data. Quote basis and purity assumptions must be verified against current official MCX contract specifications and Bhavcopy conventions before live use. The backtest is a simplified diagnostic: P&L is expressed in normalized spread units and estimated costs are only a proxy. It does not model lot sizes, executable two-leg fills, order-book depth, margin, taxes or expiry settlement. It is not verified trading performance.
