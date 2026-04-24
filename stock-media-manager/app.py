import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
from database import (
    init_db, PLATFORMS,
    add_media_file, get_media_files, get_media_file, update_media_file,
    delete_media_file, get_media_count,
    add_upload, update_upload, get_uploads_for_media, get_upload_stats,
    add_earning, get_earnings, get_earnings_summary,
    add_platform_account, get_platform_accounts,
)
from media_scanner import (
    scan_directory, classify_file, format_file_size,
    generate_stock_keywords,
)

# --- Page Config ---
st.set_page_config(
    page_title="Stock Media Manager | The Passive Approach",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Initialize ---
init_db()

# --- Styling ---
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
    .stat-highlight {
        font-size: 1.8rem;
        font-weight: 700;
        color: #667eea;
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar ---
st.sidebar.markdown("## 📸 Stock Media Manager")
st.sidebar.markdown("*Turn Your Work Into Royalties*")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    ["📊 Dashboard", "📂 Import Media", "🏷️ Manage & Tag", "📤 Upload Tracker", "💰 Earnings", "⚙️ Platforms"],
    label_visibility="collapsed",
)

# ============================================================
# DASHBOARD
# ============================================================
if page == "📊 Dashboard":
    st.markdown('<p class="main-header">Stock Media Manager</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Turn your existing photos & videos into recurring royalty income</p>', unsafe_allow_html=True)
    st.markdown("---")

    media_stats = get_media_count()
    upload_stats = get_upload_stats()
    earnings = get_earnings_summary()

    # Top metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Media Files", media_stats["total"])
    with col2:
        photos = media_stats["by_type"].get("photo", 0)
        st.metric("Photos", photos)
    with col3:
        videos = media_stats["by_type"].get("video", 0)
        st.metric("Videos", videos)
    with col4:
        st.metric("Total Earnings", f"${earnings['grand_total']:,.2f}")

    st.markdown("---")

    if media_stats["total"] == 0:
        st.info("👋 Welcome! Get started by importing your media files in the **Import Media** tab.")
        st.markdown("""
        ### How It Works
        1. **📂 Import Media** — Point to a folder of photos/videos you want to monetize
        2. **🏷️ Manage & Tag** — Add titles, descriptions, and keywords for stock platforms
        3. **📤 Upload Tracker** — Track which files you've submitted to which platforms
        4. **💰 Earnings** — Log and monitor your royalty income
        5. **⚙️ Platforms** — Set up your stock media platform accounts

        ### Why This Works for You
        As a photographer and videographer, you're **already creating content**.
        Your B-roll, outtakes, behind-the-scenes shots, and extra edits can all
        generate passive income on stock platforms — without any additional shooting.
        """)
    else:
        col_left, col_right = st.columns(2)

        with col_left:
            # Upload status breakdown
            if upload_stats:
                st.subheader("Upload Status")
                df_uploads = pd.DataFrame(upload_stats)
                fig = px.bar(
                    df_uploads, x="platform", y="count", color="status",
                    barmode="group",
                    color_discrete_map={
                        "pending": "#ffc107",
                        "uploaded": "#17a2b8",
                        "approved": "#28a745",
                        "rejected": "#dc3545",
                    },
                )
                fig.update_layout(margin=dict(t=20, b=20))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No uploads tracked yet. Go to **Upload Tracker** to start.")

        with col_right:
            # Earnings by platform
            if earnings["by_platform"]:
                st.subheader("Earnings by Platform")
                df_earn = pd.DataFrame(earnings["by_platform"])
                fig = px.pie(
                    df_earn, values="total", names="platform",
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Set2,
                )
                fig.update_layout(margin=dict(t=20, b=20))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No earnings logged yet. Go to **Earnings** to start tracking.")

        # Recent media
        st.markdown("---")
        st.subheader("Recently Added Media")
        recent = get_media_files(limit=10)
        if recent:
            df_recent = pd.DataFrame(recent)
            display_cols = ["file_name", "file_type", "title", "keywords", "date_added"]
            display_df = df_recent[display_cols].copy()
            display_df.columns = ["File", "Type", "Title", "Keywords", "Added"]
            display_df["Added"] = pd.to_datetime(display_df["Added"]).dt.strftime("%Y-%m-%d")
            st.dataframe(display_df, use_container_width=True, hide_index=True)


# ============================================================
# IMPORT MEDIA
# ============================================================
elif page == "📂 Import Media":
    st.header("📂 Import Media")
    st.markdown("Scan a folder to import your photos and videos for stock submission.")
    st.markdown("---")

    scan_path = st.text_input(
        "Folder path to scan",
        placeholder="e.g. /Users/michaeledwards/Photos/Stock-Ready",
        help="Enter the full path to a folder containing photos or videos",
    )
    recursive = st.checkbox("Include subfolders", value=True)

    if st.button("🔍 Scan Folder", type="primary"):
        if scan_path:
            with st.spinner(f"Scanning {scan_path}..."):
                results = scan_directory(scan_path, recursive=recursive)

            if results:
                st.success(f"Found {len(results)} media files!")

                # Preview results
                df = pd.DataFrame(results)
                display_df = df[["file_name", "file_type", "file_size", "width", "height"]].copy()
                display_df["file_size"] = display_df["file_size"].apply(format_file_size)
                display_df["dimensions"] = display_df.apply(
                    lambda r: f"{r['width']}x{r['height']}" if r["width"] > 0 else "N/A", axis=1
                )
                display_df = display_df[["file_name", "file_type", "file_size", "dimensions"]]
                display_df.columns = ["File", "Type", "Size", "Dimensions"]
                st.dataframe(display_df, use_container_width=True, hide_index=True)

                if st.button("✅ Import All to Library", type="primary"):
                    imported = 0
                    for item in results:
                        media_id = add_media_file(
                            file_path=item["file_path"],
                            file_name=item["file_name"],
                            file_type=item["file_type"],
                            file_size=item["file_size"],
                            width=item.get("width", 0),
                            height=item.get("height", 0),
                            date_taken=item.get("date_taken", ""),
                            camera_model=item.get("camera_model", ""),
                        )
                        if media_id:
                            imported += 1
                    st.success(f"Imported {imported} new files to your library!")
                    st.rerun()
            else:
                st.warning("No photo or video files found in that folder.")
        else:
            st.warning("Please enter a folder path.")

    # Supported formats
    with st.expander("Supported File Formats"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            **Photos**: JPG, JPEG, PNG, TIFF, BMP, WebP, HEIC, RAW, CR2, NEF, ARW, DNG
            """)
        with col2:
            st.markdown("""
            **Videos**: MP4, MOV, AVI, MKV, WMV, FLV, WebM, M4V, MPG, MPEG, MXF
            """)


# ============================================================
# MANAGE & TAG
# ============================================================
elif page == "🏷️ Manage & Tag":
    st.header("🏷️ Manage & Tag Media")
    st.markdown("Add titles, descriptions, and keywords to prepare files for stock submission.")
    st.markdown("---")

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        filter_type = st.selectbox("Filter by type", ["All", "photo", "video"])
    with col2:
        filter_cat = st.selectbox("Filter by category", [
            "All", "Landscape", "Portrait", "Architecture", "Food",
            "Business", "Technology", "Lifestyle", "Events", "Sports", "Abstract",
        ])

    media_type = filter_type if filter_type != "All" else None
    media_cat = filter_cat if filter_cat != "All" else None
    files = get_media_files(file_type=media_type, category=media_cat)

    if not files:
        st.info("No media files found. Import some files first!")
    else:
        st.markdown(f"**{len(files)} files** in your library")

        for f in files:
            with st.expander(f"{'📷' if f['file_type'] == 'photo' else '🎬'} {f['file_name']}", expanded=False):
                col1, col2 = st.columns([1, 2])

                with col1:
                    st.markdown(f"**File**: {f['file_name']}")
                    st.markdown(f"**Size**: {format_file_size(f['file_size'])}")
                    if f["width"] > 0:
                        st.markdown(f"**Dimensions**: {f['width']}x{f['height']}")
                    if f["camera_model"]:
                        st.markdown(f"**Camera**: {f['camera_model']}")
                    if f["date_taken"]:
                        st.markdown(f"**Taken**: {f['date_taken']}")

                    # Upload status
                    uploads = get_uploads_for_media(f["id"])
                    if uploads:
                        st.markdown("**Uploaded to:**")
                        for u in uploads:
                            status_icon = {"pending": "🟡", "uploaded": "🔵", "approved": "🟢", "rejected": "🔴"}.get(u["status"], "⚪")
                            st.markdown(f"{status_icon} {u['platform']} — {u['status']}")

                with col2:
                    title = st.text_input("Title", value=f["title"], key=f"title_{f['id']}")
                    description = st.text_area("Description", value=f["description"], key=f"desc_{f['id']}", height=80)

                    category = st.selectbox("Category", [
                        "", "Landscape", "Portrait", "Architecture", "Food",
                        "Business", "Technology", "Lifestyle", "Events", "Sports", "Abstract",
                    ], index=0, key=f"cat_{f['id']}")

                    # Keyword suggestions
                    suggested = generate_stock_keywords(f["file_name"], category)
                    current_keywords = f["keywords"]
                    if suggested and not current_keywords:
                        st.caption(f"Suggested keywords: {', '.join(suggested)}")

                    keywords = st.text_input(
                        "Keywords (comma-separated)",
                        value=current_keywords,
                        key=f"kw_{f['id']}",
                        placeholder="e.g. sunset, ocean, beach, travel, golden hour",
                    )

                    location = st.text_input("Location", value=f.get("location", ""), key=f"loc_{f['id']}")

                    col_save, col_del = st.columns([3, 1])
                    with col_save:
                        if st.button("💾 Save", key=f"save_{f['id']}", type="primary"):
                            update_media_file(
                                f["id"],
                                title=title,
                                description=description,
                                keywords=keywords,
                                category=category,
                                location=location,
                            )
                            st.success("Saved!")
                    with col_del:
                        if st.button("🗑️ Remove", key=f"del_{f['id']}"):
                            delete_media_file(f["id"])
                            st.rerun()


# ============================================================
# UPLOAD TRACKER
# ============================================================
elif page == "📤 Upload Tracker":
    st.header("📤 Upload Tracker")
    st.markdown("Track your submissions to stock media platforms.")
    st.markdown("---")

    # Log new upload
    with st.expander("➕ Log New Upload", expanded=True):
        files = get_media_files(limit=500)
        if not files:
            st.info("Import media files first before tracking uploads.")
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                file_options = {f["id"]: f["file_name"] for f in files}
                selected_media = st.selectbox(
                    "Media File",
                    options=list(file_options.keys()),
                    format_func=lambda x: file_options[x],
                )
            with col2:
                platform = st.selectbox("Platform", PLATFORMS)
            with col3:
                status = st.selectbox("Status", ["pending", "uploaded", "approved", "rejected"])

            upload_notes = st.text_input("Notes", placeholder="e.g. Batch upload #3")

            if st.button("Log Upload", type="primary"):
                add_upload(selected_media, platform, status, notes=upload_notes)
                st.success(f"Logged upload of {file_options[selected_media]} to {platform}!")
                st.rerun()

    # Upload overview
    st.markdown("---")
    st.subheader("Upload Overview")

    stats = get_upload_stats()
    if stats:
        df_stats = pd.DataFrame(stats)
        # Pivot for a cleaner view
        pivot = df_stats.pivot_table(index="platform", columns="status", values="count", fill_value=0)
        st.dataframe(pivot, use_container_width=True)

        # Per-file upload status
        st.markdown("---")
        st.subheader("File Upload Status")
        files_with_uploads = []
        for f in get_media_files(limit=200):
            uploads = get_uploads_for_media(f["id"])
            if uploads:
                for u in uploads:
                    files_with_uploads.append({
                        "File": f["file_name"],
                        "Platform": u["platform"],
                        "Status": u["status"],
                        "Date": u["upload_date"][:10] if u["upload_date"] else "",
                        "upload_id": u["id"],
                    })

        if files_with_uploads:
            df_files = pd.DataFrame(files_with_uploads)
            st.dataframe(df_files[["File", "Platform", "Status", "Date"]],
                        use_container_width=True, hide_index=True)
    else:
        st.info("No uploads tracked yet. Log your first upload above!")

    # Batch upload helper
    st.markdown("---")
    st.subheader("Batch Log Uploads")
    st.markdown("Quickly log multiple files as uploaded to a platform.")
    batch_platform = st.selectbox("Platform for batch", PLATFORMS, key="batch_platform")
    batch_files = get_media_files(limit=500)
    if batch_files:
        batch_options = {f["id"]: f["file_name"] for f in batch_files}
        batch_selected = st.multiselect(
            "Select files",
            options=list(batch_options.keys()),
            format_func=lambda x: batch_options[x],
        )
        if st.button("Log All Selected as Uploaded"):
            for mid in batch_selected:
                add_upload(mid, batch_platform, "uploaded")
            st.success(f"Logged {len(batch_selected)} files as uploaded to {batch_platform}!")
            st.rerun()


# ============================================================
# EARNINGS
# ============================================================
elif page == "💰 Earnings":
    st.header("💰 Earnings Tracker")
    st.markdown("Track your royalty income from stock media platforms.")
    st.markdown("---")

    # Log earning
    with st.expander("➕ Log New Earning", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            earn_platform = st.selectbox("Platform", PLATFORMS, key="earn_platform")
        with col2:
            earn_amount = st.number_input("Amount ($)", min_value=0.0, step=0.01, format="%.2f")
        with col3:
            earn_date = st.date_input("Date", value=date.today())

        earn_type = st.selectbox("Type", ["royalty", "bonus", "referral", "payout", "other"])
        earn_notes = st.text_input("Notes", placeholder="e.g. March 2026 royalties")

        if st.button("Log Earning", type="primary"):
            if earn_amount > 0:
                add_earning(earn_platform, earn_amount, earn_date.isoformat(),
                           earning_type=earn_type, notes=earn_notes)
                st.success(f"Logged ${earn_amount:.2f} from {earn_platform}!")
                st.rerun()

    # Earnings summary
    st.markdown("---")
    summary = get_earnings_summary()

    if summary["grand_total"] > 0:
        st.metric("Total Earnings (All Time)", f"${summary['grand_total']:,.2f}")

        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Earnings by Platform")
            if summary["by_platform"]:
                df_plat = pd.DataFrame(summary["by_platform"])
                fig = px.bar(
                    df_plat, x="platform", y="total",
                    labels={"total": "Total ($)", "platform": "Platform"},
                    color_discrete_sequence=["#667eea"],
                )
                fig.update_layout(margin=dict(t=20, b=20))
                st.plotly_chart(fig, use_container_width=True)

        with col_right:
            st.subheader("Platform Details")
            if summary["by_platform"]:
                df_detail = pd.DataFrame(summary["by_platform"])
                df_detail.columns = ["Platform", "Total", "Transactions", "First Earning", "Last Earning"]
                df_detail["Total"] = df_detail["Total"].apply(lambda x: f"${x:,.2f}")
                st.dataframe(df_detail, use_container_width=True, hide_index=True)

        # Earnings timeline
        st.markdown("---")
        st.subheader("Earnings Timeline")
        all_earnings = get_earnings()
        if all_earnings:
            df_timeline = pd.DataFrame(all_earnings)
            df_timeline["earning_date"] = pd.to_datetime(df_timeline["earning_date"])
            df_monthly = df_timeline.groupby(
                df_timeline["earning_date"].dt.to_period("M")
            )["amount"].sum().reset_index()
            df_monthly["earning_date"] = df_monthly["earning_date"].astype(str)
            fig = px.line(
                df_monthly, x="earning_date", y="amount",
                labels={"amount": "Earnings ($)", "earning_date": "Month"},
                markers=True,
                color_discrete_sequence=["#00c853"],
            )
            fig.update_layout(margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No earnings logged yet. Start by logging your first royalty payment above!")
        st.markdown("""
        ### Tips for Getting Started
        - Most platforms pay monthly, 30-60 days after the sale
        - Log earnings when you receive your payout notification
        - Even small amounts add up — $5/month from 5 platforms = $300/year
        - The more files you have approved, the more you earn passively
        """)


# ============================================================
# PLATFORMS
# ============================================================
elif page == "⚙️ Platforms":
    st.header("⚙️ Platform Accounts")
    st.markdown("Manage your stock media platform accounts.")
    st.markdown("---")

    # Add/update platform
    with st.expander("➕ Add Platform Account", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            plat_name = st.selectbox("Platform", PLATFORMS, key="plat_setup")
        with col2:
            plat_user = st.text_input("Username / Email")
        with col3:
            plat_id = st.text_input("Contributor ID (optional)")

        if st.button("Save Platform", type="primary"):
            if plat_name:
                add_platform_account(plat_name, plat_user, plat_id)
                st.success(f"Saved {plat_name} account!")
                st.rerun()

    # Current accounts
    st.markdown("---")
    st.subheader("Your Platform Accounts")
    accounts = get_platform_accounts()

    if accounts:
        for acc in accounts:
            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"**{acc['platform']}**")
                with col2:
                    st.markdown(f"Username: {acc['username']}")
                with col3:
                    if acc["contributor_id"]:
                        st.markdown(f"ID: {acc['contributor_id']}")
                st.markdown("---")
    else:
        st.info("No platform accounts set up yet.")

    st.markdown("""
    ### Recommended Platforms for Photographers & Videographers

    | Platform | Best For | Commission |
    |----------|----------|------------|
    | **Adobe Stock** | Photos & Videos | 33% royalty |
    | **Shutterstock** | High volume | 15-40% tiered |
    | **Getty / iStock** | Premium content | 15-45% |
    | **Pond5** | Video clips | 40-60% |
    | **Alamy** | Editorial | Up to 50% |

    *Start with 2-3 platforms to maximize your reach without spreading too thin.*
    """)
