# The Passive Approach to Generating Wealth

A suite of tools designed to generate passive income with minimal ongoing effort.

## Applications

### 1. Dividend Dashboard (`dividend-dashboard/`)
Investment tracking and analysis tool — monitors dividend stocks, projects passive income, and alerts on buy opportunities.

### 2. Stock Media Manager (`stock-media-manager/`)
Turns existing photo/video work into recurring royalty income — organizes, tags, and tracks media uploads to stock platforms.

## Tech Stack
- Python 3.10+
- Streamlit (web dashboard)
- SQLite (local database)
- yfinance (market data)
- pandas (analysis)

## Running
Each app runs independently via Streamlit:
```bash
cd dividend-dashboard && streamlit run app.py
cd stock-media-manager && streamlit run app.py
```
