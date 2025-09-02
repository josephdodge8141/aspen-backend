from typing import Optional, List
from sqlmodel import Session, select
from app.models.users import User, ServiceUser


class UsersRepo:
    def create(self, session: Session, user: User) -> User:
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    def get(self, session: Session, user_id: int) -> Optional[User]:
        return session.get(User, user_id)

    def get_by_member_id(self, session: Session, member_id: int) -> Optional[User]:
        statement = select(User).where(User.member_id == member_id)
        return session.exec(statement).first()

    def get_by_service_user_id(self, session: Session, service_user_id: int) -> Optional[User]:
        statement = select(User).where(User.service_user_id == service_user_id)
        return session.exec(statement).first()

    def list(self, session: Session, *, has_member: Optional[bool] = None) -> List[User]:
        statement = select(User)
        if has_member is not None:
            if has_member:
                statement = statement.where(User.member_id.is_not(None))
            else:
                statement = statement.where(User.member_id.is_(None))
        return session.exec(statement).all()

    def update(self, session: Session, user: User) -> User:
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    def delete(self, session: Session, user_id: int) -> bool:
        user = session.get(User, user_id)
        if user:
            session.delete(user)
            session.commit()
            return True
        return False

    def create_service_user(self, session: Session, service_user: ServiceUser) -> ServiceUser:
        session.add(service_user)
        session.commit()
        session.refresh(service_user)
        return service_user

    def get_service_user(self, session: Session, service_user_id: int) -> Optional[ServiceUser]:
        return session.get(ServiceUser, service_user_id)

    def get_service_user_by_hash(self, session: Session, segment_hash: bytes) -> Optional[ServiceUser]:
        statement = select(ServiceUser).where(ServiceUser.segment_hash == segment_hash)
        return session.exec(statement).first()

    def list_service_users(self, session: Session, *, user_id: Optional[int] = None, service_id: Optional[int] = None) -> List[ServiceUser]:
        statement = select(ServiceUser)
        if user_id is not None:
            statement = statement.where(ServiceUser.user_id == user_id)
        if service_id is not None:
            statement = statement.where(ServiceUser.service_id == service_id)
        return session.exec(statement).all()

    def update_service_user(self, session: Session, service_user: ServiceUser) -> ServiceUser:
        session.add(service_user)
        session.commit()
        session.refresh(service_user)
        return service_user

    def delete_service_user(self, session: Session, service_user_id: int) -> bool:
        service_user = session.get(ServiceUser, service_user_id)
        if service_user:
            session.delete(service_user)
            session.commit()
            return True
        return False 