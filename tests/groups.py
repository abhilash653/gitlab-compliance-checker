# tests/test_groups.py

import pytest
from unittest.mock import MagicMock

from gitlab_utils.groups import get_user_groups


@pytest.fixture
def mock_client():
    return MagicMock()


def test_get_user_groups_success(mock_client):
    """Test successful group fetch"""

    mock_client._get_paginated.return_value = [
        {
            "id": 1,
            "name": "Dev Team",
            "full_path": "company/dev-team",
            "visibility": "private"
        },
        {
            "id": 2,
            "name": "QA Team",
            "full_path": "company/qa-team",
            "visibility": "internal"
        }
    ]

    result = get_user_groups(mock_client, user_id=123)

    assert len(result) == 2

    assert result[0]["name"] == "Dev Team"
    assert result[0]["full_path"] == "company/dev-team"
    assert result[0]["visibility"] == "private"

    assert result[1]["name"] == "QA Team"


def test_get_user_groups_duplicate_removal(mock_client):
    """Test duplicate groups are removed"""

    mock_client._get_paginated.return_value = [
        {
            "id": 1,
            "name": "Dev Team",
            "full_path": "company/dev-team",
            "visibility": "private"
        },
        {
            "id": 1,  # duplicate
            "name": "Dev Team",
            "full_path": "company/dev-team",
            "visibility": "private"
        }
    ]

    result = get_user_groups(mock_client, user_id=123)

    assert len(result) == 1
    assert result[0]["name"] == "Dev Team"


def test_get_user_groups_empty(mock_client):
    """Test empty groups response"""

    mock_client._get_paginated.return_value = []

    result = get_user_groups(mock_client, user_id=123)

    assert result == []


def test_get_user_groups_exception(mock_client):
    """Test exception handling"""

    mock_client._get_paginated.side_effect = Exception("API error")

    result = get_user_groups(mock_client, user_id=123)

    assert result == []


def test_get_user_groups_missing_fields(mock_client):
    """Test missing optional fields"""

    mock_client._get_paginated.return_value = [
        {
            "id": 1
        }
    ]

    result = get_user_groups(mock_client, user_id=123)

    assert len(result) == 1

    assert result[0]["name"] is None
    assert result[0]["full_path"] is None
    assert result[0]["visibility"] is None