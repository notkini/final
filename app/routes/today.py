from flask import Blueprint, jsonify

from app.services.today_service import get_today

today_bp = Blueprint("today", __name__)


@today_bp.get("/api/today")
def today():
    return jsonify(get_today())