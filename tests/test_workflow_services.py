import pytest
import uuid
import hashlib
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
from app.database import engine
from app.models.workflow_services import WorkflowService
from app.models.workflows import Workflow
from app.models.services import Service
from app.models.team import Team
from app.models.common import Environment


@pytest.fixture
def db_session():
    with Session(engine) as session:
        yield session


def test_create_workflow_service(db_session):
    # Create a team first
    team = Team(name=f"WS Team {uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()

    # Create a workflow
    workflow = Workflow(name="Test Workflow for Service", team_id=team.id)
    db_session.add(workflow)
    db_session.commit()

    # Create a service
    api_key = "sk-test123456789abcdef"
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    api_key_last4 = api_key[-4:]

    service = Service(
        name=f"Test Service {uuid.uuid4()}",
        environment=Environment.dev,
        api_key_hash=api_key_hash,
        api_key_last4=api_key_last4,
    )
    db_session.add(service)
    db_session.commit()

    # Create workflow service relationship
    workflow_service = WorkflowService(workflow_id=workflow.id, service_id=service.id)
    db_session.add(workflow_service)
    db_session.commit()

    assert workflow_service.id is not None
    assert workflow_service.workflow_id == workflow.id
    assert workflow_service.service_id == service.id
    assert workflow_service.created_on is not None
    assert workflow_service.updated_on is not None


def test_unique_workflow_service_constraint(db_session):
    # Create a team first
    team = Team(name=f"Unique WS Team {uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()

    # Create a workflow
    workflow = Workflow(name="Unique Test Workflow", team_id=team.id)
    db_session.add(workflow)
    db_session.commit()

    # Create a service
    api_key = "sk-unique123456789abc"
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    api_key_last4 = api_key[-4:]

    service = Service(
        name=f"Unique Test Service {uuid.uuid4()}",
        environment=Environment.prod,
        api_key_hash=api_key_hash,
        api_key_last4=api_key_last4,
    )
    db_session.add(service)
    db_session.commit()

    # Create first workflow service relationship
    workflow_service1 = WorkflowService(workflow_id=workflow.id, service_id=service.id)
    db_session.add(workflow_service1)
    db_session.commit()

    # Try to create duplicate relationship
    workflow_service2 = WorkflowService(workflow_id=workflow.id, service_id=service.id)
    db_session.add(workflow_service2)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_multiple_services_per_workflow(db_session):
    # Create a team first
    team = Team(name=f"Multi Service Team {uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()

    # Create a workflow
    workflow = Workflow(name="Multi Service Workflow", team_id=team.id)
    db_session.add(workflow)
    db_session.commit()

    # Create multiple services
    services = []
    for env in [Environment.dev, Environment.stage, Environment.prod]:
        api_key = f"sk-{env.value}123456789abc"
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        api_key_last4 = api_key[-4:]

        service = Service(
            name=f"Service {env.value} {uuid.uuid4()}",
            environment=env,
            api_key_hash=api_key_hash,
            api_key_last4=api_key_last4,
        )
        services.append(service)
        db_session.add(service)

    db_session.commit()

    # Create workflow service relationships for all services
    workflow_services = []
    for service in services:
        workflow_service = WorkflowService(
            workflow_id=workflow.id, service_id=service.id
        )
        workflow_services.append(workflow_service)
        db_session.add(workflow_service)

    db_session.commit()

    # Verify all relationships were created
    assert len(workflow_services) == 3
    for ws in workflow_services:
        assert ws.id is not None
        assert ws.workflow_id == workflow.id

    # Verify we can query them back
    retrieved_ws = db_session.exec(
        select(WorkflowService).where(WorkflowService.workflow_id == workflow.id)
    ).all()
    assert len(retrieved_ws) == 3


def test_multiple_workflows_per_service(db_session):
    # Create a team first
    team = Team(name=f"Multi Workflow Team {uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()

    # Create multiple workflows
    workflows = []
    for i in range(3):
        workflow = Workflow(name=f"Workflow {i+1}", team_id=team.id)
        workflows.append(workflow)
        db_session.add(workflow)

    db_session.commit()

    # Create a service
    api_key = "sk-multi123456789abc"
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    api_key_last4 = api_key[-4:]

    service = Service(
        name=f"Multi Workflow Service {uuid.uuid4()}",
        environment=Environment.stage,
        api_key_hash=api_key_hash,
        api_key_last4=api_key_last4,
    )
    db_session.add(service)
    db_session.commit()

    # Create workflow service relationships for all workflows
    workflow_services = []
    for workflow in workflows:
        workflow_service = WorkflowService(
            workflow_id=workflow.id, service_id=service.id
        )
        workflow_services.append(workflow_service)
        db_session.add(workflow_service)

    db_session.commit()

    # Verify all relationships were created
    assert len(workflow_services) == 3
    for ws in workflow_services:
        assert ws.id is not None
        assert ws.service_id == service.id

    # Verify we can query them back
    retrieved_ws = db_session.exec(
        select(WorkflowService).where(WorkflowService.service_id == service.id)
    ).all()
    assert len(retrieved_ws) == 3


def test_foreign_key_integrity(db_session):
    # Create a team first
    team = Team(name=f"FK WS Team {uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()

    # Create a workflow
    workflow = Workflow(name="FK Test Workflow", team_id=team.id)
    db_session.add(workflow)
    db_session.commit()

    # Create a service
    api_key = "sk-fk123456789abcdef"
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    api_key_last4 = api_key[-4:]

    service = Service(
        name=f"FK Test Service {uuid.uuid4()}",
        environment=Environment.dev,
        api_key_hash=api_key_hash,
        api_key_last4=api_key_last4,
    )
    db_session.add(service)
    db_session.commit()

    # Create workflow service relationship
    workflow_service = WorkflowService(workflow_id=workflow.id, service_id=service.id)
    db_session.add(workflow_service)
    db_session.commit()

    # Verify foreign key relationships
    assert workflow_service.workflow_id == workflow.id
    assert workflow_service.service_id == service.id

    # Test that we can retrieve related objects (would fail if FK is broken)
    retrieved_workflow = db_session.get(Workflow, workflow_service.workflow_id)
    retrieved_service = db_session.get(Service, workflow_service.service_id)

    assert retrieved_workflow is not None
    assert retrieved_service is not None
    assert retrieved_workflow.id == workflow.id
    assert retrieved_service.id == service.id


def test_workflow_service_visibility_mapping(db_session):
    """Test the core use case: mapping which workflows are visible to which services"""
    # Create a team
    team = Team(name=f"Visibility Team {uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()

    # Create workflows
    public_workflow = Workflow(name="Public Workflow", team_id=team.id)
    private_workflow = Workflow(name="Private Workflow", team_id=team.id)
    admin_workflow = Workflow(name="Admin Workflow", team_id=team.id)

    db_session.add(public_workflow)
    db_session.add(private_workflow)
    db_session.add(admin_workflow)
    db_session.commit()

    # Create services
    dev_service = Service(
        name=f"Dev Service {uuid.uuid4()}",
        environment=Environment.dev,
        api_key_hash=hashlib.sha256("dev-key".encode()).hexdigest(),
        api_key_last4="key"[-4:],
    )
    prod_service = Service(
        name=f"Prod Service {uuid.uuid4()}",
        environment=Environment.prod,
        api_key_hash=hashlib.sha256("prod-key".encode()).hexdigest(),
        api_key_last4="key"[-4:],
    )
    admin_service = Service(
        name=f"Admin Service {uuid.uuid4()}",
        environment=Environment.stage,
        api_key_hash=hashlib.sha256("admin-key".encode()).hexdigest(),
        api_key_last4="key"[-4:],
    )

    db_session.add(dev_service)
    db_session.add(prod_service)
    db_session.add(admin_service)
    db_session.commit()

    # Create visibility mappings
    mappings = [
        # Public workflow visible to dev and prod
        WorkflowService(workflow_id=public_workflow.id, service_id=dev_service.id),
        WorkflowService(workflow_id=public_workflow.id, service_id=prod_service.id),
        # Private workflow only visible to dev
        WorkflowService(workflow_id=private_workflow.id, service_id=dev_service.id),
        # Admin workflow only visible to admin service
        WorkflowService(workflow_id=admin_workflow.id, service_id=admin_service.id),
    ]

    for mapping in mappings:
        db_session.add(mapping)
    db_session.commit()

    # Test: Get workflows visible to dev service
    dev_workflows = db_session.exec(
        select(WorkflowService).where(WorkflowService.service_id == dev_service.id)
    ).all()
    dev_workflow_ids = [ws.workflow_id for ws in dev_workflows]
    assert public_workflow.id in dev_workflow_ids
    assert private_workflow.id in dev_workflow_ids
    assert admin_workflow.id not in dev_workflow_ids

    # Test: Get workflows visible to prod service
    prod_workflows = db_session.exec(
        select(WorkflowService).where(WorkflowService.service_id == prod_service.id)
    ).all()
    prod_workflow_ids = [ws.workflow_id for ws in prod_workflows]
    assert public_workflow.id in prod_workflow_ids
    assert private_workflow.id not in prod_workflow_ids
    assert admin_workflow.id not in prod_workflow_ids

    # Test: Get workflows visible to admin service
    admin_workflows = db_session.exec(
        select(WorkflowService).where(WorkflowService.service_id == admin_service.id)
    ).all()
    admin_workflow_ids = [ws.workflow_id for ws in admin_workflows]
    assert public_workflow.id not in admin_workflow_ids
    assert private_workflow.id not in admin_workflow_ids
    assert admin_workflow.id in admin_workflow_ids
