from typing import Optional
from sqlmodel import Field
from sqlalchemy import UniqueConstraint
from .common import TimestampMixin, TeamRole


class Team(TimestampMixin, table=True):
    __tablename__ = "teams"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False)


class Member(TimestampMixin, table=True):
    __tablename__ = "members"

    id: Optional[int] = Field(default=None, primary_key=True)
    first_name: str = Field(nullable=False)
    last_name: str = Field(nullable=False)
    email: str = Field(nullable=False, unique=True)


class TeamMember(TimestampMixin, table=True):
    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("team_id", "member_id", name="uq_team_members_team_member"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="teams.id", nullable=False)
    member_id: int = Field(foreign_key="members.id", nullable=False)
    role: TeamRole = Field(nullable=False)
