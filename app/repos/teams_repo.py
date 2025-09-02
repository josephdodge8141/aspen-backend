from typing import Optional, List
from sqlmodel import Session, select
from app.models.team import Team, Member, TeamMember
from app.models.common import TeamRole


class TeamsRepo:
    def create(self, session: Session, team: Team) -> Team:
        session.add(team)
        session.commit()
        session.refresh(team)
        return team

    def get(self, session: Session, team_id: int) -> Optional[Team]:
        return session.get(Team, team_id)

    def get_by_name(self, session: Session, name: str) -> Optional[Team]:
        statement = select(Team).where(Team.name == name)
        return session.exec(statement).first()

    def list(self, session: Session) -> List[Team]:
        statement = select(Team)
        return session.exec(statement).all()

    def update(self, session: Session, team: Team) -> Team:
        session.add(team)
        session.commit()
        session.refresh(team)
        return team

    def delete(self, session: Session, team_id: int) -> bool:
        team = session.get(Team, team_id)
        if team:
            session.delete(team)
            session.commit()
            return True
        return False

    def create_member(self, session: Session, member: Member) -> Member:
        session.add(member)
        session.commit()
        session.refresh(member)
        return member

    def get_member(self, session: Session, member_id: int) -> Optional[Member]:
        return session.get(Member, member_id)

    def get_member_by_email(self, session: Session, email: str) -> Optional[Member]:
        statement = select(Member).where(Member.email == email)
        return session.exec(statement).first()

    def list_members(self, session: Session) -> List[Member]:
        statement = select(Member)
        return session.exec(statement).all()

    def update_member(self, session: Session, member: Member) -> Member:
        session.add(member)
        session.commit()
        session.refresh(member)
        return member

    def delete_member(self, session: Session, member_id: int) -> bool:
        member = session.get(Member, member_id)
        if member:
            session.delete(member)
            session.commit()
            return True
        return False

    def add_member_to_team(
        self, session: Session, team_id: int, member_id: int, role: TeamRole
    ) -> TeamMember:
        team_member = TeamMember(team_id=team_id, member_id=member_id, role=role)
        session.add(team_member)
        session.commit()
        session.refresh(team_member)
        return team_member

    def remove_member_from_team(
        self, session: Session, team_id: int, member_id: int
    ) -> bool:
        statement = select(TeamMember).where(
            TeamMember.team_id == team_id, TeamMember.member_id == member_id
        )
        team_member = session.exec(statement).first()
        if team_member:
            session.delete(team_member)
            session.commit()
            return True
        return False

    def get_team_members(self, session: Session, team_id: int) -> List[TeamMember]:
        statement = select(TeamMember).where(TeamMember.team_id == team_id)
        return session.exec(statement).all()

    def get_member_teams(self, session: Session, member_id: int) -> List[TeamMember]:
        statement = select(TeamMember).where(TeamMember.member_id == member_id)
        return session.exec(statement).all()

    def update_member_role(
        self, session: Session, team_id: int, member_id: int, role: TeamRole
    ) -> Optional[TeamMember]:
        statement = select(TeamMember).where(
            TeamMember.team_id == team_id, TeamMember.member_id == member_id
        )
        team_member = session.exec(statement).first()
        if team_member:
            team_member.role = role
            session.add(team_member)
            session.commit()
            session.refresh(team_member)
            return team_member
        return None
