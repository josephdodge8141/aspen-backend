import pytest
import uuid
from sqlmodel import Session
from sqlalchemy.exc import IntegrityError
from app.database import engine
from app.models.team import Team, Member, TeamMember
from app.models.common import TeamRole


@pytest.fixture
def db_session():
    with Session(engine) as session:
        yield session


def unique_email():
    return f"test-{uuid.uuid4()}@example.com"


def test_create_member(db_session):
    member = Member(first_name="John", last_name="Doe", email=unique_email())
    db_session.add(member)
    db_session.commit()

    assert member.id is not None
    assert member.first_name == "John"
    assert member.last_name == "Doe"


def test_create_team(db_session):
    team = Team(name=f"Engineering-{uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()

    assert team.id is not None
    assert team.name.startswith("Engineering")


def test_create_team_member(db_session):
    # Create member and team first
    member = Member(first_name="Jane", last_name="Smith", email=unique_email())
    team = Team(name=f"Product-{uuid.uuid4()}")

    db_session.add(member)
    db_session.add(team)
    db_session.commit()

    # Create team member relationship
    team_member = TeamMember(team_id=team.id, member_id=member.id, role=TeamRole.admin)
    db_session.add(team_member)
    db_session.commit()

    assert team_member.id is not None
    assert team_member.team_id == team.id
    assert team_member.member_id == member.id
    assert team_member.role == TeamRole.admin


def test_unique_email_constraint(db_session):
    email = unique_email()

    member1 = Member(first_name="Alice", last_name="Johnson", email=email)
    member2 = Member(first_name="Bob", last_name="Wilson", email=email)  # Same email

    db_session.add(member1)
    db_session.commit()

    db_session.add(member2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_unique_team_member_constraint(db_session):
    # Create member and team
    member = Member(first_name="Charlie", last_name="Brown", email=unique_email())
    team = Team(name=f"Design-{uuid.uuid4()}")

    db_session.add(member)
    db_session.add(team)
    db_session.commit()

    # Create first team member relationship
    team_member1 = TeamMember(
        team_id=team.id, member_id=member.id, role=TeamRole.member
    )
    db_session.add(team_member1)
    db_session.commit()

    # Try to create duplicate relationship
    team_member2 = TeamMember(team_id=team.id, member_id=member.id, role=TeamRole.admin)
    db_session.add(team_member2)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_team_role_enum_validation(db_session):
    member = Member(first_name="David", last_name="Lee", email=unique_email())
    team = Team(name=f"Marketing-{uuid.uuid4()}")

    db_session.add(member)
    db_session.add(team)
    db_session.commit()

    # Test both enum values
    team_member_admin = TeamMember(
        team_id=team.id, member_id=member.id, role=TeamRole.admin
    )
    assert team_member_admin.role == TeamRole.admin

    team_member_member = TeamMember(
        team_id=team.id, member_id=member.id, role=TeamRole.member
    )
    assert team_member_member.role == TeamRole.member
