from datetime import datetime, timedelta
import json
import math

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required
from pywebpush import WebPushException, webpush

from ..models import Post, PushSubscription, Reaction, User, db

api_bp = Blueprint("api", __name__)


# --- NOTIFICATION HELPER ---
def send_push_to_partner(title, body):
    if not current_user.partner_id:
        return
    subs = PushSubscription.query.filter_by(user_id=current_user.partner_id).all()
    for sub in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"auth": sub.keys_auth, "p256dh": sub.keys_p256dh},
                },
                data=json.dumps({"title": title, "body": body}),
                vapid_private_key=current_app.config["VAPID_PRIVATE_KEY"],
                vapid_claims={"sub": "mailto:admin@example.com"},
            )
        except WebPushException:
            db.session.delete(sub)  # Remove expired subscriptions
    db.session.commit()


# --- NEW ROUTE: SETTINGS ---
@api_bp.route("/settings", methods=["POST"])
@login_required
def update_settings():
    data = request.get_json()
    if data.get("username"):
        existing = User.query.filter_by(username=data["username"]).first()
        if existing and existing.id != current_user.id:
            return jsonify({"error": "Username taken"}), 400
        current_user.username = data["username"]
    if data.get("password"):
        current_user.set_password(data["password"])
    db.session.commit()
    return jsonify({"status": "success"})


# --- NEW ROUTE: PUSH SUBSCRIPTION ---
@api_bp.route("/subscribe", methods=["POST"])
@login_required
def subscribe():
    data = request.get_json()
    endpoint = data.get("endpoint")
    keys = data.get("keys", {})
    if not PushSubscription.query.filter_by(endpoint=endpoint).first():
        sub = PushSubscription(
            user_id=current_user.id,
            endpoint=endpoint,
            keys_auth=keys.get("auth"),
            keys_p256dh=keys.get("p256dh"),
        )
        db.session.add(sub)
        db.session.commit()
    return jsonify({"status": "success"})


