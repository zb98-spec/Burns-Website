from urllib.parse import urlparse

from flask import abort
from flask_login import current_user


def require_project_access(project_key):
    """Call from a blueprint's before_request to gate an entire project
    behind its access-control key. Admins bypass this (see User.has_access).
    Assumes the global login gate in create_app() already ran, so the
    caller is always authenticated by this point.
    """
    if not current_user.has_access(project_key):
        abort(403)


def safe_redirect_target(target):
    """Only accept same-site relative paths for post-login redirects, to
    avoid an open redirect via a crafted ?next= value. Backslashes are
    rejected outright rather than normalized: browsers treat a leading
    "/\\" the same as "//" (a protocol-relative URL), which would
    otherwise slip past the "//" check below."""
    if not target or not target.startswith("/") or target.startswith("//"):
        return None
    if "\\" in target:
        return None
    parsed = urlparse(target)
    if parsed.netloc or parsed.scheme:
        return None
    return target
