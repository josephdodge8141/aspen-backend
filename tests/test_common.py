from datetime import datetime
from sqlmodel import Field
from app.models.common import (
    ExpertStatus,
    TeamRole,
    Environment,
    NodeType,
    TimestampMixin,
)


def test_expert_status_enum():
    assert ExpertStatus.draft == "draft"
    assert ExpertStatus.active == "active"
    assert ExpertStatus.archive == "archive"
    assert ExpertStatus.historical == "historical"


def test_team_role_enum():
    assert TeamRole.admin == "admin"
    assert TeamRole.member == "member"


def test_environment_enum():
    assert Environment.dev == "dev"
    assert Environment.stage == "stage"
    assert Environment.prod == "prod"


def test_node_type_enum():
    assert NodeType.job == "job"
    assert NodeType.embed == "embed"
    assert NodeType.guru == "guru"
    assert NodeType.get_api == "get_api"
    assert NodeType.post_api == "post_api"
    assert NodeType.vector_query == "vector_query"
    assert NodeType.filter == "filter"
    assert NodeType.map == "map"
    assert NodeType.if_else == "if_else"
    assert NodeType.for_each == "for_each"
    assert NodeType.merge == "merge"
    assert NodeType.split == "split"
    assert NodeType.advanced == "advanced"
    assert NodeType.return_ == "return"
    assert NodeType.workflow == "workflow"


def test_timestamp_mixin():
    class TestModel(TimestampMixin, table=True):
        __tablename__ = "test_model"
        id: int = Field(default=None, primary_key=True)

    model = TestModel()
    assert isinstance(model.created_on, datetime)
    assert isinstance(model.updated_on, datetime)


def test_enum_round_trip():
    status = ExpertStatus.active
    assert status.value == "active"
    assert ExpertStatus(status.value) == ExpertStatus.active

    role = TeamRole.admin
    assert role.value == "admin"
    assert TeamRole(role.value) == TeamRole.admin
