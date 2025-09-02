from fastapi import HTTPException
from sqlmodel import Session, select
from app.models.team import TeamMember, TeamRole
from app.models.users import User


def require_team_member(session: Session, user: User, team_id: int) -> None:
    team_member = session.exec(
        select(TeamMember).where(
            TeamMember.member_id == user.member_id, TeamMember.team_id == team_id
        )
    ).first()

    if not team_member:
        raise HTTPException(status_code=403, detail="forbidden")


def require_team_admin(session: Session, user: User, team_id: int) -> None:
    team_member = session.exec(
        select(TeamMember).where(
            TeamMember.member_id == user.member_id, TeamMember.team_id == team_id
        )
    ).first()

    if not team_member or team_member.role != TeamRole.admin:
        raise HTTPException(status_code=403, detail="forbidden")
