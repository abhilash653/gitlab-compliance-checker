def get_user_mrs(client, user_id, start_date=None, end_date=None):
    """
    Fetch Merge Requests:
    - Authored MRs (GET /merge_requests?author_id=:id)
    - Assigned MRs (GET /merge_requests?assignee_id=:id)

    Args:
        client: GitLab client instance
        user_id: GitLab user ID
        start_date: Optional date filter (date object or string)
        end_date: Optional date filter (date object or string)

    Returns:
      - mrs_list: List of MR dicts
      - stats: Dict {total, merged, closed, opened, pending}
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
    print(f"[DEBUG] MRs Date range: start_date={start_date}, end_date={end_date}")
    print(f"[DEBUG] MRs GitLab API params: created_after={since_iso}, created_before={until_iso}")

    mrs_list = []
    seen_ids = set()

    stats = {
        "total": 0,
        "merged": 0,
        "closed": 0,
        "opened": 0,  # "opened" acts as Pending often
        "pending": 0,  # Explicit pending check if needed (usually 'opened')
    }

    # helper to fetch and process
    def fetch_and_add(params, role_label):
        try:
            # Add date filtering params to API call
            api_params = dict(params)
            if since_iso:
                api_params["created_after"] = since_iso
            if until_iso:
                api_params["created_before"] = until_iso

            items = client._get_paginated(
                "/merge_requests", params=api_params, per_page=100, max_pages=10
            )
            for item in items:
                if item["id"] not in seen_ids:
                    # Date range filtering
                    created_at_str = item.get("created_at")
                    if created_at_str:
                        try:
                            dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                            mr_date = dt.date()

                            if start_date and mr_date < start_date:
                                continue
                            if end_date and mr_date > end_date:
                                continue
                        except Exception:
                            pass

                    state = item.get("state")  # opened, closed, merged, locked

                    mrs_list.append(
                        {
                            "title": item.get("title"),
                            "project_id": item.get("project_id"),
                            "web_url": item.get("web_url"),
                            "state": state,
                            "created_at": created_at_str,
                            "role": role_label,
                        }
                    )
                    seen_ids.add(item["id"])

                    # Update Stats
                    stats["total"] += 1
                    if state == "merged":
                        stats["merged"] += 1
                    elif state == "closed":
                        stats["closed"] += 1
                    elif state == "opened":
                        stats["opened"] += 1
                        stats["pending"] += 1

        except Exception:
            pass

    # 1. Authored
    fetch_and_add({"author_id": user_id, "scope": "all"}, "Authored")

    # 2. Assigned
    fetch_and_add({"assignee_id": user_id, "scope": "all"}, "Assigned")

    return mrs_list, stats
