import pytest
from app.security.apikeys import generate_api_key, hash_api_key


def test_generate_api_key_format():
    plaintext_key, api_key_hash, last4 = generate_api_key()
    
    assert plaintext_key.startswith("sk-")
    assert len(plaintext_key) >= 43  # "sk-" + 32 base64url chars (min)
    assert isinstance(api_key_hash, str)
    assert len(api_key_hash) == 64  # SHA256 hex digest
    assert isinstance(last4, str)
    assert len(last4) == 4
    assert plaintext_key.endswith(last4)


def test_generate_api_key_uniqueness():
    key1, hash1, last4_1 = generate_api_key()
    key2, hash2, last4_2 = generate_api_key()
    
    assert key1 != key2
    assert hash1 != hash2
    assert last4_1 != last4_2 or key1[-4:] != key2[-4:]


def test_hash_api_key_deterministic():
    plaintext = "sk-test_api_key_123"
    hash1 = hash_api_key(plaintext)
    hash2 = hash_api_key(plaintext)
    
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex digest
    assert isinstance(hash1, str)


def test_hash_api_key_different_inputs():
    key1 = "sk-test_key_1"
    key2 = "sk-test_key_2"
    
    hash1 = hash_api_key(key1)
    hash2 = hash_api_key(key2)
    
    assert hash1 != hash2


def test_generate_api_key_high_entropy():
    keys = [generate_api_key()[0] for _ in range(100)]
    
    # All keys should be unique
    assert len(set(keys)) == 100
    
    # All keys should have proper format
    for key in keys:
        assert key.startswith("sk-")
        assert len(key) >= 43


def test_hash_consistency_with_generate():
    plaintext_key, generated_hash, last4 = generate_api_key()
    manual_hash = hash_api_key(plaintext_key)
    
    assert generated_hash == manual_hash
    assert plaintext_key[-4:] == last4 