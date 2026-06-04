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
