import pytest
import uuid
import hashlib
import json
from sqlmodel import Session
from app.database import engine
from app.repos import ExpertsRepo, WorkflowsRepo, ServicesRepo, UsersRepo, TeamsRepo
from app.models.experts import Expert
from app.models.workflows import Workflow, Node
from app.models.services import Service
from app.models.users import User, ServiceUser
from app.models.team import Team, Member
from app.models.common import ExpertStatus, Environment, NodeType, TeamRole


@pytest.fixture
def db_session():
    with Session(engine) as session:
        yield session


def hash_segment_key(segment_key: dict) -> bytes:
    """Create a canonical hash for segment key"""
    canonical = json.dumps(segment_key, sort_keys=True)
    return hashlib.sha256(canonical.encode()).digest()


def test_experts_repo_round_trip(db_session):
    experts_repo = ExpertsRepo()
    teams_repo = TeamsRepo()
    
    # Create a team first
    team = Team(name=f"Expert Test Team {uuid.uuid4()}")
    created_team = teams_repo.create(db_session, team)
    
    # Test expert creation and retrieval
    expert = Expert(
        prompt="You are a helpful assistant",
        name="Test Expert",
        model_name="gpt-4",
        status=ExpertStatus.active,
        input_params={"temperature": 0.7},
        team_id=created_team.id
    )
    
    created_expert = experts_repo.create(db_session, expert)
    assert created_expert.id is not None
    assert created_expert.uuid is not None
    
    # Test retrieval by ID
    retrieved_expert = experts_repo.get(db_session, created_expert.id)
    assert retrieved_expert is not None
    assert retrieved_expert.name == "Test Expert"
    assert retrieved_expert.status == ExpertStatus.active
    
    # Test retrieval by UUID
    retrieved_by_uuid = experts_repo.get_by_uuid(db_session, created_expert.uuid)
    assert retrieved_by_uuid is not None
    assert retrieved_by_uuid.id == created_expert.id
    
    # Test list with filters
    experts_list = experts_repo.list(db_session, team_id=created_team.id)
    assert len(experts_list) >= 1
    assert any(e.id == created_expert.id for e in experts_list)


def test_workflows_repo_round_trip(db_session):
    workflows_repo = WorkflowsRepo()
    teams_repo = TeamsRepo()
    
    # Create a team first
    team = Team(name=f"Workflow Test Team {uuid.uuid4()}")
    created_team = teams_repo.create(db_session, team)
    
    # Test workflow creation and retrieval
    workflow = Workflow(
        name="Test Workflow",
        description="A test workflow",
        input_params={"param1": "value1"},
        is_api=True,
        team_id=created_team.id
    )
    
    created_workflow = workflows_repo.create(db_session, workflow)
    assert created_workflow.id is not None
    assert created_workflow.uuid is not None
    
    # Test retrieval by ID
    retrieved_workflow = workflows_repo.get(db_session, created_workflow.id)
    assert retrieved_workflow is not None
    assert retrieved_workflow.name == "Test Workflow"
    assert retrieved_workflow.is_api is True
    
    # Test node creation
    node = Node(
        workflow_id=created_workflow.id,
        node_type=NodeType.job,
        node_metadata={"config": "test"}
    )
    
    created_node = workflows_repo.create_node(db_session, node)
    assert created_node.id is not None
    assert created_node.workflow_id == created_workflow.id
    
    # Test list nodes
    nodes = workflows_repo.list_nodes(db_session, created_workflow.id)
    assert len(nodes) >= 1
    assert any(n.id == created_node.id for n in nodes)


def test_services_repo_round_trip(db_session):
    services_repo = ServicesRepo()
    
    # Test service creation and retrieval
    api_key = "sk-test123456789abcdef"
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    api_key_last4 = api_key[-4:]
    
    service = Service(
        name=f"Test Service {uuid.uuid4()}",
        environment=Environment.dev,
        api_key_hash=api_key_hash,
        api_key_last4=api_key_last4
    )
    
    created_service = services_repo.create(db_session, service)
    assert created_service.id is not None
    
    # Test retrieval by ID
    retrieved_service = services_repo.get(db_session, created_service.id)
    assert retrieved_service is not None
    assert retrieved_service.environment == Environment.dev
    
    # Test retrieval by name and environment
    retrieved_by_name = services_repo.get_by_name_and_env(
        db_session, created_service.name, Environment.dev
    )
    assert retrieved_by_name is not None
    assert retrieved_by_name.id == created_service.id
    
    # Test list with environment filter
    services_list = services_repo.list(db_session, environment=Environment.dev)
    assert len(services_list) >= 1
    assert any(s.id == created_service.id for s in services_list)


