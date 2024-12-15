from flask import Flask, render_template, redirect, url_for, request, jsonify, session, flash
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import requests
import os
import sqlite3
import hashlib
from functools import wraps

app = Flask(__name__)

# Load environment variables
load_dotenv()

# Google API Key
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# Configure upload folder
UPLOAD_FOLDER = 'static/uploads'  # Folder to store uploaded images
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}  # Allowed file types
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Helper function to check file type
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def hash_password(password):
    salt = "dietdrpepper"
    password += salt
    print(hashlib.sha256(password.encode('utf-8')).hexdigest())
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')
PUBLIC_PATHS = ['/', '/login', '/register']

@app.before_request
def restrict_access():
    # Check if the requested path is public or user is logged in
    if request.path not in PUBLIC_PATHS and 'user_id' not in session:
        flash("You must log in to access this page.")
        return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        hashed_password = hash_password(password)
        
        try:
            db_connection = sqlite3.connect('data/database.db')  # Ensure this path is correct
            cursor = db_connection.cursor()

            cursor.execute(
                'SELECT user_id FROM Users WHERE username = ? AND password = ?',
                (username, hashed_password)
            )
            user = cursor.fetchone()
            db_connection.close()

            print(f"Hashed password: {hashed_password}")
            print(f"Query result: {user}")

            if user:
                session['user_id'] = user[0]
                flash("Login successful!", "success")
                return redirect(url_for('home'))
            else:
                flash("Invalid username or password.", "danger")
                return render_template('login.html')
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            flash("An error occurred. Please try again.", "danger")
            return render_template('login.html')
    return render_template('login.html')

# currently does not have an associated button
################################################################################################################
@app.route('/logout')
def logout():
    session.clear()  # Clear the session
    flash("You have been logged out.")
    return redirect(url_for('login'))
