from app.models.experts import Expert
from app.schemas.experts import ExpertListItem, ExpertRead


def to_list_item(
    expert: Expert, workflows_count: int, services_count: int
) -> ExpertListItem:
    """Convert Expert model to ExpertListItem DTO."""
    return ExpertListItem(
        id=expert.id,
        name=expert.name,
        prompt=expert.prompt,
        status=expert.status,
        model_name=expert.model_name,
        workflows_count=workflows_count,
        services_count=services_count,
        team_id=expert.team_id,
    )


def to_read(expert: Expert) -> ExpertRead:
    """Convert Expert model to ExpertRead DTO."""
    return ExpertRead(
        id=expert.id,
        uuid=expert.uuid,
        name=expert.name,
        prompt=expert.prompt,  # Full prompt for read operations
        input_params=expert.input_params or {},  # Handle None case
        status=expert.status,
        model_name=expert.model_name,
        team_id=expert.team_id,
    )
