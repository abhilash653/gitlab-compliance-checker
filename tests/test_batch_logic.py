import pytest
import sys
import os
from unittest.mock import MagicMock, patch
import sys
import os

# Add parent directory to path for local imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from local gitlab_utils
from gitlab_utils import batch, projects


@pytest.fixture
def mock_client():
    client = MagicMock()
    client._get_paginated.return_value = []
    return client


def test_project_classification_personal(mock_client):
    username = "testuser"
    user_id = 123

    mock_projects = [
        {
            "id": 1,
            "name": "Personal Project",
            "namespace": {"path": "testuser", "kind": "user"}
        },
        {
            "id": 2,
            "name": "Contributed Project",
            "namespace": {"path": "otheruser", "kind": "user"}
        },
        {
            "id": 3,
            "name": "Group Project",
            "namespace": {"path": "somegroup", "kind": "group"}
        }
    ]

    mock_client._get_paginated.return_value = mock_projects

    res = projects.get_user_projects(mock_client, user_id, username)

    assert len(res["personal"]) == 1
    assert res["personal"][0]["id"] == 1
    assert len(res["contributed"]) == 2


@patch("gitlab_utils.users.get_user_by_username")
@patch("gitlab_utils.projects.get_user_projects")
@patch("gitlab_utils.commits.get_user_commits")
@patch("gitlab_utils.groups.get_user_groups")
@patch("gitlab_utils.merge_requests.get_user_mrs")
@patch("gitlab_utils.issues.get_user_issues")
def test_process_single_user_success(
    mock_issues,
    mock_mrs,
    mock_groups,
    mock_commits,
    mock_projects,
    mock_users,
    mock_client
):

    username = "testuser"
    user_id = 123

    mock_users.return_value = {
        "id": user_id,
        "username": username,
        "name": "Test User"
    }

    mock_projects.return_value = {
        "personal": [{"id": 1}],
        "contributed": [{"id": 2}],
        "all": [{"id": 1}, {"id": 2}]
    }

    mock_commits.return_value = ([], {1: 10, 2: 5}, {"total": 15})
    mock_groups.return_value = []
    mock_mrs.return_value = ([], {"total": 0})
    mock_issues.return_value = ([], {"total": 0})

    result = batch.process_single_user(mock_client, username)

    assert result["status"] == "Success"
    assert result["username"] == username
    assert "projects" in result["data"]