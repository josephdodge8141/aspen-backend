import pytest
import uuid
from sqlmodel import Session

from app.repos.experts_repo import ExpertsRepo
from app.models.team import Team, Member
from app.models.experts import Expert, ExpertWorkflow, ExpertService
from app.models.workflows import Workflow
from app.models.services import Service
from app.models.common import ExpertStatus, Environment, NodeType
from app.schemas.experts import ExpertListItem


@pytest.fixture
def experts_repo():
    return ExpertsRepo()


@pytest.fixture
def seed_data(db_session: Session):
    """Create seed data for testing"""
    # Create teams
    team1 = Team(name=f"Team 1 {uuid.uuid4()}")
    team2 = Team(name=f"Team 2 {uuid.uuid4()}")
    db_session.add(team1)
    db_session.add(team2)
    db_session.commit()
    db_session.refresh(team1)
    db_session.refresh(team2)

    # Create workflows
    workflow1 = Workflow(
        name=f"Workflow 1 {uuid.uuid4()}",
        description="Test workflow 1",
        team_id=team1.id,
    )
    workflow2 = Workflow(
        name=f"Workflow 2 {uuid.uuid4()}",
        description="Test workflow 2",
        team_id=team1.id,
    )
    db_session.add(workflow1)
    db_session.add(workflow2)
    db_session.commit()
    db_session.refresh(workflow1)
    db_session.refresh(workflow2)

    # Create services
    service1 = Service(
        name=f"Service 1 {uuid.uuid4()}",
        environment=Environment.dev,
        api_key_hash="hash1",
        api_key_last4="abc1",
    )
    service2 = Service(
        name=f"Service 2 {uuid.uuid4()}",
        environment=Environment.prod,
        api_key_hash="hash2",
        api_key_last4="abc2",
    )
    db_session.add(service1)
    db_session.add(service2)
    db_session.commit()
    db_session.refresh(service1)
    db_session.refresh(service2)

    # Create experts with different statuses
    expert1 = Expert(
        prompt="You are a helpful assistant for team 1. This is a very long prompt that should be truncated when displayed in list view because it exceeds the 120 character limit that we have set for the prompt truncation feature.",
        name=f"Expert 1 {uuid.uuid4()}",
        model_name="gpt-4",
        status=ExpertStatus.active,
        input_params={"temperature": 0.7},
        team_id=team1.id,
    )
    expert2 = Expert(
        prompt="Short prompt",
        name=f"Expert 2 {uuid.uuid4()}",
        model_name="gpt-3.5-turbo",
        status=ExpertStatus.draft,
        input_params={"temperature": 0.5},
        team_id=team1.id,
    )
    expert3 = Expert(
        prompt="Another assistant",
        name=f"Expert 3 {uuid.uuid4()}",
        model_name="gpt-4",
        status=ExpertStatus.active,
        input_params={"temperature": 0.8},
        team_id=team2.id,
    )
    expert4 = Expert(
        prompt="Archived expert",
        name=f"Expert 4 {uuid.uuid4()}",
        model_name="gpt-4",
        status=ExpertStatus.archive,
        input_params={"temperature": 0.9},
        team_id=team1.id,
    )

    db_session.add(expert1)
    db_session.add(expert2)
    db_session.add(expert3)
    db_session.add(expert4)
    db_session.commit()
    db_session.refresh(expert1)
    db_session.refresh(expert2)
    db_session.refresh(expert3)
    db_session.refresh(expert4)

    # Create expert-workflow links
    ew1 = ExpertWorkflow(expert_id=expert1.id, workflow_id=workflow1.id)
    ew2 = ExpertWorkflow(expert_id=expert1.id, workflow_id=workflow2.id)
    ew3 = ExpertWorkflow(expert_id=expert2.id, workflow_id=workflow1.id)
    db_session.add(ew1)
    db_session.add(ew2)
    db_session.add(ew3)
    db_session.commit()

    # Create expert-service links
    es1 = ExpertService(expert_id=expert1.id, service_id=service1.id)
    es2 = ExpertService(expert_id=expert2.id, service_id=service1.id)
    es3 = ExpertService(expert_id=expert2.id, service_id=service2.id)
    db_session.add(es1)
    db_session.add(es2)
    db_session.add(es3)
    db_session.commit()

    return {
        "teams": [team1, team2],
        "workflows": [workflow1, workflow2],
        "services": [service1, service2],
        "experts": [expert1, expert2, expert3, expert4],
    }


