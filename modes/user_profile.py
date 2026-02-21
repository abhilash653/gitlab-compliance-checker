from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from gitlab_utils import commits, groups, issues, merge_requests, projects


def get_user_events(client, user_id, start_date, end_date):
    """
    Fetch user events from GitLab API with date filtering.

    Args:
        client: GitLabClient instance
        user_id: GitLab user ID
        start_date: Start date for filtering (date object)
        end_date: End date for filtering (date object)

    Returns:
        List of events within the date range
    """
    # Convert dates to ISO format (YYYY-MM-DD)
    after_date = start_date.isoformat()
    before_date = end_date.isoformat()

    # Use the client's _get_paginated method to fetch events
    # GitLab API: GET /users/:id/events
    endpoint = f"/users/{user_id}/events"
    params = {"after": after_date, "before": before_date, "per_page": 100}

    try:
        events = client._get_paginated(endpoint, params=params, per_page=100, max_pages=10)
        return events if events else []
    except Exception as e:
        st.warning(f"Could not fetch events: {e}")
        return []


def process_events(events):
    """
    Process GitLab events to extract relevant fields.

    Args:
        events: List of event dictionaries from GitLab API

    Returns:
        List of processed event dictionaries
    """
    processed = []
    for event in events or []:
        created_at = event.get("created_at")
        # Extract date from ISO timestamp
        event_date = "-"
        if created_at:
            try:
                # Parse ISO format and extract date
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                event_date = dt.strftime("%Y-%m-%d")
            except Exception:
                event_date = "-"

        processed.append(
            {
                "created_at": created_at or "-",
                "date": event_date,
                "action_name": event.get("action_name", "-"),
                "target_type": event.get("target_type", "-"),
                "project_name": event.get("project", {}).get("name", "-")
                if event.get("project")
                else "-",
                "target_title": event.get("target_title", "-") or "-",
            }
        )
    return processed


def render_user_profile(client, simple_user_info):
    """
    Renders the User Profile UI.
    """
    if not simple_user_info:
        st.error("User info not provided.")
        return

    user_id = simple_user_info.get("id")
    username = simple_user_info.get("username")
    name = simple_user_info.get("name")
    avatar_url = simple_user_info.get("avatar_url")
    web_url = simple_user_info.get("web_url")

    # Header
    col1, col2 = st.columns([1, 4])
    with col1:
        if avatar_url:
            st.image(avatar_url, width=100)
    with col2:
        st.markdown(f"### {name} (@{username})")
        st.markdown(f"**ID:** {user_id} | [GitLab Profile]({web_url})")

    # --- Date Range Selection for Contribution Analytics ---
    st.markdown("---")
    st.subheader("📊 Contribution Analytics (Date Range)")

    # Calculate default dates
    today = date.today()
    default_start = today - timedelta(days=30)

    # Date input fields
    date_col1, date_col2 = st.columns(2)
    with date_col1:
        start_date = st.date_input(
            "Start Date",
            value=default_start,
            max_value=today,
            help="Select the start date for contribution filtering",
        )
    with date_col2:
        end_date = st.date_input(
            "End Date",
            value=today,
            min_value=start_date,
            max_value=today,
            help="Select the end date for contribution filtering",
        )

    # Validate date range
    if start_date > end_date:
        st.error("❌ Error: Start Date cannot be after End Date. Please adjust the date range.")
        return

    # Cache key for events (to avoid duplicate API calls)
    events_cache_key = f"events_{user_id}_{start_date}_{end_date}"

    # Fetch events with date filtering
    with st.spinner(f"Fetching contributions from {start_date} to {end_date}..."):
        # Check if events are cached
        if events_cache_key not in st.session_state:
            events = get_user_events(client, user_id, start_date, end_date)
            st.session_state[events_cache_key] = events
        else:
            events = st.session_state[events_cache_key]

    # Process events
    processed_events = process_events(events)

    # Display events count and info
    st.markdown(f"**Contributions found:** {len(processed_events)} events")

    if not processed_events:
        st.info(
            f"ℹ️ No contributions found between {start_date} and {end_date}. Try selecting a different date range."
        )
    else:
        # Aggregate events by date for chart
        date_counts = {}
        for event in processed_events:
            event_date = event.get("date", "-")
            if event_date and event_date != "-":
                date_counts[event_date] = date_counts.get(event_date, 0) + 1

        # Sort by date
        sorted_dates = sorted(date_counts.keys())

        # Display line chart for daily contribution activity
        if sorted_dates:
            chart_data = pd.DataFrame(
                {"Date": sorted_dates, "Contributions": [date_counts[d] for d in sorted_dates]}
            )
            st.markdown("### Daily Contribution Activity")
            st.line_chart(chart_data.set_index("Date"), height=250)

        # Display events in structured format
        st.markdown("### Contribution Details")
        with st.expander("View All Contributions", expanded=True):
            df_events = pd.DataFrame(processed_events)
            # Display relevant columns
            display_cols = ["date", "action_name", "target_type", "project_name", "target_title"]
            available_cols = [col for col in display_cols if col in df_events.columns]
            st.dataframe(df_events[available_cols], width="stretch", use_container_width=True)

    # --- End Contribution Analytics ---

    # Cache keys for data (include date range to refresh when dates change)
    cache_key_projects = f"projects_{user_id}"
    cache_key_commits = f"commits_{user_id}_{start_date}_{end_date}"
    cache_key_mrs = f"mrs_{user_id}_{start_date}_{end_date}"
    cache_key_issues = f"issues_{user_id}_{start_date}_{end_date}"

    # Fetch Data
    with st.spinner(f"Fetching data from {start_date} to {end_date}..."):
        # 1. Projects (not date filtered - always lifetime)
        if cache_key_projects not in st.session_state:
            proj_data = projects.get_user_projects(client, user_id, username)
            st.session_state[cache_key_projects] = proj_data
        else:
            proj_data = st.session_state[cache_key_projects]

        # 2. Commits with date filtering
        if cache_key_commits not in st.session_state:
            all_projs = proj_data["all"]
            all_commits, commit_counts, commit_stats = commits.get_user_commits(
                client, simple_user_info, all_projs, start_date, end_date
            )
            st.session_state[cache_key_commits] = (all_commits, commit_counts, commit_stats)
        else:
            all_commits, commit_counts, commit_stats = st.session_state[cache_key_commits]

        verified_contributed = []
        for p in proj_data["contributed"]:
            if commit_counts.get(p["id"], 0) > 0:
                verified_contributed.append(p)

        personal_projects = proj_data["personal"]

        # 3. Groups (not date filtered)
        cache_key_groups = f"groups_{user_id}"
        if cache_key_groups not in st.session_state:
            user_groups = groups.get_user_groups(client, user_id)
            st.session_state[cache_key_groups] = user_groups
        else:
            user_groups = st.session_state[cache_key_groups]

        # 4. MRs with date filtering
        if cache_key_mrs not in st.session_state:
            user_mrs, mr_stats = merge_requests.get_user_mrs(client, user_id, start_date, end_date)
            st.session_state[cache_key_mrs] = (user_mrs, mr_stats)
        else:
            user_mrs, mr_stats = st.session_state[cache_key_mrs]

        # 5. Issues with date filtering
        if cache_key_issues not in st.session_state:
            user_issues, issue_stats = issues.get_user_issues(client, user_id, start_date, end_date)
            st.session_state[cache_key_issues] = (user_issues, issue_stats)
        else:
            user_issues, issue_stats = st.session_state[cache_key_issues]

    # --- Display ---

    # Projects
    st.markdown("---")
    st.subheader("📦 Projects")
    p_col1, p_col2 = st.columns(2)
    with p_col1:
        st.metric("Personal Projects", len(personal_projects))
        if personal_projects:
            with st.expander("View Personal Projects"):
                for p in personal_projects:
                    st.write(f"- [{p['name_with_namespace']}]({p['web_url']})")
    with p_col2:
        st.metric("Contributed Projects", len(verified_contributed))
        if verified_contributed:
            with st.expander("View Contributed Projects"):
                for p in verified_contributed:
                    st.write(f"- [{p['name_with_namespace']}]({p['web_url']})")

    # Commits
    st.markdown("---")
    st.subheader("💻 Commits Analysis (IST)")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Commits", commit_stats["total"])
    c2.metric("Morning (9:30-12:30)", commit_stats["morning_commits"])
    c3.metric("Afternoon (2:00-5:00)", commit_stats["afternoon_commits"])

    if all_commits:
        with st.expander("View Recent Commits"):
            # Use pandas for table
            df_commits = pd.DataFrame(all_commits)
            # Display updated columns
            st.dataframe(
                df_commits[["project_name", "message", "date", "time", "slot"]], width="stretch"
            )

    # Groups
    st.markdown("---")
    st.subheader("👥 Groups")
    if user_groups:
        st.write(f"**Total Groups:** {len(user_groups)}")
        df_groups = pd.DataFrame(user_groups)
        st.dataframe(df_groups, width="stretch")
    else:
        st.info("No groups found.")

    # Merge Requests
    st.markdown("---")
    st.subheader("🔀 Merge Requests")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total MRs", mr_stats["total"])
    m2.metric("Merged", mr_stats["merged"])
    m3.metric("Open/Pending", mr_stats["opened"])
    m4.metric("Closed", mr_stats["closed"])

    if user_mrs:
        with st.expander("View MR Details"):
            df_mrs = pd.DataFrame(user_mrs)
            st.dataframe(df_mrs[["title", "role", "state", "created_at"]], width="stretch")

    # Issues
    st.markdown("---")
    st.subheader("⚠️ Issues")
    i1, i2, i3 = st.columns(3)
    i1.metric("Total Issues", issue_stats["total"])
    i2.metric("Open", issue_stats["opened"])
    i3.metric("Closed", issue_stats["closed"])

    if user_issues:
        with st.expander("View Issue Details"):
            df_issues = pd.DataFrame(user_issues)
            st.dataframe(df_issues[["title", "state", "created_at"]], width="stretch")
