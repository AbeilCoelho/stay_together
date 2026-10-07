from flask import Blueprint, current_app, render_template, send_from_directory
from flask_login import login_required

web_bp = Blueprint("web", __name__)


@web_bp.route("/")
@login_required
def index():
    # Pass VAPID Public key to frontend for push subs
    return render_template("index.html", vapid_public_key=current_app.config["VAPID_PUBLIC_KEY"])


# Serve Service Worker from root scope
@web_bp.route("/sw.js")
def sw():
    return send_from_directory("static", "sw.js", mimetype="application/javascript")
