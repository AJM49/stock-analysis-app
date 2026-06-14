from __future__ import annotations

import streamlit as st


QUOTA_STATE_KEY = "market_data_quota_limited"


def set_market_data_quota_limited() -> None:
    st.session_state[QUOTA_STATE_KEY] = True


def clear_market_data_quota_limited() -> None:
    st.session_state[QUOTA_STATE_KEY] = False


def is_market_data_quota_limited() -> bool:
    return bool(st.session_state.get(QUOTA_STATE_KEY, False))
