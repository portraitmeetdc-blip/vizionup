import streamlit as st
from config import get_supabase, get_supabase_url, APP_NAME, APP_TAGLINE
from gotrue.errors import AuthApiError


def _inject_auth_styles():
    """Professional auth page styling."""
    st.markdown("""
    <style>
        .auth-container {
            max-width: 420px;
            margin: 0 auto;
            padding: 2.5rem 2rem;
        }
        .auth-brand {
            text-align: center;
            margin-bottom: 2rem;
        }
        .auth-brand h1 {
            font-size: 2rem;
            font-weight: 700;
            color: #e6edf3;
            margin-bottom: 0.25rem;
            letter-spacing: -0.5px;
        }
        .auth-brand p {
            color: #7d8590;
            font-size: 0.95rem;
            margin-top: 0;
        }
        .auth-divider {
            display: flex;
            align-items: center;
            margin: 1.5rem 0;
            color: #484f58;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .auth-divider::before,
        .auth-divider::after {
            content: '';
            flex: 1;
            border-bottom: 1px solid #30363d;
        }
        .auth-divider span {
            padding: 0 1rem;
        }
        .google-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.75rem;
            width: 100%;
            padding: 0.7rem 1rem;
            background: #21262d;
            border: 1px solid #30363d;
            border-radius: 8px;
            color: #e6edf3;
            font-size: 0.95rem;
            font-weight: 500;
            cursor: pointer;
            text-decoration: none;
            transition: background 0.15s, border-color 0.15s;
        }
        .google-btn:hover {
            background: #30363d;
            border-color: #484f58;
            color: #e6edf3;
        }
        .google-btn svg {
            width: 20px;
            height: 20px;
        }
        .auth-footer {
            text-align: center;
            margin-top: 1.5rem;
            color: #7d8590;
            font-size: 0.85rem;
        }
        .auth-footer a {
            color: #667eea;
            text-decoration: none;
        }
    </style>
    """, unsafe_allow_html=True)


def _google_oauth_url() -> str:
    """Build the Supabase Google OAuth redirect URL."""
    base = get_supabase_url()
    # Redirect back to the app after OAuth
    redirect_to = st.query_params.get("redirect_to", "")
    if not redirect_to:
        # Default: current app URL
        redirect_to = st.context.headers.get("Origin", "http://localhost:8501")
    return (
        f"{base}/auth/v1/authorize"
        f"?provider=google"
        f"&redirect_to={redirect_to}"
    )


def _handle_oauth_callback():
    """Check URL for OAuth tokens returned by Supabase after redirect."""
    access_token = st.query_params.get("access_token")
    refresh_token = st.query_params.get("refresh_token")

    if access_token and refresh_token:
        try:
            supabase = get_supabase()
            session = supabase.auth.set_session(access_token, refresh_token)
            if session and session.user:
                st.session_state.user = {
                    "id": session.user.id,
                    "email": session.user.email,
                    "name": session.user.user_metadata.get(
                        "full_name", session.user.email
                    ),
                    "avatar": session.user.user_metadata.get("avatar_url", ""),
                }
                st.session_state.access_token = access_token
                # Clear URL params
                st.query_params.clear()
                return True
        except Exception:
            pass
    return False


def check_auth() -> bool:
    """Check if user is authenticated. Returns True if logged in."""
    if "user" in st.session_state and st.session_state.user:
        return True
    # Check for OAuth callback
    return _handle_oauth_callback()


def get_current_user() -> dict | None:
    """Get the current authenticated user."""
    return st.session_state.get("user")


def sign_out():
    """Sign out the current user."""
    try:
        supabase = get_supabase()
        supabase.auth.sign_out()
    except Exception:
        pass
    for key in ["user", "access_token", "supabase_client"]:
        st.session_state.pop(key, None)


def render_auth_page():
    """Render the login/signup page."""
    _inject_auth_styles()

    st.markdown(f"""
    <div class="auth-container">
        <div class="auth-brand">
            <h1>{APP_NAME}</h1>
            <p>{APP_TAGLINE}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Center the form
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        # Google OAuth button
        google_url = _google_oauth_url()
        st.markdown(f"""
        <a href="{google_url}" class="google-btn">
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            Continue with Google
        </a>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="auth-divider"><span>or</span></div>
        """, unsafe_allow_html=True)

        # Tab between Sign In and Sign Up
        auth_mode = st.radio(
            "auth_mode",
            ["Sign In", "Create Account"],
            horizontal=True,
            label_visibility="collapsed",
        )

        if auth_mode == "Sign In":
            _render_sign_in()
        else:
            _render_sign_up()


def _render_sign_in():
    """Render email/password sign-in form."""
    with st.form("sign_in_form", clear_on_submit=False):
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password", placeholder="Your password")
        submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

    if submitted:
        if not email or not password:
            st.error("Please enter both email and password.")
            return
        try:
            supabase = get_supabase()
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })
            if response.user:
                st.session_state.user = {
                    "id": response.user.id,
                    "email": response.user.email,
                    "name": response.user.user_metadata.get(
                        "full_name", email.split("@")[0]
                    ),
                    "avatar": response.user.user_metadata.get("avatar_url", ""),
                }
                st.session_state.access_token = response.session.access_token
                st.rerun()
        except AuthApiError as e:
            st.error("Invalid email or password. Please try again.")
        except Exception as e:
            st.error(f"Something went wrong. Please try again.")


def _render_sign_up():
    """Render email/password sign-up form."""
    with st.form("sign_up_form", clear_on_submit=False):
        full_name = st.text_input("Full Name", placeholder="e.g. Michael Edwards")
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password", placeholder="At least 6 characters")
        password_confirm = st.text_input("Confirm Password", type="password", placeholder="Re-enter your password")
        submitted = st.form_submit_button("Create Account", use_container_width=True, type="primary")

    if submitted:
        if not full_name or not email or not password:
            st.error("Please fill in all fields.")
            return
        if password != password_confirm:
            st.error("Passwords do not match.")
            return
        if len(password) < 6:
            st.error("Password must be at least 6 characters.")
            return
        try:
            supabase = get_supabase()
            response = supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "full_name": full_name,
                    }
                },
            })
            if response.user:
                if response.user.confirmed_at:
                    st.session_state.user = {
                        "id": response.user.id,
                        "email": response.user.email,
                        "name": full_name,
                        "avatar": "",
                    }
                    st.session_state.access_token = response.session.access_token
                    st.rerun()
                else:
                    st.success(
                        "Account created. Check your email to confirm, then sign in."
                    )
        except AuthApiError as e:
            if "already registered" in str(e).lower():
                st.error("An account with this email already exists. Try signing in.")
            else:
                st.error("Could not create account. Please try again.")
        except Exception:
            st.error("Something went wrong. Please try again.")
