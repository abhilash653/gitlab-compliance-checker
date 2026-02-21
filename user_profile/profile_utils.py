from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Asia/Kolkata")

PRODUCTIVITY_WEIGHTS = {
    "pushed to": 2,
    "opened": 3,
    "merged": 5,
    "commented on": 1,
}


def parse_gitlab_datetime(timestamp):
    if not timestamp:
        return None
    normalized = timestamp.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(LOCAL_TZ)
    except Exception:
        return None


def classify_time_slot(timestamp):
    """
    Morning:   09:00 – 12:30
    Afternoon: 14:00 – 17:00
    Other:     All other times
    """
    dt = parse_gitlab_datetime(timestamp)
    if not dt:
        return None

    hour = dt.hour
    minute = dt.minute

    # Morning: 9:00 AM to 12:30 PM
    # 9, 10, 11 are fully in. 12 is in if minute <= 30.
    if (9 <= hour < 12) or (hour == 12 and minute <= 30):
        return "Morning"

    # Afternoon: 2:00 PM to 5:00 PM (14:00 - 17:00)
    # 14, 15, 16 are fully in. 17:00 is exactly on the edge, usually "until 5" includes 5:00 or excludes?
    # User said "2-5 pm". I'll assume 14:00:00 to 17:00:00 inclusive.
    if 14 <= hour <= 17:
        if hour == 17 and minute > 0:
            return "Other"
        return "Afternoon"

    return "Other"


def _format_date_time(timestamp):
    dt = parse_gitlab_datetime(timestamp)
    if not dt:
        return "-", "-"
    return dt.date().isoformat(), dt.strftime("%I:%M %p")


def process_commits(commits):
    processed = []
    for commit in commits or []:
        created_at = commit.get("created_at") or commit.get("committed_date")
        slot = classify_time_slot(created_at)
        if slot is None:
            continue

        date_str, time_str = _format_date_time(created_at)
        processed.append(
            {
                "project_type": commit.get("project_scope", "-"),
                "project": commit.get("project_name", "-"),
                "message": commit.get("title") or commit.get("message", "").split("\n")[0],
                "date": date_str,
                "time": time_str,
                "slot": slot,
            }
        )
    return processed


def process_groups(groups):
    rows = []
    for group in groups or []:
        rows.append(
            {
                "name": group.get("name", "-"),
                "path": group.get("full_path") or group.get("path", "-"),
                "visibility": group.get("visibility", "-"),
                "web_url": group.get("web_url", "-"),
            }
        )
    return rows


