from datetime import datetime

from flask import Blueprint, jsonify, request
from werkzeug.exceptions import BadRequest

from app.services.history_service import (
    get_custom_history,
    get_history,
)

history_bp = Blueprint("history", __name__)


@history_bp.get("/api/history")
def history():

    range_type = request.args.get(
        "range",
        "7d",
    )

    if range_type in ("7d", "month", "year", "date"):

        year = request.args.get(
            "year",
            type=int,
        )

        month = request.args.get(
            "month",
            type=int,
        )

        selected_date = request.args.get("date")

        return jsonify(
            get_history(
                range_type=range_type,
                year=year,
                month=month,
                date=selected_date,
            )
        )

    elif range_type == "custom":

        machine_id = int(
            request.args.get("machine_id")
        )

        from_date = datetime.strptime(
            request.args.get("from_date"),
            "%Y-%m-%d",
        ).date()

        to_date = datetime.strptime(
            request.args.get("to_date"),
            "%Y-%m-%d",
        ).date()

        shifts = request.args.get(
            "shifts",
            "A,B,C",
        )

        return jsonify(
            get_custom_history(
                machine_id,
                from_date,
                to_date,
                shifts,
            )
        )

    raise BadRequest("Invalid history range")