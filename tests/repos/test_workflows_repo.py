import pytest
from sqlmodel import Session
import uuid

from app.models.workflows import Workflow, Node, NodeNode
from app.models.experts import Expert, ExpertWorkflow, ExpertService
from app.models.services import Service
from app.models.team import Team, Member, TeamMember
from app.models.users import User
from app.models.common import TeamRole, ExpertStatus, Environment, NodeType
from app.repos.workflows_repo import (
    list_with_counts,
    get_expanded,
    truncate_description,
)


class TestTruncateDescription:
    def test_truncate_none(self):
        """Test truncation with None description."""
        result = truncate_description(None)
        assert result is None

    def test_truncate_empty_string(self):
        """Test truncation with empty string."""
        result = truncate_description("")
        assert result == ""

    def test_truncate_short_description(self):
        """Test truncation with description shorter than max length."""
        desc = "Short description"
        result = truncate_description(desc)
        assert result == desc

    def test_truncate_exact_length(self):
        """Test truncation with description exactly at max length."""
        desc = "A" * 120
        result = truncate_description(desc)
        assert result == desc
        assert len(result) == 120

    def test_truncate_long_description(self):
        """Test truncation with description longer than max length."""
        desc = "A" * 150
        result = truncate_description(desc)
        assert result == "A" * 120 + "..."
        assert len(result) == 123

    def test_truncate_custom_length(self):
        """Test truncation with custom max length."""
        desc = "This is a longer description"
        result = truncate_description(desc, max_length=10)
        assert result == "This is a ..."
        assert len(result) == 13


