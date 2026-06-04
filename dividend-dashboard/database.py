from config import get_supabase


# ── Family Management ──────────────────────────────────────────────

def create_family(name: str) -> dict:
    """Create a new family group. Returns the family record."""
    sb = get_supabase()
    result = sb.table("families").insert({"name": name}).execute()
    return result.data[0] if result.data else {}


def get_family(family_id: str) -> dict:
    sb = get_supabase()
    result = sb.table("families").select("*").eq("id", family_id).single().execute()
    return result.data if result.data else {}


def join_family_by_code(user_id: str, invite_code: str) -> bool:
    """Join a family using an invite code."""
    sb = get_supabase()
    family = sb.table("families").select("id").eq("invite_code", invite_code).execute()
    if not family.data:
        return False
    family_id = family.data[0]["id"]
    sb.table("profiles").update({"family_id": family_id}).eq("id", user_id).execute()
    return True


def get_family_members(family_id: str) -> list[dict]:
    """Get all members of a family."""
    sb = get_supabase()
    result = (
        sb.table("profiles")
        .select("*")
        .eq("family_id", family_id)
        .order("created_at")
        .execute()
    )
    return result.data or []


def get_family_invite_code(family_id: str) -> str:
    family = get_family(family_id)
    return family.get("invite_code", "")


# ── Profile Management ─────────────────────────────────────────────

def get_profile(user_id: str) -> dict:
    sb = get_supabase()
    result = sb.table("profiles").select("*").eq("id", user_id).single().execute()
    return result.data if result.data else {}


