"""Admin dashboard and live analytics pages for Vizion Income."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

from database import (
    is_admin, get_all_users, get_all_families, get_platform_stats,
    get_signup_activity, get_all_activity, get_portfolio_history,
    get_holdings, get_watchlist, get_portfolio_dividend_calendar,
    save_portfolio_snapshot, log_activity, get_family_members,
    get_family_portfolio_history,
)
from market_data import get_stock_info, get_price_history, calculate_portfolio_income
from alerts import check_watchlist_alerts, check_portfolio_alerts, get_alert_color


CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#7d8590",
    margin=dict(t=20, b=20, l=20, r=20),
    xaxis=dict(gridcolor="#21262d"),
    yaxis=dict(gridcolor="#21262d"),
    legend=dict(font=dict(color="#7d8590")),
)


def _metric_card(label: str, value: str, delta: str = None, delta_positive: bool = True):
    delta_html = ""
    if delta:
        cls = "delta-pos" if delta_positive else "delta-neg"
        delta_html = f'<div class="{cls}">{delta}</div>'
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="label">{label}</div>'
        f'<div class="value">{value}</div>'
        f'{delta_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _section(title: str):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


# ── Admin Dashboard ────────────────────────────────────────────────

def page_admin(user: dict, profile: dict):
    """Platform admin dashboard — analytics, users, families, activity."""
    if not is_admin(user["id"]):
        st.warning("You do not have access to the admin dashboard.")
        return

    st.markdown('<p class="main-title">Admin Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-text">Platform-wide analytics and management</p>', unsafe_allow_html=True)

    # Platform overview
    with st.spinner("Loading platform stats..."):
        stats = get_platform_stats()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        _metric_card("Total Users", str(stats["total_users"]))
    with col2:
        _metric_card("Total Families", str(stats["total_families"]))
    with col3:
        _metric_card("Platform Value", f"${stats['total_portfolio_value']:,.2f}")
    with col4:
        _metric_card("Platform Income", f"${stats['total_portfolio_income']:,.2f}/yr")

    st.markdown("---")

    # Signup trend
    _section("Signup Trend (30 Days)")
    signups = get_signup_activity(30)
    if signups:
        df_signups = pd.DataFrame(signups)
        df_signups["date"] = pd.to_datetime(df_signups["created_at"]).dt.date
        daily = df_signups.groupby("date").size().reset_index(name="signups")
        fig = px.line(
            daily, x="date", y="signups",
            labels={"date": "Date", "signups": "New Users"},
            color_discrete_sequence=["#667eea"],
        )
        fig.update_layout(**CHART_LAYOUT)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No signups in the last 30 days.")

    st.markdown("---")

    # Two columns: users and families
    col_left, col_right = st.columns(2)

    with col_left:
        _section("All Users")
        users = get_all_users()
        if users:
            df_users = pd.DataFrame(users)
            display_cols = []
            if "display_name" in df_users.columns:
                display_cols.append("display_name")
            if "role" in df_users.columns:
                display_cols.append("role")
            if "is_admin" in df_users.columns:
                display_cols.append("is_admin")
            if "created_at" in df_users.columns:
                df_users["joined"] = pd.to_datetime(df_users["created_at"]).dt.strftime("%b %d, %Y")
                display_cols.append("joined")

            if display_cols:
                show_df = df_users[display_cols].copy()
                show_df.columns = [c.replace("_", " ").title() for c in display_cols]
                st.dataframe(show_df, use_container_width=True, hide_index=True)
        else:
            st.info("No users registered yet.")

    with col_right:
        _section("All Families")
        families = get_all_families()
        if families:
            family_rows = []
            for f in families:
                count = 0
                if isinstance(f.get("profiles"), list):
                    count = len(f["profiles"])
                elif isinstance(f.get("profiles"), dict):
                    count = f["profiles"].get("count", 0)
                family_rows.append({
                    "Family": f.get("name", "Unknown"),
                    "Members": count,
                    "Invite Code": f.get("invite_code", ""),
                    "Created": pd.to_datetime(f.get("created_at", "")).strftime("%b %d, %Y") if f.get("created_at") else "",
                })
            st.dataframe(pd.DataFrame(family_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No families created yet.")

    st.markdown("---")

    # Activity feed
    _section("Recent Activity")
    activity = get_all_activity(50)
    if activity:
        for a in activity[:20]:
            name = ""
            if isinstance(a.get("profiles"), dict):
                name = a["profiles"].get("display_name", "")
            ts = pd.to_datetime(a.get("created_at", "")).strftime("%b %d, %H:%M") if a.get("created_at") else ""
            action = a.get("action", "")
            st.markdown(
                f'<div style="padding:0.4rem 0;border-bottom:1px solid #21262d;font-size:0.85rem;">'
                f'<span style="color:#e6edf3;font-weight:500;">{name}</span> '
                f'<span style="color:#7d8590;">{action}</span> '
                f'<span style="color:#484f58;float:right;">{ts}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("No activity recorded yet.")


# ── Live Analytics Page ────────────────────────────────────────────

def page_analytics(user: dict, profile: dict):
    """Per-user live portfolio analytics with performance tracking."""
    name = profile.get("display_name", user.get("name", ""))
    first_name = name.split()[0] if name else "Your"
    st.markdown(f'<p class="main-title">{first_name}\'s Analytics</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-text">Live portfolio performance and market intelligence</p>', unsafe_allow_html=True)

    holdings = get_holdings(user["id"])

    if not holdings:
        st.info("Add holdings to your portfolio to see analytics here.")
        return

    # Fetch live data and save snapshot
    with st.spinner("Loading live market data..."):
        holdings_data = []
        for h in holdings:
            info = get_stock_info(h["ticker"])
            if "error" not in info:
                info["shares"] = h["shares"]
                info["avg_cost"] = h["avg_cost"]
                holdings_data.append(info)

    if not holdings_data:
        st.warning("Could not fetch market data. Please try again.")
        return

    income = calculate_portfolio_income(holdings_data)

    # Save today's snapshot
    try:
        save_portfolio_snapshot(
            user["id"],
            income["total_value"],
            income["total_annual_income"],
            len(holdings_data),
        )
    except Exception:
        pass

    # ── Portfolio Performance Over Time ──
    _section("Portfolio Performance")
    history = get_portfolio_history(user["id"], 90)

    if history and len(history) >= 2:
        df_hist = pd.DataFrame(history)
        df_hist["snapshot_date"] = pd.to_datetime(df_hist["snapshot_date"])

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_hist["snapshot_date"], y=df_hist["total_value"],
            mode="lines+markers", name="Portfolio Value",
            line=dict(color="#667eea", width=3),
            fill="tozeroy", fillcolor="rgba(102,126,234,0.1)",
        ))
        fig.update_layout(
            yaxis_title="Value ($)",
            hovermode="x unified",
            **CHART_LAYOUT,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Show period change
        first_val = df_hist.iloc[0]["total_value"]
        last_val = df_hist.iloc[-1]["total_value"]
        if first_val > 0:
            change = last_val - first_val
            change_pct = (change / first_val) * 100
            col1, col2, col3 = st.columns(3)
            with col1:
                _metric_card("Current Value", f"${last_val:,.2f}")
            with col2:
                _metric_card(
                    "Period Change",
                    f"${change:+,.2f}",
                    delta=f"{change_pct:+.1f}%",
                    delta_positive=change >= 0,
                )
            with col3:
                _metric_card("Annual Income", f"${income['total_annual_income']:,.2f}")
    else:
        # No history yet, just show current
        col1, col2, col3 = st.columns(3)
        with col1:
            _metric_card("Current Value", f"${income['total_value']:,.2f}")
        with col2:
            _metric_card("Annual Income", f"${income['total_annual_income']:,.2f}")
        with col3:
            _metric_card("Portfolio Yield", f"{income['portfolio_yield']:.2f}%")
        st.caption("Portfolio history will build over time as daily snapshots are recorded.")

    st.markdown("---")

    # ── Income Growth ──
    _section("Income Projection")
    months = pd.date_range(start=pd.Timestamp.now(), periods=12, freq="MS")
    monthly_income = income["total_monthly_income"]

    # Show growing income with 5% quarterly dividend growth assumption
    projected = []
    for i, m in enumerate(months):
        growth_factor = 1 + (0.05 * (i // 3) / 4)
        projected.append({"month": m.strftime("%b %Y"), "income": monthly_income * growth_factor})

    fig_income = px.bar(
        pd.DataFrame(projected), x="month", y="income",
        labels={"month": "Month", "income": "Projected Income ($)"},
        color_discrete_sequence=["#22c55e"],
    )
    fig_income.update_layout(**CHART_LAYOUT)
    st.plotly_chart(fig_income, use_container_width=True)

    st.markdown("---")

    # ── Holdings Breakdown ──
    _section("Holdings Detail")
    df_details = pd.DataFrame(income["details"])
    if not df_details.empty:
        display_df = df_details[[
            "ticker", "name", "shares", "price", "avg_cost",
            "current_yield", "monthly_income", "gain_loss_pct"
        ]].copy()
        display_df.columns = [
            "Ticker", "Name", "Shares", "Price", "Avg Cost",
            "Yield %", "Monthly $", "Gain/Loss %"
        ]
        display_df["Price"] = display_df["Price"].apply(lambda x: f"${x:,.2f}")
        display_df["Avg Cost"] = display_df["Avg Cost"].apply(lambda x: f"${x:,.2f}")
        display_df["Yield %"] = display_df["Yield %"].apply(lambda x: f"{x:.2f}%")
        display_df["Monthly $"] = display_df["Monthly $"].apply(lambda x: f"${x:,.2f}")
        display_df["Gain/Loss %"] = display_df["Gain/Loss %"].apply(lambda x: f"{x:+.1f}%")
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Dividend Calendar ──
    _section("Upcoming Dividends")
    with st.spinner("Checking dividend calendar..."):
        calendar = get_portfolio_dividend_calendar(user["id"])

    if calendar:
        total_upcoming = sum(c["est_payout"] for c in calendar)
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="label">Upcoming Dividend Payments</div>'
            f'<div class="value">${total_upcoming:,.2f}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        cal_df = pd.DataFrame(calendar)
        cal_df = cal_df[["ticker", "ex_date", "shares", "dividend_rate", "est_payout"]]
        cal_df.columns = ["Ticker", "Ex-Dividend Date", "Shares", "Annual Rate", "Est. Payout"]
        cal_df["Annual Rate"] = cal_df["Annual Rate"].apply(lambda x: f"${x:.2f}")
        cal_df["Est. Payout"] = cal_df["Est. Payout"].apply(lambda x: f"${x:.2f}")
        st.dataframe(cal_df, use_container_width=True, hide_index=True)
    else:
        st.info("No upcoming dividend dates found for your holdings.")

    st.markdown("---")

    # ── Benchmark Comparison ──
    _section("vs. S&P 500")
    try:
        spy_hist = get_price_history("SPY", "3mo")
        if not spy_hist.empty and history and len(history) >= 2:
            spy_start = spy_hist["Close"].iloc[0]
            spy_end = spy_hist["Close"].iloc[-1]
            spy_return = ((spy_end - spy_start) / spy_start) * 100

            df_hist = pd.DataFrame(history)
            port_start = df_hist.iloc[0]["total_value"]
            port_end = df_hist.iloc[-1]["total_value"]
            port_return = ((port_end - port_start) / port_start) * 100 if port_start > 0 else 0

            col1, col2 = st.columns(2)
            with col1:
                _metric_card(
                    "Your Return (3mo)",
                    f"{port_return:+.1f}%",
                    delta_positive=port_return >= 0,
                )
            with col2:
                _metric_card(
                    "S&P 500 Return (3mo)",
                    f"{spy_return:+.1f}%",
                    delta_positive=spy_return >= 0,
                )

            beat = port_return - spy_return
            if beat > 0:
                st.markdown(
                    f'<div style="color:#22c55e;font-size:0.9rem;margin-top:0.5rem;">'
                    f'You are outperforming the S&P 500 by {beat:.1f} percentage points.</div>',
                    unsafe_allow_html=True,
                )
            elif beat < 0:
                st.markdown(
                    f'<div style="color:#7d8590;font-size:0.9rem;margin-top:0.5rem;">'
                    f'The S&P 500 leads by {abs(beat):.1f} percentage points. '
                    f'Dividend income helps close the gap.</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Benchmark comparison will be available once you have a few days of portfolio history.")
    except Exception:
        st.caption("Could not load benchmark data.")

    st.markdown("---")

    # ── Alerts ──
    _section("Active Alerts")
    watchlist = get_watchlist(user["id"])
    watchlist_alerts = check_watchlist_alerts(watchlist)
    portfolio_alerts = check_portfolio_alerts(holdings_data)
    all_alerts = watchlist_alerts + portfolio_alerts

    if all_alerts:
        for a in all_alerts:
            color = get_alert_color(a.get("type", ""))
            st.markdown(
                f'<div style="background:#161b22;border-left:3px solid {color};'
                f'border-radius:0 8px 8px 0;padding:0.75rem 1rem;margin-bottom:0.5rem;">'
                f'<div style="color:#e6edf3;font-weight:600;font-size:0.9rem;">'
                f'{a.get("ticker", "")}</div>'
                f'<div style="color:#7d8590;font-size:0.82rem;">{a.get("message", "")}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div style="color:#7d8590;font-size:0.85rem;">No active alerts. All positions are within normal ranges.</div>',
            unsafe_allow_html=True,
        )
