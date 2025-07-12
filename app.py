import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///skillswap.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize extensions
db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Import models after db initialization
with app.app_context():
    import models
    db.create_all()

# Routes
@app.route('/')
def index():
    from models import User
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 3  # Number of profiles per page
    
    # Exclude current user from the list
    base_query = User.query.filter(User.is_public == True, User.is_active == True)
    if current_user.is_authenticated:
        base_query = base_query.filter(User.id != current_user.id)
    
    if search_query:
        search_term = f"%{search_query}%"
        base_query = base_query.filter(User.skills_offered.ilike(search_term))
    
    # Paginate the results
    pagination = base_query.paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    users = pagination.items
    
    return render_template('index.html', 
                         users=users, 
                         search_query=search_query,
                         pagination=pagination)

@app.route('/register', methods=['GET', 'POST'])
def register():
    from models import User
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        full_name = request.form['full_name']
        gender = request.form.get('gender', '')
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validation
        if not username or not email or not full_name or not password:
            flash('All fields are required.', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'error')
            return render_template('register.html')
        
        # Create new user
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            gender=gender,
            password_hash=password_hash
        )
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    from models import User
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.is_active and bcrypt.check_password_hash(user.password_hash, password):
            # Update last login
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            if user and not user.is_active:
                flash('Your account has been deactivated. Please contact support.', 'error')
            else:
                flash('Invalid username or password.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    from models import SwapRequest
    
    # Get profile stats
    sent_requests = SwapRequest.query.filter_by(requester_id=current_user.id).count()
    received_requests = SwapRequest.query.filter_by(requested_user_id=current_user.id).count()
    accepted_swaps = SwapRequest.query.filter_by(requester_id=current_user.id, status='accepted').count()
    pending_requests = SwapRequest.query.filter_by(requested_user_id=current_user.id, status='pending').count()
    
    skills_offered_count = len([s.strip() for s in current_user.skills_offered.split(',') if s.strip()]) if current_user.skills_offered else 0
    skills_wanted_count = len([s.strip() for s in current_user.skills_wanted.split(',') if s.strip()]) if current_user.skills_wanted else 0
    
    return render_template('profile.html', 
                         sent_requests=sent_requests,
                         received_requests=received_requests,
                         accepted_swaps=accepted_swaps,
                         pending_requests=pending_requests,
                         skills_offered_count=skills_offered_count,
                         skills_wanted_count=skills_wanted_count)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        current_user.full_name = request.form['full_name']
        current_user.email = request.form['email']
        current_user.gender = request.form.get('gender', '')
        current_user.skills_offered = request.form['skills_offered']
        current_user.skills_wanted = request.form['skills_wanted']
        current_user.availability = request.form['availability']
        current_user.is_public = 'is_public' in request.form
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('edit_profile.html')

@app.route('/view_profile/<int:user_id>')
def view_profile(user_id):
    from models import User
    user = User.query.get_or_404(user_id)
    
    if not user.is_public and (not current_user.is_authenticated or current_user.id != user.id):
        flash('This profile is private.', 'error')
        return redirect(url_for('index'))
    
    return render_template('view_profile.html', user=user)

@app.route('/send_request/<int:user_id>', methods=['POST'])
@login_required
def send_request(user_id):
    from models import User, SwapRequest
    
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot send a request to yourself.', 'error')
        return redirect(url_for('view_profile', user_id=user_id))
    
    # Check if request already exists
    existing_request = SwapRequest.query.filter_by(
        requester_id=current_user.id,
        requested_user_id=user_id
    ).first()
    
    if existing_request:
        flash('You have already sent a request to this user.', 'error')
        return redirect(url_for('view_profile', user_id=user_id))
    
    offered_skill = request.form['offered_skill']
    requested_skill = request.form['requested_skill']
    
    if not offered_skill or not requested_skill:
        flash('Please specify both offered and requested skills.', 'error')
        return redirect(url_for('view_profile', user_id=user_id))
    
    swap_request = SwapRequest(
        requester_id=current_user.id,
        requested_user_id=user_id,
        offered_skill=offered_skill,
        requested_skill=requested_skill
    )
    
    db.session.add(swap_request)
    db.session.commit()
    
    flash('Swap request sent successfully!', 'success')
    return redirect(url_for('view_profile', user_id=user_id))

@app.route('/swap_requests')
@login_required
def swap_requests():
    from models import SwapRequest
    
    received_requests = SwapRequest.query.filter_by(requested_user_id=current_user.id).all()
    sent_requests = SwapRequest.query.filter_by(requester_id=current_user.id).all()
    
    return render_template('swap_requests.html', 
                         received_requests=received_requests,
                         sent_requests=sent_requests)

@app.route('/handle_request/<int:request_id>/<action>')
@login_required
def handle_request(request_id, action):
    from models import SwapRequest
    
    swap_request = SwapRequest.query.get_or_404(request_id)
    
    if swap_request.requested_user_id != current_user.id:
        flash('You are not authorized to handle this request.', 'error')
        return redirect(url_for('swap_requests'))
    
    if action == 'accept':
        swap_request.status = 'accepted'
        flash('Request accepted successfully!', 'success')
    elif action == 'reject':
        swap_request.status = 'rejected'
        flash('Request rejected.', 'info')
    elif action == 'delete':
        db.session.delete(swap_request)
        db.session.commit()
        flash('Request deleted.', 'info')
        return redirect(url_for('swap_requests'))
    
    db.session.commit()
    return redirect(url_for('swap_requests'))

@app.route('/delete_sent_request/<int:request_id>')
@login_required
def delete_sent_request(request_id):
    from models import SwapRequest
    
    swap_request = SwapRequest.query.get_or_404(request_id)
    
    if swap_request.requester_id != current_user.id:
        flash('You are not authorized to delete this request.', 'error')
        return redirect(url_for('swap_requests'))
    
    db.session.delete(swap_request)
    db.session.commit()
    flash('Request deleted.', 'info')
    return redirect(url_for('swap_requests'))

@app.route('/complete_swap/<int:request_id>')
@login_required
def complete_swap(request_id):
    from models import SwapRequest
    
    swap_request = SwapRequest.query.get_or_404(request_id)
    
    if swap_request.requested_user_id != current_user.id:
        flash('You are not authorized to complete this request.', 'error')
        return redirect(url_for('swap_requests'))
    
    swap_request.status = 'completed'
    db.session.commit()
    flash('Swap marked as completed! You can now rate each other.', 'success')
    return redirect(url_for('swap_requests'))

@app.route('/rate_user/<int:swap_request_id>', methods=['GET', 'POST'])
@login_required
def rate_user(swap_request_id):
    from models import SwapRequest, Rating
    
    swap_request = SwapRequest.query.get_or_404(swap_request_id)
    
    # Check if user is part of this swap
    if swap_request.requester_id != current_user.id and swap_request.requested_user_id != current_user.id:
        flash('You are not authorized to rate this swap.', 'error')
        return redirect(url_for('swap_requests'))
    
    # Check if swap is completed
    if swap_request.status != 'completed':
        flash('You can only rate completed swaps.', 'error')
        return redirect(url_for('swap_requests'))
    
    # Determine who to rate
    if swap_request.requester_id == current_user.id:
        rated_user_id = swap_request.requested_user_id
    else:
        rated_user_id = swap_request.requester_id
    
    # Check if already rated
    existing_rating = Rating.query.filter_by(
        rater_id=current_user.id,
        swap_request_id=swap_request_id
    ).first()
    
    if existing_rating:
        flash('You have already rated this swap.', 'error')
        return redirect(url_for('swap_requests'))
    
    if request.method == 'POST':
        rating = int(request.form['rating'])
        feedback = request.form.get('feedback', '')
        
        new_rating = Rating(
            rater_id=current_user.id,
            rated_user_id=rated_user_id,
            swap_request_id=swap_request_id,
            rating=rating,
            feedback=feedback
        )
        
        db.session.add(new_rating)
        db.session.commit()
        
        flash('Rating submitted successfully!', 'success')
        return redirect(url_for('swap_requests'))
    
    from models import User
    rated_user = User.query.get(rated_user_id)
    return render_template('rate_user.html', swap_request=swap_request, rated_user=rated_user)

@app.route('/leaderboard')
def leaderboard():
    from models import User, Rating
    from sqlalchemy import func
    
    # Get users with their average ratings, excluding users with no ratings
    users = db.session.query(User).join(Rating, User.id == Rating.rated_user_id)\
        .filter(User.is_public == True, User.is_active == True)\
        .group_by(User.id)\
        .order_by(func.avg(Rating.rating).desc())\
        .limit(50).all()
    
    return render_template('leaderboard.html', users=users)

# Admin routes
@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    from models import User, SwapRequest, Rating, Announcement
    
    # Get statistics
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    pending_swaps = SwapRequest.query.filter_by(status='pending').count()
    completed_swaps = SwapRequest.query.filter_by(status='completed').count()
    total_ratings = Rating.query.count()
    
    # Get recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    
    # Get active announcements
    announcements = Announcement.query.filter_by(is_active=True).order_by(Announcement.created_at.desc()).all()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         active_users=active_users,
                         pending_swaps=pending_swaps,
                         completed_swaps=completed_swaps,
                         total_ratings=total_ratings,
                         recent_users=recent_users,
                         announcements=announcements)

