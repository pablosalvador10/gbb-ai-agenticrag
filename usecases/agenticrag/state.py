import streamlit as st

from usecases.agenticrag.settings import AGENTS_KEY, CHAT_HISTORY_KEY


def init_session_state():
    if CHAT_HISTORY_KEY not in st.session_state:
        st.session_state[CHAT_HISTORY_KEY] = []
    if AGENTS_KEY not in st.session_state:
        # Initialize all agent instances ONCE
        st.session_state[AGENTS_KEY] = load_agents_from_configs()


def get_agents():
    return st.session_state[AGENTS_KEY]


def get_history():
    return st.session_state[CHAT_HISTORY_KEY]
