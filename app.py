from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import os
from config import Config
from models import mongo, User, Complaint
from utils import load_model, predict_image, save_uploaded_file
from datetime import datetime
from geopy.geocoders import Nominatim

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
mongo.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Load ML model
model, device = load_model()

@login_manager.user_loader
def load_user(user_id):
    return User.find_by_id(user_id)

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Create admin user on first run
def create_admin():
    try:
        admin = User.find_by_email('admin@environmental.com')
        if not admin:
            User.create_user('Admin', 'admin@environmental.com', 'admin123', is_admin=True)
            print("Admin user created: admin@environmental.com / admin123")
    except Exception as e:
        print(f"Error creating admin user: {e}")

# Call create_admin on startup
with app.app_context():
    create_admin()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Validate inputs
        if not name or not email or not password:
            flash('All fields are required.', 'error')
            return redirect(url_for('register'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return redirect(url_for('register'))
        
        if User.find_by_email(email):
            flash('Email already exists. Please use a different email.', 'error')
            return redirect(url_for('register'))
        
        try:
            user = User.create_user(name, email, password)
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Registration failed. Please try again.', 'error')
            print(f"Registration error: {e}")
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Email and password are required.', 'error')
            return redirect(url_for('login'))
        
        try:
            user = User.find_by_email(email)
            if user and user.check_password(password):
                login_user(user)
                next_page = request.args.get('next')
                if user.is_admin:
                    flash(f'Welcome back, Admin {user.name}!', 'success')
                    return redirect(url_for('dashboard'))
                flash(f'Welcome back, {user.name}!', 'success')
                return redirect(next_page) if next_page else redirect(url_for('index'))
            else:
                flash('Invalid email or password.', 'error')
        except Exception as e:
            flash('Login failed. Please try again.', 'error')
            print(f"Login error: {e}")
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    user_name = current_user.name
    logout_user()
    flash(f'Goodbye {user_name}! You have been logged out successfully.', 'success')
    return redirect(url_for('index'))

@app.route('/complaint', methods=['GET', 'POST'])
@login_required
def complaint():
    if request.method == 'POST':
        issue_type = request.form.get('issue_type')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        description = request.form.get('description')

        if not issue_type or not latitude or not longitude or not description:
            flash('All fields are required, including location selection.', 'error')
            return redirect(url_for('complaint'))

        try:
            geolocator = Nominatim(user_agent="environmental_app")
            location = geolocator.reverse((latitude, longitude), exactly_one=True)
            address = location.address if location else f"Lat: {latitude}, Lon: {longitude}"
        except Exception as e:
            print(f"Geocoding error: {e}")
            address = f"Lat: {latitude}, Lon: {longitude}"
        
        # Validate inputs
        if len(description.strip()) < 10:
            flash('Please provide a more detailed description (at least 10 characters).', 'error')
            return redirect(url_for('complaint'))
        
        # Handle file uploads
        uploaded_files = request.files.getlist('images')
        
        # Filter out empty files
        uploaded_files = [f for f in uploaded_files if f.filename != '']
        
        if len(uploaded_files) < 3 or len(uploaded_files) > 5:
            flash('Please upload between 3 and 5 images.', 'error')
            return redirect(url_for('complaint'))
        
        saved_files = []
        predictions = []
        
        try:
            for file in uploaded_files:
                if file and file.filename != '':
                    filename = save_uploaded_file(file, app.config['UPLOAD_FOLDER'])
                    if filename:
                        saved_files.append(filename)
                        
                        # Predict image if model is available
                        if model:
                            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                            prediction = predict_image(filepath, model, device)
                            if prediction:
                                predictions.append(prediction)
                        else:
                            # If no model available, add default prediction
                            predictions.append({
                                'predicted_class': issue_type,
                                'confidence': 0.0,
                                'all_probabilities': {issue_type: 0.0}
                            })
            
            if len(saved_files) != len(uploaded_files):
                # Clean up uploaded files if there was an error
                for filename in saved_files:
                    try:
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    except:
                        pass
                flash('Some files could not be uploaded. Please check file formats and try again.', 'error')
                return redirect(url_for('complaint'))
            
            # Create complaint
            complaint_id = Complaint.create_complaint(
                current_user.id,
                issue_type,
                address,
                description.strip(),
                saved_files,
                predictions
            )
            
            flash('Complaint submitted successfully! Our team will review it soon. You can track its progress in "My Complaints".', 'success')
            return redirect(url_for('my_complaints'))
            
        except Exception as e:
            # Clean up uploaded files if there was an error
            for filename in saved_files:
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                except:
                    pass
            flash('Error submitting complaint. Please try again.', 'error')
            print(f"Complaint submission error: {e}")
    
    return render_template('complaint.html')

@app.route('/my_complaints')
@login_required
def my_complaints():
    try:
        complaints = Complaint.get_user_complaints(current_user.id)
        return render_template('my_complaints.html', complaints=complaints)
    except Exception as e:
        flash('Error loading your complaints.', 'error')
        print(f"My complaints error: {e}")
        return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    try:
        stats = Complaint.get_stats()
        return render_template('dashboard.html', stats=stats)
    except Exception as e:
        flash('Error loading dashboard.', 'error')
        print(f"Dashboard error: {e}")
        return redirect(url_for('index'))

@app.route('/admin/cutting_trees')
@login_required
def admin_cutting_trees():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    try:
        complaints = Complaint.get_complaints_by_type('cutting_trees')
        # Add user info to complaints
        for complaint in complaints:
            user = User.find_by_id(str(complaint['user_id']))
            complaint['user_name'] = user.name if user else 'Unknown User'
            complaint['user_email'] = user.email if user else 'Unknown Email'
        return render_template('admin_cutting_trees.html', complaints=complaints)
    except Exception as e:
        flash('Error loading complaints.', 'error')
        print(f"Admin cutting trees error: {e}")
        return redirect(url_for('dashboard'))

@app.route('/admin/garbage')
@login_required
def admin_garbage():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    try:
        complaints = Complaint.get_complaints_by_type('garbage')
        # Add user info to complaints
        for complaint in complaints:
            user = User.find_by_id(str(complaint['user_id']))
            complaint['user_name'] = user.name if user else 'Unknown User'
            complaint['user_email'] = user.email if user else 'Unknown Email'
        return render_template('admin_garbage.html', complaints=complaints)
    except Exception as e:
        flash('Error loading complaints.', 'error')
        print(f"Admin garbage error: {e}")
        return redirect(url_for('dashboard'))

@app.route('/admin/polluted_water')
@login_required
def admin_polluted_water():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    try:
        complaints = Complaint.get_complaints_by_type('polluted_water')
        # Add user info to complaints
        for complaint in complaints:
            user = User.find_by_id(str(complaint['user_id']))
            complaint['user_name'] = user.name if user else 'Unknown User'
            complaint['user_email'] = user.email if user else 'Unknown Email'
        return render_template('admin_polluted_water.html', complaints=complaints)
    except Exception as e:
        flash('Error loading complaints.', 'error')
        print(f"Admin polluted water error: {e}")
        return redirect(url_for('dashboard'))

@app.route('/update_complaint_status', methods=['POST'])
@login_required
def update_complaint_status():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied. Admin privileges required.'})
    
    try:
        complaint_id = request.form.get('complaint_id')
        status = request.form.get('status')
        admin_notes = request.form.get('admin_notes', '').strip()
        
        if not complaint_id:
            return jsonify({'success': False, 'message': 'Complaint ID is required.'})
        
        if not status:
            return jsonify({'success': False, 'message': 'Status is required.'})
        
        # Validate status
        valid_statuses = ['Pending', 'Under-review', 'Resolved', 'Rejected']
        if status not in valid_statuses:
            return jsonify({'success': False, 'message': 'Invalid status provided.'})
        
        # Check if complaint exists
        complaint = Complaint.get_complaint_by_id(complaint_id)
        if not complaint:
            return jsonify({'success': False, 'message': 'Complaint not found.'})
        
        # Add admin info to notes if not already present
        if admin_notes and not admin_notes.startswith(f"[{current_user.name}]"):
            admin_notes = f"[{current_user.name} - {datetime.now().strftime('%Y-%m-%d %H:%M')}]: {admin_notes}"
        
        Complaint.update_complaint_status(complaint_id, status, admin_notes)
        
        return jsonify({
            'success': True, 
            'message': f'Complaint status updated to "{status}" successfully.',
            'new_status': status
        })
        
    except Exception as e:
        print(f"Update status error: {e}")
        return jsonify({'success': False, 'message': 'An error occurred while updating the status.'})

@app.route('/delete_complaint/<complaint_id>', methods=['POST'])
@login_required
def delete_complaint(complaint_id):
    try:
        complaint = Complaint.get_complaint_by_id(complaint_id)
        if not complaint:
            return jsonify({'success': False, 'message': 'Complaint not found.'}), 404

        # Authorization check
        is_owner = str(complaint['user_id']) == current_user.id
        is_admin = current_user.is_admin

        # User can delete their own pending complaints, Admins can delete any.
        if not (is_admin or (is_owner and complaint['status'] == 'Pending')):
            return jsonify({'success': False, 'message': 'You are not authorized to delete this complaint.'}), 403

        # Delete associated images
        for image in complaint.get('images', []):
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image))
            except Exception as e:
                print(f"Error deleting image {image}: {e}") # Log error but continue

        # Delete complaint from database
        mongo.db.complaints.delete_one({'_id': complaint['_id']})

        return jsonify({'success': True, 'message': 'Complaint deleted successfully.'})

    except Exception as e:
        print(f"Delete complaint error: {e}")
        return jsonify({'success': False, 'message': 'An error occurred while deleting the complaint.'}), 500

