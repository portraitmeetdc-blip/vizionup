"""Portfolio insights engine — generates actionable tips and analysis."""

from market_data import get_stock_info


def generate_insights(holdings_data: list[dict], watchlist: list[dict] = None) -> list[dict]:
    """
    Analyze portfolio data and return a list of insight dicts:
    {"type": "opportunity"|"warning"|"tip"|"milestone", "title": str, "detail": str}
    """
    if not holdings_data:
        return [{
            "type": "tip",
            "title": "Get started",
            "detail": "Add your first stock holding to begin tracking your passive income.",
        }]

    insights = []

    # Portfolio-level metrics
    total_value = sum(h.get("current_value", 0) for h in holdings_data)
    total_income = sum(h.get("annual_income", 0) for h in holdings_data)
    total_cost = sum(h.get("cost_basis", 0) for h in holdings_data)
    portfolio_yield = (total_income / total_cost * 100) if total_cost > 0 else 0

    # ── Sector concentration ──
    sectors = {}
    for h in holdings_data:
        sector = h.get("sector", "Unknown")
        val = h.get("current_value", 0)
        sectors[sector] = sectors.get(sector, 0) + val

    if sectors and total_value > 0:
        top_sector = max(sectors, key=sectors.get)
        top_pct = sectors[top_sector] / total_value * 100
        if top_pct > 50:
            insights.append({
                "type": "warning",
                "title": "Concentration risk",
                "detail": (
                    f"{top_pct:.0f}% of your portfolio is in {top_sector}. "
                    f"Consider diversifying across sectors to reduce risk."
                ),
            })
        elif len(sectors) >= 4:
            insights.append({
                "type": "tip",
                "title": "Well diversified",
                "detail": f"Your portfolio spans {len(sectors)} sectors. Good diversification.",
            })

    # ── Yield analysis ──
    if portfolio_yield > 6:
        insights.append({
            "type": "tip",
            "title": "High yield portfolio",
            "detail": (
                f"Your portfolio yield is {portfolio_yield:.1f}%, well above the S&P 500 average of ~1.3%. "
                f"Ensure high-yield holdings have sustainable payout ratios."
            ),
        })
    elif portfolio_yield > 0:
        insights.append({
            "type": "tip",
            "title": "Yield overview",
            "detail": (
                f"Your portfolio yields {portfolio_yield:.1f}% on cost, "
                f"generating ${total_income:,.0f}/yr in passive income."
            ),
        })

    # ── Individual stock alerts ──
    for h in holdings_data:
        ticker = h.get("ticker", "")
        payout = h.get("payout_ratio", 0)
        gain_loss_pct = h.get("gain_loss_pct", 0)
        div_yield = h.get("current_yield", 0)

        # Unsustainable payout
        if payout and payout > 0.9:
            insights.append({
                "type": "warning",
                "title": f"{ticker} payout ratio is high",
                "detail": (
                    f"{ticker} has a {payout*100:.0f}% payout ratio. "
                    f"Dividends above 90% payout may not be sustainable long-term."
                ),
            })

        # Big winners
        if gain_loss_pct > 25:
            insights.append({
                "type": "milestone",
                "title": f"{ticker} is up {gain_loss_pct:.0f}%",
                "detail": (
                    f"Your position in {ticker} has gained {gain_loss_pct:.0f}% "
                    f"since purchase. Consider whether to take profits or let it ride."
                ),
            })

        # Positions down significantly
        if gain_loss_pct < -15:
            insights.append({
                "type": "warning",
                "title": f"{ticker} is down {abs(gain_loss_pct):.0f}%",
                "detail": (
                    f"{ticker} is down {abs(gain_loss_pct):.0f}% from your cost basis. "
                    f"If the dividend is still covered, this could be a chance to average down."
                ),
            })

    # ── Watchlist opportunities ──
    if watchlist:
        for item in watchlist:
            ticker = item.get("ticker", "")
            target = item.get("target_price")
            if not target:
                continue
            try:
                info = get_stock_info(ticker)
                if "error" not in info and info["price"] <= target:
                    insights.append({
                        "type": "opportunity",
                        "title": f"{ticker} hit your target price",
                        "detail": (
                            f"{ticker} is trading at ${info['price']:,.2f}, "
                            f"below your ${target:,.2f} target. Consider buying."
                        ),
                    })
            except Exception:
                continue

    # ── Income milestones ──
    monthly = total_income / 12 if total_income > 0 else 0
    if monthly >= 1000:
        insights.append({
            "type": "milestone",
            "title": "Four-figure monthly income",
            "detail": f"You're earning ${monthly:,.0f}/mo in dividends. Reinvesting accelerates compounding.",
        })
    elif monthly >= 100:
        insights.append({
            "type": "milestone",
            "title": "Triple-digit monthly income",
            "detail": f"${monthly:,.0f}/mo in passive income. Stay consistent and this compounds fast.",
        })
    elif monthly > 0:
        insights.append({
            "type": "tip",
            "title": "Building momentum",
            "detail": (
                f"You're earning ${monthly:,.2f}/mo. Every dollar reinvested "
                f"brings you closer to financial freedom."
            ),
        })

    return insights


def get_insight_icon(insight_type: str) -> str:
    """Return an SVG icon path for the insight type."""
    icons = {
        "opportunity": "#22c55e",  # green
        "warning": "#f59e0b",      # amber
        "tip": "#667eea",          # brand purple
        "milestone": "#06b6d4",    # cyan
    }
    return icons.get(insight_type, "#667eea")
