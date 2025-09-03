import pytest
from app.services.templates import (
    extract_placeholders,
    validate_placeholders,
    validate_template,
    TEMPLATE_RE,
)


class TestExtractPlaceholders:
    def test_extract_simple_placeholders(self):
        """Test extracting simple placeholders."""
        text = "Hello {{base.name}}, your score is {{input.score}}"
        placeholders = extract_placeholders(text)
        assert placeholders == ["base.name", "input.score"]

    def test_extract_with_whitespace(self):
        """Test extracting placeholders with various whitespace."""
        text = "Hello {{ base.name }}, score: {{  input.score  }}"
        placeholders = extract_placeholders(text)
        assert placeholders == ["base.name", "input.score"]

    def test_extract_empty_text(self):
        """Test extracting from empty text."""
        placeholders = extract_placeholders("")
        assert placeholders == []

    def test_extract_no_placeholders(self):
        """Test text with no placeholders."""
        text = "Hello world, no placeholders here"
        placeholders = extract_placeholders(text)
        assert placeholders == []

    def test_extract_complex_expressions(self):
        """Test extracting complex JSONata expressions."""
        text = "Result: {{base.items[0].name}} and {{input.data.filter($$.type = 'active')}}"
        placeholders = extract_placeholders(text)
        assert placeholders == [
            "base.items[0].name",
            "input.data.filter($$.type = 'active')",
        ]

    def test_extract_empty_placeholder(self):
        """Test extracting empty placeholders."""
        text = "Empty: {{}} and valid: {{base.name}}"
        placeholders = extract_placeholders(text)
        assert placeholders == ["", "base.name"]


class TestValidatePlaceholders:
    def test_validate_valid_placeholders(self):
        """Test validation of valid placeholders."""
        placeholders = ["base.name", "input.score", "base.items[0]", "input.data.type"]
        result = validate_placeholders(placeholders)
        assert result == []

    def test_validate_empty_placeholder(self):
        """Test validation of empty placeholder."""
        placeholders = [""]
        result = validate_placeholders(placeholders)
        assert "Empty placeholder found: {{}}" in result

    def test_validate_unknown_root_warning(self):
        """Test validation warns about unknown roots."""
        placeholders = ["unknown.field", "custom.value"]
        result = validate_placeholders(placeholders)
        assert len(result) == 2
        assert "Unknown root in placeholder: {{unknown.field}}" in result[0]
        assert "Unknown root in placeholder: {{custom.value}}" in result[1]

    def test_validate_malformed_braces(self):
        """Test validation of malformed braces."""
        placeholders = ["base.{name}", "input.score}"]
        result = validate_placeholders(placeholders)
        assert len(result) == 2
        assert "Malformed placeholder" in result[0]
        assert "Malformed placeholder" in result[1]

    def test_validate_unclosed_brackets(self):
        """Test validation of unclosed brackets."""
        placeholders = ["base.items[0", "input.data[name]]"]
        result = validate_placeholders(placeholders)
        assert len(result) == 2
        assert "Unclosed brackets" in result[0]
        assert "Unclosed brackets" in result[1]

    def test_validate_unclosed_parentheses(self):
        """Test validation of unclosed parentheses."""
        placeholders = ["base.func(param", "input.calc(a, b))"]
        result = validate_placeholders(placeholders)
        assert len(result) == 2
        assert "Unclosed parentheses" in result[0]
        assert "Unclosed parentheses" in result[1]

    def test_validate_mixed_issues(self):
        """Test validation with multiple types of issues."""
        placeholders = ["", "unknown.field", "base.items[0", "input.{malformed}"]
        result = validate_placeholders(placeholders)
        assert len(result) == 4
        assert any("Empty placeholder" in msg for msg in result)
        assert any("Unknown root" in msg for msg in result)
        assert any("Unclosed brackets" in msg for msg in result)
        assert any("Malformed placeholder" in msg for msg in result)


class TestValidateTemplate:
    def test_validate_valid_template(self):
        """Test validation of a valid template."""
        prompt = "Hello {{base.name}}, your score is {{input.score}}"
        input_params = {"score": 95}

        result = validate_template(prompt, input_params)

        assert result["placeholders"] == ["base.name", "input.score"]
        assert result["warnings"] == []
        assert result["errors"] == []

    def test_validate_template_with_warnings(self):
        """Test validation with warnings."""
        prompt = "Hello {{custom.name}}, score: {{input.score}}"
        input_params = {"score": 95}

        result = validate_template(prompt, input_params)

        assert result["placeholders"] == ["custom.name", "input.score"]
        assert len(result["warnings"]) == 1
        assert "Unknown root in placeholder: {{custom.name}}" in result["warnings"][0]
        assert result["errors"] == []

    def test_validate_template_with_errors(self):
        """Test validation with errors."""
        prompt = "Hello {{}}, score: {{base.items[0}}"
        input_params = {}

        result = validate_template(prompt, input_params)

        assert result["placeholders"] == ["", "base.items[0"]
        assert result["warnings"] == []
        assert len(result["errors"]) == 2
        assert any("Empty placeholder" in msg for msg in result["errors"])
        assert any("Unclosed brackets" in msg for msg in result["errors"])

    def test_validate_template_with_warnings_and_errors(self):
        """Test validation with both warnings and errors."""
        prompt = "Hello {{custom.name}}, empty: {{}}, score: {{input.score}}"
        input_params = {"score": 95}

        result = validate_template(prompt, input_params)

        assert len(result["placeholders"]) == 3
        assert len(result["warnings"]) == 1
        assert len(result["errors"]) == 1
        assert "Unknown root" in result["warnings"][0]
        assert "Empty placeholder" in result["errors"][0]

    def test_validate_template_no_placeholders(self):
        """Test validation of template with no placeholders."""
        prompt = "Hello world, no placeholders here"
        input_params = {}

        result = validate_template(prompt, input_params)

        assert result["placeholders"] == []
        assert result["warnings"] == []
        assert result["errors"] == []


class TestTemplateRegex:
    def test_regex_pattern(self):
        """Test the template regex pattern directly."""
        text = "Hello {{base.name}} and {{ input.score }}"
        matches = TEMPLATE_RE.findall(text)
        # The regex already strips whitespace due to \s* in the pattern
        assert matches == ["base.name", "input.score"]

        # Test that extract_placeholders works the same way
        placeholders = extract_placeholders(text)
        assert placeholders == ["base.name", "input.score"]
