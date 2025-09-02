from datetime import datetime, timezone
from enum import Enum
from sqlmodel import SQLModel, Field
from sqlalchemy import event


class ExpertStatus(str, Enum):
    draft = "draft"
    active = "active"
    archive = "archive"
    historical = "historical"


class TeamRole(str, Enum):
    admin = "admin"
    member = "member"


class Environment(str, Enum):
    dev = "dev"
    stage = "stage"
    prod = "prod"


class NodeType(str, Enum):
    job = "job"
    embed = "embed"
    guru = "guru"
    get_api = "get_api"
    post_api = "post_api"
    vector_query = "vector_query"
    filter = "filter"
    map = "map"
    if_else = "if_else"
    for_each = "for_each"
    merge = "merge"
    split = "split"
    advanced = "advanced"
    return_ = "return"
    workflow = "workflow"


def utc_now():
    return datetime.now(timezone.utc)


class TimestampMixin(SQLModel):
    created_on: datetime = Field(default_factory=utc_now, nullable=False)
    updated_on: datetime = Field(default_factory=utc_now, nullable=False)


@event.listens_for(TimestampMixin, "before_update", propagate=True)
def update_timestamp(mapper, connection, target):
    target.updated_on = datetime.now(timezone.utc)