def test_list_with_counts_no_filters(
    db_session: Session, experts_repo: ExpertsRepo, seed_data
):
    """Test list_with_counts returns all experts with correct counts"""
    results = experts_repo.list_with_counts(db_session)

    # Should include at least our 4 seed experts (may include more from other tests)
    assert len(results) >= 4

    # Find specific experts and check counts
    expert1_result = next(
        (r for r in results if r.name == seed_data["experts"][0].name), None
    )
    expert2_result = next(
        (r for r in results if r.name == seed_data["experts"][1].name), None
    )
    expert3_result = next(
        (r for r in results if r.name == seed_data["experts"][2].name), None
    )
    expert4_result = next(
        (r for r in results if r.name == seed_data["experts"][3].name), None
    )

    # All our seed experts should be found
    assert expert1_result is not None
    assert expert2_result is not None
    assert expert3_result is not None
    assert expert4_result is not None

    # Check expert1 counts (2 workflows, 1 service)
    assert expert1_result.workflows_count == 2
    assert expert1_result.services_count == 1

    # Check expert2 counts (1 workflow, 2 services)
    assert expert2_result.workflows_count == 1
    assert expert2_result.services_count == 2

    # Check expert3 counts (0 workflows, 0 services)
    assert expert3_result.workflows_count == 0
    assert expert3_result.services_count == 0

    # Check expert4 counts (0 workflows, 0 services)
    assert expert4_result.workflows_count == 0
    assert expert4_result.services_count == 0


def test_list_with_counts_team_filter(
    db_session: Session, experts_repo: ExpertsRepo, seed_data
):
    """Test filtering by team_id"""
    team1_id = seed_data["teams"][0].id
    team2_id = seed_data["teams"][1].id

    # Filter by team1 - should include expert1, expert2, expert4
    results = experts_repo.list_with_counts(db_session, team_id=team1_id)
    team1_names = {r.name for r in results}
    assert seed_data["experts"][0].name in team1_names  # expert1
    assert seed_data["experts"][1].name in team1_names  # expert2
    assert seed_data["experts"][3].name in team1_names  # expert4

    # Filter by team2 - should include expert3
    results = experts_repo.list_with_counts(db_session, team_id=team2_id)
    team2_names = {r.name for r in results}
    assert seed_data["experts"][2].name in team2_names  # expert3


def test_list_with_counts_status_filter(
    db_session: Session, experts_repo: ExpertsRepo, seed_data
):
    """Test filtering by status"""
    # Filter by active status - should include at least expert1 and expert3
    results = experts_repo.list_with_counts(db_session, status=[ExpertStatus.active])
    active_names = {r.name for r in results}
    assert seed_data["experts"][0].name in active_names  # expert1
    assert seed_data["experts"][2].name in active_names  # expert3

    # Filter by draft status - should include at least expert2
    results = experts_repo.list_with_counts(db_session, status=[ExpertStatus.draft])
    draft_names = {r.name for r in results}
    assert seed_data["experts"][1].name in draft_names  # expert2

    # Filter by multiple statuses - should include expert1, expert2, expert3
    results = experts_repo.list_with_counts(
        db_session, status=[ExpertStatus.active, ExpertStatus.draft]
    )
    multi_names = {r.name for r in results}
    assert seed_data["experts"][0].name in multi_names  # expert1
    assert seed_data["experts"][1].name in multi_names  # expert2
    assert seed_data["experts"][2].name in multi_names  # expert3


