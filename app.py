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

    # Credentials (allow override or from env)
    default_url = os.getenv("GITLAB_URL", "https://gitlab.com")
    default_token = os.getenv("GITLAB_TOKEN", "")

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

    # Routing
    if mode == "Check Project Compliance":
        # Compliance mode expects the python-gitlab object for now (legacy compatibility)
        # We might want to refactor compliance_mode.py later, but for now passing .client works
        render_compliance_mode(client.client)

    elif mode == "Contribution Mapping":
        # Contribution Mapping mode with nested button flow
        st.subheader("🗺 Contribution Mapping")
        
        # Step 1: Show buttons for User Profile Overview and Team
        sub_mode_choice = st.radio(
            "Select Analysis Type",
            ["User Profile Overview", "Team"],
            horizontal=True
        )
        
        st.markdown("---")
        
        if sub_mode_choice == "User Profile Overview":
            # Step 2: Show buttons for Contribution and Graphical
            contribution_type = st.radio(
                "Select View",
                ["Contribution", "Graphical"],
                horizontal=True
            )
            
            st.markdown("---")
            
            if contribution_type == "Contribution":
                # Show the User Profile Overview content
                st.subheader("👤 User Profile Overview")
                user_input = st.text_input("Enter Username", placeholder="username")
                
                if user_input:
                    with st.spinner(f"Finding user '{user_input}'..."):
                        user_info = users.get_user_by_username(client, user_input)
                    
                    if user_info:
                        render_user_profile(client, user_info)
                    else:
                        st.error(f"User '{user_input}' not found.")
            else:
                # Show single-user Contribution Mapping (Graphical)
                # Import and call the single user mapping directly
                from modes.contribution_mapping import render_single_user_mapping
                render_single_user_mapping(client)
        
        elif sub_mode_choice == "Team":
            # Show Team mapping
            from modes.contribution_mapping import render_team_mapping
            render_team_mapping(client)


if __name__ == "__main__":
    main()
