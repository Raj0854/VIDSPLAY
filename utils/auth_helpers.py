from functools import wraps
from flask import jsonify, request, redirect, url_for
from flask_login import current_user


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            # If API request
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Authentication required"}), 401
            # If web view
            return redirect(url_for("views.admin_login", next=request.url))

        if current_user.role not in ["admin", "superadmin", "editor"]:
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Insufficient privileges"}), 403
            return redirect(url_for("views.index"))

        return f(*args, **kwargs)

    return decorated_function
