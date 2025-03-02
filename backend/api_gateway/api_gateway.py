#!/usr/bin/env python3
"""api_gateway.py - API Gateway for the News Aggregator Backend
This Flask application aggregates endpoints from various microservices.
"""

from flask import Blueprint, Flask, jsonify, request, make_response
from flask_cors import CORS
from flask_restx import Api, Resource, fields, Namespace
import sys
import os
import jwt
import json
import uuid
import datetime
from datetime import datetime, timedelta
from functools import wraps
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

print("[DEBUG] [api_gateway] [startup] API Gateway starting up...")

# load env
from dotenv import load_dotenv
load_dotenv()
print("[DEBUG] [api_gateway] [startup] Environment variables loaded")

from backend.microservices.summarization_service import run_summarization, process_articles
from backend.microservices.news_fetcher import fetch_news
from backend.core.config import Config
from backend.core.utils import setup_logger, log_exception
from backend.microservices.auth_service import load_users
from backend.microservices.news_storage import store_article_in_supabase, log_user_search, add_bookmark, get_user_bookmarks, delete_bookmark

# Initialize logger
logger = setup_logger(__name__)
print("[DEBUG] [api_gateway] [startup] Logger initialized")

# Initialize Flask app with CORS support
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key')  # Change this in production
print("[DEBUG] [api_gateway] [startup] Flask app initialized with secret key")

