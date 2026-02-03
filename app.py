from flask import Flask, render_template, request, redirect, session, url_for, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from datetime import datetime
from dotenv import load_dotenv
import base64
from werkzeug.utils import secure_filename

# Load environment variables from .env file (for local development)
load_dotenv()

app = Flask(__name__)

# ------------------ ENV VARIABLES ------------------
app.secret_key = os.environ.get("SECRET_KEY")
MONGO_URI = os.environ.get("MONGO_URI")

# Validate required environment variables
if not app.secret_key:
    raise ValueError("⚠️ SECRET_KEY environment variable is not set!")
if not MONGO_URI:
    raise ValueError("⚠️ MONGO_URI environment variable is not set!")

# File upload settings
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# ------------------ MONGO CONNECTION ------------------
try:
    client = MongoClient(MONGO_URI)
    db = client.get_database()  # uses database from URI
    users_collection = db.users
    posts_collection = db.posts
    # Test connection
    client.server_info()
    print("✅ Connected to MongoDB successfully!")
except Exception as e:
    print(f"❌ MongoDB connection error: {e}")
    raise

# ------------------ HELPER FUNCTIONS ------------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def image_to_base64(file):
    """Convert uploaded file to base64 string"""
    return base64.b64encode(file.read()).decode('utf-8')

# ------------------ ROUTES ------------------
@app.route("/")
def index():
    username = session.get("username")
    user_id = session.get("user_id")
    
    all_posts = list(posts_collection.find().sort("timestamp", -1))
    
    # Mark ownership for template
    for post in all_posts:
        post["is_owner"] = str(post.get("user_id")) == str(user_id)
    
    return render_template("dashboard.html", posts=all_posts, username=username)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        if not username or len(username.strip()) == 0:
            return render_template("signup.html", error="Please enter a valid username")
        
        username = username.strip()
        
        # Check if user exists
        if users_collection.find_one({"username": username}):
            return render_template("signup.html", error="Username already exists")
        
        # Insert new user
        user = {"username": username, "created_at": datetime.utcnow()}
        result = users_collection.insert_one(user)
        
        session["username"] = username
        session["user_id"] = str(result.inserted_id)
        
        return redirect(url_for("index"))
    
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        if not username:
            return render_template("login.html", error="Please enter a username")
            
        user = users_collection.find_one({"username": username.strip()})
        
        if user:
            session["username"] = user["username"]
            session["user_id"] = str(user["_id"])
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="No account with this username. Please sign up.")
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/create", methods=["GET", "POST"])
def create_post():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        
        if not title or not content:
            return render_template("create.html", error="Title and content are required")
        
        # Handle image upload
        image_data = None
        image_type = None
        
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                if allowed_file(file.filename):
                    # Check file size
                    file.seek(0, os.SEEK_END)
                    file_size = file.tell()
                    file.seek(0)
                    
                    if file_size > MAX_FILE_SIZE:
                        return render_template("create.html", error="Image too large (max 5MB)")
                    
                    # Convert to base64
                    image_data = image_to_base64(file)
                    image_type = file.filename.rsplit('.', 1)[1].lower()
                else:
                    return render_template("create.html", error="Invalid file type. Only PNG, JPG, JPEG, GIF, WEBP allowed")
        
        post = {
            "user_id": ObjectId(session["user_id"]),
            "username": session["username"],
            "title": title.strip(),
            "content": content.strip(),
            "image": image_data,
            "image_type": image_type,
            "timestamp": datetime.utcnow()
        }
        posts_collection.insert_one(post)
        return redirect(url_for("index"))
    
    return render_template("create.html")

@app.route("/delete/<post_id>", methods=["POST", "GET"])
def delete_post(post_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    try:
        # Only delete if user owns the post
        result = posts_collection.delete_one({
            "_id": ObjectId(post_id),
            "user_id": ObjectId(session["user_id"])
        })
        
        if result.deleted_count > 0:
            flash("Post deleted successfully!", "success")
        else:
            flash("You don't have permission to delete this post", "error")
    except Exception as e:
        flash(f"Error deleting post: {str(e)}", "error")
    
    return redirect(url_for("index"))

@app.route("/edit/<post_id>", methods=["GET", "POST"])
def edit_post(post_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    # Find the post
    post = posts_collection.find_one({
        "_id": ObjectId(post_id),
        "user_id": ObjectId(session["user_id"])
    })
    
    if not post:
        flash("Post not found or you don't have permission to edit", "error")
        return redirect(url_for("index"))
    
    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        
        if not title or not content:
            return render_template("edit.html", post=post, error="Title and content are required")
        
        # Handle image upload
        image_data = post.get("image")  # Keep existing image by default
        image_type = post.get("image_type")
        
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                if allowed_file(file.filename):
                    # Check file size
                    file.seek(0, os.SEEK_END)
                    file_size = file.tell()
                    file.seek(0)
                    
                    if file_size > MAX_FILE_SIZE:
                        return render_template("edit.html", post=post, error="Image too large (max 5MB)")
                    
                    # Convert to base64
                    image_data = image_to_base64(file)
                    image_type = file.filename.rsplit('.', 1)[1].lower()
                else:
                    return render_template("edit.html", post=post, error="Invalid file type. Only PNG, JPG, JPEG, GIF, WEBP allowed")
        
        # Check if user wants to remove image
        if request.form.get("remove_image") == "true":
            image_data = None
            image_type = None
        
        # Update post
        posts_collection.update_one(
            {"_id": ObjectId(post_id)},
            {"$set": {
                "title": title.strip(),
                "content": content.strip(),
                "image": image_data,
                "image_type": image_type,
                "updated_at": datetime.utcnow()
            }}
        )
        
        flash("Post updated successfully!", "success")
        return redirect(url_for("index"))
    
    return render_template("edit.html", post=post)

# ------------------ RUN ------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)