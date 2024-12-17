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
    if 'user_id' in session:
        flash("You are already logged in!", "info")
        return redirect(url_for('home'))  # Redirect to home if logged in

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

            # print(f"Hashed password: {hashed_password}")
            # print(f"Query result: {user}")

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
    try:
        db_connection = sqlite3.connect('data/database.db')
        cursor = db_connection.cursor()

        cursor.execute('SELECT username, pet_name, pet_breed, profile_picture FROM Users WHERE user_id = ?', (user_id,))
        user_data = cursor.fetchone()

        if not user_data:
            flash("User not found")
            return redirect(url_for('home'))
        
        username, pet_name, pet_breed, profile_picture = user_data
        if not profile_picture:
            profile_picture = '/assets/default-profile-pic.png'


        cursor.execute('SELECT post_id, content, image_url, created_at FROM Posts WHERE user_id = ?', (user_id,))
        posts = cursor.fetchall()  

        cursor.execute('SELECT COUNT(*) FROM Followers WHERE followed_id = ?', (user_id,))
        followers_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM Followers WHERE follower_id = ?', (user_id,))
        following_count = cursor.fetchone()[0]

        db_connection.close()

        return render_template(
    'profile.html', 
    username=username, 
    pet_name=pet_name, 
    pet_breed=pet_breed, 
    profile_picture=profile_picture,
    posts=posts,
    followers=followers_count,
    following=following_count,
    user_id=user_id 
)


    except sqlite3.Error as e:
        print(f"Database error: {e}")
        flash("An error occurred. Please try again.")
        return redirect(url_for('home'))



@app.route('/get_followers')
@login_required
def get_followers():
    user_id = session['user_id']
    try:
        db_connection = sqlite3.connect('data/database.db')
        cursor = db_connection.cursor()

        cursor.execute('''
            SELECT Users.user_id, Users.username
            FROM Followers
            JOIN Users ON Followers.follower_id = Users.user_id
            WHERE Followers.followed_id = ?
        ''', (user_id,))
        followers = cursor.fetchall()

        db_connection.close()

        # Return the list as JSON
        return jsonify([{'user_id': follower[0], 'username': follower[1]} for follower in followers])

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return jsonify([])

@app.route('/get_following')
@login_required
def get_following():
    user_id = session['user_id']
    try:
        db_connection = sqlite3.connect('data/database.db')
        cursor = db_connection.cursor()

        cursor.execute('''
            SELECT Users.user_id, Users.username
            FROM Followers
            JOIN Users ON Followers.followed_id = Users.user_id
            WHERE Followers.follower_id = ?
        ''', (user_id,))
        following = cursor.fetchall()

        db_connection.close()

        # Return the list as JSON
        return jsonify([{'user_id': follow[0], 'username': follow[1]} for follow in following])

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return jsonify([])

