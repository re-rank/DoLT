"""Streamlit SessionState 관리."""

from __future__ import annotations

import streamlit as st

from dolt.models.config import DoltConfig
from dolt.storage.local_store import LocalStore


def init_state() -> None:
    """세션 상태를 초기화한다."""
    if "config" not in st.session_state:
        st.session_state.config = DoltConfig.load()
    if "store" not in st.session_state:
        st.session_state.store = LocalStore(st.session_state.config.storage.path)


def get_config() -> DoltConfig:
    return st.session_state.config


def get_store() -> LocalStore:
    return st.session_state.store
