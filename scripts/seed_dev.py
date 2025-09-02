#!/usr/bin/env python3
"""
Development database seeding script.
Creates sample data for local development and testing.
"""

import hashlib
import json
from sqlmodel import Session, select
from app.database import engine
from app.models.team import Team, Member, TeamMember
from app.models.experts import Expert, ExpertWorkflow, ExpertService
from app.models.workflows import Workflow, Node, NodeNode
from app.models.services import Service
from app.models.common import TeamRole, ExpertStatus, Environment, NodeType


def hash_api_key(api_key: str) -> str:
    """Hash an API key for secure storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def create_sample_data():
    """Create sample data for development"""
    with Session(engine) as session:
        print("🌱 Seeding development database...")

        # Check if demo data already exists
        existing_expert = session.exec(
            select(Expert).where(Expert.name == "Demo Assistant")
        ).first()
        
        if existing_expert:
            print("✅ Demo data already exists, skipping seed")
            print(f"   • Expert: {existing_expert.name} (uuid: {existing_expert.uuid})")
            return

        # Create team
        team = Team(name="Demo Team")
        session.add(team)
        session.commit()
        session.refresh(team)
        print(f"✅ Created team: {team.name} (id: {team.id})")

        # Create members
        admin_member = Member(
            first_name="Alice", last_name="Admin", email="alice.admin@example.com"
        )
        regular_member = Member(
            first_name="Bob", last_name="Developer", email="bob.developer@example.com"
        )
        session.add(admin_member)
        session.add(regular_member)
        session.commit()
        session.refresh(admin_member)
        session.refresh(regular_member)
        print(f"✅ Created members: {admin_member.email}, {regular_member.email}")

        # Add members to team
        admin_team_member = TeamMember(
            team_id=team.id, member_id=admin_member.id, role=TeamRole.admin
        )
        regular_team_member = TeamMember(
            team_id=team.id, member_id=regular_member.id, role=TeamRole.member
        )
        session.add(admin_team_member)
        session.add(regular_team_member)
        session.commit()
        print(f"✅ Added members to team with roles: admin, member")

        # Create services for each environment
        services = []
        for env in Environment:
            api_key = f"sk-demo-{env.value}-12345678901234567890"
            service = Service(
                name=f"Demo Service {env.value.title()}",
                environment=env,
                api_key_hash=hash_api_key(api_key),
                api_key_last4=api_key[-4:],
            )
            services.append(service)
            session.add(service)

        session.commit()
        for service in services:
            session.refresh(service)
        print(
            f"✅ Created {len(services)} services for environments: {', '.join([s.environment.value for s in services])}"
        )

        # Create expert
        expert = Expert(
            prompt="You are a helpful AI assistant for property management. You can help with tenant inquiries, lease information, and maintenance requests. Use the provided context from {{base.property_data}} and respond to {{input.user_query}} in a friendly and professional manner.",
            name="Demo Assistant",
            model_name="gpt-4",
            status=ExpertStatus.active,
            input_params={
                "user_query": {"type": "string", "description": "The user's question or request"},
                "context": {"type": "object", "description": "Additional context for the response"}
            },
            team_id=team.id,
        )
        session.add(expert)
        session.commit()
        session.refresh(expert)
        print(f"✅ Created expert: {expert.name} (uuid: {expert.uuid})")

        # Create workflow
        workflow = Workflow(
            name="Property Management Workflow",
            description="A sample workflow for handling property management tasks and tenant inquiries",
            input_params={
                "tenant_query": {
                    "type": "string",
                    "description": "Tenant's question or request",
                    "required": True,
                },
                "property_id": {
                    "type": "string",
                    "description": "Property identifier",
                    "required": True,
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "default": "medium"
                },
            },
            is_api=True,
            cron_schedule=None,
            team_id=team.id,
        )
        session.add(workflow)
        session.commit()
        session.refresh(workflow)
        print(f"✅ Created workflow: {workflow.name} (uuid: {workflow.uuid})")

        # Create workflow nodes
        # Input node
        input_node = Node(
            workflow_id=workflow.id,
            node_type=NodeType.job,
            node_metadata={
                "name": "Input Processing",
                "description": "Process and validate tenant query",
                "config": {"validate_property_id": True, "sanitize_input": True},
            },
            structured_output={
                "type": "object",
                "properties": {
                    "processed_query": {"type": "string"},
                    "property_context": {"type": "object"},
                    "priority_level": {"type": "string"},
                },
            },
        )

        # Expert node
        expert_node = Node(
            workflow_id=workflow.id,
            node_type=NodeType.guru,
            node_metadata={
                "name": "AI Assistant Response",
                "description": "Generate response using the demo assistant",
                "expert_id": expert.id,
                "config": {"temperature": 0.7, "max_tokens": 500},
            },
            structured_output={
                "type": "object",
                "properties": {
                    "response": {"type": "string"},
                    "confidence": {"type": "number"},
                    "follow_up_needed": {"type": "boolean"},
                },
            },
        )

        # Output node
        output_node = Node(
            workflow_id=workflow.id,
            node_type=NodeType.return_,
            node_metadata={
                "name": "Format Response",
                "description": "Format final response for tenant",
                "config": {"include_metadata": True, "format": "json"},
            },
            structured_output={
                "type": "object",
                "properties": {
                    "tenant_response": {"type": "string"},
                    "metadata": {"type": "object"},
                    "timestamp": {"type": "string"},
                },
            },
        )

        nodes = [input_node, expert_node, output_node]
        for node in nodes:
            session.add(node)

        session.commit()
        for node in nodes:
            session.refresh(node)
        print(f"✅ Created {len(nodes)} workflow nodes")

        # Create workflow edges (linear flow)
        edges = [
            NodeNode(parent_id=input_node.id, child_id=expert_node.id),
            NodeNode(parent_id=expert_node.id, child_id=output_node.id),
        ]

        for edge in edges:
            session.add(edge)

        session.commit()
        print(f"✅ Created {len(edges)} workflow edges")

        # Link expert to workflow
        expert_workflow = ExpertWorkflow(expert_id=expert.id, workflow_id=workflow.id)
        session.add(expert_workflow)
        session.commit()
        print(f"✅ Linked expert to workflow")

        # Link expert to the production service
        prod_service = next(s for s in services if s.environment == Environment.prod)
        expert_service = ExpertService(expert_id=expert.id, service_id=prod_service.id)
        session.add(expert_service)
        session.commit()
        print(f"✅ Linked expert to service: {prod_service.name} ({prod_service.environment.value})")

        print("\n🎉 Database seeding completed successfully!")
        print("\n📊 Summary:")
        print(f"   • 1 team: {team.name}")
        print(f"   • 2 members: {admin_member.email}, {regular_member.email}")
        print(f"   • {len(services)} services (one per environment)")
        print(f"   • 1 expert: {expert.name}")
        print(f"   • 1 workflow: {workflow.name}")
        print(f"   • {len(nodes)} nodes, {len(edges)} edges")
        print(f"   • Expert linked to 1 workflow and 1 service")
        print(f"\n🔗 Expert UUID: {expert.uuid}")
        print(f"🔗 Workflow UUID: {workflow.uuid}")


if __name__ == "__main__":
    try:
        create_sample_data()
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        raise