class TestListWithCounts:
    @pytest.fixture
    def test_data(self, db_session: Session):
        """Create test data with teams, workflows, experts, and services."""
        # Create team
        test_uuid = str(uuid.uuid4())[:8]
        team = Team(name=f"Test Team {test_uuid}")
        db_session.add(team)
        db_session.commit()
        db_session.refresh(team)

        # Create member and user
        member = Member(
            email=f"user{test_uuid}@test.com", first_name="Test", last_name="User"
        )
        db_session.add(member)
        db_session.commit()
        db_session.refresh(member)

        user = User(member_id=member.id)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Create team membership
        team_member = TeamMember(
            team_id=team.id, member_id=member.id, role=TeamRole.admin
        )
        db_session.add(team_member)

        # Create workflows
        workflow1 = Workflow(
            name="Alpha Workflow",
            description="A" * 150,  # Long description for truncation test
            team_id=team.id,
            is_api=True,
            input_params={"param1": "value1"},
        )
        workflow2 = Workflow(
            name="Beta Workflow",
            description="Short description",
            team_id=team.id,
            is_api=False,
            input_params={},
        )
        workflow3 = Workflow(
            name="Gamma Workflow",
            description=None,
            team_id=team.id,
            is_api=True,
            input_params={},
        )
        db_session.add_all([workflow1, workflow2, workflow3])
        db_session.commit()
        db_session.refresh(workflow1)
        db_session.refresh(workflow2)
        db_session.refresh(workflow3)

        # Create experts
        experts = []
        for i in range(7):  # More than 5 to test limit
            expert = Expert(
                name=f"Expert {i+1}",
                prompt=f"Prompt for expert {i+1}",
                model_name="gpt-4",
                team_id=team.id,
                status=ExpertStatus.active,
                input_params={},
            )
            experts.append(expert)
            db_session.add(expert)

        db_session.commit()
        for expert in experts:
            db_session.refresh(expert)

        # Create services
        services = []
        for env in [Environment.dev, Environment.prod]:
            service = Service(
                name=f"Service {env.value} {test_uuid}",
                environment=env,
                api_key_hash=f"hash_{env.value}_{test_uuid}",
                api_key_last4="1234",
            )
            services.append(service)
            db_session.add(service)

        db_session.commit()
        for service in services:
            db_session.refresh(service)

        # Link experts to workflow1 (first 5 experts)
        for i in range(5):
            expert_workflow = ExpertWorkflow(
                expert_id=experts[i].id, workflow_id=workflow1.id
            )
            db_session.add(expert_workflow)

        # Link experts to workflow2 (2 experts)
        for i in range(2):
            expert_workflow = ExpertWorkflow(
                expert_id=experts[i].id, workflow_id=workflow2.id
            )
            db_session.add(expert_workflow)

        # Link services to experts (which links them to workflows)
        for i in range(3):  # First 3 experts get services
            for service in services:
                expert_service = ExpertService(
                    expert_id=experts[i].id, service_id=service.id
                )
                db_session.add(expert_service)

        db_session.commit()

        return {
            "team": team,
            "workflows": [workflow1, workflow2, workflow3],
            "experts": experts,
            "services": services,
        }

    def test_list_no_filters(self, db_session: Session, test_data):
        """Test listing all workflows without filters."""
        result = list_with_counts(db_session)

        assert len(result) >= 3  # At least our test workflows

        # Find our test workflows (sorted by name)
        alpha_workflow = next(w for w in result if w.name == "Alpha Workflow")
        beta_workflow = next(w for w in result if w.name == "Beta Workflow")
        gamma_workflow = next(w for w in result if w.name == "Gamma Workflow")

        # Check Alpha Workflow (5 experts, 2 services through 3 experts)
        assert alpha_workflow.experts_count == 5
        assert alpha_workflow.services_count == 2
        assert len(alpha_workflow.experts) == 5  # First 5 experts
        assert alpha_workflow.description_truncated == "A" * 120 + "..."

        # Check Beta Workflow (2 experts, 2 services through 2 experts)
        assert beta_workflow.experts_count == 2
        assert beta_workflow.services_count == 2
        assert len(beta_workflow.experts) == 2
        assert beta_workflow.description_truncated == "Short description"

        # Check Gamma Workflow (0 experts, 0 services)
        assert gamma_workflow.experts_count == 0
        assert gamma_workflow.services_count == 0
        assert len(gamma_workflow.experts) == 0
        assert gamma_workflow.description_truncated is None

    def test_list_with_team_filter(self, db_session: Session, test_data):
        """Test listing workflows filtered by team."""
        result = list_with_counts(db_session, team_id=test_data["team"].id)

        # Should return exactly our 3 test workflows
        workflow_names = [w.name for w in result]
        assert "Alpha Workflow" in workflow_names
        assert "Beta Workflow" in workflow_names
        assert "Gamma Workflow" in workflow_names

    def test_list_ordering_stable(self, db_session: Session, test_data):
        """Test that list ordering is stable (by name)."""
        result1 = list_with_counts(db_session, team_id=test_data["team"].id)
        result2 = list_with_counts(db_session, team_id=test_data["team"].id)

        # Should return workflows in same order (alphabetical by name)
        names1 = [w.name for w in result1]
        names2 = [w.name for w in result2]
        assert names1 == names2

        # Check alphabetical ordering for our test workflows
        test_workflow_names = [w.name for w in result1 if w.name.endswith(" Workflow")]
        assert test_workflow_names == [
            "Alpha Workflow",
            "Beta Workflow",
            "Gamma Workflow",
        ]

    def test_experts_limit_five(self, db_session: Session, test_data):
        """Test that experts list is limited to first 5."""
        result = list_with_counts(db_session, team_id=test_data["team"].id)
        alpha_workflow = next(w for w in result if w.name == "Alpha Workflow")

        # Should have exactly 5 experts in the list
        assert len(alpha_workflow.experts) == 5
        assert alpha_workflow.experts_count == 5

        # Check expert structure
        for expert in alpha_workflow.experts:
            assert "id" in expert
            assert "name" in expert
            assert isinstance(expert["id"], int)
            assert isinstance(expert["name"], str)


