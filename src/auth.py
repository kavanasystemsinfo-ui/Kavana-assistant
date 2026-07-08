"""Auth — JWT simple para el asistente (independiente de V3)."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    import jwt
except ImportError:
    jwt = None


class AuthHandler:
    """Autenticación con JWT.
    
    Independiente de V3. Cuando se integre con V3, se puede 
    reemplazar este módulo por el SSO de V3.
    """

    def __init__(self, secret: Optional[str] = None):
        self.secret = secret or os.getenv("JWT_SECRET", "kavana-assistant-dev-secret")
        self._users: dict[str, dict] = {}
        self._load_default_users()

    def _load_default_users(self):
        """Carga usuarios por defecto y de variables de entorno."""
        # Admin por defecto
        self._users["admin@kavana.com"] = {
            "email": "admin@kavana.com",
            "password": self._hash("admin123"),
            "name": "Admin KAVANA",
            "role": "admin",
        }
        # Cargar de variable de entorno (para producción)
        users_json = os.getenv("ASSISTANT_USERS", "")
        if users_json:
            try:
                for u in json.loads(users_json):
                    self._users[u["email"]] = {
                        "email": u["email"],
                        "password": self._hash(u["password"]),
                        "name": u.get("name", u["email"]),
                        "role": u.get("role", "operator"),
                    }
            except (json.JSONDecodeError, KeyError):
                pass

    def _hash(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def authenticate(self, email: str, password: str) -> Optional[dict]:
        user = self._users.get(email)
        if not user or user["password"] != self._hash(password):
            return None
        return {"email": user["email"], "name": user["name"], "role": user["role"]}

    def generate_token(self, user: dict) -> str:
        if jwt:
            payload = {
                **user,
                "exp": datetime.now(timezone.utc) + timedelta(days=7),
                "iat": datetime.now(timezone.utc),
            }
            return jwt.encode(payload, self.secret, algorithm="HS256")
        # Fallback sin jwt (dev)
        return f"dev-token-{user['email']}"

    def verify_token(self, token: str) -> Optional[dict]:
        if jwt:
            try:
                return jwt.decode(token, self.secret, algorithms=["HS256"])
            except jwt.PyJWTError:
                return None
        # Fallback dev
        if token.startswith("dev-token-"):
            email = token.replace("dev-token-", "")
            user = self._users.get(email)
            if user:
                return {"email": user["email"], "name": user["name"], "role": user["role"]}
        return None
