import pytest
import os
import json
import yaml
from unittest.mock import Mock, patch, MagicMock, mock_open
from promptcraft.main import run_session
from promptcraft.models import PromptData


class TestPhase3:
    """Test suite for Phase 3 functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create test configuration
        self.test_config = {
            "framework": "FastAPI",
            "database": "PostgreSQL",
            "style_guide": "PEP 8",
            "llm": {
                "provider": "OpenAI",
                "model": "gpt-4o-mini"
            }
        }
        
        # Create test session data
        self.test_session = {
            "persona": "You are a senior Python developer",
            "task": "Write a FastAPI endpoint for user authentication",
            "context": "Using PostgreSQL database and JWT tokens",
            "schemas": ["User(id: int, email: str, password: str)"],
            "examples": ["POST /auth/login"],
            "constraints": "Follow PEP 8 style guide"
        }

    @patch('promptcraft.main.os.path.exists')
    @patch('promptcraft.main.yaml.safe_load')
    @patch('promptcraft.main.json.load')
    @patch('promptcraft.main.os.getenv')
    @patch('promptcraft.main.OpenAI')
    @patch('promptcraft.main.typer.echo')
    @patch('builtins.open', new_callable=mock_open)
    @patch('rich.console.Console.print')
    def test_run_command_success(self, mock_rich_print, mock_open, mock_echo, mock_openai, mock_getenv,
                                 mock_json_load, mock_yaml_load, mock_exists):
        """Test successful run command execution."""
        
        # Mock file existence
        mock_exists.return_value = True
        
        # Mock configuration and session loading
        mock_yaml_load.return_value = self.test_config
        mock_json_load.return_value = self.test_session
        
        # Mock environment variable
        mock_getenv.return_value = "test-api-key"
        
        # Mock OpenAI client and response
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Here's your FastAPI endpoint code..."
        mock_client.chat.completions.create.return_value = mock_response
        
        # Call the function
        run_session("test-session")
        
        # Verify OpenAI client was created with correct API key
        mock_openai.assert_called_once_with(api_key="test-api-key")
        
        # Verify API call was made
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        
        # Check that the prompt was correctly assembled
        messages = call_args[1]['messages']
        assert len(messages) == 1
        assert messages[0]['role'] == 'user'
        
        # The content should contain the generated prompt
        prompt_content = messages[0]['content']
        assert "# Persona" in prompt_content
        assert "You are a senior Python developer" in prompt_content
        assert "# Task" in prompt_content
        assert "Write a FastAPI endpoint for user authentication" in prompt_content
        
        # Verify success messages were printed
        mock_echo.assert_any_call("🚀 Running session 'test-session' with OpenAI gpt-4o-mini...")
        mock_echo.assert_any_call("⏳ Generating response...")

    @patch('promptcraft.main.os.path.exists')
    @patch('promptcraft.main.typer.echo')
    def test_run_command_no_config(self, mock_echo, mock_exists):
        """Test run command when no configuration exists."""
        mock_exists.return_value = False
        
        run_session("test-session")
        
        mock_echo.assert_any_call("❌ No configuration found. Run 'promptcraft init' first.")

    @patch('promptcraft.main.os.path.exists')
    @patch('promptcraft.main.yaml.safe_load')
    @patch('promptcraft.main.json.load')
    @patch('promptcraft.main.os.getenv')
    @patch('promptcraft.main.typer.echo')
    @patch('builtins.open', new_callable=mock_open)
    def test_run_command_no_api_key(self, mock_open, mock_echo, mock_getenv, mock_json_load,
                                   mock_yaml_load, mock_exists):
        """Test run command when API key is not set."""
        mock_exists.return_value = True
        mock_yaml_load.return_value = self.test_config
        mock_json_load.return_value = self.test_session
        mock_getenv.return_value = None  # No API key

        run_session("test-session")

        mock_echo.assert_any_call("❌ OPENAI_API_KEY environment variable not set.")

    @patch('promptcraft.main.os.path.exists')
    @patch('promptcraft.main.yaml.safe_load')
    @patch('promptcraft.main.typer.echo')
    @patch('builtins.open', new_callable=mock_open)
    def test_run_command_session_not_found(self, mock_open, mock_echo, mock_yaml_load, mock_exists):
        """Test run command when session file doesn't exist."""
        # Mock config exists but session doesn't
        def exists_side_effect(path):
            if path == ".promptcraft.yml":
                return True
            return False
        
        mock_exists.side_effect = exists_side_effect
        mock_yaml_load.return_value = self.test_config
        
        run_session("non-existent-session")
        
        mock_echo.assert_any_call("❌ Session 'non-existent-session' not found.")
        mock_echo.assert_any_call("💡 Use 'promptcraft list' to see available sessions.")