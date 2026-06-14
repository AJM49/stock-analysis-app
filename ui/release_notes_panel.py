from __future__ import annotations

import streamlit as st

from release_notes import RELEASE_NOTES


def render_release_notes_panel():
    with st.sidebar.expander("Release Notes"):
        for release in RELEASE_NOTES:
            st.write("Version:", release["version"])
            st.write(release["title"])

            for change in release["changes"]:
                st.markdown("- " + change)
