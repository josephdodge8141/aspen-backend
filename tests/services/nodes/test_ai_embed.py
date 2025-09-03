import pytest
from unittest.mock import patch, MagicMock
from app.services.nodes.ai_embed import EmbedService
from app.services.nodes.base import NodeValidationError


class TestEmbedService:
    def setup_method(self):
        self.service = EmbedService()

    def test_validate_valid_metadata(self):
        metadata = {
            "vector_store_id": "vs_customers",
            "namespace": "orders",
            "input_selector": "input.order.items[*].description",
            "id_selector": "input.order.id",
            "metadata_map": {"customer": "input.customer.id"},
            "upsert": True,
        }
        structured_output = {}

        self.service.validate(metadata, structured_output)

    def test_validate_minimal_metadata(self):
        metadata = {"vector_store_id": "vs_test", "input_selector": "input.text"}
        structured_output = {}

        self.service.validate(metadata, structured_output)

    def test_validate_missing_required_fields(self):
        metadata = {"vector_store_id": "vs_test"}
        structured_output = {}

        with pytest.raises(NodeValidationError, match="Invalid embed metadata"):
            self.service.validate(metadata, structured_output)

    def test_validate_empty_vector_store_id(self):
        metadata = {"vector_store_id": "", "input_selector": "input.text"}
        structured_output = {}

        with pytest.raises(NodeValidationError, match="Invalid embed metadata"):
            self.service.validate(metadata, structured_output)

    def test_validate_unknown_fields(self):
        metadata = {
            "vector_store_id": "vs_test",
            "input_selector": "input.text",
            "unknown_field": "value",
        }
        structured_output = {}

        with pytest.raises(
            NodeValidationError, match="Unknown fields in metadata: unknown_field"
        ):
            self.service.validate(metadata, structured_output)

    def test_plan_returns_expected_shape(self):
        metadata = {"vector_store_id": "vs_test", "input_selector": "input.text"}
        inputs_shape = {"text": "string"}
        structured_output = {}

        result = self.service.plan(metadata, inputs_shape, structured_output)

        assert result == {"embedded": "boolean", "count": "number"}

    @patch("app.services.nodes.ai_embed.get_openai_service")
    def test_execute_returns_expected_result(self, mock_service):
        # Mock OpenAI service to return embedding response
        mock_openai = mock_service.return_value
        mock_response = MagicMock()
        mock_response.data[0].embedding = [0.1, 0.2, 0.3]
        mock_openai.client.embeddings.create.return_value = mock_response

        inputs = {
            "input": "Sample text"
        }  # Changed from "text" to "input" to match implementation
        metadata = {
            "vector_store_id": "vs_test",
            "model_name": "text-embedding-3-small",
        }

        result = self.service.execute(inputs, metadata)

        assert result == {
            "embedding": [0.1, 0.2, 0.3],
            "dimensions": 3,
            "model": "text-embedding-3-small",
            "input_length": 11,
        }