@app.route('/api/stats')
@login_required
def api_stats():
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        stats = Complaint.get_stats()
        return jsonify(stats)
    except Exception as e:
        print(f"API stats error: {e}")
        return jsonify({'error': 'Failed to fetch statistics'}), 500

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'model_loaded': model is not None
    })

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

@app.errorhandler(413)
def too_large(error):
    flash('File too large. Please upload files smaller than 16MB.', 'error')
    return redirect(request.url)

# Context processor to make utility functions available in templates
@app.context_processor
def utility_processor():
    def format_datetime(dt):
        if dt:
            return dt.strftime('%B %d, %Y at %I:%M %p')
        return 'Unknown'
    
    def format_date(dt):
        if dt:
            return dt.strftime('%B %d, %Y')
        return 'Unknown'
    
    def get_status_color(status):
        colors = {
            'Pending': 'danger',
            'Under-review': 'warning',
            'Resolved': 'success',
            'Rejected': 'secondary'
        }
        return colors.get(status, 'secondary')
    
    def get_issue_icon(issue_type):
        icons = {
            'cutting_trees': 'fas fa-tree',
            'garbage': 'fas fa-trash',
            'polluted_water': 'fas fa-water'
        }
        return icons.get(issue_type, 'fas fa-exclamation-triangle')
    
    return dict(
        format_datetime=format_datetime,
        format_date=format_date,
        get_status_color=get_status_color,
        get_issue_icon=get_issue_icon
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)