from urllib.parse import urlparse

from flask import abort
from flask_login import current_user


def require_project_access(project_key):
    """Call from a blueprint's before_request to gate an entire project
    behind its access-control key. Admins bypass this (see User.has_access).
    """
    if not current_user.is_authenticated or not current_user.has_access(project_key):
        abort(403)


def safe_redirect_target(target):
    """Only accept same-site relative paths for post-login redirects, to
    avoid an open redirect via a crafted ?next= value."""
    if not target or not target.startswith("/") or target.startswith("//"):
        return None
    parsed = urlparse(target)
    if parsed.netloc or parsed.scheme:
        return None
    return target
