import pytest
from unittest.mock import patch, MagicMock
from gitlab_utils.batch import process_single_user, process_batch_users


@pytest.fixture
def mock_client():
    return MagicMock()


@patch("gitlab_utils.batch.users.get_user_by_username")
@patch("gitlab_utils.batch.projects.get_user_projects")
@patch("gitlab_utils.batch.commits.get_user_commits")
@patch("gitlab_utils.batch.groups.get_user_groups")
@patch("gitlab_utils.batch.merge_requests.get_user_mrs")
@patch("gitlab_utils.batch.issues.get_user_issues")
def test_process_single_user_success(
    mock_issues,
    mock_mrs,
    mock_groups,
    mock_commits,
    mock_projects,
    mock_users,
    mock_client
):

    mock_users.return_value = {"id": 1, "username": "testuser"}

    mock_projects.return_value = {
        "personal": [{"id": 1}],
        "contributed": [{"id": 2}],
        "all": [{"id": 1}, {"id": 2}]
    }

    mock_commits.return_value = (
        [{"id": "c1"}],
        {1: 5, 2: 3},
        {"total": 8}
    )

    mock_groups.return_value = [{"id": 1}]
    mock_mrs.return_value = ([{"id": 1}], {"total": 1})
    mock_issues.return_value = ([{"id": 1}], {"total": 1})

    result = process_single_user(mock_client, "testuser")

    assert result["status"] == "Success"
    assert result["data"]["commit_stats"]["total"] == 8
    assert len(result["data"]["projects"]["personal"]) == 1


def test_process_single_user_not_found(mock_client):

    with patch("gitlab_utils.batch.users.get_user_by_username") as mock_users:
        mock_users.return_value = None

        result = process_single_user(mock_client, "invalid")

        assert result["status"] == "Not Found"


@patch("gitlab_utils.batch.process_single_user")
def test_process_batch_users(mock_process, mock_client):

    mock_process.side_effect = [
        {"username": "user1", "status": "Success"},
        {"username": "user2", "status": "Success"}
    ]

    result = process_batch_users(mock_client, ["user1", "user2"])

    assert len(result) == 2
    assert result[0]["status"] == "Success"