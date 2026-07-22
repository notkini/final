import base64
from datetime import datetime

from flask import (
    Blueprint,
    request,
    send_file,
)
from werkzeug.exceptions import BadRequest

from app.services.excel_export import create_excel_report
from app.services.pdf_export import create_pdf_report
from app.services.history_service import (
    get_custom_history,
    get_history,
)

export_bp = Blueprint("export", __name__)


@export_bp.get("/api/history/export/excel")
def export_excel():

    range_type = request.args.get(
        "range",
        "7d",
    )

    if range_type in ("7d", "month", "year", "date"):

        history = get_history(
            range_type=range_type,
            year=request.args.get("year", type=int),
            month=request.args.get("month", type=int),
            date=request.args.get("date"),
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

        history = get_custom_history(
            machine_id,
            from_date,
            to_date,
            shifts,
        )

    else:
        raise BadRequest("Invalid history range")

    workbook = create_excel_report(history)

    filename = f"History_{range_type}.xlsx"

    return send_file(
        workbook,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@export_bp.post("/api/history/export/pdf")
def export_pdf():

    payload = request.get_json()

    range_type = payload.get(
        "range",
        "7d",
    )

    if range_type in ("7d", "month", "year", "date"):

        history = get_history(
            range_type=range_type,
            year=payload.get("year"),
            month=payload.get("month"),
            date=payload.get("date"),
        )

    elif range_type == "custom":

        history = get_custom_history(
            machine_id=payload["machine_id"],
            from_date=datetime.strptime(
                payload["from_date"],
                "%Y-%m-%d",
            ).date(),
            to_date=datetime.strptime(
                payload["to_date"],
                "%Y-%m-%d",
            ).date(),
            shifts=payload.get(
                "shifts",
                "A,B,C",
            ),
        )

    else:
        raise BadRequest(
            "Invalid history range"
        )

    pdf = create_pdf_report(
        history,
        payload.get("uptime_chart"),
        payload.get("trend_chart"),
    )

    filename = f"History_{range_type}.pdf"

    return send_file(
        pdf,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )