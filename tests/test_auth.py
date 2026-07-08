"""Tests de autenticación."""
import pytest
from src.auth import AuthHandler


class TestAuth:
    def test_authenticates_admin(self):
        auth = AuthHandler(secret="test")
        user = auth.authenticate("admin@kavana.com", "admin123")
        assert user is not None
        assert user["role"] == "admin"

    def test_rejects_wrong_password(self):
        auth = AuthHandler(secret="test")
        user = auth.authenticate("admin@kavana.com", "wrong")
        assert user is None

    def test_rejects_unknown_user(self):
        auth = AuthHandler(secret="test")
        user = auth.authenticate("unknown@test.com", "pass")
        assert user is None

    def test_generates_and_verifies_token(self):
        auth = AuthHandler(secret="test-secret")
        user = {"email": "test@test.com", "name": "Test", "role": "operator"}
        token = auth.generate_token(user)
        assert token is not None
        assert len(token) > 10

    def test_accepts_dev_token(self):
        auth = AuthHandler(secret="test")
        user = auth.verify_token("dev-token-admin@kavana.com")
        assert user is not None
        assert user["email"] == "admin@kavana.com"
