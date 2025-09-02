import pytest
from app.security.passwords import hash_password, verify_password


def test_hash_password_returns_string():
    result = hash_password("test_password")
    assert isinstance(result, str)
    assert len(result) > 0


def test_hash_password_different_for_same_input():
    password = "test_password"
    hash1 = hash_password(password)
    hash2 = hash_password(password)
    assert hash1 != hash2


def test_verify_password_correct():
    password = "test_password"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True


def test_verify_password_incorrect():
    password = "test_password"
    wrong_password = "wrong_password"
    hashed = hash_password(password)
    assert verify_password(wrong_password, hashed) is False


def test_hash_verify_round_trip():
    passwords = [
        "simple",
        "Complex!Password123",
        "with spaces and symbols @#$%",
        "unicode_test_ñ_emoji_🔑",
        "reasonably_long_password_but_not_extreme",
    ]
    
    for password in passwords:
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
        assert verify_password(password + "_wrong", hashed) is False


def test_empty_password():
    password = ""
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True
    assert verify_password("not_empty", hashed) is False 