def test_users_repo_round_trip(db_session):
    users_repo = UsersRepo()
    teams_repo = TeamsRepo()
    services_repo = ServicesRepo()
    
    # Create a member and service first
    member = Member(
        first_name="Test",
        last_name="User",
        email=f"test.user.{uuid.uuid4()}@example.com"
    )
    created_member = teams_repo.create_member(db_session, member)
    
    # Test internal user creation
    internal_user = User(
        member_id=created_member.id,
        password_hash="hashed_password_123",
        service_user_id=None
    )
    
    created_user = users_repo.create(db_session, internal_user)
    assert created_user.id is not None
    
    # Test retrieval by ID
    retrieved_user = users_repo.get(db_session, created_user.id)
    assert retrieved_user is not None
    assert retrieved_user.member_id == created_member.id
    
    # Test retrieval by member ID
    retrieved_by_member = users_repo.get_by_member_id(db_session, created_member.id)
    assert retrieved_by_member is not None
    assert retrieved_by_member.id == created_user.id
    
    # Test service user creation
    api_key = "sk-test123456789abcdef"
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    api_key_last4 = api_key[-4:]
    
    service = Service(
        name=f"User Test Service {uuid.uuid4()}",
        environment=Environment.dev,
        api_key_hash=api_key_hash,
        api_key_last4=api_key_last4
    )
    created_service = services_repo.create(db_session, service)
    
    external_user = User(
        member_id=None,
        password_hash=None,
        service_user_id=None
    )
    created_external_user = users_repo.create(db_session, external_user)
    
    segment_key = {
        "version": 1,
        "properties": {
            "user_id": f"test_user_{uuid.uuid4()}",
            "client_id": "test_client"
        }
    }
    segment_hash = hash_segment_key(segment_key)
    
    service_user = ServiceUser(
        user_id=created_external_user.id,
        segment_key=segment_key,
        segment_hash=segment_hash,
        service_id=created_service.id,
        version=1
    )
    
    created_service_user = users_repo.create_service_user(db_session, service_user)
    assert created_service_user.id is not None
    
    # Test service user retrieval by hash
    retrieved_by_hash = users_repo.get_service_user_by_hash(db_session, segment_hash)
    assert retrieved_by_hash is not None
    assert retrieved_by_hash.id == created_service_user.id


def test_teams_repo_round_trip(db_session):
    teams_repo = TeamsRepo()
    
    # Test team creation and retrieval
    team = Team(name=f"Test Team {uuid.uuid4()}")
    created_team = teams_repo.create(db_session, team)
    assert created_team.id is not None
    
    # Test retrieval by ID
    retrieved_team = teams_repo.get(db_session, created_team.id)
    assert retrieved_team is not None
    assert retrieved_team.name == team.name
    
    # Test member creation
    member = Member(
        first_name="John",
        last_name="Doe", 
        email=f"john.doe.{uuid.uuid4()}@example.com"
    )
    created_member = teams_repo.create_member(db_session, member)
    assert created_member.id is not None
    
    # Test retrieval by email
    retrieved_by_email = teams_repo.get_member_by_email(db_session, member.email)
    assert retrieved_by_email is not None
    assert retrieved_by_email.id == created_member.id
    
    # Test adding member to team
    team_member = teams_repo.add_member_to_team(
        db_session, created_team.id, created_member.id, TeamRole.admin
    )
    assert team_member.id is not None
    assert team_member.role == TeamRole.admin
    
    # Test getting team members
    team_members = teams_repo.get_team_members(db_session, created_team.id)
    assert len(team_members) >= 1
    assert any(tm.member_id == created_member.id for tm in team_members)
    
    # Test getting member teams
    member_teams = teams_repo.get_member_teams(db_session, created_member.id)
    assert len(member_teams) >= 1
    assert any(mt.team_id == created_team.id for mt in member_teams) 