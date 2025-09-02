import pytest
import uuid
from fastapi import HTTPException
from sqlmodel import Session

from app.models.team import Team, Member, TeamMember
from app.models.users import User
from app.models.common import TeamRole
from app.security.permissions import require_team_member, require_team_admin
from app.security.passwords import hash_password


def test_require_team_member_success(db_session: Session):
    # Create test data
    team = Team(name=f"Test Team {uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    member = Member(
        first_name="Test", last_name="User", email=f"test.{uuid.uuid4()}@example.com"
    )
    db_session.add(member)
    db_session.commit()
    db_session.refresh(member)

    user = User(member_id=member.id, password_hash=hash_password("test_password"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    team_member = TeamMember(team_id=team.id, member_id=member.id, role=TeamRole.member)
    db_session.add(team_member)
    db_session.commit()

    # Should not raise exception
    require_team_member(db_session, user, team.id)


def test_require_team_member_not_member(db_session: Session):
    # Create team
    team = Team(name=f"Test Team {uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    # Create user not in team
    member = Member(
        first_name="Test", last_name="User", email=f"test.{uuid.uuid4()}@example.com"
    )
    db_session.add(member)
    db_session.commit()
    db_session.refresh(member)

    user = User(member_id=member.id, password_hash=hash_password("test_password"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Should raise 403
    with pytest.raises(HTTPException) as exc_info:
        require_team_member(db_session, user, team.id)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "forbidden"


def test_require_team_admin_success(db_session: Session):
    # Create test data
    team = Team(name=f"Test Team {uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    member = Member(
        first_name="Test", last_name="Admin", email=f"admin.{uuid.uuid4()}@example.com"
    )
    db_session.add(member)
    db_session.commit()
    db_session.refresh(member)

    user = User(member_id=member.id, password_hash=hash_password("test_password"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    team_member = TeamMember(team_id=team.id, member_id=member.id, role=TeamRole.admin)
    db_session.add(team_member)
    db_session.commit()

    # Should not raise exception
    require_team_admin(db_session, user, team.id)


def test_require_team_admin_regular_member(db_session: Session):
    # Create test data
    team = Team(name=f"Test Team {uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    member = Member(
        first_name="Test",
        last_name="Member",
        email=f"member.{uuid.uuid4()}@example.com",
    )
    db_session.add(member)
    db_session.commit()
    db_session.refresh(member)

    user = User(member_id=member.id, password_hash=hash_password("test_password"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    team_member = TeamMember(
        team_id=team.id,
        member_id=member.id,
        role=TeamRole.member,  # Regular member, not admin
    )
    db_session.add(team_member)
    db_session.commit()

    # Should raise 403
    with pytest.raises(HTTPException) as exc_info:
        require_team_admin(db_session, user, team.id)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "forbidden"


def test_require_team_admin_not_member(db_session: Session):
    # Create team
    team = Team(name=f"Test Team {uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    # Create user not in team
    member = Member(
        first_name="Test",
        last_name="Outsider",
        email=f"outsider.{uuid.uuid4()}@example.com",
    )
    db_session.add(member)
    db_session.commit()
    db_session.refresh(member)

    user = User(member_id=member.id, password_hash=hash_password("test_password"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Should raise 403
    with pytest.raises(HTTPException) as exc_info:
        require_team_admin(db_session, user, team.id)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "forbidden"


def test_require_team_member_user_without_member_id(db_session: Session):
    # Create team
    team = Team(name=f"Test Team {uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    # Create user without member_id (service user)
    user = User(member_id=None, password_hash=None, service_user_id=1)  # External user
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Should raise 403 (no member_id to check against)
    with pytest.raises(HTTPException) as exc_info:
        require_team_member(db_session, user, team.id)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "forbidden"


def test_require_team_admin_user_without_member_id(db_session: Session):
    # Create team
    team = Team(name=f"Test Team {uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    # Create user without member_id (service user)
    user = User(member_id=None, password_hash=None, service_user_id=1)  # External user
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Should raise 403 (no member_id to check against)
    with pytest.raises(HTTPException) as exc_info:
        require_team_admin(db_session, user, team.id)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "forbidden"
