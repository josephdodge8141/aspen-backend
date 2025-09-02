import pytest
import uuid
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
from app.database import engine
from app.models.experts import Expert, ExpertService, ExpertWorkflow
from app.models.team import Team
from app.models.common import ExpertStatus


@pytest.fixture
def db_session():
    with Session(engine) as session:
        yield session


def unique_email():
    return f"test-{uuid.uuid4()}@example.com"


def test_create_expert(db_session):
    # Create a team first
    team = Team(name=f"Engineering-{uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()
    
    expert = Expert(
        prompt="You are a helpful AI assistant",
        name="Test Expert",
        model_name="gpt-4",
        status=ExpertStatus.draft,
        input_params={"temperature": 0.7, "max_tokens": 1000},
        team_id=team.id
    )
    db_session.add(expert)
    db_session.commit()
    
    assert expert.id is not None
    assert expert.uuid is not None
    assert expert.prompt == "You are a helpful AI assistant"
    assert expert.name == "Test Expert"
    assert expert.model_name == "gpt-4"
    assert expert.status == ExpertStatus.draft
    assert expert.input_params == {"temperature": 0.7, "max_tokens": 1000}
    assert expert.team_id == team.id


def test_expert_with_different_statuses(db_session):
    # Create a team first
    team = Team(name=f"Product-{uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()
    
    # Test all expert statuses
    statuses = [ExpertStatus.draft, ExpertStatus.active, ExpertStatus.archive, ExpertStatus.historical]
    
    for status in statuses:
        expert = Expert(
            prompt=f"Expert with {status.value} status",
            name=f"Expert {status.value}",
            model_name="gpt-3.5-turbo",
            status=status,
            team_id=team.id
        )
        db_session.add(expert)
    
    db_session.commit()
    
    # Verify all experts were created
    experts = db_session.exec(select(Expert).where(Expert.team_id == team.id)).all()
    assert len(experts) == 4
    
    created_statuses = [expert.status for expert in experts]
    for status in statuses:
        assert status in created_statuses


def test_expert_with_null_input_params(db_session):
    # Create a team first
    team = Team(name=f"Design-{uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()
    
    expert = Expert(
        prompt="Simple expert without input params",
        name="Simple Expert",
        model_name="claude-3",
        status=ExpertStatus.active,
        input_params=None,
        team_id=team.id
    )
    db_session.add(expert)
    db_session.commit()
    
    assert expert.id is not None
    assert expert.input_params is None


def test_expert_uuid_uniqueness(db_session):
    # Create a team first
    team = Team(name=f"Marketing-{uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()
    
    expert1 = Expert(
        prompt="First expert",
        name="Expert 1",
        model_name="gpt-4",
        status=ExpertStatus.active,
        team_id=team.id
    )
    db_session.add(expert1)
    db_session.commit()
    
    # Try to create another expert with the same UUID (this should be prevented by the unique constraint)
    expert2 = Expert(
        prompt="Second expert",
        name="Expert 2", 
        model_name="gpt-4",
        status=ExpertStatus.active,
        team_id=team.id
    )
    expert2.uuid = expert1.uuid  # Force same UUID
    
    db_session.add(expert2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_create_expert_service(db_session):
    # Create a team and expert first
    team = Team(name=f"Engineering-{uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()
    
    expert = Expert(
        prompt="Test expert for service",
        name="Service Expert",
        model_name="gpt-4",
        status=ExpertStatus.active,
        team_id=team.id
    )
    db_session.add(expert)
    db_session.commit()
    
    # Create expert service relationship
    expert_service = ExpertService(
        expert_id=expert.id,
        service_id=1  # Mock service ID since services table doesn't exist yet
    )
    db_session.add(expert_service)
    db_session.commit()
    
    assert expert_service.id is not None
    assert expert_service.expert_id == expert.id
    assert expert_service.service_id == 1


def test_unique_expert_service_constraint(db_session):
    # Create a team and expert first
    team = Team(name=f"Product-{uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()
    
    expert = Expert(
        prompt="Test expert for unique service constraint",
        name="Unique Service Expert",
        model_name="gpt-4",
        status=ExpertStatus.active,
        team_id=team.id
    )
    db_session.add(expert)
    db_session.commit()
    
    # Create first expert service relationship
    expert_service1 = ExpertService(
        expert_id=expert.id,
        service_id=2
    )
    db_session.add(expert_service1)
    db_session.commit()
    
    # Try to create duplicate relationship
    expert_service2 = ExpertService(
        expert_id=expert.id,
        service_id=2  # Same service ID
    )
    db_session.add(expert_service2)
    
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_create_expert_workflow(db_session):
    # Create a team and expert first
    team = Team(name=f"Design-{uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()
    
    expert = Expert(
        prompt="Test expert for workflow",
        name="Workflow Expert",
        model_name="claude-3",
        status=ExpertStatus.active,
        team_id=team.id
    )
    db_session.add(expert)
    db_session.commit()
    
    # Create expert workflow relationship
    expert_workflow = ExpertWorkflow(
        expert_id=expert.id,
        workflow_id=1  # Mock workflow ID since workflows table doesn't exist yet
    )
    db_session.add(expert_workflow)
    db_session.commit()
    
    assert expert_workflow.id is not None
    assert expert_workflow.expert_id == expert.id
    assert expert_workflow.workflow_id == 1


def test_unique_expert_workflow_constraint(db_session):
    # Create a team and expert first
    team = Team(name=f"Marketing-{uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()
    
    expert = Expert(
        prompt="Test expert for unique workflow constraint",
        name="Unique Workflow Expert",
        model_name="gpt-3.5-turbo",
        status=ExpertStatus.active,
        team_id=team.id
    )
    db_session.add(expert)
    db_session.commit()
    
    # Create first expert workflow relationship
    expert_workflow1 = ExpertWorkflow(
        expert_id=expert.id,
        workflow_id=3
    )
    db_session.add(expert_workflow1)
    db_session.commit()
    
    # Try to create duplicate relationship
    expert_workflow2 = ExpertWorkflow(
        expert_id=expert.id,
        workflow_id=3  # Same workflow ID
    )
    db_session.add(expert_workflow2)
    
    with pytest.raises(IntegrityError):
        db_session.commit() 