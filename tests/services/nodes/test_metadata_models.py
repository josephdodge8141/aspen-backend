import pytest
from pydantic import ValidationError
from app.services.nodes.models import (
    MetaCommon,
    MetaJob,
    MetaEmbed,
    MetaGuru,
    MetaGetAPI,
    MetaPostAPI,
    MetaVectorQuery,
    MetaFilter,
    MetaMap,
    MetaIfElse,
    MetaForEach,
    MetaMerge,
    MetaSplit,
    MetaAdvanced,
    MetaReturn,
    MetaWorkflowCall,
    MergeStrategy,
    SplitMode,
    ContentType,
)


class TestMetaCommon:
    def test_valid_common_fields(self):
        meta = MetaCommon(
            name="Test Node",
            description="A test node",
            timeout_ms=5000,
            retry=3,
            on_error="fail",
            tags=["test", "example"],
        )
        assert meta.name == "Test Node"
        assert meta.timeout_ms == 5000
        assert meta.retry == 3
        assert meta.on_error == "fail"
        assert meta.tags == ["test", "example"]

    def test_optional_fields(self):
        meta = MetaCommon()
        assert meta.name is None
        assert meta.timeout_ms is None
        assert meta.on_error is None

    def test_invalid_timeout(self):
        with pytest.raises(ValidationError):
            MetaCommon(timeout_ms=0)

        with pytest.raises(ValidationError):
            MetaCommon(timeout_ms=-100)

    def test_invalid_on_error(self):
        with pytest.raises(ValidationError):
            MetaCommon(on_error="invalid")


class TestMetaJob:
    def test_valid_job_metadata(self):
        meta = MetaJob(
            prompt="Summarize the following text: {{ input.text }}",
            model_name="gpt-4o-mini",
            temperature=0.7,
            max_tokens=500,
            stop=["END"],
            system="You are a helpful assistant",
        )
        assert meta.prompt == "Summarize the following text: {{ input.text }}"
        assert meta.model_name == "gpt-4o-mini"
        assert meta.temperature == 0.7
        assert meta.max_tokens == 500

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            MetaJob()

        with pytest.raises(ValidationError):
            MetaJob(prompt="test")

    def test_temperature_validation(self):
        with pytest.raises(ValidationError):
            MetaJob(prompt="test", model_name="gpt-4", temperature=-0.1)

        with pytest.raises(ValidationError):
            MetaJob(prompt="test", model_name="gpt-4", temperature=2.1)


class TestMetaEmbed:
    def test_valid_embed_metadata(self):
        meta = MetaEmbed(
            vector_store_id="vs_customers",
            namespace="orders",
            input_selector="input.order.items[*].description",
            id_selector="input.order.id",
            metadata_map={"customer": "input.customer.id"},
            upsert=True,
        )
        assert meta.vector_store_id == "vs_customers"
        assert meta.input_selector == "input.order.items[*].description"
        assert meta.upsert is True

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            MetaEmbed()

        with pytest.raises(ValidationError):
            MetaEmbed(vector_store_id="vs_test")


class TestMetaGuru:
    def test_valid_guru_metadata(self):
        meta = MetaGuru(
            space="support-faqs",
            query_template="FAQ for {{ input.topic }}",
            top_k=5,
            filters={"language": "en"},
        )
        assert meta.space == "support-faqs"
        assert meta.query_template == "FAQ for {{ input.topic }}"
        assert meta.top_k == 5

    def test_top_k_validation(self):
        with pytest.raises(ValidationError):
            MetaGuru(space="test", query_template="test", top_k=0)


class TestMetaGetAPI:
    def test_valid_get_api_metadata(self):
        meta = MetaGetAPI(
            url="https://api.example.com/search",
            headers={"X-Client": "workflow-engine"},
            query_map={"q": "input.query", "limit": "5"},
        )
        assert str(meta.url) == "https://api.example.com/search"
        assert meta.headers["X-Client"] == "workflow-engine"

    def test_url_validation(self):
        with pytest.raises(ValidationError):
            MetaGetAPI(url="not-a-url")


class TestMetaPostAPI:
    def test_valid_post_api_metadata(self):
        meta = MetaPostAPI(
            url="https://api.example.com/orders",
            headers={"Authorization": "Bearer token"},
            body_map={"user_id": "input.user.id"},
            content_type=ContentType.json,
        )
        assert str(meta.url) == "https://api.example.com/orders"
        assert meta.content_type == ContentType.json

    def test_content_type_enum(self):
        meta = MetaPostAPI(
            url="https://api.example.com/form", content_type=ContentType.form
        )
        assert meta.content_type == "application/x-www-form-urlencoded"


