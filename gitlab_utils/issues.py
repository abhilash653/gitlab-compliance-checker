def get_user_issues(client, user_id, start_date=None, end_date=None):
    """
    Fetch Issues:
    - Authored Issues (GET /issues?author_id=:id)

    Args:
        client: GitLab client instance
        user_id: GitLab user ID
        start_date: Optional date filter (date object or string)
        end_date: Optional date filter (date object or string)

    Returns:
      - issues_list
      - stats: {total, opened, closed}
    """
    # Parse dates if provided
    from datetime import datetime, timedelta

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
    print(f"[DEBUG] Issues Date range: start_date={start_date}, end_date={end_date}")
    print(
        f"[DEBUG] Issues GitLab API params: created_after={since_iso}, created_before={until_iso}"
    )

    issues_list = []
    stats = {"total": 0, "opened": 0, "closed": 0}

    try:
        # GET /issues is available at instance level if authorized, or usually /issues?scope=all
        # Build params with date filters
        api_params = {"author_id": user_id, "scope": "all"}
        if since_iso:
            api_params["created_after"] = since_iso
        if until_iso:
            api_params["created_before"] = until_iso

        items = client._get_paginated("/issues", params=api_params, per_page=100, max_pages=10)

        for item in items:
            # Date range filtering
            created_at_str = item.get("created_at")
            if created_at_str:
                try:
                    dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    issue_date = dt.date()

                    if start_date and issue_date < start_date:
                        continue
                    if end_date and issue_date > end_date:
                        continue
                except Exception:
                    pass

            state = item.get("state")

            issues_list.append(
                {
                    "title": item.get("title"),
                    "project_id": item.get("project_id"),
                    "web_url": item.get("web_url"),
                    "state": state,
                    "created_at": created_at_str,
                }
            )

            stats["total"] += 1
            if state == "opened":
                stats["opened"] += 1
            elif state == "closed":
                stats["closed"] += 1

    except Exception:
        pass

    return issues_list, stats