@app.route('/delete_post/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    user_id = session['user_id']
    try:
        db_connection = sqlite3.connect('data/database.db')
        cursor = db_connection.cursor()

        cursor.execute('SELECT post_id FROM Posts WHERE post_id = ? AND user_id = ?', (post_id, user_id))
        post = cursor.fetchone()

        if not post:
            flash("Post not found or you don't have permission to delete it.")
            return redirect(url_for('profile'))

        cursor.execute('DELETE FROM Posts WHERE post_id = ?', (post_id,))
        db_connection.commit()
        db_connection.close()

        flash("Post deleted successfully!")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        flash("An error occurred while deleting the post. Please try again.")
    return redirect(url_for('profile'))

@app.route('/update_profile_picture', methods=['POST'])
@login_required
def update_profile_picture():
    user_id = session['user_id']
    file = request.files.get('profile_picture')
    
    if file and allowed_file(file.filename):
        filename = os.path.join('static/uploads/profile', secure_filename(file.filename))
        file.save(filename)

        try:
            db_connection = sqlite3.connect('data/database.db')
            cursor = db_connection.cursor()
            cursor.execute('UPDATE Users SET profile_picture = ? WHERE user_id = ?', ('uploads/profile/' + secure_filename(file.filename), user_id))
            db_connection.commit()
            db_connection.close()

            flash ("Profile picture updated successfully!")
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            flash("An error occurred while updating your profile pictre. Please try again.")
    return redirect(url_for('profile'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        flash("You are already logged in!", "info")
        return redirect(url_for('home'))  # Redirect to home if logged in

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
            flash("An error occurred. Please try again.")
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    if request.method == 'POST':
        # Handle post submission
        content = request.form.get('content')
        file = request.files.get('image')
        user_id = session['user_id']
        
        if not content:
            flash("Content cannot be empty.", "danger")
            return redirect(url_for('home'))

        # Save the file
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
        else:
            file_path = None

        # Insert post into the database
        try:
            db_connection = sqlite3.connect('data/database.db')
            cursor = db_connection.cursor()
            cursor.execute(
                'INSERT INTO Posts (user_id, content, image_url) VALUES (?, ?, ?)',
                (user_id, content, file_path)
            )
            db_connection.commit()
            db_connection.close()
            flash("Post created successfully!", "success")
        except sqlite3.Error as e:
            print(f"Error inserting post: {e}")
            flash("An error occurred. Please try again.", "danger")
        return redirect(url_for('home'))

    # Render homepage
    return render_template('home.html')

@app.route('/search', methods=['GET'])
@login_required
def search():
    query = request.args.get('query', '').strip()  # Get the search query
    if not query:
        return render_template('search.html', users=[], pets=[], posts=[], query=query)

    try:
        db_connection = sqlite3.connect('data/database.db')
        cursor = db_connection.cursor()

        # Search for users based on username
        cursor.execute('''
            SELECT user_id, username, profile_picture
            FROM Users
            WHERE username LIKE ?
        ''', (f'%{query}%',))
        users = cursor.fetchall()

        # Search for pets based on pet_name and pet_breed
        cursor.execute('''
            SELECT user_id, pet_name, pet_breed, profile_picture
            FROM Users
            WHERE pet_name LIKE ? OR pet_breed LIKE ?
        ''', (f'%{query}%', f'%{query}%'))
        pets = cursor.fetchall()

        # Search for posts based on content
        cursor.execute('''
            SELECT Posts.post_id, Users.user_id, Users.username, Posts.content, Posts.image_url, Posts.created_at
            FROM Posts
            JOIN Users ON Posts.user_id = Users.user_id
            WHERE Posts.content LIKE ?
            ORDER BY Posts.created_at DESC
        ''', (f'%{query}%',))
        posts = cursor.fetchall()

        db_connection.close()

        # Format results for the template
        formatted_users = [
            {
                'user_id': user[0],
                'username': user[1],
                'profile_picture': user[2] if user[2] else 'assets/default-profile-pic.png'
            }
            for user in users
        ]
        formatted_pets = [
            {
                'user_id': pet[0],
                'pet_name': pet[1],
                'pet_breed': pet[2],
                'profile_picture': pet[3] if pet[3] else 'assets/default-profile-pic.png'
            }
            for pet in pets
        ]
        formatted_posts = [
            {
                'post_id': post[0],
                'user_id': post[1],
                'username': post[2],
                'content': post[3],
                'image_url': post[4],
                'created_at': post[5]
            }
            for post in posts
        ]

        return render_template('search.html', users=formatted_users, pets=formatted_pets, posts=formatted_posts, query=query)

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        flash("An error occurred while searching. Please try again.")
        return render_template('search.html', users=[], pets=[], posts=[], query=query)

@app.route('/map')
def map_view():
    google_api_key = os.getenv('GOOGLE_API_KEY')
    return render_template('map.html', google_api_key=google_api_key)

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
        user_id = session['user_id']  # Sent from the form
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
        user_id = session['user_id']  # Current logged-in user
        db_connection = sqlite3.connect('data/database.db')
        cursor = db_connection.cursor()

        # Fetch posts with user details and like status
        cursor.execute('''
            SELECT Posts.post_id, Users.user_id, Users.username, Posts.content, Posts.image_url, Posts.created_at,
                   (SELECT COUNT(*) FROM Likes WHERE Likes.post_id = Posts.post_id) AS like_count,
                   EXISTS (SELECT 1 FROM Likes WHERE Likes.post_id = Posts.post_id AND Likes.user_id = ?) AS user_liked
            FROM Posts
            JOIN Users ON Posts.user_id = Users.user_id
            ORDER BY Posts.created_at DESC
        ''', (user_id,))
        posts = cursor.fetchall()
        db_connection.close()

        # Structure posts with user_id for linking profiles
        posts_list = [
            {
                'post_id': post[0],
                'user_id': post[1],  # Added for linking profile
                'username': post[2],
                'content': post[3],
                'image_url': post[4],
                'created_at': post[5],
                'like_count': post[6],
                'user_liked': bool(post[7])
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
        user_id = session['user_id']
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
        post_id = request.args.get('post_id')
        if not post_id:
            return jsonify({'error': 'Post ID is required'}), 400

        db_connection = sqlite3.connect('data/database.db')
        cursor = db_connection.cursor()

        # Fetch comments with user details
        cursor.execute('''
            SELECT Users.user_id, Users.username, Comments.content, Comments.created_at
            FROM Comments
            JOIN Users ON Comments.user_id = Users.user_id
            WHERE Comments.post_id = ?
            ORDER BY Comments.created_at ASC
        ''', (post_id,))
        comments = cursor.fetchall()
        db_connection.close()

        # Structure comments with user_id for linking profiles
        comments_list = [
            {
                'user_id': comment[0],  # Added for profile linking
                'username': comment[1],
                'content': comment[2],
                'created_at': comment[3]
            }
            for comment in comments
        ]

        return jsonify(comments_list)

    except Exception as e:
        print(f"Error in /fetch_comments: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/like_post', methods=['POST'])
def like_post():
    try:
        post_id = request.form.get('post_id')
        user_id = session['user_id']  # Fetch user ID from session
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
        db_connection.close()

@app.route('/user_profile/<int:user_id>', methods=['GET'])
def user_profile(user_id):
    try:
        db_connection = sqlite3.connect('data/database.db')
        cursor = db_connection.cursor()

        # Fetch user details
        cursor.execute('SELECT username, pet_name, pet_breed, profile_picture FROM Users WHERE user_id = ?', (user_id,))
        user_data = cursor.fetchone()

        if not user_data:
            return render_template('user_profile.html', error="User not found.")

        # Check if the current user is following the profile user
        is_following = False
        if 'user_id' in session:
            cursor.execute('SELECT 1 FROM Followers WHERE follower_id = ? AND followed_id = ?', 
                           (session['user_id'], user_id))
            is_following = cursor.fetchone() is not None

        # Fetch followers and following counts
        cursor.execute('SELECT COUNT(*) FROM Followers WHERE followed_id = ?', (user_id,))
        followers = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM Followers WHERE follower_id = ?', (user_id,))
        following = cursor.fetchone()[0]

        # Fetch the user's posts
        cursor.execute('''
            SELECT post_id, content, image_url, created_at
            FROM Posts
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        user_posts = cursor.fetchall()
        db_connection.close()

        # Pass data to the template
        return render_template('user_profile.html', user={
            'username': user_data[0],
            'pet_name': user_data[1],
            'pet_breed': user_data[2],
            'profile_picture': user_data[3],
            'user_id': user_id,
            'posts': user_posts,
            'is_following': is_following
        }, followers=followers, following=following)

    except Exception as e:
        print(f"Error in /user_profile: {e}")
        return render_template('user_profile.html', error="An error occurred.")


@app.route('/follow', methods=['POST'])
@login_required
def follow():
    try:
        follower_id = session['user_id']  # The logged-in user
        followed_id = request.form.get('followed_id')  # The user to follow/unfollow

        if not followed_id or int(followed_id) == follower_id:
            return jsonify({'error': 'Invalid user ID'}), 400

        db_connection = sqlite3.connect('data/database.db')
        cursor = db_connection.cursor()

        # Check if already following
        cursor.execute('SELECT * FROM Followers WHERE follower_id = ? AND followed_id = ?', 
                       (follower_id, followed_id))
        existing_follow = cursor.fetchone()

        if existing_follow:
            # Unfollow logic
            cursor.execute('DELETE FROM Followers WHERE follower_id = ? AND followed_id = ?', 
                           (follower_id, followed_id))
            message = 'Unfollowed'
            is_following = False
        else:
            # Follow logic
            cursor.execute('INSERT INTO Followers (follower_id, followed_id, followed_at) VALUES (?, ?, datetime("now"))', 
                           (follower_id, followed_id))
            message = 'Followed'
            is_following = True

        db_connection.commit()
        db_connection.close()

        return jsonify({'message': message, 'is_following': is_following}), 200

    except Exception as e:
        print(f"Error in /follow: {e}")
        return jsonify({'error': 'An error occurred'}), 500
    
@app.route('/follow_stats/<int:user_id>', methods=['GET'])
def follow_stats(user_id):
    try:
        db_connection = sqlite3.connect('data/database.db')
        cursor = db_connection.cursor()

        # Count followers
        cursor.execute('SELECT COUNT(*) FROM Followers WHERE followed_id = ?', (user_id,))
        followers_count = cursor.fetchone()[0]

        # Count following
        cursor.execute('SELECT COUNT(*) FROM Followers WHERE follower_id = ?', (user_id,))
        following_count = cursor.fetchone()[0]

        db_connection.close()

        return jsonify({'followers': followers_count, 'following': following_count}), 200

    except Exception as e:
        print(f"Error in /follow_stats: {e}")
        return jsonify({'error': 'An error occurred'}), 500

if __name__ == '__main__':
    app.run(debug=True)