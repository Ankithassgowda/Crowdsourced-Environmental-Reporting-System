import pytz  # Import pytz for timezone handling
from datetime import datetime
from flask_pymongo import PyMongo
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId

mongo = PyMongo()

# Helper function to get current time in IST using pytz
def current_ist_time():
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist)

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.name = user_data['name']
        self.email = user_data['email']
        self.password_hash = user_data['password']
        self.is_admin = user_data.get('is_admin', False)
        # Ensure created_at is timezone-aware in IST
        self.created_at = user_data.get('created_at', current_ist_time())

    @staticmethod
    def find_by_email(email):
        user_data = mongo.db.users.find_one({'email': email})
        return User(user_data) if user_data else None
    
    @staticmethod
    def find_by_id(user_id):
        user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        return User(user_data) if user_data else None
    
    @staticmethod
    def create_user(name, email, password, is_admin=False):
        password_hash = generate_password_hash(password)
        user_data = {
            'name': name,
            'email': email,
            'password': password_hash,
            'is_admin': is_admin,
            # Ensure created_at is timezone-aware in IST
            'created_at': current_ist_time()
        }
        result = mongo.db.users.insert_one(user_data)
        user_data['_id'] = result.inserted_id
        return User(user_data)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Complaint:
    @staticmethod
    def create_complaint(user_id, issue_type, location, description, images, prediction_result):
        # Check if prediction matches issue type
        ai_prediction_match = False
        if prediction_result and len(prediction_result) > 0:
            predicted_class = prediction_result[0]['predicted_class']
            ai_prediction_match = predicted_class == issue_type
        
        complaint_data = {
            'user_id': ObjectId(user_id),
            'issue_type': issue_type,
            'location': location,
            'description': description,
            'images': images,
            'prediction_result': prediction_result,
            'ai_prediction_match': ai_prediction_match,
            'needs_manual_review': not ai_prediction_match,
            'status': 'Pending',
            # Ensure created_at and updated_at are timezone-aware in IST
            'created_at': current_ist_time(),
            'updated_at': current_ist_time(),
            'admin_notes': ''
        }
        result = mongo.db.complaints.insert_one(complaint_data)
        return result.inserted_id
    
    @staticmethod
    def get_complaints_by_type(issue_type):
        return list(mongo.db.complaints.find({'issue_type': issue_type}).sort('created_at', -1))
    
    @staticmethod
    def get_complaint_by_id(complaint_id):
        return mongo.db.complaints.find_one({'_id': ObjectId(complaint_id)})
    
    @staticmethod
    def update_complaint_status(complaint_id, status, admin_notes=''):
        mongo.db.complaints.update_one(
            {'_id': ObjectId(complaint_id)},
            {
                '$set': {
                    'status': status,
                    'admin_notes': admin_notes,
                    # Ensure updated_at is timezone-aware in IST
                    'updated_at': current_ist_time()
                }
            }
        )
    
    @staticmethod
    def get_user_complaints(user_id):
        return list(mongo.db.complaints.find({'user_id': ObjectId(user_id)}).sort('created_at', -1))
    
    @staticmethod
    def get_complaints_with_user_info():
        pipeline = [
            {
                '$lookup': {
                    'from': 'users',
                    'localField': 'user_id',
                    'foreignField': '_id',
                    'as': 'user_info'
                }
            },
            {
                '$unwind': '$user_info'
            },
            {
                '$sort': {'created_at': -1}
            }
        ]
        return list(mongo.db.complaints.aggregate(pipeline))
    
    @staticmethod
    def get_stats():
        pipeline = [
            {
                '$group': {
                    '_id': '$issue_type',
                    'count': {'$sum': 1}
                }
            }
        ]
        type_stats = list(mongo.db.complaints.aggregate(pipeline))
        
        status_pipeline = [
            {
                '$group': {
                    '_id': '$status',
                    'count': {'$sum': 1}
                }
            }
        ]
        status_stats = list(mongo.db.complaints.aggregate(status_pipeline))
        
        # Get prediction mismatch stats
        mismatch_pipeline = [
            {
                '$group': {
                    '_id': '$needs_manual_review',
                    'count': {'$sum': 1}
                }
            }
        ]
        mismatch_stats = list(mongo.db.complaints.aggregate(mismatch_pipeline))
        
        return {
            'type_stats': {item['_id']: item['count'] for item in type_stats},
            'status_stats': {item['_id']: item['count'] for item in status_stats},
            'mismatch_stats': {item['_id']: item['count'] for item in mismatch_stats}
        }