# Improved CORS configuration to handle preflight requests properly
CORS(app, 
     origins=["http://localhost:5173", "http://localhost:5001"], 
     supports_credentials=True, 
     allow_headers=["Content-Type", "Authorization"], 
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
print("[DEBUG] [api_gateway] [startup] CORS configured")

# Initialize Flask-RestX
api = Api(app, version='1.0', title='News Aggregator API',
          description='A news aggregation and summarization API')
print("[DEBUG] [api_gateway] [startup] Flask-RestX API initialized")

# Define namespaces
news_ns = api.namespace('api/news', description='News operations')
health_ns = api.namespace('health', description='Health check operations')
summarize_ns = api.namespace('summarize', description='Text summarization operations')
user_ns = api.namespace('api/user', description='User operations')
auth_ns = api.namespace('api/auth', description='Authentication operations')
bookmark_ns = api.namespace('api/bookmarks', description='Bookmark operations')
story_tracking_ns = api.namespace('api/story_tracking', description='Story tracking operations')
print("[DEBUG] [api_gateway] [startup] API namespaces defined")

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        print("[DEBUG] [api_gateway] [token_required] Checking token in request")
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            print("[DEBUG] [api_gateway] [token_required] Authorization header missing")
            return {'error': 'Authorization header missing'}, 401
        try:
            token = auth_header.split()[1]
            print(f"[DEBUG] [api_gateway] [token_required] Decoding token: {token[:10]}...")
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'],audience='authenticated')
            print(f"[DEBUG] [api_gateway] [token_required] Token decoded successfully, user: {payload.get('sub', 'unknown')}")

            return f(*args, **kwargs)
        except Exception as e:
            print(f"[DEBUG] [api_gateway] [token_required] Token validation error: {str(e)}")
            return {'error': 'Invalid token', 'message': str(e)}, 401
    return decorated

# Define models for documentation
article_model = api.model('Article', {
    'article_text': fields.String(required=True, description='The text to summarize')
})

user_profile_model = api.model('UserProfile', {
    'id': fields.String(description='User ID'),
    'username': fields.String(description='Username'),
    'email': fields.String(description='Email address'),
    'firstName': fields.String(description='First name'),
    'lastName': fields.String(description='Last name'),
    'avatarUrl': fields.String(description='URL to user avatar')
})

# Model for user signup
signup_model = api.model('Signup', {
    'username': fields.String(required=True, description='Username'),
    'password': fields.String(required=True, description='Password'),
    'email': fields.String(required=True, description='Email address'),
    'firstName': fields.String(required=False, description='First name'),
    'lastName': fields.String(required=False, description='Last name')
})

print("[DEBUG] [api_gateway] [startup] API models defined")

# Health check endpoint
@health_ns.route('/')
class HealthCheck(Resource):
    def get(self):
        """Check if API Gateway is healthy"""
        print("[DEBUG] [api_gateway] [health_check] Called")
        return {"status": "API Gateway is healthy"}, 200

# Summarization endpoint
@summarize_ns.route('/')
class Summarize(Resource):
    @summarize_ns.expect(article_model)
    def post(self):
        """Summarize the given article text"""
        print("[DEBUG] [api_gateway] [summarize] Called")
        data = request.get_json()
        article_text = data.get('article_text', '')
        print(f"[DEBUG] [api_gateway] [summarize] Summarizing text of length: {len(article_text)}")
        summary = run_summarization(article_text)
        print(f"[DEBUG] [api_gateway] [summarize] Summarization complete, summary length: {len(summary)}")
        return {"summary": summary}, 200

@news_ns.route('/fetch')
class NewsFetch(Resource):
    @news_ns.param('keyword', 'Search keyword for news')
    @news_ns.param('user_id', 'User ID for logging search history')
    @news_ns.param('session_id', 'Session ID for tracking requests')
    def get(self):
        """
        Fetch news articles, store them in Supabase, and log user search history if a user ID is provided.
        """
        try:
            keyword = request.args.get('keyword', '')
            user_id = request.args.get('user_id')  # optional
            session_id = request.args.get('session_id')
            print(f"[DEBUG] [api_gateway] [news_fetch] Called with keyword: '{keyword}', user_id: {user_id}, session_id: {session_id}")

            print(f"[DEBUG] [api_gateway] [news_fetch] Fetching news articles for keyword: '{keyword}'")
            articles = fetch_news(keyword)  # This returns a list of articles.
            print(f"[DEBUG] [api_gateway] [news_fetch] Found {len(articles) if articles else 0} articles")
            stored_article_ids = []

            for article in articles:
                print(f"[DEBUG] [api_gateway] [news_fetch] Storing article: {article.get('title', 'No title')}")
                article_id = store_article_in_supabase(article)
                stored_article_ids.append(article_id)
                print(f"[DEBUG] [api_gateway] [news_fetch] Stored article with ID: {article_id}")

                if user_id:
                    print(f"[DEBUG] [api_gateway] [news_fetch] Logging search for user {user_id}, article {article_id}")
                    log_user_search(user_id, article_id, session_id)

            print(f"[DEBUG] [api_gateway] [news_fetch] Returning {len(stored_article_ids)} article IDs")
            return make_response(jsonify({
                'status': 'success',
                'data': stored_article_ids
            }), 200)

        except Exception as e:
            print(f"[DEBUG] [api_gateway] [news_fetch] Error: {str(e)}")
            return make_response(jsonify({
                'status': 'error',
                'message': str(e)
            }), 500)


# News processing endpoint
@news_ns.route('/process')
class NewsProcess(Resource):
    @news_ns.param('session_id', 'Session ID for tracking requests')
    def post(self):
        """Process and summarize articles"""
        try:
            session_id = request.args.get('session_id')
            print(f"[DEBUG] [api_gateway] [news_process] Called with session_id: {session_id}")
            print("[DEBUG] [api_gateway] [news_process] Processing articles...")
            summarized_articles = process_articles(session_id)
            print(f"[DEBUG] [api_gateway] [news_process] Processed {len(summarized_articles) if summarized_articles else 0} articles")
            return {
                'status': 'success',
                'message': 'Articles processed and summarized successfully',
                'data' : summarized_articles,
                'session_id': session_id
            }, 200
        except Exception as e:
            print(f"[DEBUG] [api_gateway] [news_process] Error: {str(e)}")
            logger.error(f"Error processing articles: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }, 500

# User authentication endpoints
@auth_ns.route('/signup')
class Signup(Resource):
    @auth_ns.expect(signup_model)
    def post(self):
        """Register a new user"""
        print("[DEBUG] [api_gateway] [signup] User signup endpoint called")
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        firstName = data.get('firstName', '')
        lastName = data.get('lastName', '')
        print(f"[DEBUG] [api_gateway] [signup] Request for username: {username}, email: {email}")

        if not username or not password or not email:
            print("[DEBUG] [api_gateway] [signup] Validation failed: missing required fields")
            return {'error': 'Username, password, and email are required'}, 400

        users = load_users()
        print(f"[DEBUG] [api_gateway] [signup] Loaded {len(users)} existing users")

        # Check if username already exists
        if any(u.get('username') == username for u in users):
            print(f"[DEBUG] [api_gateway] [signup] Username {username} already exists")
            return {'error': 'Username already exists'}, 400

        # Create new user with unique ID
        new_user = {
            'id': str(uuid.uuid4()),
            'username': username,
            'password': password,
            'email': email,
            'firstName': firstName,
            'lastName': lastName
        }
        print(f"[DEBUG] [api_gateway] [signup] Created new user with ID: {new_user['id']}")
        
        users.append(new_user)

        try:
            # Save updated users list
            print("[DEBUG] [api_gateway] [signup] Saving updated users list")
            with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'users.txt'), 'w') as f:
                json.dump(users, f, indent=4)
            print("[DEBUG] [api_gateway] [signup] Users list saved successfully")
        except Exception as e:
            print(f"[DEBUG] [api_gateway] [signup] Error saving user data: {str(e)}")
            return {'error': 'Failed to save user data', 'message': str(e)}, 500

        # Generate JWT token
        print("[DEBUG] [api_gateway] [signup] Generating JWT token")
        token = jwt.encode({
            'id': new_user['id'],
            'username': new_user['username'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        print(f"[DEBUG] [api_gateway] [signup] Token generated: {token[:10]}...")

        # Exclude password from response
        user_data = {k: new_user[k] for k in new_user if k != 'password'}
        print("[DEBUG] [api_gateway] [signup] Signup successful")
        return {'message': 'User registered successfully', 'user': user_data, 'token': token}, 201

@auth_ns.route('/login')
class Login(Resource):
    def post(self):
        """Login and get authentication token"""
        print("[DEBUG] [api_gateway] [login] Login endpoint called")
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        print(f"[DEBUG] [api_gateway] [login] Login attempt for username: {username}")
        
        if not username or not password:
            print("[DEBUG] [api_gateway] [login] Validation failed: missing username or password")
            return {'error': 'Username and password are required'}, 400
        
        users = load_users()
        print(f"[DEBUG] [api_gateway] [login] Loaded {len(users)} users")
        user = next((u for u in users if u.get('username') == username and u.get('password') == password), None)
        
        if not user:
            print(f"[DEBUG] [api_gateway] [login] Invalid credentials for username: {username}")
            return {'error': 'Invalid credentials'}, 401
        
        print(f"[DEBUG] [api_gateway] [login] Valid credentials for user: {user.get('id')}")
        print("[DEBUG] [api_gateway] [login] Generating JWT token")
        token = jwt.encode({
            'id': user['id'],
            'username': user['username'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        print(f"[DEBUG] [api_gateway] [login] Token generated: {token[:10]}...")
        
        user_data = {k: user[k] for k in user if k != 'password'}
        print("[DEBUG] [api_gateway] [login] Login successful")
        return {'token': token, 'user': user_data}

@user_ns.route('/profile')
class UserProfile(Resource):
    @token_required
    @user_ns.marshal_with(user_profile_model)
    def get(self):
        """Get user profile information"""
        print("[DEBUG] [api_gateway] [user_profile] Called")
        auth_header = request.headers.get('Authorization')
        token = auth_header.split()[1]
        print(f"[DEBUG] [api_gateway] [user_profile] Decoding token: {token[:10]}...")
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        print(f"[DEBUG] [api_gateway] [user_profile] Looking up user with ID: {payload.get('id')}")
        
        users = load_users()
        user = next((u for u in users if u.get('id') == payload.get('id')), None)
        if not user:
            print(f"[DEBUG] [api_gateway] [user_profile] User not found with ID: {payload.get('id')}")
            return {'error': 'User not found'}, 404
            
        print(f"[DEBUG] [api_gateway] [user_profile] Found user: {user.get('username')}")
        return {k: user[k] for k in user if k != 'password'}, 200

@bookmark_ns.route('/')
class Bookmark(Resource):
    @token_required
    def get(self):
        """Get all bookmarked articles for the authenticated user"""
        try:
            print("[DEBUG] [api_gateway] [get_bookmarks] Called")
            # Get the user ID from the token
            auth_header = request.headers.get('Authorization')
            token = auth_header.split()[1]
            print(f"[DEBUG] [api_gateway] [get_bookmarks] Decoding token: {token[:10]}...")
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'],audience='authenticated')
            user_id = payload.get('sub')
            print(f"[DEBUG] [api_gateway] [get_bookmarks] Getting bookmarks for user: {user_id}")

            # Get bookmarks using the news_storage service
            bookmarks = get_user_bookmarks(user_id)
            print(f"[DEBUG] [api_gateway] [get_bookmarks] Found {len(bookmarks)} bookmarks")

            return {
                'status': 'success',
                'data': bookmarks
            }, 200

        except Exception as e:
            print(f"[DEBUG] [api_gateway] [get_bookmarks] Error: {str(e)}")
            logger.error(f"Error fetching bookmarks: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }, 500

    @token_required
    def post(self):
        """Add a bookmark for a news article"""
        try:
            print("[DEBUG] [api_gateway] [add_bookmark] Called")
            # Get the user ID from the token
            auth_header = request.headers.get('Authorization')
            token = auth_header.split()[1]
            print(f"[DEBUG] [api_gateway] [add_bookmark] Decoding token: {token[:10]}...")
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'],audience='authenticated')
            user_id = payload.get('sub')
            print(f"[DEBUG] [api_gateway] [add_bookmark] Adding bookmark for user: {user_id}")

            # Get the news article ID from the request body
            data = request.get_json()
            news_id = data.get('news_id')
            print(f"[DEBUG] [api_gateway] [add_bookmark] News article ID: {news_id}")

            if not news_id:
                print("[DEBUG] [api_gateway] [add_bookmark] News article ID missing in request")
                return {'error': 'News article ID is required'}, 400

            # Add the bookmark using the news_storage service
            print(f"[DEBUG] [api_gateway] [add_bookmark] Adding bookmark for user {user_id}, article {news_id}")
            bookmark = add_bookmark(user_id, news_id)
            print(f"[DEBUG] [api_gateway] [add_bookmark] Bookmark added with ID: {bookmark['id'] if isinstance(bookmark, dict) else bookmark}")
            
            return {
                'status': 'success',
                'message': 'Bookmark added successfully',
                'data': {
                    'bookmark_id': bookmark['id'] if isinstance(bookmark, dict) else bookmark
                }
            }, 201

        except Exception as e:
            print(f"[DEBUG] [api_gateway] [add_bookmark] Error: {str(e)}")
            logger.error(f"Error adding bookmark: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }, 500

@bookmark_ns.route('/<string:bookmark_id>')
class BookmarkDelete(Resource):
    @token_required
    def delete(self, bookmark_id):
        """Remove a bookmark for a news article"""
        try:
            print(f"[DEBUG] [api_gateway] [delete_bookmark] Called for bookmark: {bookmark_id}")
            # Get the user ID from the token
            auth_header = request.headers.get('Authorization')
            token = auth_header.split()[1]
            print(f"[DEBUG] [api_gateway] [delete_bookmark] Decoding token: {token[:10]}...")
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'],audience='authenticated')
            user_id = payload.get('sub')
            print(f"[DEBUG] [api_gateway] [delete_bookmark] Deleting bookmark {bookmark_id} for user {user_id}")

            # Delete the bookmark using the news_storage service
            result = delete_bookmark(user_id, bookmark_id)
            print(f"[DEBUG] [api_gateway] [delete_bookmark] Deletion result: {result}")
            
            return {
                'status': 'success',
                'message': 'Bookmark removed successfully'
            }, 200

        except Exception as e:
            print(f"[DEBUG] [api_gateway] [delete_bookmark] Error: {str(e)}")
            logger.error(f"Error removing bookmark: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }, 500
            
            
            
# Import story tracking service
from backend.microservices.story_tracking_service import (
    create_tracked_story, get_tracked_stories, get_story_details, 
    delete_tracked_story, find_related_articles, update_all_tracked_stories
)
print("[DEBUG] [api_gateway] [startup] Story tracking service modules imported")

@story_tracking_ns.route('/')
class StoryTracking(Resource):
    @story_tracking_ns.param('keyword', 'Keyword to track for news updates')
    def get(self):
        """Fetch latest news for a tracked keyword"""
        try:
            print("[DEBUG] [api_gateway] [story_tracking] Story tracking get endpoint called")
            keyword = request.args.get('keyword')
            print(f"[DEBUG] [api_gateway] [story_tracking] Requested keyword: '{keyword}'")
            if not keyword:
                print("[DEBUG] [api_gateway] [story_tracking] Keyword parameter missing")
                return make_response(jsonify({
                    'status': 'error',
                    'message': 'Keyword parameter is required'
                }), 400)

            print(f"[DEBUG] [api_gateway] [story_tracking] Fetching news for keyword: '{keyword}'")
            articles = fetch_news(keyword)
            print(f"[DEBUG] [api_gateway] [story_tracking] Found {len(articles) if articles else 0} articles")
            
            processed_articles = []
            for article in articles:
                print(f"[DEBUG] [api_gateway] [story_tracking] Processing article: {article.get('title', 'No title')}")
                article_id = store_article_in_supabase(article)
                print(f"[DEBUG] [api_gateway] [story_tracking] Stored article with ID: {article_id}")
                processed_articles.append({
                    'id': article_id,
                    'title': article.get('title'),
                    'url': article.get('url'),
                    'source': article.get('source', {}).get('name') if isinstance(article.get('source'), dict) else article.get('source'),
                    'publishedAt': article.get('publishedAt', datetime.now().isoformat())
                })

            print(f"[DEBUG] [api_gateway] [story_tracking] Returning {len(processed_articles)} processed articles")
            return make_response(jsonify({
                'status': 'success',
                'articles': processed_articles
            }), 200)

        except Exception as e:
            print(f"[DEBUG] [api_gateway] [story_tracking] Error: {str(e)}")
            logger.error(f"Error in story tracking: {str(e)}")
            return make_response(jsonify({
                'status': 'error',
                'message': str(e)
            }), 500)
    
    @token_required
    def post(self):
        """Create a new tracked story"""
        try:
            print("[DEBUG] [api_gateway] [story_tracking] Called")
            # Get the user ID from the token
            auth_header = request.headers.get('Authorization')
            token = auth_header.split()[1]
            print(f"[DEBUG] [api_gateway] [story_tracking] Decoding token: {token[:10]}...")
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'], audience='authenticated')
            user_id = payload.get('sub')
            print(f"[DEBUG] [api_gateway] [story_tracking] Creating tracked story for user: {user_id}")
            
            # Get request data
            data = request.get_json()
            keyword = data.get('keyword')
            source_article_id = data.get('sourceArticleId')
            print(f"[DEBUG] [api_gateway] [story_tracking] Story details - Keyword: '{keyword}', Source article: {source_article_id}")
            
            if not keyword:
                print("[DEBUG] [api_gateway] [story_tracking] Keyword parameter missing in request")
                return make_response(jsonify({
                    'status': 'error',
                    'message': 'Keyword is required'
                }), 400)
            
            print(f"[DEBUG] [api_gateway] [story_tracking] Calling create_tracked_story with user_id: {user_id}, keyword: '{keyword}'")
            tracked_story = create_tracked_story(user_id, keyword, source_article_id)
            print(f"[DEBUG] [api_gateway] [story_tracking] Tracked story created with ID: {tracked_story['id'] if tracked_story else 'unknown'}")
            
            print(f"[DEBUG] [api_gateway] [story_tracking] Getting full story details for story: {tracked_story['id']}")
            story_with_articles = get_story_details(tracked_story['id'])
            print(f"[DEBUG] [api_gateway] [story_tracking] Found {len(story_with_articles.get('articles', [])) if story_with_articles else 0} related articles")
            
            return make_response(jsonify({
                'status': 'success',
                'data': story_with_articles
            }), 201)
            
        except Exception as e:
            print(f"[DEBUG] [api_gateway] [story_tracking] Error: {str(e)}")
            logger.error(f"Error creating tracked story: {str(e)}")
            return make_response(jsonify({
                'status': 'error',
                'message': str(e)
            }), 500)

@story_tracking_ns.route('/user')
class UserStoryTracking(Resource):
    @token_required
    def get(self):
        """Get all tracked stories for the authenticated user"""
        try:
            print("[DEBUG] [api_gateway] [user_story_tracking] Called")
            # Get the user ID from the token
            auth_header = request.headers.get('Authorization')
            token = auth_header.split()[1]
            print(f"[DEBUG] [api_gateway] [user_story_tracking] Decoding token: {token[:10]}...")
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'], audience='authenticated')
            user_id = payload.get('sub')
            print(f"[DEBUG] [api_gateway] [user_story_tracking] Getting tracked stories for user: {user_id}")
            
            print(f"[DEBUG] [api_gateway] [user_story_tracking] Calling get_tracked_stories")
            tracked_stories = get_tracked_stories(user_id)
            print(f"[DEBUG] [api_gateway] [user_story_tracking] Found {len(tracked_stories)} tracked stories")
            
            return make_response(jsonify({
                'status': 'success',
                'data': tracked_stories
            }), 200)
            
        except Exception as e:
            print(f"[DEBUG] [api_gateway] [user_story_tracking] Error: {str(e)}")
            logger.error(f"Error getting tracked stories: {str(e)}")
            return make_response(jsonify({
                'status': 'error',
                'message': str(e)
            }), 500)

@story_tracking_ns.route('/<string:story_id>')
class StoryTrackingDetail(Resource):
    @token_required
    def get(self, story_id):
        """Get details for a specific tracked story"""
        try:
            print(f"[DEBUG] [api_gateway] [story_tracking_detail] Called for story: {story_id}")
            print(f"[DEBUG] [api_gateway] [story_tracking_detail] Calling get_story_details for story: {story_id}")
            story = get_story_details(story_id)
            
            if not story:
                print(f"[DEBUG] [api_gateway] [story_tracking_detail] No story found with ID: {story_id}")
                return make_response(jsonify({
                    'status': 'error',
                    'message': 'Tracked story not found'
                }), 404)
            
            print(f"[DEBUG] [api_gateway] [story_tracking_detail] Found story: {story['keyword']}")
            print(f"[DEBUG] [api_gateway] [story_tracking_detail] Story has {len(story.get('articles', []))} articles")
            return make_response(jsonify({
                'status': 'success',
                'data': story
            }), 200)
            
        except Exception as e:
            print(f"[DEBUG] [api_gateway] [story_tracking_detail] Error: {str(e)}")
            logger.error(f"Error getting story details: {str(e)}")
            return make_response(jsonify({
                'status': 'error',
                'message': str(e)
            }), 500)
    
    @token_required
    def delete(self, story_id):
        """Stop tracking a story"""
        try:
            print(f"[DEBUG] [api_gateway] [delete_story_tracking] Called for story: {story_id}")
            # Get the user ID from the token
            auth_header = request.headers.get('Authorization')
            token = auth_header.split()[1]
            print(f"[DEBUG] [api_gateway] [delete_story_tracking] Decoding token: {token[:10]}...")
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'], audience='authenticated')
            user_id = payload.get('sub')
            print(f"[DEBUG] [api_gateway] [delete_story_tracking] Deleting tracked story {story_id} for user {user_id}")
            
            print(f"[DEBUG] [api_gateway] [delete_story_tracking] Calling delete_tracked_story")
            success = delete_tracked_story(user_id, story_id)
            print(f"[DEBUG] [api_gateway] [delete_story_tracking] Delete result: {success}")
            
            if not success:
                print(f"[DEBUG] [api_gateway] [delete_story_tracking] Failed to delete story or story not found")
                return make_response(jsonify({
                    'status': 'error',
                    'message': 'Failed to delete tracked story or story not found'
                }), 404)
            
            print(f"[DEBUG] [api_gateway] [delete_story_tracking] Story deleted successfully")
            return make_response(jsonify({
                'status': 'success',
                'message': 'Tracked story deleted successfully'
            }), 200)
            
        except Exception as e:
            print(f"[DEBUG] [api_gateway] [delete_story_tracking] Error: {str(e)}")
            logger.error(f"Error deleting tracked story: {str(e)}")
            return make_response(jsonify({
                'status': 'error',
                'message': str(e)
            }), 500)

@app.route('/api/story_tracking', methods=['OPTIONS'])
def story_tracking_options():
    print("[DEBUG] [api_gateway] [story_tracking_options] Called")
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
    print("[DEBUG] [api_gateway] [story_tracking_options] Responding with CORS headers")
    return response

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else Config.API_PORT
    print(f"[DEBUG] [api_gateway] [main] Starting on {Config.API_HOST}:{port} with debug={True}")
    app.run(host=Config.API_HOST, port=port, debug=True)
