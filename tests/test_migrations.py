"""
Tests for database migration integrity.
These tests ensure migrations can be applied and rolled back properly.
"""

import pytest
import subprocess
import os
from sqlmodel import Session, create_engine, text
from app.database import engine


def test_migration_status():
    """Test that migrations are at the expected state"""
    # This should pass if all migrations have been applied
    result = subprocess.run(
        ["alembic", "current"],
        capture_output=True,
        text=True,
        cwd=os.getcwd()
    )
    
    assert result.returncode == 0, f"Failed to get migration status: {result.stderr}"
    assert "head" in result.stdout, "Migrations are not at head"


def test_migration_history():
    """Test that migration history is valid and contains expected migrations"""
    result = subprocess.run(
        ["alembic", "history"],
        capture_output=True, 
        text=True,
        cwd=os.getcwd()
    )
    
    assert result.returncode == 0, f"Failed to get migration history: {result.stderr}"
    
    # Check that we have the expected migrations in order
    expected_migrations = [
        "create_team_member_tables",
        "create_experts_tables", 
        "create_services_tables",
        "create_users_tables",
        "create_workflows_tables",
        "create_workflow_services_table"
    ]
    
    output = result.stdout
    for migration in expected_migrations:
        assert migration in output, f"Migration '{migration}' not found in history"


def test_database_schema_integrity():
    """Test that the current database schema matches our models"""
    with Session(engine) as session:
        # Test that all expected tables exist
        expected_tables = [
            "teams", "members", "team_members",
            "experts", "expert_services", "expert_workflows", 
            "services", "service_segments",
            "users", "service_users",
            "workflows", "nodes", "node_nodes",
            "workflow_services",
            "alembic_version"  # Alembic's own table
        ]
        
        for table in expected_tables:
            result = session.exec(text(f"""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = '{table}'
            """))
            count = result.fetchone()[0]
            assert count == 1, f"Table '{table}' not found in database"


def test_enum_types():
    """Test that enum types are properly created"""
    with Session(engine) as session:
        # Test that enum types exist in PostgreSQL
        enum_types = [
            "teamrole",
            "expertstatus", 
            "environment",
            "nodetype"
        ]
        
        for enum_type in enum_types:
            result = session.exec(text(f"""
                SELECT COUNT(*) FROM pg_type 
                WHERE typname = '{enum_type}' AND typtype = 'e'
            """))
            count = result.fetchone()[0]
            assert count == 1, f"Enum type '{enum_type}' not found in database"


def test_indexes():
    """Test that indexes are properly created"""
    with Session(engine) as session:
        # Test that important indexes exist
        expected_indexes = [
            ("experts", "idx_experts_team_id"),
            ("experts", "idx_experts_status"),
        ]
        
        for table, index in expected_indexes:
            result = session.exec(text(f"""
                SELECT COUNT(*) FROM pg_indexes 
                WHERE tablename = '{table}' AND indexname = '{index}'
            """))
            count = result.fetchone()[0]
            assert count == 1, f"Index '{index}' not found on table '{table}'"


def test_basic_crud_operations():
    """Test that basic CRUD operations work after migrations"""
    from app.models.team import Team, Member
    
    with Session(engine) as session:
        # Test create
        team = Team(name="Migration Test Team")
        session.add(team)
        session.commit()
        session.refresh(team)
        
        # Test read
        retrieved_team = session.get(Team, team.id)
        assert retrieved_team is not None
        assert retrieved_team.name == "Migration Test Team"
        
        # Test that relationships work
        import uuid
        member = Member(
            first_name="Test",
            last_name="User",
            email=f"test.{uuid.uuid4()}@example.com"
        )
        session.add(member)
        session.commit()
        
        # Test that foreign keys work
        from app.models.team import TeamMember
        from app.models.common import TeamRole
        
        team_member = TeamMember(
            team_id=team.id,
            member_id=member.id,
            role=TeamRole.member
        )
        session.add(team_member)
        session.commit()
        
        assert team_member.id is not None
        assert team_member.team_id == team.id
        assert team_member.member_id == member.id


def test_data_types_and_constraints():
    """Test that data types and constraints work as expected"""
    from app.models.experts import Expert
    from app.models.team import Team
    from app.models.common import ExpertStatus
    
    with Session(engine) as session:
        # Create a team first
        team = Team(name="Expert Test Team")
        session.add(team)
        session.commit()
        session.refresh(team)
        
        # Test JSON fields
        expert = Expert(
            prompt="Test prompt",
            name="Test Expert",
            model_name="test-model",
            status=ExpertStatus.active,
            input_params={"temperature": 0.7, "max_tokens": 100},
            team_id=team.id
        )
        session.add(expert)
        session.commit()
        session.refresh(expert)
        
        # Test that JSON data is preserved
        assert expert.input_params["temperature"] == 0.7
        assert expert.input_params["max_tokens"] == 100
        
        # Test that UUID is generated
        assert expert.uuid is not None
        assert len(expert.uuid) == 36  # Standard UUID format 