# ... (Keep all existing routes like serialize_post, handle_widgets, get_main_feed exactly the same) ...
def haversine(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return 0
    R = 6371
    a = (
        math.sin(math.radians(lat2 - lat1) / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    )
    return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def serialize_post(p, is_reply=False):
    reaction_data = {}
    for r in p.reactions:
        if r.emoji not in reaction_data:
            reaction_data[r.emoji] = {"count": 0, "reacted_by_me": False}
        reaction_data[r.emoji]["count"] += 1
        if r.user_id == current_user.id:
            reaction_data[r.emoji]["reacted_by_me"] = True

    data = {
        "id": p.id,
        "sender": p.sender.username,
        "is_mine": p.sender_id == current_user.id,
        "is_secret": p.is_secret,
        "text_content": p.text_content,
        "media_data": p.media_data,
        "media_type": p.media_type,
        "time_iso": p.created_at.isoformat() + "Z",
        "time": p.created_at.strftime("%H:%M %b %d"),
        "reactions": reaction_data,
    }
    if not is_reply:
        sorted_replies = sorted(p.replies, key=lambda x: x.created_at)
        data["replies"] = [serialize_post(r, is_reply=True) for r in sorted_replies]
    return data


@api_bp.route("/widgets", methods=["GET", "POST"])
@login_required
def handle_widgets():
    partner = User.query.get(current_user.partner_id) if current_user.partner_id else None
    if request.method == "POST":
        data = request.get_json()
        if "lat" in data:
            current_user.lat, current_user.lng = data["lat"], data["lng"]
        if data.get("action") == "miss_you":
            current_user.miss_you_count += 1
            send_push_to_partner(
                "🥺 Miss You Ping!", f"{current_user.username} is thinking of you."
            )  # TRIGGER PUSH!
        if data.get("action") == "set_date" and data.get("date"):
            date_obj = datetime.strptime(data["date"], "%Y-%m-%d")
            current_user.meetup_date = date_obj
            if partner:
                partner.meetup_date = date_obj
        db.session.commit()
        return jsonify({"status": "updated"})
    distance = (
        haversine(current_user.lat, current_user.lng, partner.lat, partner.lng) if partner else 0
    )
    days_left = None
    if current_user.meetup_date:
        delta = (current_user.meetup_date - datetime.utcnow()).days
        days_left = delta if delta >= 0 else None
    return jsonify(
        {
            "distance_km": distance,
            "my_pings": current_user.miss_you_count,
            "partner_pings": partner.miss_you_count if partner else 0,
            "days_left": days_left,
        }
    )


@api_bp.route("/posts/feed", methods=["GET"])
@login_required
def get_main_feed():
    if not current_user.partner_id:
        return jsonify([])
    time_threshold = datetime.utcnow() - timedelta(hours=24)
    posts = (
        Post.query.filter(
            Post.parent_id.is_(None),
            Post.sender_id.in_([current_user.id, current_user.partner_id]),
            db.or_(
                Post.is_secret == False,
                db.and_(
                    Post.is_secret == True,
                    Post.sender_id == current_user.id,
                    Post.created_at >= time_threshold,
                ),
            ),
        )
        .order_by(Post.created_at.desc())
        .all()
    )
    return jsonify([serialize_post(p) for p in posts])


@api_bp.route("/posts/vault/count", methods=["GET"])
@login_required
def get_vault_count():
    if not current_user.partner_id:
        return jsonify({"count": 0})
    time_threshold = datetime.utcnow() - timedelta(hours=24)
    count = Post.query.filter(
        Post.sender_id == current_user.partner_id,
        Post.is_secret == True,
        Post.is_read == False,
        Post.created_at >= time_threshold,
    ).count()
    return jsonify({"count": count})


@api_bp.route("/posts/vault", methods=["GET"])
@login_required
def open_vault():
    if not current_user.partner_id:
        return jsonify([])
    time_threshold = datetime.utcnow() - timedelta(hours=24)
    secrets = (
        Post.query.filter(
            Post.parent_id.is_(None),
            Post.sender_id == current_user.partner_id,
            Post.is_secret == True,
            Post.created_at >= time_threshold,
        )
        .order_by(Post.created_at.desc())
        .all()
    )
    all_unread = Post.query.filter(
        Post.sender_id == current_user.partner_id, Post.is_secret == True, Post.is_read == False
    ).all()
    for s in all_unread:
        s.is_read = True
    db.session.commit()
    return jsonify([serialize_post(s) for s in secrets])


@api_bp.route("/posts", methods=["POST"])
@login_required
def create_post():
    data = request.get_json()
    parent_id = data.get("parent_id")
    is_secret = data.get("is_secret", False)
    if parent_id:
        parent = Post.query.get(parent_id)
        if parent and parent.is_secret:
            is_secret = True

    post = Post(
        sender_id=current_user.id,
        text_content=data.get("text_content"),
        media_data=data.get("media_data"),
        media_type=data.get("media_type"),
        is_secret=is_secret,
        parent_id=parent_id,
    )
    db.session.add(post)
    db.session.commit()

    # TRIGGER PUSH!
    if is_secret:
        send_push_to_partner("🤫 New Secret", f"{current_user.username} sent you a secret!")
    else:
        send_push_to_partner("✨ New Post", f"{current_user.username} shared something.")

    return jsonify({"status": "success"})


@api_bp.route("/posts/<int:post_id>", methods=["PUT", "DELETE"])
@login_required
def modify_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.sender_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    if request.method == "DELETE":
        db.session.delete(post)
        db.session.commit()
        return jsonify({"status": "deleted"})
    if request.method == "PUT":
        post.text_content = request.get_json().get("text_content")
        db.session.commit()
        return jsonify({"status": "updated"})


@api_bp.route("/posts/<int:post_id>/react", methods=["POST"])
@login_required
def toggle_reaction(post_id):
    emoji = request.get_json().get("emoji")
    existing = Reaction.query.filter_by(
        post_id=post_id, user_id=current_user.id, emoji=emoji
    ).first()
    if existing:
        db.session.delete(existing)
    else:
        db.session.add(Reaction(post_id=post_id, user_id=current_user.id, emoji=emoji))
    db.session.commit()
    return jsonify({"status": "success"})
