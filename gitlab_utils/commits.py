from datetime import datetime, timedelta, timezone

import dateutil.parser


def get_user_commits(client, user, projects, start_date=None, end_date=None):
    """
    Fetches commits for a user across given projects.
    Filters by author name/email because GitLab repository commits API
    does not support author_id reliably.

    Args:
        client: GitLab client instance
        user: User dict with name, email, username
        projects: List of project dicts
        start_date: Optional date filter (date object or string)
        end_date: Optional date filter (date object or string)

    Returns:
      - all_commits: List of unique commit dicts
      - project_commit_counts: Dict {project_id: count}
      - stats: Dict {morning_commits, afternoon_commits, total}
    """
    # Parse dates if provided
    if isinstance(start_date, str):
        start_date = datetime.fromisoformat(start_date).date()
    if isinstance(end_date, str):
        end_date = datetime.fromisoformat(end_date).date()

    # Convert dates to ISO 8601 format with UTC for GitLab API
    # start_date: datetime at 00:00:00
    # end_date: add 1 day to include the full end date
    since_iso = None
    until_iso = None
    if start_date:
        since = datetime.strptime(str(start_date), "%Y-%m-%d")
        since_iso = since.isoformat() + "Z"
    if end_date:
        until = datetime.strptime(str(end_date), "%Y-%m-%d") + timedelta(days=1)
        until_iso = until.isoformat() + "Z"

    # Debug logs for date filtering
    print(f"[DEBUG] Date range: start_date={start_date}, end_date={end_date}")
    print(f"[DEBUG] GitLab API params: since={since_iso}, until={until_iso}")
    all_commits = []
    project_commit_counts = {}
    seen_shas = set()

    # Use name and email for stricter filtering
    author_name = user.get("name")
    author_email = user.get("email")
    username = user.get("username")

    # Define IST timezone (+5:30)
    ist = timezone(timedelta(hours=5, minutes=30))

    # Define slot boundary times for comparison (IST)
    # Morning: 6 AM – 12 PM
    # Afternoon: 12 PM – 6 PM
    # Evening: 6 PM – 10 PM
    # Night: 10 PM – 6 AM
    morning_start = datetime.strptime("06:00", "%H:%M").time()
    morning_end = datetime.strptime("12:00", "%H:%M").time()
    afternoon_start = datetime.strptime("12:00", "%H:%M").time()
    afternoon_end = datetime.strptime("18:00", "%H:%M").time()
    evening_start = datetime.strptime("18:00", "%H:%M").time()
    evening_end = datetime.strptime("22:00", "%H:%M").time()
    night_start = datetime.strptime("22:00", "%H:%M").time()
    night_end = datetime.strptime("06:00", "%H:%M").time()

    stats = {
        "total": 0,
        "morning_commits": 0,  # 06:00 AM – 12:00 PM
        "afternoon_commits": 0,  # 12:00 PM – 06:00 PM
        "evening_commits": 0,  # 06:00 PM – 10:00 PM
        "night_commits": 0,  # 10:00 PM – 06:00 AM
    }

    for project in projects:
        try:
            pid = project.get("id")
            pname = project.get("name_with_namespace")

            # Fetch commits with date filtering via GitLab API
            # Build params with date filters
            api_params = {"author": author_name or username, "all": True}
            if since_iso:
                api_params["since"] = since_iso
            if until_iso:
                api_params["until"] = until_iso

            commits_data = client._get_paginated(
                f"/projects/{pid}/repository/commits",
                params=api_params,
                per_page=100,
                max_pages=20,
            )

            if commits_data:
                valid_project_commits = 0
                for c in commits_data:
                    sha = c.get("id")

                    # Validation
                    c_author_name = c.get("author_name")
                    c_author_email = c.get("author_email")

                    is_match = False
                    if author_name and c_author_name == author_name:
                        is_match = True
                    elif author_email and c_author_email == author_email:
                        is_match = True
                    elif username and (
                        username in str(c_author_name).lower()
                        or username in str(c_author_email).lower()
                    ):
                        is_match = True

                    if not is_match:
                        continue

                    valid_project_commits += 1

                    if sha in seen_shas:
                        continue

                    seen_shas.add(sha)
                    stats["total"] += 1

                    # Parse and Convert to IST
                    created_at_str = c.get("created_at")
                    try:
                        dt_utc = dateutil.parser.isoparse(created_at_str)
                        dt_ist = dt_utc.replace(tzinfo=timezone.utc).astimezone(ist)

                        commit_date = dt_ist.date()

                        # Date range filtering
                        if start_date and commit_date < start_date:
                            continue
                        if end_date and commit_date > end_date:
                            continue

                        date_str = dt_ist.strftime("%Y-%m-%d")
                        time_str = dt_ist.strftime("%I:%M %p")
                        t_obj = dt_ist.time()

                        slot = "Other"
                        if t_obj >= morning_start and t_obj < morning_end:
                            slot = "Morning"
                            stats["morning_commits"] += 1
                        elif t_obj >= afternoon_start and t_obj < afternoon_end:
                            slot = "Afternoon"
                            stats["afternoon_commits"] += 1
                        elif t_obj >= evening_start and t_obj < evening_end:
                            slot = "Evening"
                            stats["evening_commits"] += 1
                        elif t_obj >= night_start or t_obj < night_end:
                            slot = "Night"
                            stats["night_commits"] += 1

                    except Exception:
                        date_str = created_at_str
                        time_str = "N/A"
                        slot = "N/A"

                    all_commits.append(
                        {
                            "project_name": pname,
                            "message": c.get("title"),
                            "date": date_str,
                            "time": time_str,
                            "slot": slot,
                            "author_name": c_author_name,
                            "short_id": c.get("short_id"),
                        }
                    )

                project_commit_counts[pid] = valid_project_commits

        except Exception:
            pass

    return all_commits, project_commit_counts, stats