def test_list_with_counts_combined_filters(
    db_session: Session, experts_repo: ExpertsRepo, seed_data
):
    """Test combining team_id and status filters"""
    team1_id = seed_data["teams"][0].id

    results = experts_repo.list_with_counts(
        db_session, team_id=team1_id, status=[ExpertStatus.active]
    )
    # Should include expert1 (team1 + active)
    combined_names = {r.name for r in results}
    assert seed_data["experts"][0].name in combined_names  # expert1


def test_list_with_counts_returns_expert_list_items(
    db_session: Session, experts_repo: ExpertsRepo, seed_data
):
    """Test that results are ExpertListItem instances with correct fields"""
    results = experts_repo.list_with_counts(db_session)

    for result in results:
        assert isinstance(result, ExpertListItem)
        assert hasattr(result, "id")
        assert hasattr(result, "name")
        assert hasattr(result, "model_name")
        assert hasattr(result, "status")
        assert hasattr(result, "prompt")
        assert hasattr(result, "workflows_count")
        assert hasattr(result, "services_count")
        assert hasattr(result, "team_id")


def test_get_with_expanded_existing_expert(
    db_session: Session, experts_repo: ExpertsRepo, seed_data
):
    """Test get_with_expanded returns expert with related data"""
    expert1 = seed_data["experts"][0]

    result = experts_repo.get_with_expanded(db_session, expert1.id)

    assert result is not None
    assert "expert" in result
    assert "workflows" in result
    assert "services" in result

    # Check expert data
    expert_data = result["expert"]
    assert expert_data["id"] == expert1.id
    assert expert_data["uuid"] == expert1.uuid
    assert expert_data["name"] == expert1.name
    assert expert_data["prompt"] == expert1.prompt
    assert expert_data["model_name"] == expert1.model_name
    assert expert_data["status"] == expert1.status
    assert expert_data["input_params"] == expert1.input_params
    assert expert_data["team_id"] == expert1.team_id

    # Check workflows (expert1 linked to 2 workflows)
    workflows = result["workflows"]
    assert len(workflows) == 2
    workflow_names = {wf["name"] for wf in workflows}
    expected_names = {seed_data["workflows"][0].name, seed_data["workflows"][1].name}
    assert workflow_names == expected_names

    # Check services (expert1 linked to 1 service)
    services = result["services"]
    assert len(services) == 1
    assert services[0]["name"] == seed_data["services"][0].name
    assert services[0]["environment"] == "dev"


def test_get_with_expanded_expert_with_no_links(
    db_session: Session, experts_repo: ExpertsRepo, seed_data
):
    """Test get_with_expanded for expert with no workflow/service links"""
    expert3 = seed_data["experts"][2]  # Has no links

    result = experts_repo.get_with_expanded(db_session, expert3.id)

    assert result is not None
    assert result["expert"]["id"] == expert3.id
    assert result["workflows"] == []
    assert result["services"] == []


def test_get_with_expanded_nonexistent_expert(
    db_session: Session, experts_repo: ExpertsRepo
):
    """Test get_with_expanded returns None for nonexistent expert"""
    result = experts_repo.get_with_expanded(db_session, 99999)
    assert result is None


def test_get_with_expanded_workflow_and_service_structure(
    db_session: Session, experts_repo: ExpertsRepo, seed_data
):
    """Test that workflows and services have correct structure"""
    expert2 = seed_data["experts"][1]  # Has 1 workflow, 2 services

    result = experts_repo.get_with_expanded(db_session, expert2.id)

    # Check workflow structure
    workflows = result["workflows"]
    assert len(workflows) == 1
    workflow = workflows[0]
    assert "id" in workflow
    assert "name" in workflow
    assert isinstance(workflow["id"], int)
    assert isinstance(workflow["name"], str)

    # Check services structure
    services = result["services"]
    assert len(services) == 2
    for service in services:
        assert "id" in service
        assert "name" in service
        assert "environment" in service
        assert isinstance(service["id"], int)
        assert isinstance(service["name"], str)
        assert service["environment"] in ["dev", "stage", "prod"]
