from flask import Blueprint, jsonify

from app.services.status_service import get_machine_status

status_bp = Blueprint("status", __name__)


@status_bp.get("/api/status")
def status():
    return jsonify(get_machine_status())