class TestMetaFilter:
    def test_valid_filter_metadata(self):
        meta = MetaFilter(items_selector="input.items", where="$.price > 20")
        assert meta.where == "$.price > 20"

    def test_required_where(self):
        with pytest.raises(ValidationError):
            MetaFilter()


class TestMetaMap:
    def test_valid_map_metadata(self):
        meta = MetaMap(
            mapping={
                "customer_id": "input.customer.id",
                "total": "input.items.sum($.price)",
                "count": 5,
            }
        )
        assert len(meta.mapping) == 3

    def test_empty_mapping_raises_error(self):
        with pytest.raises(ValueError, match="mapping cannot be empty"):
            MetaMap(mapping={})


class TestMetaIfElse:
    def test_valid_if_else_metadata(self):
        meta = MetaIfElse(predicate="input.total > 100")
        assert meta.predicate == "input.total > 100"

    def test_required_predicate(self):
        with pytest.raises(ValidationError):
            MetaIfElse()


class TestMetaForEach:
    def test_valid_for_each_metadata(self):
        meta = MetaForEach(
            items_selector="input.orders[*]", concurrency=5, flatten=True
        )
        assert meta.items_selector == "input.orders[*]"
        assert meta.concurrency == 5
        assert meta.flatten is True

    def test_concurrency_validation(self):
        with pytest.raises(ValidationError):
            MetaForEach(items_selector="input.items", concurrency=0)


class TestMetaMerge:
    def test_valid_merge_metadata(self):
        meta = MetaMerge(strategy=MergeStrategy.union)
        assert meta.strategy == MergeStrategy.union

    def test_default_strategy(self):
        meta = MetaMerge()
        assert meta.strategy == MergeStrategy.union

    def test_strategy_enum(self):
        meta = MetaMerge(strategy=MergeStrategy.prefer_left)
        assert meta.strategy == "prefer_left"


class TestMetaSplit:
    def test_valid_split_group_by(self):
        meta = MetaSplit(by="input.items[*].category", mode=SplitMode.group_by)
        assert meta.by == "input.items[*].category"
        assert meta.mode == SplitMode.group_by

    def test_valid_split_chunk(self):
        meta = MetaSplit(by="input.items", mode=SplitMode.chunk, chunk_size=10)
        assert meta.chunk_size == 10

    def test_chunk_mode_requires_size(self):
        with pytest.raises(
            ValueError, match="chunk_size is required when mode is 'chunk'"
        ):
            MetaSplit(by="input.items", mode=SplitMode.chunk)


class TestMetaAdvanced:
    def test_valid_advanced_metadata(self):
        meta = MetaAdvanced(
            expression="{ ids: input.items[*].id, total: input.items.sum($.price) }"
        )
        assert "ids:" in meta.expression

    def test_required_expression(self):
        with pytest.raises(ValidationError):
            MetaAdvanced()


class TestMetaReturn:
    def test_valid_return_metadata(self):
        meta = MetaReturn(
            payload_selector="{ answer: input.answer, steps: input.steps }",
            content_type=ContentType.json,
            status_code=200,
        )
        assert meta.payload_selector == "{ answer: input.answer, steps: input.steps }"
        assert meta.status_code == 200

    def test_status_code_validation(self):
        with pytest.raises(ValidationError):
            MetaReturn(payload_selector="input", status_code=99)

        with pytest.raises(ValidationError):
            MetaReturn(payload_selector="input", status_code=600)


class TestMetaWorkflowCall:
    def test_valid_workflow_call_metadata(self):
        meta = MetaWorkflowCall(
            workflow_id=42,
            input_mapping={"question": "input.user_question"},
            propagate_identity=True,
        )
        assert meta.workflow_id == 42
        assert meta.propagate_identity is True

    def test_workflow_id_validation(self):
        with pytest.raises(ValidationError):
            MetaWorkflowCall(workflow_id=0)

        with pytest.raises(ValidationError):
            MetaWorkflowCall(workflow_id=-1)

    def test_wait_validation(self):
        with pytest.raises(ValidationError):
            MetaWorkflowCall(workflow_id=1, wait="async")
