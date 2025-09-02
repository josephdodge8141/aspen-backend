import pytest
from pydantic import ValidationError
from app.schemas.experts import (
    ExpertBase,
    ExpertCreate,
    ExpertUpdate,
    ExpertRead,
    ExpertListItem,
)
from app.models.common import ExpertStatus


def test_expert_base_valid():
    """Test ExpertBase with valid data"""
    data = {
        "name": "Test Expert",
        "prompt": "You are a helpful assistant.",
        "model_name": "gpt-4",
        "status": ExpertStatus.active,
        "input_params": {"temperature": 0.7},
    }
    expert = ExpertBase(**data)
    assert expert.name == "Test Expert"
    assert expert.status == ExpertStatus.active
    assert expert.input_params == {"temperature": 0.7}


def test_expert_base_default_status():
    """Test ExpertBase uses draft as default status"""
    data = {
        "name": "Test Expert",
        "prompt": "You are a helpful assistant.",
        "model_name": "gpt-4",
        "input_params": {"temperature": 0.7},
    }
    expert = ExpertBase(**data)
    assert expert.status == ExpertStatus.draft


def test_expert_create_inherits_base():
    """Test ExpertCreate includes team_id and inherits from ExpertBase"""
    data = {
        "name": "Test Expert",
        "prompt": "You are a helpful assistant.",
        "model_name": "gpt-4",
        "input_params": {"temperature": 0.7},
        "team_id": 123,
    }
    expert = ExpertCreate(**data)
    assert expert.team_id == 123
    assert expert.name == "Test Expert"
    assert expert.status == ExpertStatus.draft


def test_expert_update_all_optional():
    """Test ExpertUpdate has all optional fields"""
    # Empty update should be valid
    expert = ExpertUpdate()
    assert expert.name is None
    assert expert.prompt is None
    assert expert.model_name is None
    assert expert.status is None
    assert expert.input_params is None

    # Partial update should be valid
    expert = ExpertUpdate(name="Updated Name", status=ExpertStatus.active)
    assert expert.name == "Updated Name"
    assert expert.status == ExpertStatus.active
    assert expert.prompt is None


def test_expert_read_all_required():
    """Test ExpertRead has all required fields"""
    data = {
        "id": 1,
        "uuid": "test-uuid-123",
        "name": "Test Expert",
        "prompt": "You are a helpful assistant.",
        "model_name": "gpt-4",
        "status": ExpertStatus.active,
        "input_params": {"temperature": 0.7},
        "team_id": 123,
    }
    expert = ExpertRead(**data)
    assert expert.id == 1
    assert expert.uuid == "test-uuid-123"
    assert expert.team_id == 123


def test_expert_list_item_has_counts():
    """Test ExpertListItem includes count fields"""
    data = {
        "id": 1,
        "name": "Test Expert",
        "model_name": "gpt-4",
        "status": ExpertStatus.active,
        "prompt_truncated": "You are a helpful...",
        "workflows_count": 3,
        "services_count": 2,
        "team_id": 123,
    }
    expert = ExpertListItem(**data)
    assert expert.workflows_count == 3
    assert expert.services_count == 2
    assert expert.prompt_truncated == "You are a helpful..."


def test_input_params_validation():
    """Test that input_params must be a dict"""
    # Valid dict
    data = {
        "name": "Test Expert",
        "prompt": "You are a helpful assistant.",
        "model_name": "gpt-4",
        "input_params": {"key": "value"},
    }
    expert = ExpertBase(**data)
    assert expert.input_params == {"key": "value"}

    # Invalid type should raise validation error
    data["input_params"] = "not a dict"
    with pytest.raises(ValidationError):
        ExpertBase(**data)


def test_status_enum_validation():
    """Test that status field validates against ExpertStatus enum"""
    data = {
        "name": "Test Expert",
        "prompt": "You are a helpful assistant.",
        "model_name": "gpt-4",
        "input_params": {"temperature": 0.7},
    }

    # Valid enum values
    for status in ExpertStatus:
        data["status"] = status
        expert = ExpertBase(**data)
        assert expert.status == status

    # Invalid status should raise validation error
    data["status"] = "invalid_status"
    with pytest.raises(ValidationError):
        ExpertBase(**data)


def test_required_fields_validation():
    """Test that required fields are validated"""
    # Missing name
    with pytest.raises(ValidationError) as exc_info:
        ExpertBase(
            prompt="You are a helpful assistant.", model_name="gpt-4", input_params={}
        )
    assert "name" in str(exc_info.value)

    # Missing prompt
    with pytest.raises(ValidationError) as exc_info:
        ExpertBase(name="Test Expert", model_name="gpt-4", input_params={})
    assert "prompt" in str(exc_info.value)


def test_schema_serialization():
    """Test that schemas can be serialized to dict/JSON"""
    expert = ExpertRead(
        id=1,
        uuid="test-uuid",
        name="Test Expert",
        prompt="You are helpful.",
        model_name="gpt-4",
        status=ExpertStatus.active,
        input_params={"temp": 0.7},
        team_id=123,
    )

    # Should serialize to dict
    data = expert.model_dump()
    assert data["id"] == 1
    assert data["status"] == "active"  # Enum serialized as string
    assert data["input_params"] == {"temp": 0.7}

    # Should serialize to JSON string
    json_str = expert.model_dump_json()
    assert isinstance(json_str, str)
    assert "Test Expert" in json_str
