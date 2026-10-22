from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from models import db, AdminUser, ActivityLog

auth_bp = Blueprint("api_auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username_or_email = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username_or_email or not password:
        return jsonify({"success": False, "error": "Username/email and password are required"}), 400

    # Find user by username or email
    user = AdminUser.query.filter(
        (AdminUser.username == username_or_email) | (AdminUser.email == username_or_email)
    ).first()

    if not user or not user.check_password(password):
        # Log failed attempt
        ActivityLog.log(
            action="login_failed",
            details=f"Failed login attempt for '{username_or_email}'",
            ip_address=request.remote_addr,
        )
        return jsonify({"success": False, "error": "Invalid username or password"}), 401

    if not user.is_active_account:
        return jsonify({"success": False, "error": "This account has been deactivated"}), 403

    # Log in user
    login_user(user, remember=bool(data.get("remember", False)))
    user.last_login = datetime.utcnow()
    db.session.commit()

    ActivityLog.log(
        action="login_success",
        details=f"Admin '{user.username}' logged in successfully",
        user_id=user.id,
        ip_address=request.remote_addr,
    )

    return jsonify({
        "success": True,
        "message": "Login successful",
        "user": user.to_dict()
    })


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    username = current_user.username
    user_id = current_user.id
    logout_user()

    ActivityLog.log(
        action="logout",
        details=f"User '{username}' logged out",
        user_id=user_id,
        ip_address=request.remote_addr,
    )

    return jsonify({"success": True, "message": "Logged out successfully"})


@auth_bp.route("/me", methods=["GET"])
def get_current_user():
    if current_user.is_authenticated:
        return jsonify({
            "authenticated": True,
            "user": current_user.to_dict()
        })
    return jsonify({
        "authenticated": False,
        "user": None
    })
