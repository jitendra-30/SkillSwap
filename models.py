from app import db
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import func

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    gender = db.Column(db.String(20), default='')
    skills_offered = db.Column(db.Text, default='')
    skills_wanted = db.Column(db.Text, default='')
    availability = db.Column(db.Text, default='')
    is_public = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sent_requests = db.relationship('SwapRequest', 
                                  foreign_keys='SwapRequest.requester_id',
                                  backref='requester', lazy='dynamic')
    received_requests = db.relationship('SwapRequest', 
                                      foreign_keys='SwapRequest.requested_user_id',
                                      backref='requested_user', lazy='dynamic')
    given_ratings = db.relationship('Rating', 
                                   foreign_keys='Rating.rater_id',
                                   backref='rater', lazy='dynamic')
    received_ratings = db.relationship('Rating', 
                                      foreign_keys='Rating.rated_user_id',
                                      backref='rated_user', lazy='dynamic')
    
    def get_skills_offered_list(self):
        """Return skills offered as a list"""
        if not self.skills_offered:
            return []
        return [skill.strip() for skill in self.skills_offered.split(',') if skill.strip()]
    
    def get_skills_wanted_list(self):
        """Return skills wanted as a list"""
        if not self.skills_wanted:
            return []
        return [skill.strip() for skill in self.skills_wanted.split(',') if skill.strip()]
    
    def get_average_rating(self):
        """Calculate average rating for this user"""
        avg = db.session.query(func.avg(Rating.rating)).filter_by(rated_user_id=self.id).scalar()
        return round(avg, 1) if avg else 0.0
    
    def get_rating_count(self):
        """Get total number of ratings received"""
        return self.received_ratings.count()
    
    def get_completed_swaps_count(self):
        """Get number of completed swaps"""
        return SwapRequest.query.filter(
            db.or_(
                db.and_(SwapRequest.requester_id == self.id, SwapRequest.status == 'accepted'),
                db.and_(SwapRequest.requested_user_id == self.id, SwapRequest.status == 'accepted')
            )
        ).count()
    
    def get_pending_requests_count(self):
        """Get number of pending incoming requests"""
        return self.received_requests.filter_by(status='pending').count()
    
    def __repr__(self):
        return f'<User {self.username}>'

class SwapRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    requested_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    offered_skill = db.Column(db.String(200), nullable=False)
    requested_skill = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SwapRequest {self.id}: {self.offered_skill} for {self.requested_skill}>'

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rater_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rated_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    swap_request_id = db.Column(db.Integer, db.ForeignKey('swap_request.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    feedback = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Rating {self.id}: {self.rating} stars>'

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    creator = db.relationship('User', backref='announcements')
    
    def __repr__(self):
        return f'<Announcement {self.id}: {self.title}>'
