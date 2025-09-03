import pytest
from app.services.nodes.ai_job import JobService
from app.services.nodes.base import NodeValidationError


class TestJobService:
    def setup_method(self):
        self.service = JobService()

    def test_validate_valid_metadata(self):
        metadata = {
            "prompt": "Summarize the following text: {{ input.text }}",
            "model_name": "gpt-4o-mini",
            "temperature": 0.7,
            "max_tokens": 500,
            "system": "You are a helpful assistant",
        }
        structured_output = {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "key_points": {"type": "array", "items": {"type": "string"}},
            },
        }

        self.service.validate(metadata, structured_output)

    def test_validate_minimal_metadata(self):
        metadata = {"prompt": "Test prompt", "model_name": "gpt-4"}
        structured_output = {}

        self.service.validate(metadata, structured_output)

    def test_validate_missing_required_fields(self):
        metadata = {"prompt": "Test prompt"}
        structured_output = {}

        with pytest.raises(NodeValidationError, match="Invalid job metadata"):
            self.service.validate(metadata, structured_output)

    def test_validate_empty_prompt(self):
        metadata = {"prompt": "", "model_name": "gpt-4"}
        structured_output = {}

        with pytest.raises(NodeValidationError, match="Invalid job metadata"):
            self.service.validate(metadata, structured_output)

    def test_validate_invalid_temperature(self):
        metadata = {"prompt": "Test prompt", "model_name": "gpt-4", "temperature": 3.0}
        structured_output = {}

        with pytest.raises(NodeValidationError, match="Invalid job metadata"):
            self.service.validate(metadata, structured_output)

    def test_validate_unknown_fields(self):
        metadata = {
            "prompt": "Test prompt",
            "model_name": "gpt-4",
            "unknown_field": "value",
        }
        structured_output = {}

        with pytest.raises(
            NodeValidationError, match="Unknown fields in metadata: unknown_field"
        ):
            self.service.validate(metadata, structured_output)

    def test_validate_invalid_metadata_type(self):
        metadata = "not a dict"
        structured_output = {}

        with pytest.raises(NodeValidationError, match="metadata must be a dictionary"):
            self.service.validate(metadata, structured_output)

    def test_validate_invalid_structured_output_type(self):
        metadata = {"prompt": "Test prompt", "model_name": "gpt-4"}
        structured_output = "not a dict"

        with pytest.raises(
            NodeValidationError, match="structured_output must be a dictionary"
        ):
            self.service.validate(metadata, structured_output)

    def test_plan_with_structured_output(self):
        metadata = {"prompt": "Test prompt", "model_name": "gpt-4"}
        inputs_shape = {"text": "string"}
        structured_output = {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "confidence": {"type": "number"},
            },
        }

        result = self.service.plan(metadata, inputs_shape, structured_output)

        assert result == {"summary": "string", "confidence": "number"}

    def test_plan_without_structured_output(self):
        metadata = {"prompt": "Test prompt", "model_name": "gpt-4"}
        inputs_shape = {"text": "string"}
        structured_output = {}

        result = self.service.plan(metadata, inputs_shape, structured_output)

        assert result == {"text": "string"}

    def test_plan_with_nested_structured_output(self):
        metadata = {"prompt": "Test prompt", "model_name": "gpt-4"}
        inputs_shape = {}
        structured_output = {
            "type": "object",
            "properties": {
                "analysis": {
                    "type": "object",
                    "properties": {
                        "sentiment": {"type": "string"},
                        "score": {"type": "number"},
                    },
                }
            },
        }

        result = self.service.plan(metadata, inputs_shape, structured_output)

        assert result == {"analysis": {"sentiment": "string", "score": "number"}}

    def test_execute_with_structured_output(self):
        inputs = {
            "text": "Sample text",
            "structured_output": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "confidence": {"type": "number"},
                },
            },
        }
        metadata = {"prompt": "Test prompt", "model_name": "gpt-4"}

        result = self.service.execute(inputs, metadata)

        assert result == {"summary": None, "confidence": None}

    def test_execute_without_structured_output(self):
        inputs = {"text": "Sample text"}
        metadata = {"prompt": "Test prompt", "model_name": "gpt-4"}

        result = self.service.execute(inputs, metadata)

        assert result == {"text": None}

    def test_execute_empty_structured_output(self):
        inputs = {"text": "Sample text", "structured_output": {}}
        metadata = {"prompt": "Test prompt", "model_name": "gpt-4"}

        result = self.service.execute(inputs, metadata)

        # When structured_output is empty, should return default text shape
        assert result == {"text": None}
