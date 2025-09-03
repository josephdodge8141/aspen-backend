import pytest
import os
from unittest.mock import patch, MagicMock
from app.services.openai_client import get_openai_service


class TestOpenAIIntegration:
    def test_openai_service_requires_api_key(self):
        """Test that OpenAI service requires API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable is required"):
                from app.services.openai_client import OpenAIService
                OpenAIService()

    @patch("app.services.openai_client.OpenAI")
    def test_chat_completion_success(self, mock_openai):
        """Test successful chat completion."""
        # Mock the OpenAI client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Test response"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        # Mock environment variable
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            from app.services.openai_client import OpenAIService
            service = OpenAIService()
            
            result = service.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                model="gpt-4"
            )
            
            assert result == "Test response"
            mock_client.chat.completions.create.assert_called_once()

    @patch("app.services.openai_client.OpenAI")
    def test_generate_text_success(self, mock_openai):
        """Test successful text generation."""
        # Mock the OpenAI client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Generated text"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        # Mock environment variable
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            from app.services.openai_client import OpenAIService
            service = OpenAIService()
            
            result = service.generate_text("Test prompt")
            
            assert result == "Generated text"
            mock_client.chat.completions.create.assert_called_once()

    @patch("app.services.openai_client.OpenAI")
    def test_embeddings_success(self, mock_openai):
        """Test successful embeddings creation."""
        # Mock the OpenAI client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data[0].embedding = [0.1, 0.2, 0.3]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client

        # Mock environment variable
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            from app.services.openai_client import OpenAIService
            service = OpenAIService()
            
            # Test the embedding functionality through the embed node
            from app.services.nodes.ai_embed import EmbedService
            embed_service = EmbedService()
            
            result = embed_service.execute(
                inputs={"input": "Test text"},
                metadata={"model_name": "text-embedding-3-small"}
            )
            
            assert "embedding" in result
            assert result["embedding"] == [0.1, 0.2, 0.3]
            assert result["dimensions"] == 3
            mock_client.embeddings.create.assert_called_once()

    def test_job_node_requires_prompt(self):
        """Test that job node requires prompt in metadata."""
        from app.services.nodes.ai_job import JobService
        job_service = JobService()
        
        with pytest.raises(ValueError, match="Job node requires a 'prompt' in metadata"):
            job_service.execute(
                inputs={},
                metadata={}
            ) 