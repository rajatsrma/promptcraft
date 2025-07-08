import pytest
from unittest.mock import Mock, patch
from promptcraft.models import PromptData
from promptcraft.main import handle_persona, handle_task, handle_context, generate_prompt_string


class TestPhase1:
    """Test suite for Phase 1 functionality."""

    def test_prompt_data_initialization(self):
        """Test that PromptData initializes with correct defaults."""
        data = PromptData()
        assert data.persona is None
        assert data.task is None
        assert data.context is None
        assert data.schemas == []
        assert data.examples == []
        assert data.constraints is None

    @patch('promptcraft.main.inquirer.text')
    def test_handle_persona(self, mock_inquirer):
        """Test persona handling updates PromptData correctly."""
        # Mock the inquirer response
        mock_inquiry = Mock()
        mock_inquiry.execute.return_value = "You are a senior Python developer"
        mock_inquirer.return_value = mock_inquiry
        
        # Create test data
        prompt_data = PromptData()
        
        # Call the function
        handle_persona(prompt_data)
        
        # Assert the data was updated
        assert prompt_data.persona == "You are a senior Python developer"
        mock_inquirer.assert_called_once()

    @patch('promptcraft.main.inquirer.text')
    def test_handle_task(self, mock_inquirer):
        """Test task handling updates PromptData correctly."""
        # Mock the inquirer response
        mock_inquiry = Mock()
        mock_inquiry.execute.return_value = "Write a FastAPI endpoint"
        mock_inquirer.return_value = mock_inquiry
        
        # Create test data
        prompt_data = PromptData()
        
        # Call the function
        handle_task(prompt_data)
        
        # Assert the data was updated
        assert prompt_data.task == "Write a FastAPI endpoint"
        mock_inquirer.assert_called_once()

    @patch('promptcraft.main.inquirer.text')
    def test_handle_context(self, mock_inquirer):
        """Test context handling updates PromptData correctly."""
        # Mock the inquirer response
        mock_inquiry = Mock()
        mock_inquiry.execute.return_value = "Using PostgreSQL database"
        mock_inquirer.return_value = mock_inquiry
        
        # Create test data
        prompt_data = PromptData()
        
        # Call the function
        handle_context(prompt_data)
        
        # Assert the data was updated
        assert prompt_data.context == "Using PostgreSQL database"
        mock_inquirer.assert_called_once()

    def test_prompt_data_schemas_list(self):
        """Test that schemas are properly managed as a list."""
        data = PromptData()
        data.schemas.append("User schema")
        data.schemas.append("Product schema")
        
        assert len(data.schemas) == 2
        assert "User schema" in data.schemas
        assert "Product schema" in data.schemas

    def test_prompt_data_examples_list(self):
        """Test that examples are properly managed as a list."""
        data = PromptData()
        data.examples.append("Example 1")
        data.examples.append("Example 2")
        
        assert len(data.examples) == 2
        assert "Example 1" in data.examples
        assert "Example 2" in data.examples

    def test_generate_prompt_string(self):
        """Test that generate_prompt_string produces correctly formatted Markdown."""
        # Create a sample PromptData object filled with data
        data = PromptData()
        data.persona = "You are a senior Python developer"
        data.task = "Write a FastAPI endpoint for user authentication"
        data.context = "Using PostgreSQL database and JWT tokens"
        data.schemas = ["User(id: int, email: str, hashed_password: str)", "Token(access_token: str, token_type: str)"]
        data.examples = ["POST /auth/login", "GET /auth/me"]
        data.constraints = "Follow PEP 8 style guide and include proper error handling"
        
        # Generate the prompt string
        result = generate_prompt_string(data)
        
        # Expected output (snapshot testing)
        expected = """# Persona

You are a senior Python developer

# Task

Write a FastAPI endpoint for user authentication

# Context

Using PostgreSQL database and JWT tokens

# Schemas

## Schema 1

User(id: int, email: str, hashed_password: str)

## Schema 2

Token(access_token: str, token_type: str)

# Examples

## Example 1

POST /auth/login

## Example 2

GET /auth/me

# Constraints

Follow PEP 8 style guide and include proper error handling"""
        
        assert result == expected

    def test_generate_prompt_string_empty(self):
        """Test that generate_prompt_string handles empty data correctly."""
        data = PromptData()
        result = generate_prompt_string(data)
        assert result == ""

    def test_generate_prompt_string_partial(self):
        """Test that generate_prompt_string handles partial data correctly."""
        data = PromptData()
        data.task = "Write a function"
        data.constraints = "Use type hints"
        
        result = generate_prompt_string(data)
        expected = """# Task

Write a function

# Constraints

Use type hints"""
        
        assert result == expected