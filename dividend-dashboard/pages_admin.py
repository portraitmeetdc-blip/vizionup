import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

from database import (
    is_admin, get_all_users, get_all_families, get_platform_stats,
    get_signup_activity, get_all_activity, get_portfolio_history,
    get_holdings, get_watchlist, get_portfolio_dividend_calendar,
    save_portfolio_snapshot, log_activity,
)
from market_data import get_stock_info, get_price_history, calculate_portfolio_income


# ── Theme Constants ───────────────────────────────────────────────
_BG = "#0e1117"
_CARD = "#161b22"
_BORDER = "#21262d"
_TEXT = "#e6edf3"
_MUTED = "#7d8590"
_ACCENT = "#667eea"

_COLOR_PALETTE = [
    "#667eea", "#764ba2", "#22c55e", "#06b6d4",
    "#f59e0b", "#f43f5e", "#8b5cf6", "#ec4899",
]


# ── Shared Helpers ────────────────────────────────────────────────

def _metric_card(label: str, value: str, delta: str = None, delta_positive: bool = True):
    """Render a styled metric card matching the app-wide design."""
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
    """Render a consistent section heading."""
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


def _chart_layout(**overrides) -> dict:
    """Return a base Plotly layout dict matching the dark theme."""
    layout = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color=_MUTED,
        margin=dict(t=20, b=20, l=20, r=20),
        xaxis=dict(gridcolor=_BORDER, zerolinecolor=_BORDER),
        yaxis=dict(gridcolor=_BORDER, zerolinecolor=_BORDER),
        legend=dict(font=dict(color=_MUTED)),
        hovermode="x unified",
    )
    layout.update(overrides)
    return layout


