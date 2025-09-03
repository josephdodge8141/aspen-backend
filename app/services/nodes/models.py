from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, HttpUrl, model_validator
from enum import Enum


class MetaCommon(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    timeout_ms: Optional[int] = Field(None, gt=0)
    retry: Optional[int] = Field(None, ge=0)
    on_error: Optional[str] = Field(None, pattern="^(fail|skip|continue)$")
    tags: Optional[List[str]] = None


class MergeStrategy(str, Enum):
    union = "union"
    concat = "concat"
    prefer_left = "prefer_left"


class SplitMode(str, Enum):
    group_by = "group_by"
    chunk = "chunk"


class ContentType(str, Enum):
    json = "application/json"
    form = "application/x-www-form-urlencoded"
    text = "text/plain"


class MetaJob(MetaCommon):
    prompt: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, gt=0)
    stop: Optional[List[str]] = None
    system: Optional[str] = None


class MetaEmbed(MetaCommon):
    vector_store_id: str = Field(min_length=1)
    namespace: Optional[str] = None
    model_name: Optional[str] = None
    input_selector: str = Field(min_length=1)
    id_selector: Optional[str] = None
    metadata_map: Optional[Dict[str, str]] = None
    upsert: Optional[bool] = True


class MetaGuru(MetaCommon):
    space: str
    query_template: str
    top_k: Optional[int] = Field(5, gt=0)
    filters: Optional[Dict[str, Union[str, int, bool]]] = None


class MetaGetAPI(MetaCommon):
    url: HttpUrl
    headers: Optional[Dict[str, str]] = None
    query_map: Optional[Dict[str, str]] = None
    auth_preset: Optional[str] = None


class MetaPostAPI(MetaCommon):
    url: HttpUrl
    headers: Optional[Dict[str, str]] = None
    body_map: Optional[Dict[str, Any]] = None
    content_type: Optional[ContentType] = ContentType.json
    auth_preset: Optional[str] = None


class MetaVectorQuery(MetaCommon):
    vector_store_id: str
    namespace: Optional[str] = None
    query_template: str
    top_k: Optional[int] = Field(5, gt=0)
    filters: Optional[Dict[str, Union[str, int, bool]]] = None


class MetaFilter(MetaCommon):
    items_selector: Optional[str] = None
    where: str


class MetaMap(MetaCommon):
    mapping: Dict[str, Union[str, int, bool]]

    @model_validator(mode="after")
    def validate_mapping_not_empty(self):
        if not self.mapping:
            raise ValueError("mapping cannot be empty")
        return self


class MetaIfElse(MetaCommon):
    predicate: str


class MetaForEach(MetaCommon):
    items_selector: str
    concurrency: Optional[int] = Field(None, gt=0)
    flatten: Optional[bool] = True


class MetaMerge(MetaCommon):
    strategy: Optional[MergeStrategy] = MergeStrategy.union
    expected_parents: Optional[int] = Field(None, gt=0)


class MetaSplit(MetaCommon):
    by: str
    mode: Optional[SplitMode] = SplitMode.group_by
    chunk_size: Optional[int] = Field(None, gt=0)

    @model_validator(mode="after")
    def validate_chunk_size_when_chunk_mode(self):
        if self.mode == SplitMode.chunk and not self.chunk_size:
            raise ValueError("chunk_size is required when mode is 'chunk'")
        return self


class MetaAdvanced(MetaCommon):
    expression: str


class MetaReturn(MetaCommon):
    payload_selector: str
    content_type: Optional[ContentType] = ContentType.json
    status_code: Optional[int] = Field(200, ge=100, le=599)


class MetaWorkflowCall(MetaCommon):
    workflow_id: int = Field(gt=0)
    input_mapping: Optional[Dict[str, str]] = None
    propagate_identity: Optional[bool] = True
    wait: Optional[str] = Field("sync", pattern="^sync$")
