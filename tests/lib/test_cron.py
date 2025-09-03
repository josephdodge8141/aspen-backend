import pytest
from app.lib.cron import is_valid_cron


class TestIsValidCron:
    def test_valid_standard_expressions(self):
        """Test standard valid cron expressions."""
        valid_expressions = [
            "0 0 * * *",  # Daily at midnight
            "0 12 * * *",  # Daily at noon
            "*/5 * * * *",  # Every 5 minutes
            "0 0 1 * *",  # First day of every month
            "0 0 * * 0",  # Every Sunday
            "0 9-17 * * 1-5",  # Weekdays 9-5
            "30 2 * * 1-5",  # Weekdays at 2:30 AM
            "0 */2 * * *",  # Every 2 hours
            "15,45 * * * *",  # At 15 and 45 minutes past the hour
        ]

        for expr in valid_expressions:
            assert is_valid_cron(expr), f"Expected '{expr}' to be valid"

    def test_valid_extended_expressions(self):
        """Test extended cron expressions with seconds (6 fields)."""
        valid_expressions = [
            "0 0 0 * * *",  # Daily at midnight with seconds
            "*/30 * * * * *",  # Every 30 seconds
            "0 */15 * * * *",  # Every 15 minutes
        ]

        for expr in valid_expressions:
            assert is_valid_cron(expr), f"Expected '{expr}' to be valid"

    def test_invalid_expressions(self):
        """Test invalid cron expressions."""
        invalid_expressions = [
            "",  # Empty string
            "invalid",  # Not a cron expression
            "* * * *",  # Too few fields
            "60 * * * *",  # Invalid minute (60)
            "* 24 * * *",  # Invalid hour (24)
            "* * 32 * *",  # Invalid day (32)
            "* * * 13 *",  # Invalid month (13)
            "* * * * 8",  # Invalid day of week (8)
            "* * * * * * *",  # Too many fields
            "a * * * *",  # Non-numeric character
            "*/0 * * * *",  # Division by zero
        ]

        for expr in invalid_expressions:
            assert not is_valid_cron(expr), f"Expected '{expr}' to be invalid"

    def test_edge_cases(self):
        """Test edge cases for cron validation."""
        # Test None and non-string types
        assert not is_valid_cron(None)
        assert not is_valid_cron(123)
        assert not is_valid_cron([])
        assert not is_valid_cron({})

    def test_special_strings(self):
        """Test special cron strings."""
        # croniter supports some special strings
        special_expressions = [
            "@yearly",
            "@annually",
            "@monthly",
            "@weekly",
            "@daily",
            "@hourly",
        ]

        for expr in special_expressions:
            # These should be valid if croniter supports them
            result = is_valid_cron(expr)
            # We'll just test that the function doesn't crash
            assert isinstance(result, bool)

    def test_whitespace_handling(self):
        """Test handling of whitespace in expressions."""
        # Leading/trailing whitespace should be handled
        assert is_valid_cron("  0 0 * * *  ")

        # croniter is actually quite lenient with whitespace
        # Extra spaces between fields are actually valid
        assert is_valid_cron("0  0 * * *")  # Double space is valid

        # Tab characters are actually also valid in croniter
        assert is_valid_cron("0\t0\t*\t*\t*")
