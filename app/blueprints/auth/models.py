import hashlib
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "auth_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    project_access = db.relationship(
        "UserProjectAccess",
        backref="user",
        cascade="all, delete-orphan",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        # Embeds a fingerprint of password_hash in Flask-Login's session
        # id, so a session created before a password reset stops
        # authenticating once the hash changes (see load_user in
        # app/__init__.py) — otherwise an admin-initiated password reset
        # wouldn't actually revoke an already-compromised session. Hashed
        # rather than sliced directly: werkzeug's hash strings start with a
        # fixed algorithm/params prefix (e.g. "scrypt:32768:8:1$..."), so a
        # raw prefix slice would be identical across different passwords —
        # hashing pulls in the salt further into the string instead.
        return f"{self.id}:{self._password_fingerprint()}"

    def _password_fingerprint(self):
        return hashlib.sha256(self.password_hash.encode()).hexdigest()[:16]

    def has_access(self, project_key):
        return self.is_admin or any(
            row.project_key == project_key for row in self.project_access
        )


class UserProjectAccess(db.Model):
    __tablename__ = "auth_user_project_access"
    __table_args__ = (
        db.UniqueConstraint("user_id", "project_key", name="uq_user_project_access"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("auth_users.id", ondelete="CASCADE"), nullable=False
    )
    project_key = db.Column(db.String(50), nullable=False)
