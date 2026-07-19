from flask import Blueprint, jsonify, request

from app.services.machine_service import (
    assign_machine,
    get_machine_config,
    get_machines,
)

machine_bp = Blueprint("machine", __name__)


@machine_bp.get("/api/machines")
def machines():
    return jsonify(
        get_machines()
    )


@machine_bp.get("/api/machines/<int:machine_id>/config")
def machine_config(machine_id):
    return jsonify(
        get_machine_config(machine_id)
    )

@machine_bp.post("/api/machines/assign")
def assign():

    data = request.get_json()

    machine_id = data.get("machine_id")

    if machine_id is None:
        return (
            jsonify(
                {
                    "message": "machine_id is required"
                }
            ),
            400,
        )

    return jsonify(
        assign_machine(
            int(machine_id)
        )
    )