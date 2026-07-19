from flask import Blueprint, jsonify, request

from app.services.config_service import (
    get_config,
    update_config,
)

config_bp = Blueprint("config", __name__)


@config_bp.get("/api/config")
def config_get():
    return jsonify(get_config())


@config_bp.post("/api/config")
def config_post():
    return jsonify(update_config(request.get_json()))