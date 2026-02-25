"""
Contribution Mapping Mode for GitLab Compliance & Analytics Tool

This module provides two sub-modes:
1. Single User Mapping - Individual contribution analysis
2. Team Mapping - Multi-user contribution analysis
"""

import json
import os
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

import gitlab_utils.issues as issue_utils
import gitlab_utils.merge_requests as mr_utils
from gitlab_utils import users

# ============================================================================
# HELPER FUNCTIONS - CACHED PROJECT LOOKUP
# ============================================================================


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_project_details(base_url, private_token, project_id):
    """
    Fetch project details from GitLab API with caching.

    Uses @st.cache_data to avoid repeated API calls for the same project.
    Cached for 1 hour (3600 seconds) to improve performance.

    Args:
        base_url: GitLab instance URL
        private_token: GitLab API token
        project_id: The project ID to fetch

    Returns:
        Dictionary with project details including path_with_namespace and web_url, or None on error
    """
    import requests

    if not project_id:
        return None

    try:
        url = f"{base_url}/api/v4/projects/{project_id}"
        headers = {"PRIVATE-TOKEN": private_token}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching project {project_id}: {e}")
        return None


def make_project_clickable(project_name, web_url):
    """
    Create a clickable markdown link for the project name.

    Args:
        project_name: The display name for the project
        web_url: The web URL to link to

    Returns:
        Markdown string with clickable link
    """
    if web_url and project_name and project_name != "-":
        return f"[{project_name}]({web_url})"
    return project_name


def get_project_name(client, project_id, project_cache):
    """
    Fetch project name from GitLab API using project_id with caching.

    Args:
        client: GitLab client instance
        project_id: The project ID from the event
        project_cache: Dictionary to cache fetched project names

    Returns:
        Tuple of (project_name, web_url) or ("-", None) if not found
    """
    if not project_id:
        return "-", None

    # Check in-memory cache first (for current request)
    # Cache stores tuple: (project_name, web_url)
    if project_cache and project_id in project_cache:
        cached = project_cache[project_id]
        if isinstance(cached, tuple):
            return cached
        return cached, None

    try:
        # Use cached API call via st.cache_data
        # Extract base_url and token from client
        base_url = client.base_url
        private_token = client.headers.get("PRIVATE-TOKEN", "")

        # Call cached function
        project = fetch_project_details(base_url, private_token, project_id)

        if project and isinstance(project, dict):
            # Prefer path_with_namespace (more descriptive), fall back to name
            project_name = project.get("path_with_namespace") or project.get("name", "-")
            web_url = project.get("web_url")
            if project_cache is not None:
                project_cache[project_id] = (project_name, web_url)
            return project_name, web_url
        else:
            if project_cache is not None:
                project_cache[project_id] = ("-", None)
            return "-", None
    except Exception as e:
        print(f"Error fetching project {project_id}: {e}")
        if project_cache is not None:
            project_cache[project_id] = ("-", None)
        return "-", None


def get_user_events(client, user_id, start_date, end_date, show_debug=False):
    """
    Fetch user events from GitLab API with date filtering.

    Note: GitLab's 'before' parameter is exclusive, so we add 1 day to make
    the end date inclusive. This ensures events on the selected end date are included.

    Args:
        client: GitLab client instance
        user_id: GitLab user ID
        start_date: Start date for filtering
        end_date: End date for filtering
        show_debug: Whether to show debug logs (default: False)
    """
    # Make end_date inclusive by adding 1 day
    # This fixes the issue where selecting 2026/02/21 → 2026/02/22 would
    # exclude all events on February 22nd
    inclusive_end_date = end_date + timedelta(days=1)

    after_date = start_date.isoformat()
    before_date = inclusive_end_date.isoformat()

    # Debug logging (only if enabled)
    if show_debug:
        st.write(f"📅 Date Filter: {start_date} → {end_date} (inclusive)")
        st.write(f"   GitLab API: after={after_date}, before={before_date}")

    endpoint = f"/users/{user_id}/events"
    params = {"after": after_date, "before": before_date, "per_page": 100}

    try:
        events = client._get_paginated(endpoint, params=params, per_page=100, max_pages=10)
        if show_debug:
            st.write(f"   Raw events fetched: {len(events) if events else 0}")
        return events if events else []
    except Exception as e:
        st.warning(f"Could not fetch events: {e}")
        return []


