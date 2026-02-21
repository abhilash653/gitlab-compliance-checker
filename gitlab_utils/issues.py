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
    from datetime import datetime
    if isinstance(start_date, str):
        start_date = datetime.fromisoformat(start_date).date()
    if isinstance(end_date, str):
        end_date = datetime.fromisoformat(end_date).date()
    
    issues_list = []
    stats = {
        "total": 0,
        "opened": 0,
        "closed": 0
    }

    try:
        # GET /issues is available at instance level if authorized, or usually /issues?scope=all
        items = client._get_paginated("/issues", params={"author_id": user_id, "scope": "all"}, per_page=50, max_pages=10)

        for item in items:
            # Date range filtering
            created_at_str = item.get("created_at")
            if created_at_str:
                try:
                    from datetime import timezone
                    dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    issue_date = dt.date()
                    
                    if start_date and issue_date < start_date:
                        continue
                    if end_date and issue_date > end_date:
                        continue
                except Exception:
                    pass
            
            state = item.get("state")

            issues_list.append({
                "title": item.get("title"),
                "project_id": item.get("project_id"),
                "web_url": item.get("web_url"),
                "state": state,
                "created_at": created_at_str
            })

            stats["total"] += 1
            if state == "opened":
                stats["opened"] += 1
            elif state == "closed":
                stats["closed"] += 1

    except Exception:
        pass

    return issues_list, stats
