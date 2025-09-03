import pytest
from app.mappers.experts import to_list_item, to_read, truncate_prompt
from app.models.experts import Expert, ExpertStatus
from app.schemas.experts import ExpertListItem, ExpertRead


class TestTruncatePrompt:
    def test_truncate_prompt_short_text(self):
        """Test truncation with text shorter than max length."""
        prompt = "Short prompt"
        result = truncate_prompt(prompt, 120)
        assert result == "Short prompt"

    def test_truncate_prompt_exact_length(self):
        """Test truncation with text exactly at max length."""
        prompt = "A" * 120
        result = truncate_prompt(prompt, 120)
        assert result == "A" * 120
        assert len(result) == 120

    def test_truncate_prompt_long_text(self):
        """Test truncation with text longer than max length."""
        prompt = "A" * 150
        result = truncate_prompt(prompt, 120)
        assert result == "A" * 120 + "..."
        assert len(result) == 123  # 120 + 3 for "..."

    def test_truncate_prompt_custom_length(self):
        """Test truncation with custom max length."""
        prompt = "This is a longer prompt that should be truncated"
        result = truncate_prompt(prompt, 20)
        assert result == "This is a longer pro..."
        assert len(result) == 23  # 20 + 3 for "..."

    def test_truncate_prompt_empty_string(self):
        """Test truncation with empty string."""
        result = truncate_prompt("", 120)
        assert result == ""

    def test_truncate_prompt_default_length(self):
        """Test truncation uses default length of 120."""
        prompt = "A" * 150
        result = truncate_prompt(prompt)  # No max_length specified
        assert result == "A" * 120 + "..."
        assert len(result) == 123


class TestToListItem:
    @pytest.fixture
    def sample_expert(self):
        """Create a sample expert for testing."""
        return Expert(
            id=1,
            uuid="test-uuid-123",
            name="Test Expert",
            prompt="This is a test prompt for the expert",
            input_params={"param1": "value1"},
            status=ExpertStatus.active,
            model_name="gpt-4",
            team_id=10,
        )

    def test_to_list_item_basic(self, sample_expert):
        """Test basic conversion to list item."""
        result = to_list_item(sample_expert, workflows_count=2, services_count=3)

        assert isinstance(result, ExpertListItem)
        assert result.id == 1
        assert result.name == "Test Expert"
        assert result.prompt_truncated == "This is a test prompt for the expert"
        assert result.status == ExpertStatus.active
        assert result.model_name == "gpt-4"
        assert result.workflows_count == 2
        assert result.services_count == 3
        assert result.team_id == 10

    def test_to_list_item_prompt_truncation(self, sample_expert):
        """Test prompt truncation in list item."""
        long_prompt = "A" * 150
        sample_expert.prompt = long_prompt

        result = to_list_item(sample_expert, workflows_count=1, services_count=1)

        assert result.prompt_truncated == "A" * 120 + "..."
        assert len(result.prompt_truncated) == 123

    def test_to_list_item_zero_counts(self, sample_expert):
        """Test list item with zero workflow and service counts."""
        result = to_list_item(sample_expert, workflows_count=0, services_count=0)

        assert result.workflows_count == 0
        assert result.services_count == 0

    def test_to_list_item_different_status(self, sample_expert):
        """Test list item with different expert status."""
        sample_expert.status = ExpertStatus.archive

        result = to_list_item(sample_expert, workflows_count=1, services_count=1)

        assert result.status == ExpertStatus.archive

    def test_to_list_item_prompt_exactly_120_chars(self, sample_expert):
        """Test list item with prompt exactly 120 characters."""
        sample_expert.prompt = "A" * 120

        result = to_list_item(sample_expert, workflows_count=1, services_count=1)

        assert result.prompt_truncated == "A" * 120
        assert len(result.prompt_truncated) == 120


class TestToRead:
    @pytest.fixture
    def sample_expert(self):
        """Create a sample expert for testing."""
        return Expert(
            id=1,
            uuid="test-uuid-123",
            name="Test Expert",
            prompt="This is a test prompt for the expert",
            input_params={"param1": "value1", "param2": {"nested": "value"}},
            status=ExpertStatus.active,
            model_name="gpt-4",
            team_id=10,
        )

    def test_to_read_basic(self, sample_expert):
        """Test basic conversion to read DTO."""
        result = to_read(sample_expert)

        assert isinstance(result, ExpertRead)
        assert result.id == 1
        assert result.uuid == "test-uuid-123"
        assert result.name == "Test Expert"
        assert result.prompt == "This is a test prompt for the expert"
        assert result.input_params == {
            "param1": "value1",
            "param2": {"nested": "value"},
        }
        assert result.status == ExpertStatus.active
        assert result.model_name == "gpt-4"
        assert result.team_id == 10

    def test_to_read_full_prompt_preserved(self, sample_expert):
        """Test that full prompt is preserved in read DTO (no truncation)."""
        long_prompt = "A" * 500  # Very long prompt
        sample_expert.prompt = long_prompt

        result = to_read(sample_expert)

        assert result.prompt == long_prompt
        assert len(result.prompt) == 500

    def test_to_read_empty_input_params(self, sample_expert):
        """Test read DTO with empty input params."""
        sample_expert.input_params = {}

        result = to_read(sample_expert)

        assert result.input_params == {}

    def test_to_read_none_input_params(self, sample_expert):
        """Test read DTO with None input params."""
        sample_expert.input_params = None

        result = to_read(sample_expert)

        assert result.input_params == {}  # None is converted to empty dict

    def test_to_read_different_status(self, sample_expert):
        """Test read DTO with different expert status."""
        sample_expert.status = ExpertStatus.archive

        result = to_read(sample_expert)

        assert result.status == ExpertStatus.archive

    def test_to_read_complex_input_params(self, sample_expert):
        """Test read DTO with complex input parameters."""
        complex_params = {
            "string_param": "value",
            "number_param": 42,
            "boolean_param": True,
            "array_param": [1, 2, 3],
            "nested_object": {"level1": {"level2": "deep_value"}},
        }
        sample_expert.input_params = complex_params

        result = to_read(sample_expert)

        assert result.input_params == complex_params


class TestMapperIntegration:
    @pytest.fixture
    def sample_expert(self):
        """Create a sample expert for testing."""
        return Expert(
            id=1,
            uuid="test-uuid-123",
            name="Test Expert",
            prompt="This is a moderately long prompt that might need truncation in list view but should be preserved in detail view. "
            + "A" * 50,  # Make it longer than 120 chars
            input_params={"param1": "value1"},
            status=ExpertStatus.active,
            model_name="gpt-4",
            team_id=10,
        )

    def test_list_vs_read_prompt_handling(self, sample_expert):
        """Test that list item truncates prompt while read preserves it."""
        list_item = to_list_item(sample_expert, workflows_count=1, services_count=1)
        read_item = to_read(sample_expert)

        # List item should have truncated prompt
        assert len(list_item.prompt_truncated) <= 123  # 120 + "..." if truncated

        # Read item should have full prompt
        assert read_item.prompt == sample_expert.prompt
        assert len(read_item.prompt) > 120

    def test_consistent_basic_fields(self, sample_expert):
        """Test that basic fields are consistent between list and read DTOs."""
        list_item = to_list_item(sample_expert, workflows_count=2, services_count=3)
        read_item = to_read(sample_expert)

        # These fields should be identical
        assert list_item.id == read_item.id
        assert list_item.name == read_item.name
        assert list_item.status == read_item.status
        assert list_item.model_name == read_item.model_name
        assert list_item.team_id == read_item.team_id