################################################################################################################

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("You need to log in first!")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/profile')
@login_required
def profile():
    user_id = session['user_id']
    # Fetch user data from the database...
    return render_template('profile.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = hash_password(password)
        
        # Save user to database (placeholder logic)
        try:
            db_connection = sqlite3.connect('data/database.db')
            cursor = db_connection.cursor()
            cursor.execute(
                'INSERT INTO Users (username, password) VALUES (?, ?)',
                (username, hashed_password)
            )
            db_connection.commit()
            db_connection.close()
            return redirect(url_for('login'))  # Redirect to login page
        except Exception as e:
            print(f"Error during registration: {e}")
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/home')
@login_required
def home():
    return render_template('home.html')

@app.route('/search')
def search():
    return render_template('search.html')

@app.route('/map')
def map_page():
    return render_template('map.html')

@app.route('/get_nearby_locations')
def get_nearby_locations():
    try:
        # Get the location and type from query parameters
        location = request.args.get('location', '37.3653,-120.4394')  # Default UC Merced location
        place_type = request.args.get('type', 'park')
        radius = 5000  # 5 km radius

        # Split the location into lat and lon
        lat, lon = location.split(',')

        # Google Places API URL
        url = f'https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={lat},{lon}&radius={radius}&type={place_type}&key={GOOGLE_API_KEY}'

        # Request data from Google Places API
        response = requests.get(url)
        
        # Check if the response was successful
        response.raise_for_status()  # This will raise an error if the response is not 200 OK

        data = response.json()  # Parse the JSON response

        return jsonify(data)

    except requests.exceptions.RequestException as e:
        # Handle any request errors
        print(f"Error making request to Google API: {e}")
        return jsonify({"error": "Error making request to Google API."}), 500

    except Exception as e:
        # Handle other exceptions
        print(f"An error occurred: {e}")
        return jsonify({"error": "Internal server error."}), 500

@app.route('/create_post', methods=['POST'])
def create_post():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        # Save the image
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Save post details to the database
        user_id = request.form.get('user_id')  # Sent from the form
        caption = request.form.get('content')  # Sent from the form
        if not user_id or not caption:
            return jsonify({'error': 'Missing required fields'}), 400

        try:
            # Insert into database
            db_connection = sqlite3.connect('data/database.db')
            cursor = db_connection.cursor()
            cursor.execute(
                'INSERT INTO Posts (user_id, content, image_url) VALUES (?, ?, ?)',
                (user_id, caption, file_path)
            )
            db_connection.commit()
            db_connection.close()
        except Exception as e:
            return jsonify({'error': str(e)}), 500

        return jsonify({'message': 'Post created successfully!'}), 201

    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/fetch_posts', methods=['GET'])
def fetch_posts():
    try:
        user_id = 1  # Hardcoding user_id for now; replace with dynamic user session later
        db_connection = sqlite3.connect('data/database.db')
        cursor = db_connection.cursor()

        # Query to fetch posts, like counts, and if the current user liked each post
        cursor.execute('''
            SELECT Posts.post_id, Users.username, Posts.content, Posts.image_url, Posts.created_at,
                   (SELECT COUNT(*) FROM Likes WHERE Likes.post_id = Posts.post_id) AS like_count,
                   EXISTS (SELECT 1 FROM Likes WHERE Likes.post_id = Posts.post_id AND Likes.user_id = ?) AS user_liked
            FROM Posts
            JOIN Users ON Posts.user_id = Users.user_id
            ORDER BY Posts.created_at DESC
        ''', (user_id,))
        posts = cursor.fetchall()
        db_connection.close()

        # Structure posts as a list of dictionaries
        posts_list = [
            {
                'post_id': post[0],
                'username': post[1],
                'content': post[2],
                'image_url': post[3],
                'created_at': post[4],
                'like_count': post[5],
                'user_liked': bool(post[6])  # Convert the 0/1 result to a boolean
            }
            for post in posts
        ]

        return jsonify(posts_list)

    except Exception as e:
        print(f"Error in /fetch_posts: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/add_comment', methods=['POST'])
def add_comment():
    try:
        # Get comment details from the form
        post_id = request.form.get('post_id')
        user_id = request.form.get('user_id')
        content = request.form.get('content')

        print(f"Received comment data: post_id={post_id}, user_id={user_id}, content={content}")

        if not post_id or not user_id or not content:
            print("Error: Missing required fields")
            return jsonify({'error': 'Missing required fields'}), 400

        # Insert the comment into the database
        db_connection = sqlite3.connect('data/database.db')
        cursor = db_connection.cursor()
        cursor.execute('''
            INSERT INTO Comments (post_id, user_id, content)
            VALUES (?, ?, ?)
        ''', (post_id, user_id, content))
        db_connection.commit()
        db_connection.close()

        print(f"Comment added successfully for post_id={post_id}")
        return jsonify({'message': 'Comment added successfully!'}), 201

    except Exception as e:
        print(f"Error in /add_comment: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/fetch_comments', methods=['GET'])
def fetch_comments():
    try:
        post_id = request.args.get('post_id')  # Get the post_id from the query parameter
        if not post_id:
            return jsonify({'error': 'Post ID is required'}), 400

        # Connect to the database
        db_connection = sqlite3.connect('data/database.db')
        cursor = db_connection.cursor()

        # Query to fetch comments for the given post_id
        cursor.execute('''
            SELECT Users.username, Comments.content, Comments.created_at
            FROM Comments
            JOIN Users ON Comments.user_id = Users.user_id
            WHERE Comments.post_id = ?
            ORDER BY Comments.created_at ASC
        ''', (post_id,))
        comments = cursor.fetchall()
        db_connection.close()

        # Structure comments as a list of dictionaries
        comments_list = [
            {
                'username': comment[0],
                'content': comment[1],
                'created_at': comment[2]
            }
            for comment in comments
        ]

        return jsonify(comments_list)  # Return the comments as JSON

    except Exception as e:
        print(f"Error in /fetch_comments: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/like_post', methods=['POST'])
def like_post():
    try:
        post_id = request.form.get('post_id')
        user_id = request.form.get('user_id')  # Replace with session-based user_id when ready
        if not post_id or not user_id:
            return jsonify({'error': 'Missing post_id or user_id'}), 400

        db_connection = sqlite3.connect('data/database.db')
        cursor = db_connection.cursor()

        # Check if the user already liked the post
        cursor.execute('SELECT * FROM Likes WHERE post_id = ? AND user_id = ?', (post_id, user_id))
        existing_like = cursor.fetchone()

        if existing_like:
            # Unlike the post
            cursor.execute('DELETE FROM Likes WHERE post_id = ? AND user_id = ?', (post_id, user_id))
            message = 'Post unliked'
            liked = False
        else:
            # Like the post
            cursor.execute('INSERT INTO Likes (post_id, user_id) VALUES (?, ?)', (post_id, user_id))
            message = 'Post liked'
            liked = True

        db_connection.commit()
        return jsonify({'message': message, 'liked': liked}), 200

    except Exception as e:
        print(f"Error in /like_post: {e}")
        return jsonify({'error': str(e)}), 500

    finally:
        db_connection.close()  # Ensure the connection is always closed

@app.route('/user_profile/<int:user_id>', methods=['GET'])
def user_profile(user_id):
    try:
        # Connect to the database
        db_connection = sqlite3.connect('data/database.db')
        cursor = db_connection.cursor()

        # Fetch user details
        cursor.execute('SELECT username, pet_name, pet_breed, profile_picture FROM Users WHERE user_id = ?', (user_id,))
        user_data = cursor.fetchone()

        if not user_data:
            return render_template('user_profile.html', error="User not found.")

        # Fetch the user's posts
        cursor.execute('''
            SELECT post_id, content, image_url, created_at
            FROM Posts
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        user_posts = cursor.fetchall()
        db_connection.close()

        # Pass the data to the user profile template
        return render_template('user_profile.html', user={
            'username': user_data[0],
            'pet_name': user_data[1],
            'pet_breed': user_data[2],
            'profile_picture': user_data[3],
            'posts': user_posts
        })

    except Exception as e:
        print(f"Error in /user_profile: {e}")
        return render_template('user_profile.html', error="An error occurred.")

if __name__ == '__main__':
    app.run(debug=True)
