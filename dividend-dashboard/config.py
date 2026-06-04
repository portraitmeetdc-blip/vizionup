import streamlit as st
from supabase import create_client, Client

def get_supabase() -> Client:
    """Get or create a Supabase client using Streamlit secrets."""
    if "supabase_client" not in st.session_state:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["anon_key"]
        st.session_state.supabase_client = create_client(url, key)
    return st.session_state.supabase_client


def get_supabase_url() -> str:
    return st.secrets["supabase"]["url"]


def get_supabase_anon_key() -> str:
    return st.secrets["supabase"]["anon_key"]


# App constants
APP_NAME = "Vizion Income"
APP_TAGLINE = "Building generational wealth, together."
