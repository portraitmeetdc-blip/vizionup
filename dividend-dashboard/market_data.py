import yfinance as yf
import pandas as pd
from functools import lru_cache
from datetime import datetime, timedelta


def get_stock_info(ticker):
    """Fetch current stock info including dividend data."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "ticker": ticker.upper(),
            "name": info.get("longName", info.get("shortName", ticker)),
            "price": info.get("currentPrice", info.get("regularMarketPrice", 0)),
            "dividend_rate": info.get("dividendRate", 0) or 0,
            "dividend_yield": info.get("dividendYield", 0) or 0,
            "ex_dividend_date": info.get("exDividendDate"),
            "payout_ratio": info.get("payoutRatio", 0) or 0,
            "market_cap": info.get("marketCap", 0),
            "sector": info.get("sector", "N/A"),
            "pe_ratio": info.get("trailingPE", 0) or 0,
            "52w_high": info.get("fiftyTwoWeekHigh", 0),
            "52w_low": info.get("fiftyTwoWeekLow", 0),
            "beta": info.get("beta", 0) or 0,
        }
    except Exception as e:
        return {"ticker": ticker.upper(), "error": str(e)}


def get_dividend_history(ticker, period="5y"):
    """Fetch historical dividend payments."""
    try:
        stock = yf.Ticker(ticker)
        dividends = stock.dividends
        if dividends.empty:
            return pd.DataFrame()
        df = dividends.reset_index()
        df.columns = ["Date", "Dividend"]
        df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
        return df.sort_values("Date", ascending=False)
    except Exception:
        return pd.DataFrame()


def get_price_history(ticker, period="1y"):
    """Fetch historical price data."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        return hist
    except Exception:
        return pd.DataFrame()


def screen_dividend_stocks(min_yield=0.03, min_market_cap=1e9, max_payout=0.8):
    """Screen for quality dividend stocks from a curated list of reliable payers."""
    # Well-known dividend aristocrats and high-yield stocks
    candidates = [
        "JNJ", "PG", "KO", "PEP", "MMM", "ABT", "ABBV", "T", "VZ",
        "XOM", "CVX", "MO", "PM", "O", "MAIN", "SCHD", "VYM", "HDV",
        "JEPI", "JEPQ", "AGNC", "NLY", "STAG", "EPD", "ET",
        "WMT", "HD", "MCD", "MSFT", "AAPL", "IBM", "CAT", "CL",
        "GPC", "EMR", "SWK", "FRT", "BEN", "TROW", "AFL",
        "SPG", "STOR", "NNN", "WPC", "MPW", "GOOD",
    ]

    results = []
    for ticker in candidates:
        try:
            info = get_stock_info(ticker)
            if "error" in info:
                continue
            yield_val = info.get("dividend_yield", 0)
            cap = info.get("market_cap", 0)
            payout = info.get("payout_ratio", 0)

            if yield_val >= min_yield and cap >= min_market_cap and payout <= max_payout:
                info["passes_screen"] = True
                results.append(info)
        except Exception:
            continue

    return sorted(results, key=lambda x: x.get("dividend_yield", 0), reverse=True)


def calculate_portfolio_income(holdings_with_data):
    """Calculate projected annual and monthly dividend income."""
    total_annual = 0
    total_invested = 0
    total_value = 0
    details = []

    for h in holdings_with_data:
        shares = h["shares"]
        div_rate = h.get("dividend_rate", 0) or 0
        price = h.get("price", 0) or 0
        avg_cost = h.get("avg_cost", 0)

        annual_income = shares * div_rate
        cost_basis = shares * avg_cost
        current_value = shares * price
        gain_loss = current_value - cost_basis
        yield_on_cost = (div_rate / avg_cost * 100) if avg_cost > 0 else 0

        total_annual += annual_income
        total_invested += cost_basis
        total_value += current_value

        details.append({
            "ticker": h["ticker"],
            "name": h.get("name", h["ticker"]),
            "shares": shares,
            "price": price,
            "avg_cost": avg_cost,
            "dividend_rate": div_rate,
            "annual_income": annual_income,
            "monthly_income": annual_income / 12,
            "cost_basis": cost_basis,
            "current_value": current_value,
            "gain_loss": gain_loss,
            "gain_loss_pct": (gain_loss / cost_basis * 100) if cost_basis > 0 else 0,
            "yield_on_cost": yield_on_cost,
            "current_yield": h.get("dividend_yield", 0) * 100,
        })

    return {
        "total_annual_income": total_annual,
        "total_monthly_income": total_annual / 12,
        "total_invested": total_invested,
        "total_value": total_value,
        "total_gain_loss": total_value - total_invested,
        "portfolio_yield": (total_annual / total_invested * 100) if total_invested > 0 else 0,
        "details": details,
    }


def project_growth(initial_investment, monthly_contribution, annual_yield, years):
    """Project portfolio growth with dividend reinvestment."""
    monthly_yield = annual_yield / 12
    balance = initial_investment
    projections = []

    for month in range(1, years * 12 + 1):
        dividend = balance * monthly_yield
        balance += dividend + monthly_contribution
        if month % 12 == 0:
            projections.append({
                "year": month // 12,
                "balance": balance,
                "annual_income": balance * annual_yield,
                "monthly_income": balance * annual_yield / 12,
            })

    return projections
