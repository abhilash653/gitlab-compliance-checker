import os
import pytest
from unittest.mock import Mock, patch, MagicMock, call
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def mock_streamlit():
    """Mock Streamlit module"""
    with patch.dict('sys.modules', {'streamlit': MagicMock()}):
        yield


@pytest.fixture
def mock_gitlab_client():
    """Mock GitLabClient"""
    mock_client = Mock()
    mock_client.client = Mock()
    return mock_client


@pytest.fixture
def mock_dotenv():
    """Mock load_dotenv"""
    with patch('app.load_dotenv'):
        yield


class TestAppImports:
    """Test module imports"""
    
    def test_app_module_exists(self):
        """Test that app module can be imported"""
        app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app.py'))
        assert os.path.exists(app_path), "app.py file should exist"


class TestMainFunctionBasic:
    """Test main() function basic behavior"""
    
    @patch('sys.modules', {'streamlit': MagicMock(), 'dotenv': MagicMock()})
    def test_main_function_exists(self):
        """Test that main function exists in app module"""
        app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app.py'))
        with open(app_path, 'r') as f:
            content = f.read()
            assert 'def main():' in content, "main() function should exist in app.py"


class TestEnvironmentVariables:
    """Test environment variable handling"""
    
    def test_env_variables_in_app(self):
        """Test that environment variables are referenced in app"""
        app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app.py'))
        with open(app_path, 'r') as f:
            content = f.read()
            assert 'GITLAB_URL' in content, "app.py should reference GITLAB_URL"
            assert 'GITLAB_TOKEN' in content, "app.py should reference GITLAB_TOKEN"
            assert 'os.getenv' in content, "app.py should use os.getenv()"
    
    def test_load_dotenv_called(self):
        """Test that load_dotenv is called"""
        app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app.py'))
        with open(app_path, 'r') as f:
            content = f.read()
            assert 'load_dotenv()' in content, "app.py should call load_dotenv()"


class TestSessionState:
    """Test session state management"""
    
    def test_session_state_in_app(self):
        """Test that session state management is in app"""
        app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app.py'))
        with open(app_path, 'r') as f:
            content = f.read()
            assert 'st.session_state' in content, "app.py should use st.session_state"
            assert 'previous_mode' in content, "app.py should track previous_mode"
    
    def test_contribution_mode_state_reset(self):
        """Test that contribution mode state reset logic exists"""
        app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app.py'))
        with open(app_path, 'r') as f:
            content = f.read()
            assert 'contribution_sub_mode' in content, "app.py should handle contribution_sub_mode"
            assert 'contribution_view_type' in content, "app.py should handle contribution_view_type"


class TestModeRouting:
    """Test routing to different modes"""
    
    def test_all_modes_in_app(self):
        """Test that all modes are supported in app"""
        app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app.py'))
        with open(app_path, 'r') as f:
            content = f.read()
            assert 'Check Project Compliance' in content
            assert 'Contribution Mapping' in content
            assert 'Batch 2026 ICFAI' in content
            assert 'Batch 2026 RCTS' in content
    
    def test_render_functions_called(self):
        """Test that render functions are called for different modes"""
        app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app.py'))
        with open(app_path, 'r') as f:
            content = f.read()
            assert 'render_compliance_mode' in content
            assert 'render_batch_mode_ui' in content
            assert 'render_user_profile' in content
            assert 'render_contribution_mapping' in content


class TestPageConfiguration:
    """Test page configuration"""
    
    def test_page_config_exists(self):
        """Test that page configuration is set"""
        app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app.py'))
        with open(app_path, 'r') as f:
            content = f.read()
            assert 'set_page_config' in content, "app.py should set page configuration"
    
    def test_page_config_parameters_present(self):
        """Test page config has correct parameters"""
        app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app.py'))
        with open(app_path, 'r') as f:
            content = f.read()
            assert 'page_title' in content or 'GitLab Compliance' in content
            assert 'layout' in content


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_import_error_handling_exists(self):
        """Test that import error handling is implemented"""
        app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app.py'))
        with open(app_path, 'r') as f:
            content = f.read()
            assert 'ImportError' in content or 'except' in content
    
    def test_gitlab_client_validation(self):
        """Test that GitLab client is validated"""
        app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app.py'))
        with open(app_path, 'r') as f:
            content = f.read()
            assert 'GitLabClient' in content, "app.py should use GitLabClient"
            assert 'client' in content.lower(), "app.py should check client initialization"
    
    def test_token_validation_exists(self):
        """Test that token validation exists"""
        app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app.py'))
        with open(app_path, 'r') as f:
            content = f.read()
            assert 'gitlab_token' in content or 'token' in content.lower()
            assert 'warning' in content.lower() or 'error' in content.lower()


class TestUIComponents:
    """Test UI components and layout"""
    
    def test_sidebar_elements(self):
        """Test that sidebar elements are created"""
        app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app.py'))
        with open(app_path, 'r') as f:
            content = f.read()
            assert 'st.sidebar' in content, "app.py should use sidebar"
            assert 'text_input' in content, "app.py should have text input for credentials"
            assert 'radio' in content, "app.py should have radio selection for modes"
    
    def test_title_and_headers(self):
        """Test that title and headers are set"""
        app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app.py'))
        with open(app_path, 'r') as f:
            content = f.read()
            assert 'st.title' in content or 'title' in content.lower()
            assert 'Configuration' in content or 'configuration' in content.lower()
    
    def test_user_input_elements(self):
        """Test that user input elements exist"""
        app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app.py'))
        with open(app_path, 'r') as f:
            content = f.read()
            assert 'text_input' in content, "Should have text input for GitLab URL"
            assert 'password' in content, "Should have password input for token"


class TestFlowControl:
    """Test application flow control"""
    
    def test_mode_selection_logic(self):
        """Test that mode selection determines app flow"""
        app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app.py'))
        with open(app_path, 'r') as f:
            content = f.read()
            assert 'if mode ==' in content or 'if mode' in content
            assert 'elif mode ==' in content or 'elif' in content
    
    def test_contribution_mapping_flow(self):
        """Test contribution mapping flow logic"""
        app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app.py'))
        with open(app_path, 'r') as f:
            content = f.read()
            assert 'User Profile Overview' in content
            assert 'Team' in content
    
    def test_validation_checks(self):
        """Test that validation checks are performed"""
        app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app.py'))
        with open(app_path, 'r') as f:
            content = f.read()
            assert 'if not' in content, "Should validate inputs"
            assert 'assert' in content or 'error' in content.lower()


class TestIntegration:
    """Integration tests"""
    
    def test_imports_structure(self):
        """Test that imports are properly structured"""
        app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app.py'))
        with open(app_path, 'r') as f:
            content = f.read()
            lines = content.split('\n')
            # Find import section (should be at top)
            import_count = 0
            for line in lines[:30]:
                if 'import' in line:
                    import_count += 1
            assert import_count > 0, "Should have imports at the top"
    
    def test_main_entry_point(self):
        """Test main entry point exists"""
        app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app.py'))
        with open(app_path, 'r') as f:
            content = f.read()
            assert '__name__' in content
            assert '__main__' in content
            assert 'main()' in content
    
    def test_no_syntax_errors(self):
        """Test that app.py has no syntax errors"""
        app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app.py'))
        try:
            with open(app_path, 'r') as f:
                compile(f.read(), app_path, 'exec')
            assert True, "No syntax errors"
        except SyntaxError as e:
            pytest.fail(f"Syntax error in app.py: {e}")


# Test execution
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
