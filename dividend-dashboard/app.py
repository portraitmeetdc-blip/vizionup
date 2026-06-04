import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import base64
import os

from config import APP_NAME, APP_TAGLINE
from auth import check_auth, get_current_user, render_auth_page, sign_out
from database import (
    get_profile, update_profile, get_holdings, add_holding, remove_holding,
    get_watchlist, add_to_watchlist, remove_from_watchlist,
    get_family_members, get_family_holdings, get_family_invite_code,
    setup_family, join_family_by_code, is_onboarded, get_family,
)
from market_data import (
    get_stock_info, get_dividend_history, get_price_history,
    screen_dividend_stocks, calculate_portfolio_income, project_growth,
)
from insights import generate_insights, get_insight_icon


# ── Page Config ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Vizion Income",
    page_icon="V",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── PWA Support ────────────────────────────────────────────────────
def inject_pwa():
    """Make the app installable as a Progressive Web App on phones and desktops."""
    st.markdown("""
    <link rel="manifest" href="data:application/json;base64,eyJuYW1lIjoiVml6aW9uIEluY29tZSIsInNob3J0X25hbWUiOiJWaXppb24iLCJzdGFydF91cmwiOiIuIiwiZGlzcGxheSI6InN0YW5kYWxvbmUiLCJiYWNrZ3JvdW5kX2NvbG9yIjoiIzBlMTExNyIsInRoZW1lX2NvbG9yIjoiIzY2N2VlYSIsImRlc2NyaXB0aW9uIjoiQnVpbGRpbmcgZ2VuZXJhdGlvbmFsIHdlYWx0aCwgdG9nZXRoZXIuIiwiaWNvbnMiOlt7InNyYyI6ImRhdGE6aW1hZ2Uvc3ZnK3htbCw8c3ZnIHhtbG5zPSdodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2Zycgdmlld0JveD0nMCAwIDEwMCAxMDAnPjxyZWN0IHdpZHRoPScxMDAnIGhlaWdodD0nMTAwJyByeD0nMjAnIGZpbGw9JyM2NjdlZWEnLz48dGV4dCB4PSc1MCcgeT0nNjgnIGZvbnQtc2l6ZT0nNTUnIGZvbnQtd2VpZ2h0PSc3MDAnIGZpbGw9J3doaXRlJyB0ZXh0LWFuY2hvcj0nbWlkZGxlJyBmb250LWZhbWlseT0nc2Fucy1zZXJpZic+Vjwvc3ZnPiIsInNpemVzIjoiNTEyeDUxMiIsInR5cGUiOiJpbWFnZS9zdmcreG1sIn1dfQ==" />
    <meta name="mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
    <meta name="apple-mobile-web-app-title" content="Vizion Income" />
    <meta name="theme-color" content="#667eea" />
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
    <link rel="apple-touch-icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%23667eea'/><text x='50' y='68' font-size='55' font-weight='700' fill='white' text-anchor='middle' font-family='sans-serif'>V</text></svg>" />
    """, unsafe_allow_html=True)

    # Register service worker for offline caching
    st.markdown("""
    <script>
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register(
            URL.createObjectURL(new Blob([`
                self.addEventListener('fetch', function(event) {
                    event.respondWith(
                        caches.match(event.request).then(function(response) {
                            return response || fetch(event.request);
                        })
                    );
                });
            `], {type: 'application/javascript'}))
        ).catch(function() {});
    }
    </script>
    """, unsafe_allow_html=True)


