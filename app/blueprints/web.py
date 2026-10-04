from flask import Blueprint, render_template
from flask_login import login_required

web_bp = Blueprint("web", __name__)


@web_bp.route("/")
@login_required
def index():
    return render_template("index.html")
