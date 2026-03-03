import os

import streamlit as st
from dotenv import load_dotenv

# --- Page Config ---
st.set_page_config(
    page_title="GitLab Compliance Checker",
    page_icon="🔍",
    layout="wide",
)

# Load environment variables
load_dotenv()

# Import local modules
try:
    from gitlab_utils import users
    from gitlab_utils.client import GitLabClient
    from modes.batch_mode import render_batch_mode_ui

    # New UI Modules
    from modes.compliance_mode import render_compliance_mode
    from modes.contribution_mapping import render_contribution_mapping_mode
    from modes.user_profile import render_user_profile

except ImportError as e:
    st.error(f"Import Error: {e}")
    st.stop()


def main():
    st.title("GitLab Compliance & Analytics Tool")

    # Sidebar: Config & Mode
    st.sidebar.header("Configuration")

    # Credentials (allow override or from env or Streamlit secrets)
    default_url = os.getenv("GITLAB_URL")
    if not default_url:
        try:
            default_url = st.secrets.get("GITLAB_URL", "https://code.swecha.org")
        except:
            default_url = "https://code.swecha.org"

    default_token = os.getenv("GITLAB_TOKEN")
    if not default_token:
        try:
            default_token = st.secrets.get("GITLAB_TOKEN", "")
        except:
            default_token = ""

    gitlab_url = st.sidebar.text_input("GitLab URL", value=default_url)
    gitlab_token = st.sidebar.text_input("GitLab Token", value=default_token, type="password")

    mode = st.sidebar.radio(
        "Select Mode",
        [
            "Check Project Compliance",
            "Contribution Mapping",
            "Batch 2026 ICFAI",
            "Batch 2026 RCTS",
        ],
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### About")
    st.sidebar.info(
        "Refactored Tool:\n"
        "- Project Compliance\n"
        "- User Analytics (Single & Batch)\n"
        "- Groups, MRs, Issues, Commits"
    )

    if not gitlab_token:
        st.warning("Please enter a GitLab Token in the sidebar or .env file.")
        st.stop()

    # Initialize Client
    client = GitLabClient(gitlab_url, gitlab_token)
    if not client.client:
        st.error("Failed to initialize GitLab client. Check URL and Token.")
        st.stop()

    # Track previous mode to reset nested state when changing modes
    if "previous_mode" not in st.session_state:
        st.session_state.previous_mode = None

    # Reset Contribution Mapping state when leaving that mode
    if st.session_state.previous_mode == "Contribution Mapping" and mode != "Contribution Mapping":
        st.session_state.contribution_sub_mode = None
        st.session_state.contribution_view_type = None

    # Update previous mode
    st.session_state.previous_mode = mode

    # Routing
    if mode == "Check Project Compliance":
        # Compliance mode expects the python-gitlab object for now (legacy compatibility)
        # We might want to refactor compliance_mode.py later, but for now passing .client works
        render_compliance_mode(client.client)

    elif mode == "Contribution Mapping":
        # Contribution Mapping mode with nested button flow
        st.subheader("🗺 Contribution Mapping")

        # Initialize session state for Contribution Mapping if not set
        if "contribution_sub_mode" not in st.session_state:
            st.session_state.contribution_sub_mode = None
        if "contribution_view_type" not in st.session_state:
            st.session_state.contribution_view_type = None

        # Step 1: Show buttons for User Profile Overview and Team
        sub_mode_choice = st.radio(
            "Select Analysis Type",
            ["User Profile Overview", "Team"],
            horizontal=True,
            key="sub_mode_radio",
            index=None,
        )

        # Update session state when user makes a selection
        if sub_mode_choice is not None:
            st.session_state.contribution_sub_mode = sub_mode_choice

        # Only show Step 2 if user has selected an analysis type
        if st.session_state.contribution_sub_mode is not None:
            st.markdown("---")

            if st.session_state.contribution_sub_mode == "User Profile Overview":
                # Show User Profile Overview with username input first
                st.subheader("👤 User Profile Overview")
                user_input = st.text_input(
                    "Enter Username", placeholder="username", key="main_user_input"
                )

                # Only show Select View after username is entered
                if user_input:
                    st.markdown("---")
                    contribution_type = st.radio(
                        "Select View",
                        ["Contribution", "Graphical"],
                        horizontal=True,
                        key="view_type_radio",
                        index=None,
                    )

                    # Update session state when user makes a selection
                    if contribution_type is not None:
                        st.session_state.contribution_view_type = contribution_type

                    # Only show content if user has selected a view type
                    if st.session_state.contribution_view_type is not None:
                        st.markdown("---")

                        if st.session_state.contribution_view_type == "Contribution":
                            # Show the User Profile Overview content
                            with st.spinner(f"Finding user '{user_input}'..."):
                                user_info = users.get_user_by_username(client, user_input)

                            if user_info:
                                render_user_profile(client, user_info)
                            else:
                                st.error(f"User '{user_input}' not found.")
                        else:
                            # Show Graphical view - call render_graphical_view
                            from modes.contribution_mapping import render_graphical_view

                            render_graphical_view(client, user_input)

            elif st.session_state.contribution_sub_mode == "Team":
                # Show Team mapping
                from modes.contribution_mapping import render_team_mapping

                render_team_mapping(client)

    elif mode == "Batch 2026 ICFAI":
        render_batch_mode_ui(client, "ICFAI")

    elif mode == "Batch 2026 RCTS":
        render_batch_mode_ui(client, "RCTS")


if __name__ == "__main__":
    main()