# ── Global Styles ──────────────────────────────────────────────────
def inject_styles():
    st.markdown("""
    <style>
        /* Typography */
        .main-title {
            font-size: 1.75rem;
            font-weight: 700;
            color: #e6edf3;
            letter-spacing: -0.5px;
            margin-bottom: 0.1rem;
        }
        .sub-text {
            font-size: 0.9rem;
            color: #7d8590;
            margin-top: 0;
            margin-bottom: 1rem;
        }
        .section-title {
            font-size: 1.15rem;
            font-weight: 600;
            color: #e6edf3;
            margin-bottom: 0.75rem;
            padding-bottom: 0.4rem;
            border-bottom: 1px solid #21262d;
        }

        /* Cards */
        .metric-card {
            background: #161b22;
            border: 1px solid #21262d;
            border-radius: 10px;
            padding: 1.1rem 1.25rem;
            margin-bottom: 0.5rem;
        }
        .metric-card .label {
            font-size: 0.75rem;
            color: #7d8590;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.3rem;
        }
        .metric-card .value {
            font-size: 1.5rem;
            font-weight: 700;
            color: #e6edf3;
        }
        .metric-card .delta-pos { color: #3fb950; font-size: 0.85rem; }
        .metric-card .delta-neg { color: #f85149; font-size: 0.85rem; }

        /* Insight cards */
        .insight-card {
            background: #161b22;
            border-left: 3px solid;
            border-radius: 0 8px 8px 0;
            padding: 0.85rem 1rem;
            margin-bottom: 0.6rem;
        }
        .insight-card .insight-title {
            font-weight: 600;
            font-size: 0.9rem;
            color: #e6edf3;
            margin-bottom: 0.2rem;
        }
        .insight-card .insight-detail {
            font-size: 0.82rem;
            color: #7d8590;
            line-height: 1.45;
        }

        /* Family member card */
        .member-card {
            background: #161b22;
            border: 1px solid #21262d;
            border-radius: 10px;
            padding: 1.25rem;
            text-align: center;
        }
        .member-card .member-name {
            font-size: 1rem;
            font-weight: 600;
            color: #e6edf3;
            margin-bottom: 0.15rem;
        }
        .member-card .member-role {
            font-size: 0.8rem;
            color: #7d8590;
            margin-bottom: 0.75rem;
        }
        .member-card .member-stat {
            font-size: 0.75rem;
            color: #7d8590;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }
        .member-card .member-value {
            font-size: 1.15rem;
            font-weight: 600;
            color: #e6edf3;
        }

        /* Navigation polish */
        section[data-testid="stSidebar"] {
            background: #0d1117;
            border-right: 1px solid #21262d;
        }
        .sidebar-brand {
            padding: 0.5rem 0 1rem 0;
            text-align: center;
        }
        .sidebar-brand h2 {
            font-size: 1.3rem;
            font-weight: 700;
            color: #e6edf3;
            margin: 0;
        }
        .sidebar-brand p {
            font-size: 0.75rem;
            color: #7d8590;
            margin: 0.15rem 0 0 0;
        }
        .sidebar-user {
            background: #161b22;
            border: 1px solid #21262d;
            border-radius: 8px;
            padding: 0.75rem 1rem;
            margin-bottom: 0.75rem;
        }
        .sidebar-user .user-name {
            font-weight: 600;
            color: #e6edf3;
            font-size: 0.9rem;
        }
        .sidebar-user .user-email {
            color: #7d8590;
            font-size: 0.75rem;
        }

        /* Tables */
        .stDataFrame { border-radius: 8px; overflow: hidden; }

        /* Hide Streamlit branding */
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        header { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────
def render_sidebar(user: dict, profile: dict):
    """Render the sidebar with navigation and user info."""
    # Brand
    logo_path = os.path.join(os.path.dirname(__file__), "logo.svg")
    if os.path.exists(logo_path):
        with open(logo_path, "r") as f:
            svg = f.read()
        b64 = base64.b64encode(svg.encode()).decode()
        st.sidebar.markdown(
            f'<div class="sidebar-brand">'
            f'<img src="data:image/svg+xml;base64,{b64}" style="width:100%;max-width:220px;">'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.markdown(
            f'<div class="sidebar-brand"><h2>{APP_NAME}</h2>'
            f'<p>{APP_TAGLINE}</p></div>',
            unsafe_allow_html=True,
        )

    # User info
    name = profile.get("display_name", user.get("name", "User"))
    email = user.get("email", "")
    st.sidebar.markdown(
        f'<div class="sidebar-user">'
        f'<div class="user-name">{name}</div>'
        f'<div class="user-email">{email}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("---")

    # Navigation
    page = st.sidebar.radio(
        "Navigate",
        ["Dashboard", "Family Overview", "My Portfolio", "Stock Screener", "Watchlist", "Growth Projector", "Settings"],
        label_visibility="collapsed",
    )

    # Sign out at bottom
    st.sidebar.markdown("---")
    if st.sidebar.button("Sign Out", use_container_width=True):
        sign_out()
        st.rerun()

    return page


# ── Metric Card Helper ─────────────────────────────────────────────
def metric_card(label: str, value: str, delta: str = None, delta_positive: bool = True):
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


# ── Onboarding Flow ───────────────────────────────────────────────
def render_onboarding(user: dict):
    """First-time user setup: create or join a family."""
    inject_styles()

    st.markdown(f'<p class="main-title">Welcome to {APP_NAME}</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-text">Let\'s get you set up. Create a new family group or join an existing one.</p>', unsafe_allow_html=True)

    tab_create, tab_join = st.tabs(["Create a Family", "Join a Family"])

    with tab_create:
        with st.form("create_family"):
            family_name = st.text_input(
                "Family Name",
                placeholder="e.g. Edwards Family",
                value=f"{user.get('name', '').split()[-1] if user.get('name') else ''} Family",
            )
            role = st.text_input("Your Role (optional)", placeholder="e.g. Dad, Mom, Son")
            submitted = st.form_submit_button("Create Family", type="primary", use_container_width=True)

        if submitted and family_name:
            family = setup_family(user["id"], family_name.strip(), role.strip())
            if family:
                st.success(f"Family \"{family_name}\" created.")
                invite = get_family_invite_code(family["id"])
                st.info(f"Share this invite code with your family: **{invite}**")
                st.rerun()

    with tab_join:
        with st.form("join_family"):
            code = st.text_input("Invite Code", placeholder="Enter the code from a family member")
            role = st.text_input("Your Role (optional)", placeholder="e.g. Son, Daughter")
            submitted = st.form_submit_button("Join Family", type="primary", use_container_width=True)

        if submitted and code:
            success = join_family_by_code(user["id"], code.strip())
            if success:
                if role:
                    update_profile(user["id"], role=role.strip())
                st.success("You've joined the family.")
                st.rerun()
            else:
                st.error("Invalid invite code. Check with your family member and try again.")


# ── Dashboard Page ─────────────────────────────────────────────────
def page_dashboard(user: dict, profile: dict):
    name = profile.get("display_name", user.get("name", ""))
    first_name = name.split()[0] if name else "there"
    st.markdown(f'<p class="main-title">{first_name}\'s Dashboard</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub-text">Your passive income at a glance</p>', unsafe_allow_html=True)

    holdings = get_holdings(user["id"])

    if not holdings:
        st.info("Start by adding stocks to your portfolio in **My Portfolio**.")
        st.markdown("""
        **Quick start:**
        1. Go to **My Portfolio** to add your first stock
        2. Use **Stock Screener** to find high-yield dividend stocks
        3. Add interesting finds to your **Watchlist**
        4. Check **Growth Projector** to see your future income
        """)
        return

    # Fetch live data
    with st.spinner("Loading market data..."):
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

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        delta = f"{'+'if income['total_gain_loss']>=0 else ''}{income['total_gain_loss']:,.2f}"
        metric_card("Portfolio Value", f"${income['total_value']:,.2f}",
                     delta=delta, delta_positive=income['total_gain_loss'] >= 0)
    with col2:
        metric_card("Monthly Income", f"${income['total_monthly_income']:,.2f}")
    with col3:
        metric_card("Annual Income", f"${income['total_annual_income']:,.2f}")
    with col4:
        metric_card("Portfolio Yield", f"{income['portfolio_yield']:.2f}%")

    st.markdown("---")

    # Charts and holdings
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown('<div class="section-title">Income Breakdown</div>', unsafe_allow_html=True)
        df_details = pd.DataFrame(income["details"])
        if not df_details.empty and df_details["annual_income"].sum() > 0:
            fig_pie = px.pie(
                df_details[df_details["annual_income"] > 0],
                values="annual_income", names="ticker", hole=0.45,
                color_discrete_sequence=["#667eea", "#764ba2", "#22c55e",
                                         "#06b6d4", "#f59e0b", "#f43f5e",
                                         "#8b5cf6", "#ec4899"],
            )
            fig_pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#7d8590",
                margin=dict(t=10, b=10, l=10, r=10),
                showlegend=True,
                legend=dict(font=dict(size=11)),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    with col_right:
        st.markdown('<div class="section-title">Holdings</div>', unsafe_allow_html=True)
        if not df_details.empty:
            display_df = df_details[["ticker", "name", "shares", "price",
                                     "current_yield", "monthly_income", "gain_loss_pct"]].copy()
            display_df.columns = ["Ticker", "Name", "Shares", "Price",
                                  "Yield %", "Monthly $", "Gain/Loss %"]
            display_df["Price"] = display_df["Price"].apply(lambda x: f"${x:,.2f}")
            display_df["Yield %"] = display_df["Yield %"].apply(lambda x: f"{x:.2f}%")
            display_df["Monthly $"] = display_df["Monthly $"].apply(lambda x: f"${x:,.2f}")
            display_df["Gain/Loss %"] = display_df["Gain/Loss %"].apply(lambda x: f"{x:+.1f}%")
            st.dataframe(display_df, use_container_width=True, hide_index=True)

    # 12-month projection
    st.markdown("---")
    st.markdown('<div class="section-title">12-Month Income Projection</div>', unsafe_allow_html=True)
    months = pd.date_range(start=pd.Timestamp.now(), periods=12, freq="MS")
    fig_bar = px.bar(
        x=[m.strftime("%b %Y") for m in months],
        y=[income["total_monthly_income"]] * 12,
        labels={"x": "Month", "y": "Projected Income ($)"},
        color_discrete_sequence=["#667eea"],
    )
    fig_bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#7d8590",
        margin=dict(t=10, b=20),
        xaxis=dict(gridcolor="#21262d"),
        yaxis=dict(gridcolor="#21262d"),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # Insights panel
    st.markdown("---")
    st.markdown('<div class="section-title">Insights</div>', unsafe_allow_html=True)
    watchlist = get_watchlist(user["id"])
    # Enrich holdings_data with extra fields for insights
    enriched = []
    for h in holdings_data:
        h_copy = dict(h)
        h_copy["cost_basis"] = h["shares"] * h["avg_cost"]
        h_copy["current_value"] = h["shares"] * h.get("price", 0)
        h_copy["gain_loss_pct"] = (
            (h_copy["current_value"] - h_copy["cost_basis"]) / h_copy["cost_basis"] * 100
            if h_copy["cost_basis"] > 0 else 0
        )
        h_copy["annual_income"] = h["shares"] * h.get("dividend_rate", 0)
        h_copy["current_yield"] = h.get("dividend_yield", 0) * 100
        enriched.append(h_copy)

    tips = generate_insights(enriched, watchlist)
    for tip in tips[:5]:
        color = get_insight_icon(tip["type"])
        st.markdown(
            f'<div class="insight-card" style="border-left-color: {color};">'
            f'<div class="insight-title">{tip["title"]}</div>'
            f'<div class="insight-detail">{tip["detail"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ── Family Overview Page ───────────────────────────────────────────
def page_family(user: dict, profile: dict):
    family_id = profile.get("family_id")
    if not family_id:
        st.info("You're not part of a family group yet. Go to Settings to create or join one.")
        return

    family = get_family(family_id)
    family_name = family.get("name", "Your Family")
    st.markdown(f'<p class="main-title">{family_name}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub-text">See how the whole family is building wealth together</p>', unsafe_allow_html=True)

    family_data = get_family_holdings(family_id)

    if not family_data:
        st.info("No family members found.")
        return

    # Aggregate family stats
    family_total_value = 0
    family_total_income = 0
    member_summaries = []

    for uid, data in family_data.items():
        member_profile = data["profile"]
        member_holdings = data["holdings"]

        if not member_holdings:
            member_summaries.append({
                "name": member_profile.get("display_name", "Member"),
                "role": member_profile.get("role", ""),
                "value": 0,
                "income": 0,
                "holdings_count": 0,
            })
            continue

        # Fetch live prices for this member's holdings
        member_data = []
        for h in member_holdings:
            info = get_stock_info(h["ticker"])
            if "error" not in info:
                info["shares"] = h["shares"]
                info["avg_cost"] = h["avg_cost"]
                member_data.append(info)

        if member_data:
            inc = calculate_portfolio_income(member_data)
            family_total_value += inc["total_value"]
            family_total_income += inc["total_annual_income"]
            member_summaries.append({
                "name": member_profile.get("display_name", "Member"),
                "role": member_profile.get("role", ""),
                "value": inc["total_value"],
                "income": inc["total_annual_income"],
                "holdings_count": len(member_data),
            })
        else:
            member_summaries.append({
                "name": member_profile.get("display_name", "Member"),
                "role": member_profile.get("role", ""),
                "value": 0,
                "income": 0,
                "holdings_count": len(member_holdings),
            })

    # Family totals
    col1, col2, col3 = st.columns(3)
    with col1:
        metric_card("Family Portfolio Value", f"${family_total_value:,.2f}")
    with col2:
        metric_card("Family Annual Income", f"${family_total_income:,.2f}")
    with col3:
        metric_card("Family Monthly Income", f"${family_total_income/12:,.2f}")

    st.markdown("---")

    # Member cards
    st.markdown('<div class="section-title">Members</div>', unsafe_allow_html=True)
    cols = st.columns(len(member_summaries)) if member_summaries else []
    for i, m in enumerate(member_summaries):
        with cols[i]:
            st.markdown(
                f'<div class="member-card">'
                f'<div class="member-name">{m["name"]}</div>'
                f'<div class="member-role">{m["role"]}</div>'
                f'<div class="member-stat">Portfolio Value</div>'
                f'<div class="member-value">${m["value"]:,.2f}</div>'
                f'<br>'
                f'<div class="member-stat">Annual Income</div>'
                f'<div class="member-value">${m["income"]:,.2f}</div>'
                f'<br>'
                f'<div class="member-stat">Holdings</div>'
                f'<div class="member-value">{m["holdings_count"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # Family allocation chart
    if family_total_value > 0:
        st.markdown("---")
        st.markdown('<div class="section-title">Family Allocation</div>', unsafe_allow_html=True)
        allocation_df = pd.DataFrame([
            {"Member": m["name"], "Value": m["value"]}
            for m in member_summaries if m["value"] > 0
        ])
        if not allocation_df.empty:
            fig = px.pie(
                allocation_df, values="Value", names="Member", hole=0.45,
                color_discrete_sequence=["#667eea", "#764ba2", "#22c55e", "#06b6d4"],
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#7d8590",
                margin=dict(t=10, b=10, l=10, r=10),
            )
            st.plotly_chart(fig, use_container_width=True)


# ── Portfolio Page ─────────────────────────────────────────────────
def page_portfolio(user: dict, profile: dict):
    name = profile.get("display_name", user.get("name", ""))
    first_name = name.split()[0] if name else "Your"
    st.markdown(f'<p class="main-title">{first_name}\'s Portfolio</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-text">Add and manage your dividend stock holdings</p>', unsafe_allow_html=True)

    # Add new holding
    with st.expander("Add New Holding", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            new_ticker = st.text_input("Stock Ticker", placeholder="e.g. SCHD").upper()
        with col2:
            new_shares = st.number_input("Number of Shares", min_value=0.0, step=0.01, format="%.4f")
        with col3:
            new_cost = st.number_input("Average Cost per Share ($)", min_value=0.0, step=0.01, format="%.2f")
        new_notes = st.text_input("Notes (optional)", placeholder="e.g. DRIP enabled")

        if st.button("Add to Portfolio", type="primary"):
            if new_ticker and new_shares > 0 and new_cost > 0:
                info = get_stock_info(new_ticker)
                if "error" in info:
                    st.error(f"Could not find ticker '{new_ticker}'. Please check the symbol.")
                else:
                    add_holding(user["id"], new_ticker, new_shares, new_cost, new_notes)
                    st.success(f"Added {new_shares} shares of {new_ticker} ({info.get('name', '')})")
                    st.rerun()
            else:
                st.warning("Please fill in ticker, shares, and cost.")

    # Current holdings
    st.markdown("---")
    holdings = get_holdings(user["id"])

    if not holdings:
        st.info("No holdings yet. Add your first stock above.")
        return

    for h in holdings:
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([2, 1.5, 1.5, 1.5, 0.8])
            with col1:
                st.markdown(f"**{h['ticker']}**")
                if h.get("notes"):
                    st.caption(h["notes"])
            with col2:
                st.metric("Shares", f"{h['shares']:.4f}")
            with col3:
                st.metric("Avg Cost", f"${h['avg_cost']:.2f}")
            with col4:
                st.metric("Cost Basis", f"${h['shares'] * h['avg_cost']:,.2f}")
            with col5:
                if st.button("Remove", key=f"del_{h['ticker']}", help=f"Remove {h['ticker']}"):
                    remove_holding(user["id"], h["ticker"])
                    st.rerun()
            st.markdown("---")


# ── Stock Screener Page ────────────────────────────────────────────
def page_screener(user: dict, profile: dict):
    st.markdown('<p class="main-title">Stock Screener</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-text">Find quality dividend stocks that match your income goals</p>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        min_yield = st.slider("Minimum Dividend Yield (%)", 1.0, 15.0, 3.0, 0.5) / 100
    with col2:
        min_cap = st.select_slider(
            "Minimum Market Cap",
            options=[1e8, 5e8, 1e9, 5e9, 1e10, 5e10, 1e11],
            value=1e9,
            format_func=lambda x: f"${x/1e9:.1f}B" if x >= 1e9 else f"${x/1e6:.0f}M",
        )
    with col3:
        max_payout = st.slider("Maximum Payout Ratio (%)", 10, 100, 80, 5) / 100

    if st.button("Run Screener", type="primary"):
        with st.spinner("Screening dividend stocks..."):
            results = screen_dividend_stocks(min_yield, min_cap, max_payout)

        if results:
            st.success(f"Found {len(results)} stocks matching your criteria")
            df = pd.DataFrame(results)
            display_df = df[["ticker", "name", "price", "dividend_rate",
                            "dividend_yield", "payout_ratio", "sector"]].copy()
            display_df.columns = ["Ticker", "Name", "Price", "Annual Div",
                                  "Yield", "Payout Ratio", "Sector"]
            display_df["Price"] = display_df["Price"].apply(lambda x: f"${x:,.2f}")
            display_df["Annual Div"] = display_df["Annual Div"].apply(lambda x: f"${x:.2f}")
            display_df["Yield"] = display_df["Yield"].apply(lambda x: f"{x*100:.2f}%")
            display_df["Payout Ratio"] = display_df["Payout Ratio"].apply(lambda x: f"{x*100:.1f}%")
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            # Quick add to watchlist
            st.markdown("---")
            st.markdown('<div class="section-title">Add to Watchlist</div>', unsafe_allow_html=True)
            tickers = [r["ticker"] for r in results]
            selected = st.multiselect("Select stocks to watch", tickers)
            if st.button("Add Selected to Watchlist"):
                for t in selected:
                    stock = next(r for r in results if r["ticker"] == t)
                    add_to_watchlist(user["id"], t, target_price=stock["price"] * 0.9)
                st.success(f"Added {len(selected)} stocks to your watchlist")
        else:
            st.warning("No stocks matched your criteria. Try adjusting the filters.")

    # Individual lookup
    st.markdown("---")
    st.markdown('<div class="section-title">Stock Lookup</div>', unsafe_allow_html=True)
    lookup = st.text_input("Enter a ticker", placeholder="e.g. O, SCHD, JEPI")
    if lookup:
        with st.spinner(f"Looking up {lookup.upper()}..."):
            info = get_stock_info(lookup)
            divs = get_dividend_history(lookup)

        if "error" not in info:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                metric_card("Price", f"${info['price']:,.2f}")
            with col2:
                metric_card("Dividend Yield", f"{info['dividend_yield']*100:.2f}%")
            with col3:
                metric_card("Annual Dividend", f"${info['dividend_rate']:.2f}")
            with col4:
                metric_card("Payout Ratio", f"{info['payout_ratio']*100:.1f}%")

            st.markdown(
                f"**{info['name']}** — Sector: {info['sector']} / "
                f"P/E: {info['pe_ratio']:.1f} / Beta: {info['beta']:.2f}"
            )

            if not divs.empty:
                st.markdown('<div class="section-title">Dividend History</div>', unsafe_allow_html=True)
                fig = px.bar(
                    divs.head(20), x="Date", y="Dividend",
                    labels={"Dividend": "Dividend ($)"},
                    color_discrete_sequence=["#667eea"],
                )
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#7d8590",
                    margin=dict(t=10, b=20),
                    xaxis=dict(gridcolor="#21262d"),
                    yaxis=dict(gridcolor="#21262d"),
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.error(f"Could not find data for '{lookup.upper()}'")


# ── Watchlist Page ─────────────────────────────────────────────────
def page_watchlist(user: dict, profile: dict):
    st.markdown('<p class="main-title">Watchlist</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-text">Track stocks you\'re interested in buying</p>', unsafe_allow_html=True)

    with st.expander("Add to Watchlist"):
        col1, col2 = st.columns(2)
        with col1:
            watch_ticker = st.text_input("Ticker", placeholder="e.g. SCHD").upper()
        with col2:
            watch_target = st.number_input("Target Buy Price ($)", min_value=0.0, step=0.01, format="%.2f")
        watch_notes = st.text_input("Notes", placeholder="e.g. Wait for next ex-div date")
        if st.button("Add to Watchlist", type="primary"):
            if watch_ticker:
                add_to_watchlist(
                    user["id"], watch_ticker,
                    watch_target if watch_target > 0 else None, watch_notes,
                )
                st.success(f"Added {watch_ticker} to watchlist")
                st.rerun()

    watchlist = get_watchlist(user["id"])

    if not watchlist:
        st.info("Your watchlist is empty. Add stocks from the screener or manually above.")
        return

    with st.spinner("Fetching current prices..."):
        for item in watchlist:
            info = get_stock_info(item["ticker"])
            with st.container():
                col1, col2, col3, col4, col5, col6 = st.columns([1.5, 1.5, 1.5, 1.5, 2, 0.5])
                with col1:
                    st.markdown(f"**{item['ticker']}**")
                    if "error" not in info:
                        st.caption(info.get("name", ""))
                with col2:
                    if "error" not in info:
                        st.metric("Current Price", f"${info['price']:,.2f}")
                with col3:
                    if item.get("target_price"):
                        st.metric("Target Price", f"${item['target_price']:,.2f}")
                        if "error" not in info and info["price"] <= item["target_price"]:
                            st.success("BUY ZONE")
                with col4:
                    if "error" not in info:
                        st.metric("Yield", f"{info['dividend_yield']*100:.2f}%")
                with col5:
                    if item.get("notes"):
                        st.caption(item["notes"])
                with col6:
                    if st.button("Remove", key=f"wdel_{item['ticker']}"):
                        remove_from_watchlist(user["id"], item["ticker"])
                        st.rerun()
                st.markdown("---")


# ── Growth Projector Page ──────────────────────────────────────────
def page_projector(user: dict, profile: dict):
    st.markdown('<p class="main-title">Growth Projector</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-text">See how your passive income grows with dividend reinvestment</p>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        initial = st.number_input("Starting Investment ($)", value=5000.0, step=500.0, format="%.0f")
    with col2:
        monthly = st.number_input("Monthly Contribution ($)", value=200.0, step=50.0, format="%.0f")
    with col3:
        avg_yield = st.slider("Average Dividend Yield (%)", 1.0, 15.0, 5.0, 0.5) / 100
    with col4:
        years = st.slider("Time Horizon (Years)", 1, 30, 10)

    projections = project_growth(initial, monthly, avg_yield, years)
    df_proj = pd.DataFrame(projections)

    if projections:
        final = projections[-1]
        col1, col2, col3 = st.columns(3)
        with col1:
            metric_card(f"Portfolio in {years} Years", f"${final['balance']:,.0f}")
        with col2:
            metric_card("Projected Annual Income", f"${final['annual_income']:,.0f}")
        with col3:
            metric_card("Projected Monthly Income", f"${final['monthly_income']:,.0f}")

        total_contributed = initial + (monthly * years * 12)
        growth = final["balance"] - total_contributed
        metric_card(
            "Total Contributed",
            f"${total_contributed:,.0f}",
            delta=f"+${growth:,.0f} from dividends",
            delta_positive=True,
        )

        st.markdown("---")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_proj["year"], y=df_proj["balance"],
            mode="lines+markers", name="Portfolio Value",
            line=dict(color="#667eea", width=3),
        ))
        fig.add_trace(go.Bar(
            x=df_proj["year"], y=df_proj["annual_income"],
            name="Annual Dividend Income",
            marker_color="#22c55e", opacity=0.6,
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#7d8590",
            xaxis_title="Year",
            yaxis_title="Amount ($)",
            hovermode="x unified",
            margin=dict(t=20, b=20),
            xaxis=dict(gridcolor="#21262d"),
            yaxis=dict(gridcolor="#21262d"),
            legend=dict(font=dict(color="#7d8590")),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Year-by-year table
        st.markdown('<div class="section-title">Year-by-Year Breakdown</div>', unsafe_allow_html=True)
        display_proj = df_proj.copy()
        display_proj.columns = ["Year", "Portfolio Value", "Annual Income", "Monthly Income"]
        display_proj["Portfolio Value"] = display_proj["Portfolio Value"].apply(lambda x: f"${x:,.0f}")
        display_proj["Annual Income"] = display_proj["Annual Income"].apply(lambda x: f"${x:,.0f}")
        display_proj["Monthly Income"] = display_proj["Monthly Income"].apply(lambda x: f"${x:,.0f}")
        st.dataframe(display_proj, use_container_width=True, hide_index=True)


# ── Settings Page ──────────────────────────────────────────────────
def page_settings(user: dict, profile: dict):
    st.markdown('<p class="main-title">Settings</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-text">Manage your profile and family group</p>', unsafe_allow_html=True)

    # Profile settings
    st.markdown('<div class="section-title">Profile</div>', unsafe_allow_html=True)
    with st.form("profile_form"):
        display_name = st.text_input("Display Name", value=profile.get("display_name", ""))
        role = st.text_input("Role", value=profile.get("role", ""), placeholder="e.g. Dad, Mom, Son")
        if st.form_submit_button("Save Profile", type="primary"):
            update_profile(user["id"], display_name=display_name.strip(), role=role.strip())
            st.success("Profile updated.")
            st.rerun()

    st.markdown("---")

    # Family settings
    st.markdown('<div class="section-title">Family</div>', unsafe_allow_html=True)
    family_id = profile.get("family_id")

    if family_id:
        family = get_family(family_id)
        st.markdown(f"**{family.get('name', 'Your Family')}**")

        invite_code = get_family_invite_code(family_id)
        st.text_input("Invite Code (share with family members)", value=invite_code, disabled=True)

        members = get_family_members(family_id)
        if members:
            st.markdown("**Members:**")
            for m in members:
                role_label = f" — {m['role']}" if m.get("role") else ""
                is_you = " (you)" if m["id"] == user["id"] else ""
                st.markdown(f"- {m['display_name']}{role_label}{is_you}")
    else:
        st.info("You're not part of a family group yet.")
        tab_create, tab_join = st.tabs(["Create a Family", "Join a Family"])

        with tab_create:
            with st.form("settings_create_family"):
                family_name = st.text_input("Family Name", placeholder="e.g. Edwards Family")
                if st.form_submit_button("Create Family", type="primary"):
                    if family_name:
                        family = setup_family(user["id"], family_name.strip())
                        if family:
                            st.success(f"Created \"{family_name}\"")
                            st.rerun()

        with tab_join:
            with st.form("settings_join_family"):
                code = st.text_input("Invite Code")
                if st.form_submit_button("Join Family", type="primary"):
                    if code and join_family_by_code(user["id"], code.strip()):
                        st.success("Joined family.")
                        st.rerun()
                    else:
                        st.error("Invalid invite code.")


# ── Main App ───────────────────────────────────────────────────────
def main():
    inject_pwa()
    inject_styles()

    # Check authentication
    if not check_auth():
        render_auth_page()
        return

    user = get_current_user()
    if not user:
        render_auth_page()
        return

    # Check onboarding
    if not is_onboarded(user["id"]):
        render_onboarding(user)
        return

    # Load profile
    profile = get_profile(user["id"])

    # Render sidebar and get selected page
    page = render_sidebar(user, profile)

    # Route to page
    pages = {
        "Dashboard": page_dashboard,
        "Family Overview": page_family,
        "My Portfolio": page_portfolio,
        "Stock Screener": page_screener,
        "Watchlist": page_watchlist,
        "Growth Projector": page_projector,
        "Settings": page_settings,
    }

    page_func = pages.get(page, page_dashboard)
    page_func(user, profile)


if __name__ == "__main__":
    main()
