import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import init_db, add_holding, remove_holding, get_holdings, update_holding
from database import add_to_watchlist, remove_from_watchlist, get_watchlist
from market_data import (
    get_stock_info,
    get_dividend_history,
    get_price_history,
    screen_dividend_stocks,
    calculate_portfolio_income,
    project_growth,
)

# --- Page Config ---
st.set_page_config(
    page_title="Dividend Dashboard | The Passive Approach",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Initialize Database ---
init_db()

# --- Custom Styling ---
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1rem;
        color: #6c757d;
        margin-top: 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
    }
    .positive { color: #00c853; }
    .negative { color: #ff1744; }
</style>
""", unsafe_allow_html=True)

# --- Sidebar Navigation ---
st.sidebar.markdown("## 💰 The Passive Approach")
st.sidebar.markdown("*Generating Wealth*")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    ["📊 Dashboard", "📈 My Portfolio", "🔍 Stock Screener", "👁️ Watchlist", "📐 Growth Projector"],
    label_visibility="collapsed",
)

# ============================================================
# DASHBOARD PAGE
# ============================================================
if page == "📊 Dashboard":
    st.markdown('<p class="main-header">The Passive Approach to Generating Wealth</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Dividend Dashboard — Your passive income at a glance</p>', unsafe_allow_html=True)
    st.markdown("---")

    holdings = get_holdings()

    if not holdings:
        st.info("👋 Welcome! Start by adding stocks to your portfolio in the **My Portfolio** tab.")
        st.markdown("""
        ### Quick Start
        1. Go to **📈 My Portfolio** to add your first stock
        2. Use **🔍 Stock Screener** to find high-yield dividend stocks
        3. Add interesting finds to your **👁️ Watchlist**
        4. Check **📐 Growth Projector** to see your passive income future
        """)
    else:
        # Fetch live data for all holdings
        with st.spinner("Fetching latest market data..."):
            holdings_data = []
            for h in holdings:
                info = get_stock_info(h["ticker"])
                if "error" not in info:
                    info["shares"] = h["shares"]
                    info["avg_cost"] = h["avg_cost"]
                    holdings_data.append(info)

        if holdings_data:
            income = calculate_portfolio_income(holdings_data)

            # Key Metrics Row
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Portfolio Value", f"${income['total_value']:,.2f}",
                          delta=f"${income['total_gain_loss']:,.2f}")
            with col2:
                st.metric("Monthly Passive Income", f"${income['total_monthly_income']:,.2f}")
            with col3:
                st.metric("Annual Passive Income", f"${income['total_annual_income']:,.2f}")
            with col4:
                st.metric("Portfolio Yield", f"{income['portfolio_yield']:.2f}%")

            st.markdown("---")

            # Income breakdown chart
            col_left, col_right = st.columns(2)

            with col_left:
                st.subheader("Income by Stock")
                df_details = pd.DataFrame(income["details"])
                if not df_details.empty and df_details["annual_income"].sum() > 0:
                    fig_pie = px.pie(
                        df_details[df_details["annual_income"] > 0],
                        values="annual_income",
                        names="ticker",
                        hole=0.4,
                        color_discrete_sequence=px.colors.qualitative.Set2,
                    )
                    fig_pie.update_layout(margin=dict(t=20, b=20, l=20, r=20))
                    st.plotly_chart(fig_pie, use_container_width=True)

            with col_right:
                st.subheader("Holdings Overview")
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

            # Monthly income projection
            st.markdown("---")
            st.subheader("12-Month Income Projection")
            months = pd.date_range(start=pd.Timestamp.now(), periods=12, freq="MS")
            monthly_vals = [income["total_monthly_income"]] * 12
            fig_bar = px.bar(
                x=[m.strftime("%b %Y") for m in months],
                y=monthly_vals,
                labels={"x": "Month", "y": "Projected Income ($)"},
                color_discrete_sequence=["#667eea"],
            )
            fig_bar.update_layout(margin=dict(t=20, b=20))
            st.plotly_chart(fig_bar, use_container_width=True)


# ============================================================
# PORTFOLIO PAGE
# ============================================================
elif page == "📈 My Portfolio":
    st.header("📈 My Portfolio")
    st.markdown("Add and manage your dividend stock holdings.")
    st.markdown("---")

    # Add new holding
    with st.expander("➕ Add New Holding", expanded=True):
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
                # Quick validation
                info = get_stock_info(new_ticker)
                if "error" in info:
                    st.error(f"Could not find ticker '{new_ticker}'. Please check the symbol.")
                else:
                    add_holding(new_ticker, new_shares, new_cost, new_notes)
                    st.success(f"Added {new_shares} shares of {new_ticker} ({info.get('name', '')}) to your portfolio!")
                    st.rerun()
            else:
                st.warning("Please fill in ticker, shares, and cost.")

    # Display current holdings
    st.markdown("---")
    st.subheader("Current Holdings")
    holdings = get_holdings()

    if not holdings:
        st.info("No holdings yet. Add your first stock above!")
    else:
        for h in holdings:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 1.5, 1.5, 1.5, 1])
                with col1:
                    st.markdown(f"**{h['ticker']}**")
                    if h["notes"]:
                        st.caption(h["notes"])
                with col2:
                    st.metric("Shares", f"{h['shares']:.4f}")
                with col3:
                    st.metric("Avg Cost", f"${h['avg_cost']:.2f}")
                with col4:
                    st.metric("Cost Basis", f"${h['shares'] * h['avg_cost']:,.2f}")
                with col5:
                    if st.button("🗑️", key=f"del_{h['ticker']}", help=f"Remove {h['ticker']}"):
                        remove_holding(h["ticker"])
                        st.rerun()
                st.markdown("---")


# ============================================================
# SCREENER PAGE
# ============================================================
elif page == "🔍 Stock Screener":
    st.header("🔍 Dividend Stock Screener")
    st.markdown("Find quality dividend stocks that match your passive income goals.")
    st.markdown("---")

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

    if st.button("🔍 Run Screener", type="primary"):
        with st.spinner("Screening dividend stocks... This may take a minute."):
            results = screen_dividend_stocks(min_yield, min_cap, max_payout)

        if results:
            st.success(f"Found {len(results)} stocks matching your criteria!")
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
            st.subheader("Quick Add to Watchlist")
            tickers = [r["ticker"] for r in results]
            selected = st.multiselect("Select stocks to watch", tickers)
            if st.button("Add Selected to Watchlist"):
                for t in selected:
                    stock = next(r for r in results if r["ticker"] == t)
                    add_to_watchlist(t, target_price=stock["price"] * 0.9)
                st.success(f"Added {len(selected)} stocks to your watchlist!")
        else:
            st.warning("No stocks matched your criteria. Try adjusting the filters.")

    # Individual stock lookup
    st.markdown("---")
    st.subheader("Quick Stock Lookup")
    lookup = st.text_input("Enter a ticker to look up", placeholder="e.g. O, SCHD, JEPI")
    if lookup:
        with st.spinner(f"Looking up {lookup.upper()}..."):
            info = get_stock_info(lookup)
            divs = get_dividend_history(lookup)

        if "error" not in info:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Price", f"${info['price']:,.2f}")
            with col2:
                st.metric("Dividend Yield", f"{info['dividend_yield']*100:.2f}%")
            with col3:
                st.metric("Annual Dividend", f"${info['dividend_rate']:.2f}")
            with col4:
                st.metric("Payout Ratio", f"{info['payout_ratio']*100:.1f}%")

            st.markdown(f"**{info['name']}** | Sector: {info['sector']} | P/E: {info['pe_ratio']:.1f} | Beta: {info['beta']:.2f}")

            if not divs.empty:
                st.subheader("Dividend History")
                fig = px.bar(divs.head(20), x="Date", y="Dividend",
                            labels={"Dividend": "Dividend ($)"},
                            color_discrete_sequence=["#667eea"])
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.error(f"Could not find data for '{lookup.upper()}'")


# ============================================================
# WATCHLIST PAGE
# ============================================================
elif page == "👁️ Watchlist":
    st.header("👁️ Watchlist")
    st.markdown("Track stocks you're interested in buying.")
    st.markdown("---")

    # Add to watchlist
    with st.expander("➕ Add to Watchlist"):
        col1, col2 = st.columns(2)
        with col1:
            watch_ticker = st.text_input("Ticker", placeholder="e.g. SCHD").upper()
        with col2:
            watch_target = st.number_input("Target Buy Price ($)", min_value=0.0, step=0.01, format="%.2f")
        watch_notes = st.text_input("Notes", placeholder="e.g. Wait for next ex-div date")
        if st.button("Add to Watchlist", type="primary"):
            if watch_ticker:
                add_to_watchlist(watch_ticker, watch_target if watch_target > 0 else None, watch_notes)
                st.success(f"Added {watch_ticker} to watchlist!")
                st.rerun()

    watchlist = get_watchlist()

    if not watchlist:
        st.info("Your watchlist is empty. Add stocks from the screener or manually above!")
    else:
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
                        if item["target_price"]:
                            st.metric("Target Price", f"${item['target_price']:,.2f}")
                            if "error" not in info and info["price"] <= item["target_price"]:
                                st.success("🎯 BUY ZONE!")
                    with col4:
                        if "error" not in info:
                            st.metric("Yield", f"{info['dividend_yield']*100:.2f}%")
                    with col5:
                        if item["notes"]:
                            st.caption(item["notes"])
                    with col6:
                        if st.button("🗑️", key=f"wdel_{item['ticker']}"):
                            remove_from_watchlist(item["ticker"])
                            st.rerun()
                    st.markdown("---")


# ============================================================
# GROWTH PROJECTOR PAGE
# ============================================================
elif page == "📐 Growth Projector":
    st.header("📐 Growth Projector")
    st.markdown("See how your passive income grows over time with dividend reinvestment.")
    st.markdown("---")

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

    # Key projections
    if projections:
        final = projections[-1]
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(f"Portfolio Value in {years} Years", f"${final['balance']:,.0f}")
        with col2:
            st.metric("Projected Annual Income", f"${final['annual_income']:,.0f}")
        with col3:
            st.metric("Projected Monthly Income", f"${final['monthly_income']:,.0f}")

        total_contributed = initial + (monthly * years * 12)
        st.metric("Total You Contributed", f"${total_contributed:,.0f}",
                  delta=f"${final['balance'] - total_contributed:,.0f} from dividends")

        st.markdown("---")

        # Growth chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_proj["year"], y=df_proj["balance"],
            mode="lines+markers", name="Portfolio Value",
            line=dict(color="#667eea", width=3),
        ))
        fig.add_trace(go.Bar(
            x=df_proj["year"], y=df_proj["annual_income"],
            name="Annual Dividend Income",
            marker_color="#00c853", opacity=0.6,
        ))
        fig.update_layout(
            title="Portfolio Growth & Income Projection",
            xaxis_title="Year",
            yaxis_title="Amount ($)",
            hovermode="x unified",
            margin=dict(t=40, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Detailed table
        st.subheader("Year-by-Year Breakdown")
        display_proj = df_proj.copy()
        display_proj.columns = ["Year", "Portfolio Value", "Annual Income", "Monthly Income"]
        display_proj["Portfolio Value"] = display_proj["Portfolio Value"].apply(lambda x: f"${x:,.0f}")
        display_proj["Annual Income"] = display_proj["Annual Income"].apply(lambda x: f"${x:,.0f}")
        display_proj["Monthly Income"] = display_proj["Monthly Income"].apply(lambda x: f"${x:,.0f}")
        st.dataframe(display_proj, use_container_width=True, hide_index=True)