class TestGetExpanded:
    @pytest.fixture
    def test_workflow_data(self, db_session: Session):
        """Create test workflow with nodes and edges."""
        # Create team
        test_uuid = str(uuid.uuid4())[:8]
        team = Team(name=f"Test Team {test_uuid}")
        db_session.add(team)
        db_session.commit()
        db_session.refresh(team)

        # Create workflow
        workflow = Workflow(
            name="Test Workflow",
            description="Test workflow description",
            team_id=team.id,
            is_api=True,
            input_params={"input1": "test"},
            cron_schedule="0 0 * * *",
        )
        db_session.add(workflow)
        db_session.commit()
        db_session.refresh(workflow)

        # Create nodes
        node1 = Node(
            workflow_id=workflow.id,
            node_type=NodeType.job,
            node_metadata={"name": "Input Node", "config": {}},
            structured_output={
                "type": "object",
                "properties": {"result": {"type": "string"}},
            },
        )
        node2 = Node(
            workflow_id=workflow.id,
            node_type=NodeType.guru,
            node_metadata={"name": "Process Node", "expert_id": 1},
            structured_output={
                "type": "object",
                "properties": {"output": {"type": "string"}},
            },
        )
        node3 = Node(
            workflow_id=workflow.id,
            node_type=NodeType.return_,
            node_metadata={"name": "Output Node"},
            structured_output={
                "type": "object",
                "properties": {"final": {"type": "string"}},
            },
        )
        db_session.add_all([node1, node2, node3])
        db_session.commit()
        db_session.refresh(node1)
        db_session.refresh(node2)
        db_session.refresh(node3)

        # Create edges
        edge1 = NodeNode(parent_id=node1.id, child_id=node2.id)
        edge2 = NodeNode(parent_id=node2.id, child_id=node3.id, branch_label="success")
        db_session.add_all([edge1, edge2])
        db_session.commit()
        db_session.refresh(edge1)
        db_session.refresh(edge2)

        # Create expert and link to workflow
        expert = Expert(
            name="Test Expert",
            prompt="Test prompt",
            model_name="gpt-4",
            team_id=team.id,
            status=ExpertStatus.active,
            input_params={},
        )
        db_session.add(expert)
        db_session.commit()
        db_session.refresh(expert)

        expert_workflow = ExpertWorkflow(expert_id=expert.id, workflow_id=workflow.id)
        db_session.add(expert_workflow)

        # Create service and link to expert
        service = Service(
            name=f"Test Service {test_uuid}",
            environment=Environment.prod,
            api_key_hash=f"test_hash_{test_uuid}",
            api_key_last4="1234",
        )
        db_session.add(service)
        db_session.commit()
        db_session.refresh(service)

        expert_service = ExpertService(expert_id=expert.id, service_id=service.id)
        db_session.add(expert_service)
        db_session.commit()

        return {
            "workflow": workflow,
            "nodes": [node1, node2, node3],
            "edges": [edge1, edge2],
            "expert": expert,
            "service": service,
        }

    def test_get_expanded_success(self, db_session: Session, test_workflow_data):
        """Test successful expanded workflow retrieval."""
        workflow_id = test_workflow_data["workflow"].id
        result = get_expanded(db_session, workflow_id)

        assert result is not None
        assert "workflow" in result
        assert "nodes" in result
        assert "edges" in result
        assert "experts" in result
        assert "services" in result

        # Check workflow data
        workflow_data = result["workflow"]
        assert workflow_data.id == workflow_id
        assert workflow_data.name == "Test Workflow"
        assert workflow_data.description == "Test workflow description"
        assert workflow_data.is_api is True
        assert workflow_data.input_params == {"input1": "test"}
        assert workflow_data.cron_schedule == "0 0 * * *"

        # Check nodes
        assert len(result["nodes"]) == 3
        node_types = [node.node_type for node in result["nodes"]]
        assert NodeType.job in node_types
        assert NodeType.guru in node_types
        assert NodeType.return_ in node_types

        # Check edges
        assert len(result["edges"]) == 2
        edge_with_label = next(
            edge for edge in result["edges"] if edge.branch_label is not None
        )
        assert edge_with_label.branch_label == "success"

        # Check experts
        assert len(result["experts"]) == 1
        assert result["experts"][0]["name"] == "Test Expert"

        # Check services
        assert len(result["services"]) == 1
        assert result["services"][0]["name"].startswith("Test Service")
        assert result["services"][0]["environment"] == "prod"

    def test_get_expanded_not_found(self, db_session: Session):
        """Test expanded retrieval for non-existent workflow."""
        result = get_expanded(db_session, 99999)
        assert result is None

    def test_get_expanded_empty_workflow(self, db_session: Session):
        """Test expanded retrieval for workflow with no nodes/edges/links."""
        # Create minimal workflow
        test_uuid = str(uuid.uuid4())[:8]
        team = Team(name=f"Empty Team {test_uuid}")
        db_session.add(team)
        db_session.commit()
        db_session.refresh(team)

        workflow = Workflow(
            name="Empty Workflow", team_id=team.id, is_api=False, input_params={}
        )
        db_session.add(workflow)
        db_session.commit()
        db_session.refresh(workflow)

        result = get_expanded(db_session, workflow.id)

        assert result is not None
        assert result["workflow"].name == "Empty Workflow"
        assert len(result["nodes"]) == 0
        assert len(result["edges"]) == 0
        assert len(result["experts"]) == 0
        assert len(result["services"]) == 0