def _styled_table(df: pd.DataFrame):
    """Display a dataframe with consistent styling."""
    st.dataframe(df, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════
# 1. ADMIN DASHBOARD
# ══════════════════════════════════════════════════════════════════

def page_admin(user: dict, profile: dict):
    """Admin-only dashboard showing platform-wide analytics."""

    # ── Access control ────────────────────────────────────────────
    if not is_admin(user["id"]):
        st.markdown(
            '<p style="color:#f85149; font-weight:600;">Access denied.</p>',
            unsafe_allow_html=True,
        )
        return

    st.markdown('<p class="main-title">Platform Admin</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-text">System-wide metrics and user management</p>',
        unsafe_allow_html=True,
    )

    # ── Platform Overview ─────────────────────────────────────────
    _section("Platform Overview")

    with st.spinner("Loading platform stats..."):
        stats = get_platform_stats()

    total_users = stats.get("total_users", 0)
    total_families = stats.get("total_families", 0)
    total_value = stats.get("total_portfolio_value", 0.0)
    total_income = stats.get("total_annual_income", 0.0)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _metric_card("Total Users", f"{total_users:,}")
    with c2:
        _metric_card("Total Families", f"{total_families:,}")
    with c3:
        _metric_card("Platform Portfolio Value", f"${total_value:,.2f}")
    with c4:
        _metric_card("Platform Annual Income", f"${total_income:,.2f}")

    st.markdown("---")

    # ── Signup Trend (last 30 days) ───────────────────────────────
    _section("Signup Trend")

    signup_data = get_signup_activity(days=30)

    if signup_data:
        df_signups = pd.DataFrame(signup_data)
        # Expect columns: date, count
        df_signups["date"] = pd.to_datetime(df_signups["date"])
        df_signups = df_signups.sort_values("date")

        fig_signups = go.Figure()
        fig_signups.add_trace(go.Scatter(
            x=df_signups["date"],
            y=df_signups["count"],
            mode="lines+markers",
            name="New Signups",
            line=dict(color=_ACCENT, width=2.5),
            marker=dict(size=5, color=_ACCENT),
            fill="tozeroy",
            fillcolor="rgba(102,126,234,0.10)",
        ))
        fig_signups.update_layout(**_chart_layout(
            xaxis_title="Date",
            yaxis_title="New Users",
        ))
        st.plotly_chart(fig_signups, use_container_width=True)
    else:
        st.info("No signup data available for the last 30 days.")

    st.markdown("---")

    # ── All Users ─────────────────────────────────────────────────
    _section("All Users")

    all_users = get_all_users()

    if all_users:
        df_users = pd.DataFrame(all_users)
        display_cols = []
        col_map = {}

        # Build display table from available columns
        if "display_name" in df_users.columns:
            display_cols.append("display_name")
            col_map["display_name"] = "Name"
        elif "name" in df_users.columns:
            display_cols.append("name")
            col_map["name"] = "Name"

        if "email" in df_users.columns:
            display_cols.append("email")
            col_map["email"] = "Email"

        if "family_name" in df_users.columns:
            display_cols.append("family_name")
            col_map["family_name"] = "Family"

        if "role" in df_users.columns:
            display_cols.append("role")
            col_map["role"] = "Role"

        if "created_at" in df_users.columns:
            display_cols.append("created_at")
            col_map["created_at"] = "Signup Date"

        if display_cols:
            df_display = df_users[display_cols].copy()
            df_display.rename(columns=col_map, inplace=True)
            if "Signup Date" in df_display.columns:
                df_display["Signup Date"] = pd.to_datetime(
                    df_display["Signup Date"], errors="coerce"
                ).dt.strftime("%Y-%m-%d")
            _styled_table(df_display)
        else:
            _styled_table(df_users)
    else:
        st.info("No users registered on the platform yet.")

    st.markdown("---")

    # ── All Families ──────────────────────────────────────────────
    _section("All Families")

    all_families = get_all_families()

    if all_families:
        df_families = pd.DataFrame(all_families)
        display_cols_f = []
        col_map_f = {}

        if "name" in df_families.columns:
            display_cols_f.append("name")
            col_map_f["name"] = "Family Name"

        if "member_count" in df_families.columns:
            display_cols_f.append("member_count")
            col_map_f["member_count"] = "Members"

        if "combined_value" in df_families.columns:
            display_cols_f.append("combined_value")
            col_map_f["combined_value"] = "Combined Value"

        if display_cols_f:
            df_fam_display = df_families[display_cols_f].copy()
            df_fam_display.rename(columns=col_map_f, inplace=True)
            if "Combined Value" in df_fam_display.columns:
                df_fam_display["Combined Value"] = df_fam_display["Combined Value"].apply(
                    lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00"
                )
            _styled_table(df_fam_display)
        else:
            _styled_table(df_families)
    else:
        st.info("No families created yet.")

    st.markdown("---")

    # ── Activity Feed ─────────────────────────────────────────────
    _section("Activity Feed")

    activities = get_all_activity(limit=50)

    if activities:
        for act in activities:
            user_name = act.get("user_name", act.get("display_name", "Unknown"))
            action = act.get("action", act.get("description", ""))
            timestamp = act.get("created_at", act.get("timestamp", ""))
            if timestamp:
                try:
                    ts = pd.to_datetime(timestamp)
                    time_str = ts.strftime("%b %d, %Y %I:%M %p")
                except Exception:
                    time_str = str(timestamp)
            else:
                time_str = ""

            st.markdown(
                f'<div style="background:{_CARD}; border:1px solid {_BORDER}; '
                f'border-radius:8px; padding:0.7rem 1rem; margin-bottom:0.4rem;">'
                f'<span style="color:{_TEXT}; font-weight:600; font-size:0.88rem;">'
                f'{user_name}</span>'
                f'<span style="color:{_MUTED}; font-size:0.82rem; margin-left:0.5rem;">'
                f'{action}</span>'
                f'<span style="color:{_BORDER}; font-size:0.75rem; float:right; '
                f'margin-top:2px;">{time_str}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("No recent activity to display.")


# ══════════════════════════════════════════════════════════════════
# 2. ANALYTICS PAGE (per-user)
# ══════════════════════════════════════════════════════════════════

def page_analytics(user: dict, profile: dict):
    """Per-user live analytics -- portfolio performance, income growth, and benchmarks."""

    name = profile.get("display_name", user.get("name", ""))
    first_name = name.split()[0] if name else "Your"
    st.markdown(
        f'<p class="main-title">{first_name}\'s Analytics</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sub-text">Portfolio performance, income trends, and market benchmarks</p>',
        unsafe_allow_html=True,
    )

    holdings = get_holdings(user["id"])

    if not holdings:
        st.info("Add holdings to your portfolio to see analytics here.")
        return

    # ── Fetch live market data for holdings ───────────────────────
    with st.spinner("Loading market data..."):
        holdings_data = []
        for h in holdings:
            info = get_stock_info(h["ticker"])
            if "error" not in info:
                info["shares"] = h["shares"]
                info["avg_cost"] = h["avg_cost"]
                holdings_data.append(info)

    if not holdings_data:
        st.warning("Could not fetch market data. Please try again later.")
        return

    income = calculate_portfolio_income(holdings_data)

    # Save a snapshot for historical tracking
    try:
        save_portfolio_snapshot(
            user["id"],
            total_value=income["total_value"],
            total_income=income["total_annual_income"],
        )
    except Exception:
        pass  # Non-critical -- snapshots are best-effort

    # ── Portfolio Performance ─────────────────────────────────────
    _section("Portfolio Performance")

    history = get_portfolio_history(user["id"])

    if history:
        df_hist = pd.DataFrame(history)
        df_hist["date"] = pd.to_datetime(df_hist["date"])
        df_hist = df_hist.sort_values("date")

        fig_perf = go.Figure()
        fig_perf.add_trace(go.Scatter(
            x=df_hist["date"],
            y=df_hist["total_value"],
            mode="lines",
            name="Portfolio Value",
            line=dict(color=_ACCENT, width=2.5),
            fill="tozeroy",
            fillcolor="rgba(102,126,234,0.08)",
        ))
        fig_perf.update_layout(**_chart_layout(
            xaxis_title="Date",
            yaxis_title="Value ($)",
        ))
        st.plotly_chart(fig_perf, use_container_width=True)
    else:
        st.info(
            "Portfolio snapshots will appear here as data is collected over time. "
            "Check back after your next session."
        )

    st.markdown("---")

    # ── Income Growth ─────────────────────────────────────────────
    _section("Income Growth")

    if history:
        df_income_hist = pd.DataFrame(history)
        df_income_hist["date"] = pd.to_datetime(df_income_hist["date"])
        df_income_hist = df_income_hist.sort_values("date")

        # Group by month for a cleaner bar chart
        if "total_income" in df_income_hist.columns:
            df_income_hist["month"] = df_income_hist["date"].dt.to_period("M").astype(str)
            df_monthly = (
                df_income_hist.groupby("month")["total_income"]
                .last()
                .reset_index()
            )
            # Convert annual income to monthly for display
            df_monthly["monthly_income"] = df_monthly["total_income"] / 12

            fig_income = px.bar(
                df_monthly,
                x="month",
                y="monthly_income",
                labels={"month": "Month", "monthly_income": "Monthly Income ($)"},
                color_discrete_sequence=[_ACCENT],
            )
            fig_income.update_layout(**_chart_layout(
                xaxis_title="Month",
                yaxis_title="Monthly Income ($)",
            ))
            st.plotly_chart(fig_income, use_container_width=True)
        else:
            st.info("Income history data is not yet available.")
    else:
        # Show a projection based on current holdings as a fallback
        current_monthly = income["total_monthly_income"]
        months = pd.date_range(
            start=pd.Timestamp.now().normalize() - timedelta(days=30 * 5),
            periods=6,
            freq="MS",
        )
        fig_income_proj = px.bar(
            x=[m.strftime("%b %Y") for m in months],
            y=[current_monthly] * len(months),
            labels={"x": "Month", "y": "Est. Monthly Income ($)"},
            color_discrete_sequence=[_ACCENT],
        )
        fig_income_proj.update_layout(**_chart_layout(
            xaxis_title="Month",
            yaxis_title="Est. Monthly Income ($)",
        ))
        st.plotly_chart(fig_income_proj, use_container_width=True)
        st.caption("Projection based on current holdings. Historical data will populate over time.")

    st.markdown("---")

    # ── Holdings Breakdown ────────────────────────────────────────
    _section("Holdings Breakdown")

    df_details = pd.DataFrame(income["details"])

    if not df_details.empty:
        display_df = df_details[[
            "ticker", "name", "shares", "price", "avg_cost",
            "current_value", "gain_loss", "gain_loss_pct", "current_yield",
        ]].copy()

        display_df.columns = [
            "Ticker", "Name", "Shares", "Price", "Avg Cost",
            "Value", "Gain/Loss", "Gain/Loss %", "Yield %",
        ]

        display_df["Price"] = display_df["Price"].apply(lambda x: f"${x:,.2f}")
        display_df["Avg Cost"] = display_df["Avg Cost"].apply(lambda x: f"${x:,.2f}")
        display_df["Value"] = display_df["Value"].apply(lambda x: f"${x:,.2f}")
        display_df["Gain/Loss"] = display_df["Gain/Loss"].apply(
            lambda x: f"{'+'if x >= 0 else ''}${x:,.2f}"
        )
        display_df["Gain/Loss %"] = display_df["Gain/Loss %"].apply(
            lambda x: f"{x:+.2f}%"
        )
        display_df["Yield %"] = display_df["Yield %"].apply(lambda x: f"{x:.2f}%")
        display_df["Shares"] = display_df["Shares"].apply(lambda x: f"{x:,.4f}")

        _styled_table(display_df)
    else:
        st.info("No holdings data to display.")

    st.markdown("---")

    # ── Dividend Calendar ─────────────────────────────────────────
    _section("Dividend Calendar")

    with st.spinner("Loading dividend schedule..."):
        calendar_data = get_portfolio_dividend_calendar(user["id"])

    if calendar_data:
        df_cal = pd.DataFrame(calendar_data)

        # Normalize column names for the date field
        date_col = None
        for candidate in ["ex_date", "ex_dividend_date", "date"]:
            if candidate in df_cal.columns:
                date_col = candidate
                break

        if date_col:
            df_cal[date_col] = pd.to_datetime(df_cal[date_col], errors="coerce")
            df_cal = df_cal.dropna(subset=[date_col])
            df_cal = df_cal.sort_values(date_col)

            display_cols_cal = []
            rename_cal = {}

            if "ticker" in df_cal.columns:
                display_cols_cal.append("ticker")
                rename_cal["ticker"] = "Ticker"

            display_cols_cal.append(date_col)
            rename_cal[date_col] = "Ex-Dividend Date"

            if "amount" in df_cal.columns:
                display_cols_cal.append("amount")
                rename_cal["amount"] = "Amount / Share"
            elif "dividend_rate" in df_cal.columns:
                display_cols_cal.append("dividend_rate")
                rename_cal["dividend_rate"] = "Annual Rate"

            if "payment_date" in df_cal.columns:
                display_cols_cal.append("payment_date")
                rename_cal["payment_date"] = "Payment Date"

            df_cal_display = df_cal[display_cols_cal].copy()
            df_cal_display.rename(columns=rename_cal, inplace=True)
            df_cal_display["Ex-Dividend Date"] = df_cal_display["Ex-Dividend Date"].dt.strftime(
                "%b %d, %Y"
            )
            if "Payment Date" in df_cal_display.columns:
                df_cal_display["Payment Date"] = pd.to_datetime(
                    df_cal_display["Payment Date"], errors="coerce"
                ).dt.strftime("%b %d, %Y")
            if "Amount / Share" in df_cal_display.columns:
                df_cal_display["Amount / Share"] = df_cal_display["Amount / Share"].apply(
                    lambda x: f"${x:.4f}" if pd.notna(x) else "--"
                )

            _styled_table(df_cal_display)
        else:
            _styled_table(df_cal)
    else:
        # Fallback: build calendar from live stock info ex-dividend dates
        cal_rows = []
        for hd in holdings_data:
            ex_date_raw = hd.get("ex_dividend_date")
            if ex_date_raw:
                try:
                    if isinstance(ex_date_raw, (int, float)):
                        ex_date = datetime.fromtimestamp(ex_date_raw)
                    else:
                        ex_date = pd.to_datetime(ex_date_raw)
                    cal_rows.append({
                        "Ticker": hd["ticker"],
                        "Ex-Dividend Date": ex_date.strftime("%b %d, %Y"),
                        "Annual Rate": f"${hd.get('dividend_rate', 0):.2f}",
                        "Est. Quarterly": f"${hd.get('dividend_rate', 0) / 4:.4f}",
                    })
                except Exception:
                    continue

        if cal_rows:
            _styled_table(pd.DataFrame(cal_rows))
        else:
            st.info("No upcoming dividend dates found for your holdings.")

    st.markdown("---")

    # ── Benchmark Comparison ──────────────────────────────────────
    _section("Benchmark Comparison")

    with st.spinner("Calculating benchmark performance..."):
        # Determine portfolio return
        total_invested = income["total_invested"]
        total_value = income["total_value"]
        portfolio_return_pct = (
            ((total_value - total_invested) / total_invested * 100)
            if total_invested > 0 else 0.0
        )

        # Fetch S&P 500 (SPY) performance over the same period
        spy_hist = get_price_history("SPY", period="1y")

    if not spy_hist.empty and "Close" in spy_hist.columns:
        spy_start = spy_hist["Close"].iloc[0]
        spy_end = spy_hist["Close"].iloc[-1]
        spy_return_pct = ((spy_end - spy_start) / spy_start) * 100

        # Summary cards
        c1, c2 = st.columns(2)
        with c1:
            delta_str = f"{'+'if portfolio_return_pct >= 0 else ''}{portfolio_return_pct:.2f}%"
            _metric_card(
                "Your Portfolio Return",
                f"${total_value:,.2f}",
                delta=delta_str,
                delta_positive=portfolio_return_pct >= 0,
            )
        with c2:
            spy_delta = f"{'+'if spy_return_pct >= 0 else ''}{spy_return_pct:.2f}%"
            _metric_card(
                "S&P 500 Return (1Y)",
                f"${spy_end:,.2f}",
                delta=spy_delta,
                delta_positive=spy_return_pct >= 0,
            )

        # Outperformance note
        diff = portfolio_return_pct - spy_return_pct
        if diff > 0:
            st.markdown(
                f'<div style="background:{_CARD}; border:1px solid {_BORDER}; '
                f'border-left:3px solid #3fb950; border-radius:0 8px 8px 0; '
                f'padding:0.75rem 1rem; margin-top:0.5rem;">'
                f'<span style="color:#3fb950; font-weight:600;">Outperforming</span>'
                f'<span style="color:{_MUTED}; margin-left:0.5rem;">'
                f'Your portfolio is ahead of the S&P 500 by {diff:.2f}%</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        elif diff < 0:
            st.markdown(
                f'<div style="background:{_CARD}; border:1px solid {_BORDER}; '
                f'border-left:3px solid #f85149; border-radius:0 8px 8px 0; '
                f'padding:0.75rem 1rem; margin-top:0.5rem;">'
                f'<span style="color:#f85149; font-weight:600;">Trailing</span>'
                f'<span style="color:{_MUTED}; margin-left:0.5rem;">'
                f'Your portfolio is behind the S&P 500 by {abs(diff):.2f}%</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="background:{_CARD}; border:1px solid {_BORDER}; '
                f'border-left:3px solid {_ACCENT}; border-radius:0 8px 8px 0; '
                f'padding:0.75rem 1rem; margin-top:0.5rem;">'
                f'<span style="color:{_ACCENT}; font-weight:600;">On Par</span>'
                f'<span style="color:{_MUTED}; margin-left:0.5rem;">'
                f'Your portfolio is tracking with the S&P 500</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Normalized comparison chart (index both to 100)
        spy_norm = (spy_hist["Close"] / spy_start) * 100
        spy_dates = spy_hist.index

        fig_bench = go.Figure()
        fig_bench.add_trace(go.Scatter(
            x=spy_dates,
            y=spy_norm,
            mode="lines",
            name="S&P 500",
            line=dict(color=_MUTED, width=2, dash="dot"),
        ))

        # If we have portfolio history, normalize and overlay it
        if history:
            df_ph = pd.DataFrame(history)
            df_ph["date"] = pd.to_datetime(df_ph["date"])
            df_ph = df_ph.sort_values("date")
            if len(df_ph) > 1:
                port_start = df_ph["total_value"].iloc[0]
                if port_start > 0:
                    df_ph["normalized"] = (df_ph["total_value"] / port_start) * 100
                    fig_bench.add_trace(go.Scatter(
                        x=df_ph["date"],
                        y=df_ph["normalized"],
                        mode="lines",
                        name="Your Portfolio",
                        line=dict(color=_ACCENT, width=2.5),
                    ))

        # Reference line at 100
        fig_bench.add_hline(
            y=100,
            line_dash="dash",
            line_color=_BORDER,
            annotation_text="Baseline",
            annotation_font_color=_MUTED,
            annotation_font_size=10,
        )

        fig_bench.update_layout(**_chart_layout(
            xaxis_title="Date",
            yaxis_title="Indexed Performance (100 = start)",
        ))
        st.plotly_chart(fig_bench, use_container_width=True)

    else:
        st.warning("Could not fetch S&P 500 benchmark data. Please try again later.")

        # Still show portfolio return if possible
        if total_invested > 0:
            delta_str = f"{'+'if portfolio_return_pct >= 0 else ''}{portfolio_return_pct:.2f}%"
            _metric_card(
                "Your Portfolio Return",
                f"${total_value:,.2f}",
                delta=delta_str,
                delta_positive=portfolio_return_pct >= 0,
            )
