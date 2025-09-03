from app.models.common import NodeType
from app.services.nodes.base import register_service, DefaultNodeService
from app.services.nodes.ai_job import JobService
from app.services.nodes.ai_embed import EmbedService
from app.services.nodes.resources.guru import GuruService
from app.services.nodes.resources.get_api import GetAPIService
from app.services.nodes.resources.post_api import PostAPIService
from app.services.nodes.resources.vector_query import VectorQueryService
from app.services.nodes.actions.filter import FilterService
from app.services.nodes.actions.map import MapService
from app.services.nodes.actions.if_else import IfElseService
from app.services.nodes.actions.merge import MergeService
from app.services.nodes.actions.return_ import ReturnService

# Register AI services
register_service(NodeType.job, JobService())
register_service(NodeType.embed, EmbedService())

# Register resource services
register_service(NodeType.guru, GuruService())
register_service(NodeType.get_api, GetAPIService())
register_service(NodeType.post_api, PostAPIService())
register_service(NodeType.vector_query, VectorQueryService())

# Register action services
register_service(NodeType.filter, FilterService())
register_service(NodeType.map, MapService())
register_service(NodeType.if_else, IfElseService())
register_service(NodeType.merge, MergeService())
register_service(NodeType.return_, ReturnService())

# Register default service for unimplemented node types
default_service = DefaultNodeService()
implemented_types = {
    NodeType.job,
    NodeType.embed,
    NodeType.guru,
    NodeType.get_api,
    NodeType.post_api,
    NodeType.vector_query,
    NodeType.filter,
    NodeType.map,
    NodeType.if_else,
    NodeType.merge,
    NodeType.return_,
}

for node_type in NodeType:
    if node_type not in implemented_types:
        register_service(node_type, default_service)
