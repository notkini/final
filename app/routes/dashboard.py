from flask import Blueprint, render_template

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def dashboard():
    return render_template("dashboard.html")


@dashboard_bp.route("/setup")
def setup():
    return render_template("setup.html")


@dashboard_bp.route("/history")
def history():
    return render_template("history.html")


@dashboard_bp.route("/custom-history")
def custom_history():
    return render_template("custom_history.html")