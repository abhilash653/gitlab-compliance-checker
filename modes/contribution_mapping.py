"""
Contribution Mapping Mode for GitLab Compliance & Analytics Tool

This module provides two sub-modes:
1. Single User Mapping - Individual contribution analysis
2. Team Mapping - Multi-user contribution analysis
"""

from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from gitlab_utils import users

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_user_events(client, user_id, start_date, end_date):
    """
    Fetch user events from GitLab API with date filtering.
    """
    after_date = start_date.isoformat()
    before_date = end_date.isoformat()

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
    """
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

        processed.append(
            {
                "created_at": created_at or "-",
                "date": event_date,
                "time": event_time,
                "action_name": event.get("action_name", "-"),
                "target_type": event.get("target_type", "-"),
                "project_name": event.get("project", {}).get("name", "-")
                if event.get("project")
                else "-",
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
    cache_key = f"contrib_events_{user_id}_{start_date}_{end_date}"

    with st.spinner(f"Fetching contributions from {start_date} to {end_date}..."):
        if cache_key not in st.session_state:
            events = get_user_events(client, user_id, start_date, end_date)
            st.session_state[cache_key] = events
        else:
            events = st.session_state[cache_key]

    processed_events = process_events(events)

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

    # ==================== SUMMARY CARDS ====================
    st.markdown("#### 📈 Summary")
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("Total Contributions", total_contributions)
    sc2.metric("Active Days", active_days)
    sc3.metric("Avg/Active Day", f"{avg_contributions:.1f}")
    sc4.metric("Longest Streak", f"{longest_streak} days")

    st.markdown(f"**Activity Classification:** {activity_class}")

    if total_contributions == 0:
        st.info(f"ℹ️ No contributions found between {start_date} and {end_date}.")
        return

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

    # ==================== DAILY TREND LINE CHART ====================
    st.markdown("#### 📉 Daily Trend")

    if sorted_dates:
        trend_data = [{"date": d, "contributions": date_counts[d]} for d in sorted_dates]
        df_trend = pd.DataFrame(trend_data)
        df_trend["date"] = pd.to_datetime(df_trend["date"])

        fig_trend = px.line(
            df_trend,
            x="date",
            y="contributions",
            title="Daily Contribution Trend",
            labels={"date": "Date", "contributions": "Contributions"},
            markers=True,
        )
        fig_trend.update_layout(template="plotly_dark")
        fig_trend.update_traces(line_color="#00CC96", line_width=2)
        st.plotly_chart(fig_trend, use_container_width=True)

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


def render_team_mapping(client):
    """
    Render Team Mapping interface.
    """
    st.markdown("### 👥 Team Members Contribution")

    # Manual input only
    username_input = st.text_area(
        "Enter Usernames (comma-separated or one per line)",
        height=150,
        placeholder="user1, user2, user3",
    )

    usernames = []
    if username_input:
        # Split by comma or newline
        usernames = [u.strip() for u in username_input.replace("\n", ",").split(",") if u.strip()]

    if not usernames:
        st.info("Please provide usernames to analyze.")
        return

    # Date range
    col1, col2 = st.columns(2)
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

    if start_date > end_date:
        st.error("❌ Start Date cannot be after End Date.")
        return

    if st.button("Run Team Analysis", type="primary"):
        st.info(f"Processing {len(usernames)} users...")

        results = []
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
                        }
                    )
                    continue

                user_id = user_info.get("id")

                # Fetch events
                events = get_user_events(client, user_id, start_date, end_date)
                processed = process_events(events)

                # Calculate metrics
                total_contributions = len(processed)

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

                results.append(
                    {
                        "username": username,
                        "status": "Success",
                        "total_contributions": total_contributions,
                        "active_days": active_days,
                        "consistency_pct": consistency_pct,
                        "collaboration_pct": collaboration_pct,
                    }
                )

        progress_bar.empty()

        # Display results
        st.success("Batch processing complete!")

        # Summary table
        st.markdown("#### 📋 Summary Table")

        if results:
            df_results = pd.DataFrame(results)

            # Format columns
            df_results["consistency_pct"] = df_results["consistency_pct"].round(1)
            df_results["collaboration_pct"] = df_results["collaboration_pct"].round(1)

            st.dataframe(df_results, use_container_width=True)

            # ==================== BAR CHART ====================
            st.markdown("#### 📊 Contributions per User")

            success_results = [r for r in results if r.get("status") == "Success"]
            if success_results:
                df_chart = pd.DataFrame(success_results)
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

                # Highlight top 3 users
                st.markdown("#### 🏆 Top 3 Contributors")
                top_3 = df_results.nlargest(3, "total_contributions")

                top_cols = st.columns(3)
                for idx, (_, row) in enumerate(top_3.iterrows()):
                    with top_cols[idx]:
                        st.metric(
                            f"#{idx + 1} {row['username']}",
                            f"{row['total_contributions']} contributions",
                            f"{row['active_days']} active days",
                        )

            # Export option
            csv = df_results.to_csv(index=False)
            st.download_button(
                label="Download Results CSV",
                data=csv,
                file_name="batch_contributions.csv",
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
    sub_mode = st.radio("Select Analysis Type", ["Single User", "Team"], horizontal=True)

    st.markdown("---")

    if sub_mode == "Single User":
        render_single_user_mapping(client)
    elif sub_mode == "Team":
        render_team_mapping(client)
