from flask import Flask, render_template, request, redirect, session, url_for, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from datetime import datetime
from dotenv import load_dotenv
import base64

# Load environment variables
load_dotenv()

app = Flask(__name__)

# ------------------ ENV VARIABLES ------------------
app.secret_key = os.environ.get("SECRET_KEY")
MONGO_URI = os.environ.get("MONGO_URI")

if not app.secret_key:
    raise ValueError("SECRET_KEY not set")
if not MONGO_URI:
    raise ValueError("MONGO_URI not set")

# ------------------ FILE SETTINGS ------------------
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# ------------------ MONGO CONNECTION ------------------
try:
    client = MongoClient(MONGO_URI)
    db = client.get_database()
    users_collection = db.users
    posts_collection = db.posts
    client.server_info()
    print("✅ Connected to MongoDB successfully!")
except Exception as e:
    print("❌ MongoDB connection error:", e)
    raise

# ------------------ HELPERS ------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def image_to_base64(file):
    return base64.b64encode(file.read()).decode("utf-8")

# ------------------ ROUTES ------------------

# Root → Signup first
@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("signup"))
    return redirect(url_for("dashboard"))

# Health check (for monitor)
@app.route("/health")
def health():
    return "OK", 200

# Signup
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()

        if not username:
            return render_template("signup.html", error="Username required")

        if users_collection.find_one({"username": username}):
            return render_template("signup.html", error="Username already exists")

        result = users_collection.insert_one({
            "username": username,
            "created_at": datetime.utcnow()
        })

        session["user_id"] = str(result.inserted_id)
        session["username"] = username
        return redirect(url_for("dashboard"))

    return render_template("signup.html")

# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        user = users_collection.find_one({"username": username})

        if not user:
            return render_template("login.html", error="User not found")

        session["user_id"] = str(user["_id"])
        session["username"] = user["username"]
        return redirect(url_for("dashboard"))

    return render_template("login.html")

# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("signup"))

# Dashboard (PROTECTED)
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    username = session["username"]

    posts = list(posts_collection.find().sort("timestamp", -1))
    for post in posts:
        post["is_owner"] = str(post["user_id"]) == user_id

    return render_template("dashboard.html", posts=posts, username=username)

# Create post
@app.route("/create", methods=["GET", "POST"])
def create_post():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()

        if not title or not content:
            return render_template("create.html", error="Title & content required")

        image_data = None
        image_type = None

        if "image" in request.files:
            file = request.files["image"]
            if file.filename and allowed_file(file.filename):
                file.seek(0, os.SEEK_END)
                if file.tell() > MAX_FILE_SIZE:
                    return render_template("create.html", error="Image too large")
                file.seek(0)
                image_data = image_to_base64(file)
                image_type = file.filename.rsplit(".", 1)[1].lower()

        posts_collection.insert_one({
            "user_id": ObjectId(session["user_id"]),
            "username": session["username"],
            "title": title,
            "content": content,
            "image": image_data,
            "image_type": image_type,
            "timestamp": datetime.utcnow()
        })

        return redirect(url_for("dashboard"))

    return render_template("create.html")

# Delete post
@app.route("/delete/<post_id>")
def delete_post(post_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    posts_collection.delete_one({
        "_id": ObjectId(post_id),
        "user_id": ObjectId(session["user_id"])
    })

    return redirect(url_for("dashboard"))

# Edit post
@app.route("/edit/<post_id>", methods=["GET", "POST"])
def edit_post(post_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    post = posts_collection.find_one({
        "_id": ObjectId(post_id),
        "user_id": ObjectId(session["user_id"])
    })

    if not post:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()

        if not title or not content:
            return render_template("edit.html", post=post, error="All fields required")

        posts_collection.update_one(
            {"_id": ObjectId(post_id)},
            {"$set": {
                "title": title,
                "content": content,
                "updated_at": datetime.utcnow()
            }}
        )

        return redirect(url_for("dashboard"))

    return render_template("edit.html", post=post)

# ------------------ RUN ------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
