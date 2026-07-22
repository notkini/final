import base64
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def format_duration(seconds):
    seconds = int(seconds or 0)

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    return f"{hours:02}:{minutes:02}:{seconds:02}"


def decode_chart(data_uri):
    """
    Converts a Chart.js base64 image into a ReportLab Image.
    """

    if not data_uri:
        return None

    if "," in data_uri:
        data_uri = data_uri.split(",", 1)[1]

    image_bytes = base64.b64decode(data_uri)

    image = BytesIO(image_bytes)

    reportlab_image = Image(
        image,
        width=6.5 * inch,
        height=3.6 * inch,
    )

    return reportlab_image


def create_summary_table(history):

    rows = [
        [
            "Weighted Efficiency",
            f'{history["weighted_efficiency_pct"]:.2f}%',
        ],
        [
            "Total Uptime",
            format_duration(
                history["total_uptime_seconds"]
            ),
        ],
        [
            "Total Downtime",
            format_duration(
                history["total_downtime_seconds"]
            ),
        ],
    ]

    table = Table(
        rows,
        colWidths=[3.2 * inch, 3.2 * inch],
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    return table


def create_pdf_report(
    history,
    uptime_chart,
    trend_chart,
):

    pdf = BytesIO()

    document = SimpleDocTemplate(
        pdf,
        rightMargin=20,
        leftMargin=20,
        topMargin=25,
        bottomMargin=25,
    )

    styles = getSampleStyleSheet()

    title = styles["Heading1"]
    title.alignment = TA_CENTER

    heading = styles["Heading2"]

    normal = styles["BodyText"]

    elements = []

    # ---------------------------------------------------
    # Header
    # ---------------------------------------------------

    elements.append(
        Paragraph(
            "<b>Machine Runtime Monitoring System</b>",
            title,
        )
    )

    elements.append(
        Paragraph(
            "Machine History Report",
            heading,
        )
    )

    elements.append(Spacer(1, 0.20 * inch))

    elements.append(
        Paragraph(
            f"<b>Machine:</b> {history['machine']}",
            normal,
        )
    )

    elements.append(
        Paragraph(
            f"<b>Period:</b> {history['from_date']} to {history['to_date']}",
            normal,
        )
    )

    elements.append(Spacer(1, 0.25 * inch))

    # ---------------------------------------------------
    # Summary
    # ---------------------------------------------------

    elements.append(
        Paragraph(
            "<b>Summary</b>",
            heading,
        )
    )

    elements.append(
        create_summary_table(history)
    )

    elements.append(
        Spacer(1, 0.30 * inch)
    )
        # ---------------------------------------------------
    # Charts
    # ---------------------------------------------------

    uptime_image = decode_chart(uptime_chart)

    if uptime_image:
        elements.append(
            Paragraph(
                "<b>Uptime vs Downtime</b>",
                heading,
            )
        )

        elements.append(uptime_image)

        elements.append(
            Spacer(1, 0.25 * inch)
        )

    trend_image = decode_chart(trend_chart)

    if trend_image:
        elements.append(
            Paragraph(
                "<b>Efficiency Trend</b>",
                heading,
            )
        )

        elements.append(trend_image)

        elements.append(
            Spacer(1, 0.30 * inch)
        )

    # ---------------------------------------------------
    # Daily Performance Table
    # ---------------------------------------------------

    elements.append(
        Paragraph(
            "<b>Daily Performance</b>",
            heading,
        )
    )

    daily_rows = [
        [
            "Date",
            "Uptime",
            "Downtime",
            "Efficiency (%)",
        ]
    ]

    for row in history["daily"]:

        daily_rows.append(
            [
                row["date"],
                format_duration(
                    row["uptime_seconds"]
                ),
                format_duration(
                    row["downtime_seconds"]
                ),
                f'{row["efficiency_pct"]:.2f}',
            ]
        )

    daily_table = Table(
        daily_rows,
        repeatRows=1,
    )

    daily_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1f4e78")),
                ("TEXTCOLOR",(0,0),(-1,0),colors.white),

                ("GRID",(0,0),(-1,-1),0.5,colors.grey),

                ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),

                ("ALIGN",(0,0),(-1,-1),"CENTER"),

                ("BOTTOMPADDING",(0,0),(-1,0),8),

                ("BACKGROUND",(0,1),(-1,-1),colors.whitesmoke),
            ]
        )
    )

    elements.append(daily_table)

    elements.append(
        Spacer(1,0.30*inch)
    )

    # ---------------------------------------------------
    # Shift Performance Table
    # ---------------------------------------------------

    elements.append(
        Paragraph(
            "<b>Shift Performance</b>",
            heading,
        )
    )

    shift_rows = [
        [
            "Date",
            "Shift",
            "Uptime",
            "Downtime",
            "Efficiency (%)",
            "Status",
        ]
    ]

    for row in history["shifts"]:

        shift_rows.append(
            [
                row["date"],
                row["shift"],
                format_duration(
                    row["uptime_seconds"]
                ),
                format_duration(
                    row["downtime_seconds"]
                ),
                f'{row["efficiency_pct"]:.2f}',
                "Final"
                if row["is_final"]
                else "In Progress",
            ]
        )

    shift_table = Table(
        shift_rows,
        repeatRows=1,
    )

    shift_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1f4e78")),
                ("TEXTCOLOR",(0,0),(-1,0),colors.white),

                ("GRID",(0,0),(-1,-1),0.5,colors.grey),

                ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),

                ("ALIGN",(0,0),(-1,-1),"CENTER"),

                ("BOTTOMPADDING",(0,0),(-1,0),8),

                ("BACKGROUND",(0,1),(-1,-1),colors.beige),
            ]
        )
    )

    elements.append(shift_table)

    elements.append(
        Spacer(1,0.25*inch)
    )

    # ---------------------------------------------------
    # Footer
    # ---------------------------------------------------

    elements.append(
        Paragraph(
            "Generated by Machine Runtime Monitoring System",
            normal,
        )
    )

    document.build(elements)

    pdf.seek(0)

    return pdf