def process_events(events, client=None, project_cache=None):
    """
    Process GitLab events to extract relevant fields.

    Args:
        events: List of GitLab events
        client: GitLab client instance (optional, for fetching project names)
        project_cache: Dictionary to cache project names by project_id

    Returns:
        List of processed event dictionaries with project_name (clickable) and web_url
    """
    # Initialize cache if not provided
    if project_cache is None:
        project_cache = {}

    processed = []
    for event in events or []:
        created_at = event.get("created_at")
        event_date = "-"
        event_time = "-"

        if created_at:
            try:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                event_date = dt.strftime("%Y-%m-%d")
                event_time = dt.strftime("%H:%M")
            except Exception:
                pass

        # Try to get project name - prioritize project_id since GitLab Events API
        # typically returns project_id directly, not nested project objects
        # Use cached API call to get project name via project_id
        project_name = "-"
        web_url = None
        if client and event.get("project_id"):
            # Use cached API call to get project name and web_url
            project_name, web_url = get_project_name(client, event.get("project_id"), project_cache)
        elif event.get("project"):
            # Fallback: check for nested project object (rare in Events API)
            project = event.get("project", {})
            project_name = project.get("name", "-")
            web_url = project.get("web_url")

        # Create clickable project name
        project_name_display = make_project_clickable(project_name, web_url)

        processed.append(
            {
                "created_at": created_at or "-",
                "date": event_date,
                "time": event_time,
                "action_name": event.get("action_name", "-"),
                "target_type": event.get("target_type", "-"),
                "project_name": project_name_display,
                "project_web_url": web_url,
                "target_title": event.get("target_title", "-") or "-",
            }
        )
    return processed


def calculate_streak(sorted_dates):
    """
    Calculate the longest streak of consecutive active days.
    """
    if not sorted_dates:
        return 0

    longest_streak = 1
    current_streak = 1

    for i in range(1, len(sorted_dates)):
        try:
            prev_date = datetime.strptime(sorted_dates[i - 1], "%Y-%m-%d").date()
            curr_date = datetime.strptime(sorted_dates[i], "%Y-%m-%d").date()

            if (curr_date - prev_date).days == 1:
                current_streak += 1
                longest_streak = max(longest_streak, current_streak)
            else:
                current_streak = 1
        except Exception:
            current_streak = 1

    return longest_streak


def classify_activity(total_contributions, active_days, consistency_pct):
    """
    Classify user activity based on contributions and consistency.
    """
    if total_contributions == 0:
        return "⚫ No Activity"

    avg_per_day = total_contributions / active_days if active_days > 0 else 0

    if consistency_pct >= 70 and avg_per_day >= 5:
        return "🔥 Highly Active - Consistent Contributor"
    elif consistency_pct >= 50 and avg_per_day >= 3:
        return "🟢 Active - Regular Contributor"
    elif consistency_pct >= 30 and avg_per_day >= 1:
        return "🟡 Moderate - Occasional Contributor"
    elif total_contributions > 0:
        return "🔵 Light - Minimal Activity"
    else:
        return "⚫ No Activity"

    # ============================================================================
    # 1️⃣ SINGLE USER MAPPING
    # ============================================================================


def render_single_user_mapping(client):
    """
    Render Single User Mapping interface.
    """
    st.markdown("### 📊 Single User Contribution Mapping")

    # Input fields
    col1, col2, col3 = st.columns(3)
    with col1:
        username = st.text_input("Username", placeholder="Enter GitLab username")
    with col2:
        today = date.today()
        default_start = today - timedelta(days=30)
        start_date = st.date_input("Start Date", value=default_start, max_value=today)
    with col3:
        end_date = st.date_input("End Date", value=today, min_value=start_date, max_value=today)

    if not username:
        st.info("Please enter a username to analyze contributions.")
        return

    col1, col2 = st.columns([2, 1])
    with col1:
        username = st.text_input(
            "Enter Username", placeholder="Enter GitLab username", key="user_profile_username"
        )

    # Only show view selection and content after username is entered
    if username:
        st.markdown("---")

        # Select View radio
        selected_view = st.radio("Select View", ["Contribution", "Graphical"], horizontal=True)

        st.markdown("---")

        if selected_view == "Contribution":
            render_contribution_view(client, username)
        elif selected_view == "Graphical":
            render_graphical_view(client, username)


def render_contribution_view(client, username):
    """
    Render Contribution view - tabular data format with detailed metrics.
    """
    # Date range inputs
    col1, col2 = st.columns(2)
    today = date.today()
    default_start = today - timedelta(days=30)

    with col1:
        start_date = st.date_input(
            "Start Date", value=default_start, max_value=today, key="contrib_start"
        )
    with col2:
        end_date = st.date_input(
            "End Date", value=today, min_value=start_date, max_value=today, key="contrib_end"
        )

        st.error("❌ Start Date cannot be after End Date.")
        return

    # Fetch user
    with st.spinner(f"Finding user '{username}'..."):
        user_info = users.get_user_by_username(client, username)

    if not user_info:
        st.error(f"User '{username}' not found.")
        return

    user_id = user_info.get("id")
    user_name = user_info.get("name")
    avatar_url = user_info.get("avatar_url")

    # Display user info
    col1, col2 = st.columns([1, 5])
    with col1:
        if avatar_url:
            st.image(avatar_url, width=80)
    with col2:
        st.markdown(f"**{user_name}** (@{username})")

    # Fetch events
    cache_key = f"contrib_events_{user_id}_{start_date}_{end_date}"

    with st.spinner(f"Fetching contributions from {start_date} to {end_date}..."):
        if cache_key not in st.session_state:
            events = get_user_events(client, user_id, start_date, end_date)
            st.session_state[cache_key] = events
        else:
            events = st.session_state[cache_key]

    # Initialize project cache for this user/date range
    project_cache_key = f"contrib_project_cache_{user_id}_{start_date}_{end_date}"
    if project_cache_key not in st.session_state:
        st.session_state[project_cache_key] = {}
    project_cache = st.session_state[project_cache_key]

    # Process events with project name resolution (using caching)
    processed_events = process_events(events, client=client, project_cache=project_cache)

    # Calculate metrics
    total_contributions = len(processed_events)

    # Group by date
    date_counts = {}
    for event in processed_events:
        event_date = event.get("date", "-")
        if event_date and event_date != "-":
            date_counts[event_date] = date_counts.get(event_date, 0) + 1

    sorted_dates = sorted(date_counts.keys())
    active_days = len(sorted_dates)

    total_days = (end_date - start_date).days + 1
    consistency_pct = (active_days / total_days * 100) if total_days > 0 else 0
    avg_contributions = total_contributions / active_days if active_days > 0 else 0
    longest_streak = calculate_streak(sorted_dates)

    # Count MRs (merged, opened, closed)
    mr_events = [e for e in processed_events if e.get("target_type") == "MergeRequest"]
    mr_opened = len([e for e in mr_events if e.get("action_name") in ["opened", "reopened"]])
    mr_merged = len([e for e in mr_events if e.get("action_name") == "merged"])
    mr_closed = len([e for e in mr_events if e.get("action_name") == "closed"])
    total_mrs = len(mr_events)

    # Count Issues (opened, closed)
    issue_events = [e for e in processed_events if e.get("target_type") == "Issue"]
    issue_opened = len([e for e in issue_events if e.get("action_name") in ["opened", "reopened"]])
    issue_closed = len([e for e in issue_events if e.get("action_name") == "closed"])
    total_issues = len(issue_events)

    # Count Commits (push events)
    total_commits = len([e for e in processed_events if e.get("action_name") == "pushed"])
    # Activity classification
    activity_class = classify_activity(total_contributions, active_days, consistency_pct)

    # ==================== SUMMARY CARDS ====================
    st.markdown("#### 📊 Contribution Summary")

    # Main metrics row
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("Total Commits", total_commits)
    sc2.metric("Total MRs", total_mrs)
    sc3.metric("Total Issues", total_issues)
    sc4.metric("Active Days", active_days)

    # MR breakdown
    st.markdown("##### 📥 Merge Requests")
    mr_col1, mr_col2, mr_col3 = st.columns(3)
    mr_col1.metric("Opened", mr_opened)
    mr_col2.metric("Merged", mr_merged)
    mr_col3.metric("Closed", mr_closed)

    # Issue breakdown
    st.markdown("##### 🐛 Issues")
    issue_col1, issue_col2 = st.columns(2)
    issue_col1.metric("Opened", issue_opened)
    issue_col2.metric("Closed", issue_closed)

    # Activity classification
    st.markdown(f"**Activity Classification:** {activity_class}")

    if total_contributions == 0:
        st.info(f"ℹ️ No contributions found between {start_date} and {end_date}.")
        return

    # ==================== CONTRIBUTION TABLE ====================
    st.markdown("#### 📋 Contribution Details")

    if processed_events:
        df_events = pd.DataFrame(processed_events)
        # Display the table
        st.dataframe(df_events, use_container_width=True)

        # Export option
        csv = df_events.to_csv(index=False)
        st.download_button(
            label="Download Contributions CSV",
            data=csv,
            file_name=f"{username}_contributions.csv",
            mime="text/csv",
        )


