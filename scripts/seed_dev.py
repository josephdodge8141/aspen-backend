#!/usr/bin/env python3
"""
Development database seeding script.
Creates sample data for local development and testing.
"""

import hashlib
import json
from sqlmodel import Session
from app.database import engine
from app.models.team import Team, Member, TeamMember
from app.models.experts import Expert
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
        
        # Create team
        team = Team(name="Demo Team")
        session.add(team)
        session.commit()
        session.refresh(team)
        print(f"✅ Created team: {team.name} (id: {team.id})")
        
        # Create members
        admin_member = Member(
            first_name="Alice",
            last_name="Admin",
            email="alice.admin@example.com"
        )
        regular_member = Member(
            first_name="Bob",
            last_name="Developer",
            email="bob.developer@example.com"
        )
        session.add(admin_member)
        session.add(regular_member)
        session.commit()
        session.refresh(admin_member)
        session.refresh(regular_member)
        print(f"✅ Created members: {admin_member.email}, {regular_member.email}")
        
        # Add members to team
        admin_team_member = TeamMember(
            team_id=team.id,
            member_id=admin_member.id,
            role=TeamRole.admin
        )
        regular_team_member = TeamMember(
            team_id=team.id,
            member_id=regular_member.id,
            role=TeamRole.member
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
                name=f"Demo Service",
                environment=env,
                api_key_hash=hash_api_key(api_key),
                api_key_last4=api_key[-4:]
            )
            services.append(service)
            session.add(service)
        
        session.commit()
        for service in services:
            session.refresh(service)
        print(f"✅ Created {len(services)} services for environments: {', '.join([s.environment.value for s in services])}")
        
        # Create expert
        expert = Expert(
            prompt="You are a helpful AI assistant that provides clear and concise answers. You are knowledgeable about software development, data analysis, and general problem-solving.",
            name="Demo Assistant",
            model_name="gpt-4",
            status=ExpertStatus.active,
            input_params={
                "temperature": 0.7,
                "max_tokens": 1000,
                "top_p": 1.0
            },
            team_id=team.id
        )
        session.add(expert)
        session.commit()
        session.refresh(expert)
        print(f"✅ Created expert: {expert.name} (uuid: {expert.uuid})")
        
        # Create workflow
        workflow = Workflow(
            name="Demo Data Processing Workflow",
            description="A sample workflow that demonstrates data processing with multiple steps",
            input_params={
                "input_text": {
                    "type": "string",
                    "description": "Text to process",
                    "required": True
                },
                "processing_options": {
                    "type": "object",
                    "properties": {
                        "sentiment_analysis": {"type": "boolean", "default": True},
                        "keyword_extraction": {"type": "boolean", "default": True},
                        "summarization": {"type": "boolean", "default": False}
                    }
                }
            },
            is_api=True,
            cron_schedule=None,
            team_id=team.id
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
                "name": "Input Validation",
                "description": "Validate and clean input text",
                "config": {
                    "min_length": 10,
                    "max_length": 10000,
                    "clean_html": True
                }
            },
            structured_output={
                "type": "object",
                "properties": {
                    "cleaned_text": {"type": "string"},
                    "validation_status": {"type": "string", "enum": ["valid", "invalid"]},
                    "word_count": {"type": "integer"}
                }
            }
        )
        
        # Processing node
        processing_node = Node(
            workflow_id=workflow.id,
            node_type=NodeType.guru,
            node_metadata={
                "name": "Text Analysis",
                "description": "Analyze text for sentiment and keywords",
                "expert_id": expert.id,
                "config": {
                    "analysis_types": ["sentiment", "keywords", "entities"]
                }
            },
            structured_output={
                "type": "object",
                "properties": {
                    "sentiment": {"type": "object"},
                    "keywords": {"type": "array", "items": {"type": "string"}},
                    "entities": {"type": "array"}
                }
            }
        )
        
        # Filter node
        filter_node = Node(
            workflow_id=workflow.id,
            node_type=NodeType.filter,
            node_metadata={
                "name": "Quality Filter",
                "description": "Filter results based on confidence scores",
                "config": {
                    "min_confidence": 0.7,
                    "filter_criteria": ["sentiment.confidence > 0.7", "keywords.length > 0"]
                }
            },
            structured_output={
                "type": "object",
                "properties": {
                    "filtered_results": {"type": "object"},
                    "filter_passed": {"type": "boolean"}
                }
            }
        )
        
        # Output node
        output_node = Node(
            workflow_id=workflow.id,
            node_type=NodeType.return_,
            node_metadata={
                "name": "Format Output",
                "description": "Format final results for API response",
                "config": {
                    "output_format": "json",
                    "include_metadata": True
                }
            },
            structured_output={
                "type": "object",
                "properties": {
                    "analysis_results": {"type": "object"},
                    "metadata": {"type": "object"},
                    "processing_time_ms": {"type": "number"}
                }
            }
        )
        
        nodes = [input_node, processing_node, filter_node, output_node]
        for node in nodes:
            session.add(node)
        
        session.commit()
        for node in nodes:
            session.refresh(node)
        print(f"✅ Created {len(nodes)} workflow nodes")
        
        # Create workflow edges (linear flow)
        edges = [
            NodeNode(parent_id=input_node.id, child_id=processing_node.id),
            NodeNode(parent_id=processing_node.id, child_id=filter_node.id),
            NodeNode(parent_id=filter_node.id, child_id=output_node.id)
        ]
        
        for edge in edges:
            session.add(edge)
        
        session.commit()
        print(f"✅ Created {len(edges)} workflow edges")
        
        print("\n🎉 Database seeding completed successfully!")
        print("\n📊 Summary:")
        print(f"   • 1 team: {team.name}")
        print(f"   • 2 members: {admin_member.email}, {regular_member.email}")
        print(f"   • {len(services)} services (one per environment)")
        print(f"   • 1 expert: {expert.name}")
        print(f"   • 1 workflow: {workflow.name}")
        print(f"   • {len(nodes)} nodes, {len(edges)} edges")


if __name__ == "__main__":
    try:
        create_sample_data()
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        raise 