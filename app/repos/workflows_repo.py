from typing import Optional, List
from sqlmodel import Session, select
from app.models.workflows import Workflow, Node, NodeNode
from app.models.workflow_services import WorkflowService


class WorkflowsRepo:
    def create(self, session: Session, workflow: Workflow) -> Workflow:
        session.add(workflow)
        session.commit()
        session.refresh(workflow)
        return workflow

    def get(self, session: Session, workflow_id: int) -> Optional[Workflow]:
        return session.get(Workflow, workflow_id)

    def get_by_uuid(self, session: Session, uuid: str) -> Optional[Workflow]:
        statement = select(Workflow).where(Workflow.uuid == uuid)
        return session.exec(statement).first()

    def list(
        self,
        session: Session,
        *,
        team_id: Optional[int] = None,
        is_api: Optional[bool] = None,
    ) -> List[Workflow]:
        statement = select(Workflow)
        if team_id is not None:
            statement = statement.where(Workflow.team_id == team_id)
        if is_api is not None:
            statement = statement.where(Workflow.is_api == is_api)
        return session.exec(statement).all()

    def update(self, session: Session, workflow: Workflow) -> Workflow:
        session.add(workflow)
        session.commit()
        session.refresh(workflow)
        return workflow

    def delete(self, session: Session, workflow_id: int) -> bool:
        workflow = session.get(Workflow, workflow_id)
        if workflow:
            session.delete(workflow)
            session.commit()
            return True
        return False

    def create_node(self, session: Session, node: Node) -> Node:
        session.add(node)
        session.commit()
        session.refresh(node)
        return node

    def get_node(self, session: Session, node_id: int) -> Optional[Node]:
        return session.get(Node, node_id)

    def list_nodes(self, session: Session, workflow_id: int) -> List[Node]:
        statement = select(Node).where(Node.workflow_id == workflow_id)
        return session.exec(statement).all()

    def update_node(self, session: Session, node: Node) -> Node:
        session.add(node)
        session.commit()
        session.refresh(node)
        return node

    def delete_node(self, session: Session, node_id: int) -> bool:
        node = session.get(Node, node_id)
        if node:
            session.delete(node)
            session.commit()
            return True
        return False

    def create_edge(self, session: Session, parent_id: int, child_id: int) -> NodeNode:
        edge = NodeNode(parent_id=parent_id, child_id=child_id)
        session.add(edge)
        session.commit()
        session.refresh(edge)
        return edge

    def get_edges(self, session: Session, workflow_id: int) -> List[NodeNode]:
        statement = (
            select(NodeNode)
            .join(Node, NodeNode.parent_id == Node.id)
            .where(Node.workflow_id == workflow_id)
        )
        return session.exec(statement).all()

    def delete_edge(self, session: Session, parent_id: int, child_id: int) -> bool:
        statement = select(NodeNode).where(
            NodeNode.parent_id == parent_id, NodeNode.child_id == child_id
        )
        edge = session.exec(statement).first()
        if edge:
            session.delete(edge)
            session.commit()
            return True
        return False

    def add_service(
        self, session: Session, workflow_id: int, service_id: int
    ) -> WorkflowService:
        workflow_service = WorkflowService(
            workflow_id=workflow_id, service_id=service_id
        )
        session.add(workflow_service)
        session.commit()
        session.refresh(workflow_service)
        return workflow_service

    def remove_service(
        self, session: Session, workflow_id: int, service_id: int
    ) -> bool:
        statement = select(WorkflowService).where(
            WorkflowService.workflow_id == workflow_id,
            WorkflowService.service_id == service_id,
        )
        workflow_service = session.exec(statement).first()
        if workflow_service:
            session.delete(workflow_service)
            session.commit()
            return True
        return False