def render_graphical_view(client, username):
    """
    Render Graphical view - charts and visualizations.
    """
    # Date range inputs
    col1, col2 = st.columns(2)
    today = date.today()
    default_start = today - timedelta(days=30)

    with col1:
        start_date = st.date_input(
            "Start Date", value=default_start, max_value=today, key="graph_start"
        )
    with col2:
        end_date = st.date_input(
            "End Date", value=today, min_value=start_date, max_value=today, key="graph_end"
        )

    if start_date > end_date:
        st.error("❌ Start Date cannot be after End Date.")
        return

    # Fetch user
    with st.spinner(f"Finding user '{username}'..."):
        user_info = users.get_user_by_username(client, username)

    if not user_info:
        st.error(f"User '{username}' not found.")
        return

    user_id = user_info.get("id")
    user_name = user_info.get("name")
    avatar_url = user_info.get("avatar_url")

    # Display user info
    col1, col2 = st.columns([1, 5])
    with col1:
        if avatar_url:
            st.image(avatar_url, width=80)
    with col2:
        st.markdown(f"**{user_name}** (@{username})")

    # Fetch events
    cache_key = f"graph_events_{user_id}_{start_date}_{end_date}"

    with st.spinner(f"Fetching contributions from {start_date} to {end_date}..."):
        if cache_key not in st.session_state:
            events = get_user_events(client, user_id, start_date, end_date)
            st.session_state[cache_key] = events
        else:
            events = st.session_state[cache_key]

    # Initialize project cache for this user/date range
    project_cache_key = f"graph_project_cache_{user_id}_{start_date}_{end_date}"
    if project_cache_key not in st.session_state:
        st.session_state[project_cache_key] = {}
    project_cache = st.session_state[project_cache_key]

    # Process events with project name resolution (using caching)
    processed_events = process_events(events, client=client, project_cache=project_cache)

    # Calculate metrics
    total_contributions = len(processed_events)

    # Group by date
    date_counts = {}
    for event in processed_events:
        event_date = event.get("date", "-")
        if event_date and event_date != "-":
            date_counts[event_date] = date_counts.get(event_date, 0) + 1

    sorted_dates = sorted(date_counts.keys())
    active_days = len(sorted_dates)

    total_days = (end_date - start_date).days + 1
    consistency_pct = (active_days / total_days * 100) if total_days > 0 else 0
    avg_contributions = total_contributions / active_days if active_days > 0 else 0
    longest_streak = calculate_streak(sorted_dates)

    # Activity classification
    activity_class = classify_activity(total_contributions, active_days, consistency_pct)

    # ==================== CONTRIBUTION ANALYTICS (DATE RANGE) ====================
    st.markdown("#### 📊 Contribution Analytics (Date Range)")

    # Main metrics row
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("Total Contributions", total_contributions)
    sc2.metric("Active Days", active_days)
    sc3.metric("Avg/Active Day", f"{avg_contributions:.1f}")
    sc4.metric("Longest Streak", f"{longest_streak} days")

    st.markdown(f"**Activity Classification:** {activity_class}")

    if total_contributions == 0:
        st.info(f"ℹ️ No contributions found between {start_date} and {end_date}.")
        return

    # Create consistency visualization
    consistency_data = []
    for d, count in date_counts.items():
        consistency_data.append({"date": d, "contributions": count, "level": "Active"})

    # Fill in inactive days
    full_range = pd.date_range(start=start_date, end=end_date)
    for d in full_range:
        d_str = d.strftime("%Y-%m-%d")
        if d_str not in date_counts:
            consistency_data.append({"date": d_str, "contributions": 0, "level": "Inactive"})

    if consistency_data:
        df_consistency = pd.DataFrame(consistency_data)
        df_consistency["date"] = pd.to_datetime(df_consistency["date"])
        df_consistency = df_consistency.sort_values("date")

        fig_consistency = px.bar(
            df_consistency,
            x="date",
            y="contributions",
            color="level",
            color_discrete_map={"Active": "#00CC96", "Inactive": "#636EFA"},
            title="Consistency Index - Active vs Inactive Days",
            labels={"date": "Date", "contributions": "Contributions", "level": "Status"},
        )
        fig_consistency.update_layout(template="plotly_dark")
        st.plotly_chart(fig_consistency, use_container_width=True)

    # ==================== CALENDAR HEATMAP ====================
    st.markdown("#### 📅 Calendar Heatmap")

    # Create heatmap data
    heatmap_data = []
    for d, count in date_counts.items():
        heatmap_data.append({"date": d, "contributions": count})

    if heatmap_data:
        df_heatmap = pd.DataFrame(heatmap_data)
        df_heatmap["date"] = pd.to_datetime(df_heatmap["date"])
        df_heatmap = df_heatmap.sort_values("date")

        # Create a complete date range and fill missing dates with 0
        full_range = pd.date_range(start=start_date, end=end_date)
        df_full = pd.DataFrame({"date": full_range})
        df_full = df_full.merge(df_heatmap, on="date", how="left").fillna(0)

        # Create heatmap using Plotly
        fig_heatmap = px.scatter(
            df_full,
            x="date",
            y="contributions",
            size="contributions",
            color="contributions",
            color_continuous_scale="Viridis",
            size_max=20,
            title="Contribution Calendar Heatmap",
            labels={"date": "Date", "contributions": "Contributions"},
        )
        fig_heatmap.update_layout(
            xaxis_title="Date", yaxis_title="Contribution Count", template="plotly_dark"
        )
        st.plotly_chart(fig_heatmap, use_container_width=True)

    # ==================== CONTRIBUTION TYPE PIE CHART ====================
    st.markdown("#### 🥧 Contribution Types")

    action_counts = {}
    for event in processed_events:
        action = event.get("action_name", "-")
        action_counts[action] = action_counts.get(action, 0) + 1

    if action_counts:
        df_pie = pd.DataFrame(list(action_counts.items()), columns=["Type", "Count"])

        fig_pie = px.pie(
            df_pie,
            values="Count",
            names="Type",
            title="Contribution Type Distribution",
            color_discrete_sequence=px.colors.qualitative.Set3,
        )
        fig_pie.update_layout(template="plotly_dark")
        st.plotly_chart(fig_pie, use_container_width=True)

    # ==================== TIME-OF-DAY BAR CHART ====================
    st.markdown("#### 🕐 Time of Day Activity")

    # Group by hour
    hour_counts = {}
    for event in processed_events:
        event_time = event.get("time", "-")
        if event_time and event_time != "-":
            try:
                hour = int(event_time.split(":")[0])
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
            except Exception:
                pass

    if hour_counts:
        # Create time buckets
        time_buckets = {
            "Morning (6-12)": 0,
            "Afternoon (12-17)": 0,
            "Evening (17-21)": 0,
            "Night (21-6)": 0,
        }

        for hour, count in hour_counts.items():
            if 6 <= hour < 12:
                time_buckets["Morning (6-12)"] += count
            elif 12 <= hour < 17:
                time_buckets["Afternoon (12-17)"] += count
            elif 17 <= hour < 21:
                time_buckets["Evening (17-21)"] += count
            else:
                time_buckets["Night (21-6)"] += count

        df_time = pd.DataFrame(list(time_buckets.items()), columns=["Time Period", "Count"])

        fig_bar = px.bar(
            df_time,
            x="Time Period",
            y="Count",
            title="Activity by Time of Day",
            color="Time Period",
            color_discrete_sequence=px.colors.qualitative.Bold,
        )
        fig_bar.update_layout(template="plotly_dark", showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)


