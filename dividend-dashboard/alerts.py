"""Alerts and notification engine for Vizion Income."""

from datetime import datetime, timedelta
from market_data import get_stock_info


def check_watchlist_alerts(watchlist: list[dict]) -> list[dict]:
    """Check watchlist items against current prices. Returns triggered alerts."""
    alerts = []
    for item in watchlist:
        ticker = item.get("ticker", "")
        target = item.get("target_price")
        if not target:
            continue
        try:
            info = get_stock_info(ticker)
            if "error" in info:
                continue
            price = info.get("price", 0)
            if price <= target:
                pct_below = ((target - price) / target) * 100
                alerts.append({
                    "type": "price_target",
                    "ticker": ticker,
                    "name": info.get("name", ticker),
                    "price": price,
                    "target": target,
                    "pct_below": pct_below,
                    "message": (
                        f"{ticker} is at ${price:,.2f}, "
                        f"{pct_below:.1f}% below your ${target:,.2f} target."
                    ),
                })
        except Exception:
            continue
    return alerts


def check_portfolio_alerts(holdings_data: list[dict]) -> list[dict]:
    """Check portfolio holdings for significant changes. Returns triggered alerts."""
    alerts = []
    for h in holdings_data:
        ticker = h.get("ticker", "")
        price = h.get("price", 0)
        avg_cost = h.get("avg_cost", 0)
        if avg_cost <= 0:
            continue

        gain_pct = ((price - avg_cost) / avg_cost) * 100

        # Significant gain
        if gain_pct >= 20:
            alerts.append({
                "type": "significant_gain",
                "ticker": ticker,
                "gain_pct": gain_pct,
                "message": f"{ticker} is up {gain_pct:.1f}% from your cost basis.",
            })

        # Significant loss
        if gain_pct <= -15:
            alerts.append({
                "type": "significant_loss",
                "ticker": ticker,
                "gain_pct": gain_pct,
                "message": (
                    f"{ticker} is down {abs(gain_pct):.1f}% from your cost basis. "
                    f"Review your position."
                ),
            })

        # High yield warning (possible dividend cut risk)
        div_yield = h.get("dividend_yield", 0)
        if div_yield > 0.08:
            alerts.append({
                "type": "high_yield_warning",
                "ticker": ticker,
                "yield_pct": div_yield * 100,
                "message": (
                    f"{ticker} yields {div_yield*100:.1f}%, which is unusually high. "
                    f"Verify the dividend is sustainable."
                ),
            })

    return alerts


def generate_weekly_summary(holdings_data: list[dict], portfolio_history: list[dict]) -> dict:
    """Generate a weekly portfolio summary."""
    if not holdings_data:
        return {
            "total_value": 0,
            "weekly_change": 0,
            "weekly_change_pct": 0,
            "total_income": 0,
            "top_performer": None,
            "worst_performer": None,
            "holdings_count": len(holdings_data),
        }

    total_value = sum(
        h.get("shares", 0) * h.get("price", 0) for h in holdings_data
    )
    total_income = sum(
        h.get("shares", 0) * h.get("dividend_rate", 0) for h in holdings_data
    )

    # Weekly change from snapshots
    weekly_change = 0
    weekly_change_pct = 0
    if portfolio_history and len(portfolio_history) >= 2:
        latest = portfolio_history[0].get("total_value", 0)
        week_ago_candidates = [
            s for s in portfolio_history
            if s.get("snapshot_date", "") <= (
                datetime.now() - timedelta(days=7)
            ).strftime("%Y-%m-%d")
        ]
        if week_ago_candidates:
            week_ago = week_ago_candidates[0].get("total_value", 0)
            if week_ago > 0:
                weekly_change = latest - week_ago
                weekly_change_pct = (weekly_change / week_ago) * 100

    # Top and worst performers
    performers = []
    for h in holdings_data:
        avg_cost = h.get("avg_cost", 0)
        price = h.get("price", 0)
        if avg_cost > 0:
            pct = ((price - avg_cost) / avg_cost) * 100
            performers.append({"ticker": h["ticker"], "pct": pct})

    performers.sort(key=lambda x: x["pct"], reverse=True)
    top = performers[0] if performers else None
    worst = performers[-1] if performers else None

    return {
        "total_value": total_value,
        "weekly_change": weekly_change,
        "weekly_change_pct": weekly_change_pct,
        "total_income": total_income,
        "top_performer": top,
        "worst_performer": worst,
        "holdings_count": len(holdings_data),
    }


def get_alert_color(alert_type: str) -> str:
    """Return color for alert type."""
    colors = {
        "price_target": "#22c55e",
        "significant_gain": "#06b6d4",
        "significant_loss": "#f85149",
        "high_yield_warning": "#f59e0b",
    }
    return colors.get(alert_type, "#667eea")
