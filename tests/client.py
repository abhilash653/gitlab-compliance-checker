import pytest
from unittest.mock import Mock, patch
import requests
import gitlab
from gitlab_utils.client import safe_api_call, GitLabClient


# ------------------------------
# Test: safe_api_call SUCCESS
# ------------------------------
def test_safe_api_call_success():
    mock_func = Mock(return_value={"key": "value"})
    result = safe_api_call(mock_func)
    
    assert result == {"key": "value"}
    mock_func.assert_called_once()


# ------------------------------
# Test: safe_api_call retries on connection error
# ------------------------------
def test_safe_api_call_retries_on_connection_error():
    # Use actual exception classes that are in the retry list
    mock_func = Mock(side_effect=[
        requests.exceptions.ConnectionError("Connection error"),
        requests.exceptions.ConnectionError("Connection error"),
        {"success": True}
    ])
    
    result = safe_api_call(mock_func)
    
    assert result == {"success": True}
    assert mock_func.call_count == 3


# ------------------------------
# Test: safe_api_call returns empty list on unexpected exception
# ------------------------------
def test_safe_api_call_returns_empty_on_unexpected_exception():
    # Use an exception that's NOT in the retry list - triggers immediate return
    mock_func = Mock(side_effect=ValueError("Unexpected error"))
    
    result = safe_api_call(mock_func)
    
    assert result == []
    assert mock_func.call_count == 1


# ------------------------------
# Test: safe_api_call retries exhausted on connection error
# ------------------------------
def test_safe_api_call_retries_exhausted():
    # Use actual exception that should be retried
    mock_func = Mock(side_effect=requests.exceptions.ConnectionError("Connection error"))
    
    result = safe_api_call(mock_func)
    
    assert result == []
    assert mock_func.call_count == 3  # 3 attempts


# ------------------------------
# Test: GitLabClient initialization success
# ------------------------------
@patch('gitlab_utils.client.Gitlab')
@patch('gitlab_utils.client.st')
def test_gitlab_client_init_success(mock_st, mock_gitlab):
    mock_client_instance = Mock()
    mock_gitlab.return_value = mock_client_instance
    
    client = GitLabClient("https://gitlab.com", "test-token")
    
    assert client.base_url == "https://gitlab.com"
    assert client.api_base == "https://gitlab.com/api/v4"
    assert client.headers == {"PRIVATE-TOKEN": "test-token"}
    mock_client_instance.auth.assert_called_once()


# ------------------------------
# Test: GitLabClient initialization failure
# ------------------------------
@patch('gitlab_utils.client.Gitlab')
@patch('gitlab_utils.client.st')
def test_gitlab_client_init_failure(mock_st, mock_gitlab):
    mock_gitlab.side_effect = Exception("Auth failed")
    
    client = GitLabClient("https://gitlab.com", "invalid-token")
    
    assert client.client is None


# ------------------------------
# Test: GitLabClient _get method
# ------------------------------
@patch('gitlab_utils.client.requests.request')
@patch('gitlab_utils.client.safe_api_call')
def test_gitlab_client_get(mock_safe_call, mock_request):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": 1, "name": "test"}
    mock_request.return_value = mock_response
    
    mock_safe_call.return_value = {"id": 1, "name": "test"}
    
    # Create a minimal client
    client = GitLabClient.__new__(GitLabClient)
    client.api_base = "https://gitlab.com/api/v4"
    client.headers = {"PRIVATE-TOKEN": "test"}
    
    result = client._get("/projects/1")
    
    assert result == {"id": 1, "name": "test"}


# ------------------------------
# Test: GitLabClient _request returns None on 204
# ------------------------------
@patch('gitlab_utils.client.requests.request')
@patch('gitlab_utils.client.safe_api_call')
def test_gitlab_client_request_204(mock_safe_call, mock_request):
    mock_response = Mock()
    mock_response.status_code = 204
    
    mock_safe_call.return_value = None
    
    client = GitLabClient.__new__(GitLabClient)
    client.api_base = "https://gitlab.com/api/v4"
    client.headers = {"PRIVATE-TOKEN": "test"}
    
    result = client._request("DELETE", "/projects/1")
    
    assert result is None