def update_profile(user_id: str, **kwargs) -> dict:
    """Update profile fields (display_name, role, avatar_url, family_id)."""
    sb = get_supabase()
    allowed = {"display_name", "role", "avatar_url", "family_id"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return {}
    result = sb.table("profiles").update(updates).eq("id", user_id).execute()
    return result.data[0] if result.data else {}


# ── Holdings (Portfolio) ───────────────────────────────────────────

def add_holding(user_id: str, ticker: str, shares: float, avg_cost: float, notes: str = ""):
    """Add or update a holding. If ticker exists, add shares and update cost basis."""
    sb = get_supabase()
    ticker = ticker.upper()

    existing = (
        sb.table("holdings")
        .select("*")
        .eq("user_id", user_id)
        .eq("ticker", ticker)
        .execute()
    )

    if existing.data:
        old = existing.data[0]
        total_shares = old["shares"] + shares
        # Weighted average cost
        if total_shares > 0:
            new_avg = (
                (old["shares"] * old["avg_cost"]) + (shares * avg_cost)
            ) / total_shares
        else:
            new_avg = avg_cost
        sb.table("holdings").update({
            "shares": total_shares,
            "avg_cost": round(new_avg, 4),
            "notes": notes or old.get("notes", ""),
            "updated_at": "now()",
        }).eq("id", old["id"]).execute()
    else:
        sb.table("holdings").insert({
            "user_id": user_id,
            "ticker": ticker,
            "shares": shares,
            "avg_cost": avg_cost,
            "notes": notes,
        }).execute()


def remove_holding(user_id: str, ticker: str):
    sb = get_supabase()
    sb.table("holdings").delete().eq("user_id", user_id).eq("ticker", ticker.upper()).execute()


def get_holdings(user_id: str) -> list[dict]:
    sb = get_supabase()
    result = (
        sb.table("holdings")
        .select("*")
        .eq("user_id", user_id)
        .order("ticker")
        .execute()
    )
    return result.data or []


def get_family_holdings(family_id: str) -> dict[str, list[dict]]:
    """Get holdings for all family members. Returns {user_id: [holdings]}."""
    members = get_family_members(family_id)
    sb = get_supabase()
    result = {}
    for m in members:
        holdings = (
            sb.table("holdings")
            .select("*")
            .eq("user_id", m["id"])
            .order("ticker")
            .execute()
        )
        result[m["id"]] = {
            "profile": m,
            "holdings": holdings.data or [],
        }
    return result


def update_holding(user_id: str, ticker: str, **kwargs):
    sb = get_supabase()
    allowed = {"shares", "avg_cost", "notes"}
    updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    if updates:
        sb.table("holdings").update(updates).eq("user_id", user_id).eq("ticker", ticker.upper()).execute()


# ── Watchlist ──────────────────────────────────────────────────────

def add_to_watchlist(user_id: str, ticker: str, target_price: float = None, notes: str = ""):
    sb = get_supabase()
    ticker = ticker.upper()

    existing = (
        sb.table("watchlist")
        .select("id")
        .eq("user_id", user_id)
        .eq("ticker", ticker)
        .execute()
    )

    if existing.data:
        updates = {}
        if target_price is not None:
            updates["target_price"] = target_price
        if notes:
            updates["notes"] = notes
        if updates:
            sb.table("watchlist").update(updates).eq("id", existing.data[0]["id"]).execute()
    else:
        sb.table("watchlist").insert({
            "user_id": user_id,
            "ticker": ticker,
            "target_price": target_price,
            "notes": notes,
        }).execute()


def remove_from_watchlist(user_id: str, ticker: str):
    sb = get_supabase()
    sb.table("watchlist").delete().eq("user_id", user_id).eq("ticker", ticker.upper()).execute()


def get_watchlist(user_id: str) -> list[dict]:
    sb = get_supabase()
    result = (
        sb.table("watchlist")
        .select("*")
        .eq("user_id", user_id)
        .order("ticker")
        .execute()
    )
    return result.data or []


# ── Onboarding Helpers ─────────────────────────────────────────────

def setup_family(user_id: str, family_name: str, user_role: str = "") -> dict:
    """Create a family and assign the user to it. Returns the family record."""
    family = create_family(family_name)
    if family:
        update_profile(user_id, family_id=family["id"], role=user_role)
    return family


def is_onboarded(user_id: str) -> bool:
    """Check if user has completed onboarding (has a family)."""
    profile = get_profile(user_id)
    return bool(profile and profile.get("family_id"))


# ── Activity Logging ──────────────────────────────────────────────

def log_activity(user_id: str, action: str, details: dict = None):
    """Insert an activity log entry."""
    sb = get_supabase()
    row = {"user_id": user_id, "action": action}
    if details:
        row["details"] = details
    sb.table("activity_log").insert(row).execute()


def get_user_activity(user_id: str, limit: int = 50) -> list[dict]:
    """Get recent activity for a specific user."""
    sb = get_supabase()
    result = (
        sb.table("activity_log")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


def get_all_activity(limit: int = 100) -> list[dict]:
    """Get all activity across the platform (admin use)."""
    sb = get_supabase()
    result = (
        sb.table("activity_log")
        .select("*, profiles(display_name)")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


# ── Portfolio Snapshots ───────────────────────────────────────────

def save_portfolio_snapshot(
    user_id: str,
    total_value: float,
    total_income: float,
    holdings_count: int,
):
    """Upsert a daily portfolio snapshot (one per user per day)."""
    sb = get_supabase()
    today = __import__("datetime").date.today().isoformat()

    existing = (
        sb.table("portfolio_snapshots")
        .select("id")
        .eq("user_id", user_id)
        .eq("snapshot_date", today)
        .execute()
    )

    row = {
        "total_value": total_value,
        "total_income": total_income,
        "holdings_count": holdings_count,
    }

    if existing.data:
        sb.table("portfolio_snapshots").update(row).eq("id", existing.data[0]["id"]).execute()
    else:
        row.update({"user_id": user_id, "snapshot_date": today})
        sb.table("portfolio_snapshots").insert(row).execute()


def get_portfolio_history(user_id: str, days: int = 90) -> list[dict]:
    """Get snapshot history for a user (for charts)."""
    sb = get_supabase()
    cutoff = (
        __import__("datetime").date.today()
        - __import__("datetime").timedelta(days=days)
    ).isoformat()

    result = (
        sb.table("portfolio_snapshots")
        .select("*")
        .eq("user_id", user_id)
        .gte("snapshot_date", cutoff)
        .order("snapshot_date")
        .execute()
    )
    return result.data or []


def get_family_portfolio_history(family_id: str, days: int = 90) -> dict[str, list[dict]]:
    """Get portfolio histories for all family members."""
    members = get_family_members(family_id)
    return {
        m["id"]: get_portfolio_history(m["id"], days)
        for m in members
    }


# ── Admin Functions ───────────────────────────────────────────────

def is_admin(user_id: str) -> bool:
    """Check if a user has admin privileges."""
    sb = get_supabase()
    result = (
        sb.table("profiles")
        .select("is_admin")
        .eq("id", user_id)
        .single()
        .execute()
    )
    return bool(result.data and result.data.get("is_admin"))


def set_admin(user_id: str, is_admin: bool = True):
    """Grant or revoke admin status for a user."""
    sb = get_supabase()
    sb.table("profiles").update({"is_admin": is_admin}).eq("id", user_id).execute()


def get_all_users() -> list[dict]:
    """Get all registered users with their profiles."""
    sb = get_supabase()
    result = (
        sb.table("profiles")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


def get_all_families() -> list[dict]:
    """Get all families with member counts."""
    sb = get_supabase()
    result = (
        sb.table("families")
        .select("*, profiles(count)")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


def get_platform_stats() -> dict:
    """Total users, families, and combined portfolio value across the platform."""
    sb = get_supabase()

    users = sb.table("profiles").select("id", count="exact").execute()
    families = sb.table("families").select("id", count="exact").execute()

    snapshots = (
        sb.table("portfolio_snapshots")
        .select("user_id, total_value, total_income, snapshot_date")
        .order("snapshot_date", desc=True)
        .execute()
    )

    # Keep only the latest snapshot per user
    latest: dict[str, dict] = {}
    for s in snapshots.data or []:
        uid = s["user_id"]
        if uid not in latest:
            latest[uid] = s

    total_value = sum(s["total_value"] for s in latest.values())
    total_income = sum(s["total_income"] for s in latest.values())

    return {
        "total_users": users.count or 0,
        "total_families": families.count or 0,
        "total_portfolio_value": total_value,
        "total_portfolio_income": total_income,
    }


def get_signup_activity(days: int = 30) -> list[dict]:
    """Get user signups over time (for admin charts)."""
    sb = get_supabase()
    cutoff = (
        __import__("datetime").date.today()
        - __import__("datetime").timedelta(days=days)
    ).isoformat()

    result = (
        sb.table("profiles")
        .select("id, created_at")
        .gte("created_at", cutoff)
        .order("created_at")
        .execute()
    )
    return result.data or []


# ── Dividend Calendar ─────────────────────────────────────────────

def get_portfolio_dividend_calendar(user_id: str) -> list[dict]:
    """Return upcoming ex-dividend dates for all of a user's holdings.

    Uses yfinance to pull each ticker's next ex-dividend date,
    dividend rate, and estimated payout.
    """
    import yfinance as yf
    from datetime import date

    holdings = get_holdings(user_id)
    calendar = []

    for h in holdings:
        try:
            info = yf.Ticker(h["ticker"]).info
            ex_date_ts = info.get("exDividendDate")
            div_rate = info.get("dividendRate")

            if not ex_date_ts or not div_rate:
                continue

            # yfinance returns ex-date as a UNIX timestamp
            ex_date = date.fromtimestamp(ex_date_ts)

            # Only include future or today's dates
            if ex_date >= date.today():
                calendar.append({
                    "ticker": h["ticker"],
                    "shares": h["shares"],
                    "ex_date": ex_date.isoformat(),
                    "dividend_rate": div_rate,
                    "est_payout": round(div_rate / 4 * h["shares"], 2),
                    "frequency": info.get("dividendYield", None),
                })
        except Exception:
            continue

    calendar.sort(key=lambda x: x["ex_date"])
    return calendar
