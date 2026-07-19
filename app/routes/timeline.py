from datetime import datetime

from flask import Blueprint, jsonify, request

from app.services.timeline_service import get_timeline

timeline_bp = Blueprint("timeline", __name__)


@timeline_bp.get("/api/timeline")
def timeline():

    date_str = request.args.get("date")

    selected_date = None

    if date_str:
        selected_date = datetime.strptime(
            date_str,
            "%Y-%m-%d",
        ).date()

    return jsonify(
        get_timeline(selected_date)
    )