# ============================================================================
# 2️⃣ TEAM MAPPING
# ============================================================================


def load_teams():
    """
    Load teams from teams.json file.
    Returns a dictionary of team_name -> list of usernames.
    """
    teams_file = "teams.json"

    if not os.path.exists(teams_file):
        return {}

    try:
        with open(teams_file, "r") as f:
            teams_data = json.load(f)

        # Convert list of {username: ...} to simple list of usernames
        teams = {}
        for team_name, members in teams_data.items():
            teams[team_name] = [
                member.get("username", "") for member in members if member.get("username")
            ]

        return teams
    except Exception as e:
        st.warning(f"Error loading teams.json: {e}")
        return {}


def render_team_mapping(client):
    """
    Render Team Mapping interface with professional dashboard layout.
    """
    st.markdown("### 👥 Team Contribution Dashboard")

    # Load teams from teams.json
    teams = load_teams()

    if not teams:
        st.error("⚠️ No teams found. Please ensure teams.json exists in the project root.")
        return

    team_names = list(teams.keys())

    # Team selection
    team_name = st.selectbox(
        "Select Team", ["Select a Team"] + team_names, index=0, key="team_select"
    )

    if team_name == "Select a Team":
        st.info("Please select a team to view members.")
        st.stop()

    usernames = teams.get(team_name, [])

    st.divider()

    # ==================== TEAM MEMBERS DASHBOARD ====================
    st.markdown("#### 👥 Team Members")

    # Create professional member cards layout
    if usernames:
        # Display members in columns (max 4 per row)
        cols_per_row = 4
        for i in range(0, len(usernames), cols_per_row):
            row_cols = st.columns(cols_per_row)
            for j, username in enumerate(usernames[i : i + cols_per_row]):
                with row_cols[j]:
                    st.info(f"👤 {username}")

    st.divider()

    # ==================== DATE RANGE SELECTION ====================
    col1, col2, col3 = st.columns([1, 1, 1])
    today = date.today()
    default_start = today - timedelta(days=30)

    with col1:
        start_date = st.date_input(
            "Start Date", value=default_start, max_value=today, key="batch_start"
        )
    with col2:
        end_date = st.date_input(
            "End Date", value=today, min_value=start_date, max_value=today, key="batch_end"
        )
    with col3:
        # Show date range summary
        date_range_days = (end_date - start_date).days + 1
        st.markdown("##### 📅 Date Range")
        st.markdown(f"**{date_range_days} days**")

    # Debug logs checkbox
    show_debug = st.checkbox("Show Debug Logs", value=False, key="show_debug")

    st.divider()

    if start_date > end_date:
        st.error("❌ Start Date cannot be after End Date.")
        return

    if st.button("Run Team Analysis", type="primary"):
        st.info(f"Processing {len(usernames)} users...")

        # Initialize project cache for this analysis
        project_cache = {}

        results = []
        total_contributions_all = 0
        progress_bar = st.progress(0)

        for i, username in enumerate(usernames):
            progress_bar.progress((i + 1) / len(usernames))

            with st.spinner(f"Processing {username}..."):
                # Fetch user
                user_info = users.get_user_by_username(client, username)

                if not user_info:
                    results.append(
                        {
                            "username": username,
                            "status": "Error",
                            "error": "User not found",
                            "total_contributions": 0,
                            "active_days": 0,
                            "consistency_pct": 0,
                            "collaboration_pct": 0,
                            "merge_requests_count": 0,
                            "issues_count": 0,
                        }
                    )
                    continue

                user_id = user_info.get("id")
                user_name = user_info.get("name", "")

                # Fetch events (pass show_debug to control debug output)
                events = get_user_events(
                    client, user_id, start_date, end_date, show_debug=show_debug
                )
                # Pass client and project_cache for proper project name resolution
                processed = process_events(events, client=client, project_cache=project_cache)

                # Debug: Count different event types (only if debug is enabled)
                commits = [e for e in processed if e.get("action_name") == "pushed"]
                mrs = [e for e in processed if e.get("target_type") == "MergeRequest"]
                issues = [e for e in processed if e.get("target_type") == "Issue"]

                # Debug logging for each user (hidden behind checkbox)
                if show_debug:
                    with st.expander(f"Debug: {username}", expanded=False):
                        st.write(f"**User:** {user_name} (@{username})")
                        st.write(f"**Start Date:** {start_date}")
                        st.write(f"**End Date:** {end_date}")
                        st.write(f"**Filtered Commits:** {len(commits)}")
                        st.write(f"**Filtered MRs:** {len(mrs)}")
                        st.write(f"**Filtered Issues:** {len(issues)}")
                        st.write(f"**Total Events:** {len(processed)}")

                        # Show project names if available
                        project_names = set(
                            e.get("project_name", "-")
                            for e in processed
                            if e.get("project_name") != "-"
                        )
                        if project_names:
                            st.write(f"**Projects:** {', '.join(project_names)}")

                # Calculate metrics
                total_contributions = len(processed)
                total_contributions_all += total_contributions

                date_counts = {}
                for event in processed:
                    event_date = event.get("date", "-")
                    if event_date and event_date != "-":
                        date_counts[event_date] = date_counts.get(event_date, 0) + 1

                active_days = len(date_counts)
                total_days = (end_date - start_date).days + 1
                consistency_pct = (active_days / total_days * 100) if total_days > 0 else 0

                # Collaboration % - based on events that involve others
                collaboration_events = sum(
                    1
                    for e in processed
                    if e.get("action_name") in ["merged", "accepted", "commented", "closed"]
                )
                collaboration_pct = (
                    (collaboration_events / total_contributions * 100)
                    if total_contributions > 0
                    else 0
                )

                # Fetch Merge Requests count for this user
                mr_count = 0
                try:
                    _, mr_stats = mr_utils.get_user_mrs(client, user_id, start_date, end_date)
                    mr_count = mr_stats.get("total", 0) if mr_stats else 0
                except Exception as e:
                    if show_debug:
                        st.warning(f"Error fetching MRs for {username}: {e}")

                # Fetch Issues count for this user
                issue_count = 0
                try:
                    _, issue_stats = issue_utils.get_user_issues(
                        client, user_id, start_date, end_date
                    )
                    issue_count = issue_stats.get("total", 0) if issue_stats else 0
                except Exception as e:
                    if show_debug:
                        st.warning(f"Error fetching Issues for {username}: {e}")

                results.append(
                    {
                        "username": username,
                        "user_name": user_name,
                        "status": "Success",
                        "total_contributions": total_contributions,
                        "active_days": active_days,
                        "consistency_pct": consistency_pct,
                        "collaboration_pct": collaboration_pct,
                        "merge_requests_count": mr_count,
                        "issues_count": issue_count,
                    }
                )

        progress_bar.empty()

        # Display results
        st.success("✅ Team analysis complete!")

        st.divider()

        # ==================== METRIC CARDS ====================
        st.markdown("#### 📊 Team Overview")

        # Calculate aggregate metrics
        successful_results = [r for r in results if r.get("status") == "Success"]
        total_members = len(usernames)
        successful_members = len(successful_results)

        # Calculate total MRs and Issues
        total_mrs = sum(r.get("merge_requests_count", 0) for r in successful_results)
        total_issues = sum(r.get("issues_count", 0) for r in successful_results)

        # Create metric cards
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric(
                label="Total Members", value=total_members, delta=f"{successful_members} successful"
            )
        with m2:
            st.metric(label="Total Contributions", value=total_contributions_all)
        with m3:
            st.metric(label="Total Merge Requests", value=total_mrs)
        with m4:
            st.metric(label="Total Issues", value=total_issues)

        # Show date range info
        date_range_str = f"{start_date} → {end_date}"
        st.info(f"📅 Analysis Period: {date_range_str}")

        st.divider()

        # ==================== SUMMARY TABLE ====================
        st.markdown("#### 📋 Team Summary")

        if results:
            df_results = pd.DataFrame(results)

            # Format columns
            df_results["consistency_pct"] = df_results["consistency_pct"].round(1)
            df_results["collaboration_pct"] = df_results["collaboration_pct"].round(1)

            # Rename columns for better display
            df_results = df_results.rename(
                columns={
                    "merge_requests_count": "MRs",
                    "issues_count": "Issues",
                    "total_contributions": "Contributions",
                    "active_days": "Active Days",
                    "consistency_pct": "Consistency %",
                    "collaboration_pct": "Collaboration %",
                }
            )

            # Display clean dataframe
            st.dataframe(df_results, use_container_width=True, hide_index=True)

            # ==================== BAR CHART ====================
            st.markdown("#### 📊 Contributions per User")

            if successful_results:
                df_chart = pd.DataFrame(successful_results)
                df_chart = df_chart.sort_values("total_contributions", ascending=True)

                # Highlight top 3
                df_chart["highlight"] = (
                    df_chart["total_contributions"]
                    >= df_chart["total_contributions"].nlargest(3).min()
                )

                fig_bar = px.bar(
                    df_chart,
                    x="username",
                    y="total_contributions",
                    title="Total Contributions per User",
                    color="highlight",
                    color_discrete_map={True: "#00CC96", False: "#636EFA"},
                    labels={"username": "User", "total_contributions": "Contributions"},
                )
                fig_bar.update_layout(template="plotly_dark", showlegend=False, xaxis_tickangle=-45)
                st.plotly_chart(fig_bar, use_container_width=True)

                st.divider()

                # ==================== TOP 3 CONTRIBUTORS ====================
                st.markdown("#### 🏆 Top 3 Contributors")

                # Use the renamed column 'Contributions' with a safeguard
                contrib_col = (
                    "Contributions"
                    if "Contributions" in df_results.columns
                    else "total_contributions"
                )
                top_3 = (
                    df_results.nlargest(3, contrib_col)
                    if contrib_col in df_results.columns
                    else pd.DataFrame()
                )

                top_cols = st.columns(3)
                for idx, (_, row) in enumerate(top_3.iterrows()):
                    with top_cols[idx]:
                        # Use renamed column with fallback
                        contrib_val = row.get("Contributions", row.get("total_contributions", 0))
                        active_val = row.get("Active Days", row.get("active_days", 0))
                        st.metric(
                            label=f"#{idx + 1} {row['username']}",
                            value=f"{contrib_val} contributions",
                            delta=f"{active_val} active days" if active_val else None,
                        )

            st.divider()

            # Export option
            csv = df_results.to_csv(index=False)
            st.download_button(
                label="📥 Download Results CSV",
                data=csv,
                file_name="team_contributions.csv",
                mime="text/csv",
            )


# ============================================================================
# MAIN RENDER FUNCTION
# ============================================================================


def render_contribution_mapping_mode(client):
    """
    Main render function for Contribution Mapping mode.
    """
    st.markdown("🗺 **Contribution Mapping**")
    st.markdown("---")

    # Sub-selection
    sub_mode = st.radio("Select Analysis Type", ["User Profile Overview", "Team"], horizontal=True)

    st.markdown("---")

    if sub_mode == "User Profile Overview":
        render_single_user_mapping(client)
    elif sub_mode == "Team":
        render_team_mapping(client)
