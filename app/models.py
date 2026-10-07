from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    partner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    pairing_code = db.Column(db.String(6), unique=True, nullable=True)

    # Widgets
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    miss_you_count = db.Column(db.Integer, default=0)
    meetup_date = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Reaction(db.Model):
    __tablename__ = "reactions"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    emoji = db.Column(db.String(10), nullable=False)


class Post(db.Model):
    __tablename__ = "posts"
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=True)  # For Replies

    text_content = db.Column(db.Text, nullable=True)
    media_data = db.Column(db.Text, nullable=True)
    media_type = db.Column(db.String(10), nullable=True)

    is_secret = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

    sender = db.relationship("User", foreign_keys=[sender_id])

    # NEW: This links replies directly to the parent post!
    replies = db.relationship(
        "Post", backref=db.backref("parent", remote_side=[id]), cascade="all, delete-orphan"
    )
    reactions = db.relationship("Reaction", backref="post", cascade="all, delete-orphan", lazy=True)

class PushSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    endpoint = db.Column(db.String(500), nullable=False)
    keys_auth = db.Column(db.String(100), nullable=False)
    keys_p256dh = db.Column(db.String(100), nullable=False)