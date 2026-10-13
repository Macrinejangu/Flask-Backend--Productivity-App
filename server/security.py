import secrets
from hmac import compare_digest

from flask import jsonify, request, session


def configure_security(app):
    @app.get("/csrf-token")
    def csrf_token():
        token = session.get("csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            session["csrf_token"] = token

        response = jsonify({"csrf_token": token})
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.before_request
    def protect_mutations():
        if not app.config.get("CSRF_ENABLED", True):
            return None

        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return None

        expected = session.get("csrf_token")
        supplied = request.headers.get("X-CSRF-Token")

        if (
            not isinstance(expected, str)
            or not isinstance(supplied, str)
            or not compare_digest(expected, supplied)
        ):
            return jsonify({"error": "Invalid or missing CSRF token."}), 403

    @app.after_request
    def prevent_private_response_caching(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response
    