def process_contributions(events, start_date, end_date):
    if not events:
        return {
            "total": 0,
            "daily_counts": {},
            "type_counts": {},
            "most_active_day": None,
            "most_active_day_count": 0,
            "top_contribution_type": None,
            "average_per_day": 0.0,
            "productivity_score": 0,
            "longest_streak": 0,
            "weekday_contributions": 0,
            "weekend_contributions": 0,
            "inactive_days": 0,
            "trend_direction": "stable",
            "peak_3day_total": 0,
            "peak_3day_start": None,
            "peak_3day_end": None,
            "consistency_percentage": 0.0,
            "activity_variance": 0.0,
        }

    total_events = len(events)
    total_days = (end_date - start_date).days + 1

    daily_counts = {}
    type_counts = {}
    productivity_score = 0
    weekday_contributions = 0
    weekend_contributions = 0

    for event in events:
        created_at = event.get("created_at")
        if not created_at:
            continue

        dt = parse_gitlab_datetime(created_at)
        if not dt:
            continue

        event_date = dt.date()
        if event_date < start_date or event_date > end_date:
            continue

        date_str = event_date.isoformat()
        daily_counts[date_str] = daily_counts.get(date_str, 0) + 1

        action_name = event.get("action_name", "").lower()
        type_counts[action_name] = type_counts.get(action_name, 0) + 1

        weight = PRODUCTIVITY_WEIGHTS.get(action_name, 1)
        productivity_score += weight

        weekday = event_date.weekday()
        if weekday < 5:
            weekday_contributions += 1
        else:
            weekend_contributions += 1

    if not daily_counts:
        return {
            "total": total_events,
            "daily_counts": {},
            "type_counts": type_counts,
            "most_active_day": None,
            "most_active_day_count": 0,
            "top_contribution_type": None,
            "average_per_day": 0.0,
            "productivity_score": productivity_score,
            "longest_streak": 0,
            "weekday_contributions": weekday_contributions,
            "weekend_contributions": weekend_contributions,
            "inactive_days": total_days,
            "trend_direction": "stable",
            "peak_3day_total": 0,
            "peak_3day_start": None,
            "peak_3day_end": None,
            "consistency_percentage": 0.0,
            "activity_variance": 0.0,
        }

    most_active_day = max(daily_counts, key=daily_counts.get)
    most_active_day_count = daily_counts[most_active_day]

    top_contribution_type = max(type_counts, key=type_counts.get) if type_counts else None

    average_per_day = round(total_events / total_days, 2)

    active_dates = sorted(daily_counts.keys())
    longest_streak = 0
    current_streak = 1

    for i in range(1, len(active_dates)):
        prev_date = datetime.fromisoformat(active_dates[i - 1]).date()
        curr_date = datetime.fromisoformat(active_dates[i]).date()
        if (curr_date - prev_date).days == 1:
            current_streak += 1
        else:
            longest_streak = max(longest_streak, current_streak)
            current_streak = 1
    longest_streak = max(longest_streak, current_streak)

    active_days_count = len(daily_counts)
    inactive_days = total_days - active_days_count

    mid_point = total_days // 2
    first_half_start = start_date
    first_half_end = start_date + timedelta(days=mid_point - 1)
    second_half_start = first_half_end + timedelta(days=1)
    second_half_end = end_date

    first_half_count = 0
    second_half_count = 0

    for date_str, count in daily_counts.items():
        event_date = datetime.fromisoformat(date_str).date()
        if first_half_start <= event_date <= first_half_end:
            first_half_count += count
        elif second_half_start <= event_date <= second_half_end:
            second_half_count += count

    if second_half_count > first_half_count * 1.1:
        trend_direction = "increasing"
    elif second_half_count < first_half_count * 0.9:
        trend_direction = "decreasing"
    else:
        trend_direction = "stable"

    all_dates = [start_date + timedelta(days=i) for i in range(total_days)]
    full_daily_counts = {
        date.isoformat(): daily_counts.get(date.isoformat(), 0) for date in all_dates
    }

    peak_3day_total = 0
    peak_3day_start = None
    peak_3day_end = None

    for i in range(len(all_dates) - 2):
        window_start = all_dates[i]
        window_end = all_dates[i + 2]
        window_total = (
            full_daily_counts[window_start.isoformat()]
            + full_daily_counts[window_end.isoformat()]
            + full_daily_counts[all_dates[i + 1].isoformat()]
        )
        if window_total > peak_3day_total:
            peak_3day_total = window_total
            peak_3day_start = window_start.isoformat()
            peak_3day_end = window_end.isoformat()

    consistency_percentage = round((active_days_count / total_days) * 100, 2)

    daily_values = list(full_daily_counts.values())
    mean = total_events / total_days
    variance = sum((x - mean) ** 2 for x in daily_values) / total_days
    activity_variance = round(variance, 2)

    return {
        "total": total_events,
        "daily_counts": daily_counts,
        "type_counts": type_counts,
        "most_active_day": most_active_day,
        "most_active_day_count": most_active_day_count,
        "top_contribution_type": top_contribution_type,
        "average_per_day": average_per_day,
        "productivity_score": productivity_score,
        "longest_streak": longest_streak,
        "weekday_contributions": weekday_contributions,
        "weekend_contributions": weekend_contributions,
        "inactive_days": inactive_days,
        "trend_direction": trend_direction,
        "peak_3day_total": peak_3day_total,
        "peak_3day_start": peak_3day_start,
        "peak_3day_end": peak_3day_end,
        "consistency_percentage": consistency_percentage,
        "activity_variance": activity_variance,
    }


def split_projects(projects, user_info):
    personal = []
    contributed = []

    username = (user_info.get("username") or "").lower()
    user_id = user_info.get("id")

    for project in projects or []:
        namespace_path = (project.get("namespace", {}) or {}).get("full_path", "").lower()
        creator_id = project.get("creator_id")

        if namespace_path == username or creator_id == user_id:
            personal.append(project)
        else:
            contributed.append(project)

    return personal, contributed