@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    from models import User
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/toggle_user_status/<int:user_id>')
@login_required
def admin_toggle_user_status(user_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    from models import User
    user = User.query.get_or_404(user_id)
    
    if user.is_admin:
        flash('Cannot modify admin user status.', 'error')
        return redirect(url_for('admin_users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.username} has been {status}.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/swaps')
@login_required
def admin_swaps():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    from models import SwapRequest
    status_filter = request.args.get('status', 'all')
    
    if status_filter == 'all':
        swaps = SwapRequest.query.order_by(SwapRequest.created_at.desc()).all()
    else:
        swaps = SwapRequest.query.filter_by(status=status_filter)\
            .order_by(SwapRequest.created_at.desc()).all()
    
    return render_template('admin/swaps.html', swaps=swaps, status_filter=status_filter)

@app.route('/admin/announcements', methods=['GET', 'POST'])
@login_required
def admin_announcements():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    from models import Announcement
    
    if request.method == 'POST':
        title = request.form['title']
        message = request.form['message']
        
        announcement = Announcement(
            title=title,
            message=message,
            created_by=current_user.id
        )
        
        db.session.add(announcement)
        db.session.commit()
        
        flash('Announcement created successfully!', 'success')
        return redirect(url_for('admin_announcements'))
    
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return render_template('admin/announcements.html', announcements=announcements)

@app.route('/admin/toggle_announcement/<int:announcement_id>')
@login_required
def admin_toggle_announcement(announcement_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    from models import Announcement
    announcement = Announcement.query.get_or_404(announcement_id)
    
    announcement.is_active = not announcement.is_active
    db.session.commit()
    
    status = 'activated' if announcement.is_active else 'deactivated'
    flash(f'Announcement has been {status}.', 'success')
    return redirect(url_for('admin_announcements'))

# Context processor for navbar notifications
@app.context_processor
def inject_notifications():
    if current_user.is_authenticated:
        from models import Announcement
        pending_count = current_user.get_pending_requests_count()
        active_announcements = Announcement.query.filter_by(is_active=True).all()
        return dict(pending_requests_count=pending_count, active_announcements=active_announcements)
    return dict(pending_requests_count=0, active_announcements=[])

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
