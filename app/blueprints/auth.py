import random
import string

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import limiter
from ..models import User, db

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form.get("username")).first()
        if user and user.check_password(request.form.get("password")):
            login_user(user)
            return redirect(url_for("web.index"))
        flash("Invalid credentials")
    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if User.query.filter_by(username=username).first():
            flash("Username exists")
            return redirect(url_for("auth.register"))

        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("web.index"))
    return render_template("register.html")


@auth_bp.route("/pair", methods=["POST"])
@login_required
def pair():
    code = request.form.get("pairing_code")
    if not code:
        # Generate code for current user
        new_code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        current_user.pairing_code = new_code
        db.session.commit()
    else:
        # Link to partner
        partner = User.query.filter_by(pairing_code=code).first()
        if partner and partner.id != current_user.id:
            current_user.partner_id = partner.id
            partner.partner_id = current_user.id
            current_user.pairing_code = None
            partner.pairing_code = None
            db.session.commit()
    return redirect(url_for("web.index"))


@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
