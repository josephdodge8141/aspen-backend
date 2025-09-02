from typing import Optional, List
from sqlmodel import Session, select
from app.models.services import Service, ServiceSegment
from app.models.common import Environment


class ServicesRepo:
    def create(self, session: Session, service: Service) -> Service:
        session.add(service)
        session.commit()
        session.refresh(service)
        return service

    def get(self, session: Session, service_id: int) -> Optional[Service]:
        return session.get(Service, service_id)

    def get_by_name_and_env(self, session: Session, name: str, environment: Environment) -> Optional[Service]:
        statement = select(Service).where(
            Service.name == name,
            Service.environment == environment
        )
        return session.exec(statement).first()

    def list(self, session: Session, *, environment: Optional[Environment] = None) -> List[Service]:
        statement = select(Service)
        if environment is not None:
            statement = statement.where(Service.environment == environment)
        return session.exec(statement).all()

    def update(self, session: Session, service: Service) -> Service:
        session.add(service)
        session.commit()
        session.refresh(service)
        return service

    def delete(self, session: Session, service_id: int) -> bool:
        service = session.get(Service, service_id)
        if service:
            session.delete(service)
            session.commit()
            return True
        return False

    def create_segment(self, session: Session, segment: ServiceSegment) -> ServiceSegment:
        session.add(segment)
        session.commit()
        session.refresh(segment)
        return segment

    def get_segment(self, session: Session, segment_id: int) -> Optional[ServiceSegment]:
        return session.get(ServiceSegment, segment_id)

    def get_segment_by_name(self, session: Session, service_id: int, name: str) -> Optional[ServiceSegment]:
        statement = select(ServiceSegment).where(
            ServiceSegment.service_id == service_id,
            ServiceSegment.name == name
        )
        return session.exec(statement).first()

    def list_segments(self, session: Session, service_id: int) -> List[ServiceSegment]:
        statement = select(ServiceSegment).where(ServiceSegment.service_id == service_id)
        return session.exec(statement).all()

    def update_segment(self, session: Session, segment: ServiceSegment) -> ServiceSegment:
        session.add(segment)
        session.commit()
        session.refresh(segment)
        return segment

    def delete_segment(self, session: Session, segment_id: int) -> bool:
        segment = session.get(ServiceSegment, segment_id)
        if segment:
            session.delete(segment)
            session.commit()
            return True
        return False 