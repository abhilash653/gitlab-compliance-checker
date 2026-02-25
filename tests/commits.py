# tests/test_commits.py

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from gitlab_utils.commits import get_user_commits


@pytest.fixture
def mock_client():
    client = MagicMock()

    # Mock commit data
    client._get_paginated.return_value = [
        {
            "id": "sha1",
            "short_id": "sha1",
            "title": "Morning commit",
            "author_name": "Test User",
            "author_email": "test@example.com",
            "created_at": "2026-02-25T02:30:00Z",  # 08:00 IST → Morning
        },
        {
            "id": "sha2",
            "short_id": "sha2",
            "title": "Afternoon commit",
            "author_name": "Test User",
            "author_email": "test@example.com",
            "created_at": "2026-02-25T08:30:00Z",  # 14:00 IST → Afternoon
        },
        {
            "id": "sha3",
            "short_id": "sha3",
            "title": "Evening commit",
            "author_name": "Test User",
            "author_email": "test@example.com",
            "created_at": "2026-02-25T13:30:00Z",  # 19:00 IST → Evening
        },
        {
            "id": "sha4",
            "short_id": "sha4",
            "title": "Night commit",
            "author_name": "Test User",
            "author_email": "test@example.com",
            "created_at": "2026-02-25T18:30:00Z",  # 00:00 IST → Night
        },
        {
            "id": "sha1",  # duplicate SHA
            "short_id": "sha1",
            "title": "Duplicate commit",
            "author_name": "Test User",
            "author_email": "test@example.com",
            "created_at": "2026-02-25T02:30:00Z",
        },
        {
            "id": "sha5",
            "short_id": "sha5",
            "title": "Wrong author",
            "author_name": "Other User",
            "author_email": "other@example.com",
            "created_at": "2026-02-25T10:30:00Z",
        },
    ]

    return client


@pytest.fixture
def mock_user():
    return {
        "name": "Test User",
        "email": "test@example.com",
        "username": "testuser"
    }


@pytest.fixture
def mock_projects():
    return [
        {
            "id": 1,
            "name_with_namespace": "Test Group / Test Project"
        }
    ]


def test_get_user_commits_basic(mock_client, mock_user, mock_projects):
    commits, project_counts, stats = get_user_commits(
        mock_client,
        mock_user,
        mock_projects
    )

    # Should ignore duplicate and wrong author
    assert len(commits) == 4

    assert project_counts[1] == 5  # includes duplicate before SHA filtering

    assert stats["total"] == 4
    assert stats["morning_commits"] == 1
    assert stats["afternoon_commits"] == 1
    assert stats["evening_commits"] == 1
    assert stats["night_commits"] == 1


def test_date_filter(mock_client, mock_user, mock_projects):
    commits, project_counts, stats = get_user_commits(
        mock_client,
        mock_user,
        mock_projects,
        start_date="2026-02-25",
        end_date="2026-02-25"
    )

    # The night commit (18:30 UTC = 00:00 IST next day) is filtered out
    # because it becomes 2026-02-26 in IST
    assert len(commits) == 3
    # Note: stats["total"] is incremented before date filtering,
    # so it includes all 4 commits even though only 3 are returned
    assert stats["total"] == 4


def test_empty_projects(mock_client, mock_user):
    commits, project_counts, stats = get_user_commits(
        mock_client,
        mock_user,
        []
    )

    assert commits == []
    assert project_counts == {}
    assert stats["total"] == 0


def test_author_filter(mock_client, mock_projects):
    user = {
        "name": "Wrong User",
        "email": "wrong@example.com",
        "username": "wronguser"
    }

    commits, project_counts, stats = get_user_commits(
        mock_client,
        user,
        mock_projects
    )

    assert commits == []
    assert stats["total"] == 0


def test_date_out_of_range(mock_client, mock_user, mock_projects):
    # Night commit at 18:30 UTC becomes 00:00 IST on Feb 26
    # So with date range Feb 26-27, we get 1 commit (the night one)
    commits, project_counts, stats = get_user_commits(
        mock_client,
        mock_user,
        start_date="2026-02-26",
        end_date="2026-02-27",
        projects=mock_projects
    )

    # The night commit (18:30 UTC = 00:00 IST next day) falls on 2026-02-26
    assert len(commits) == 1
    assert commits[0]["date"] == "2026-02-26"