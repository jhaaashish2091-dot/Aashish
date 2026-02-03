from flask import Flask, render_template, request, redirect, session, url_for, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from datetime import datetime
from dotenv import load_dotenv
import base64

# Load env
load_dotenv()

app = Flask(__name__)

# ------------------ ENV VARIABLES ------------------
app.secret_key = os.environ.get("SECRET_KEY")
MONGO_URI = os.environ.get("MONGO_URI")

if not app.secret_key:
    raise ValueError("⚠️ SECRET_KEY not set")
if not MONGO_URI:
    raise ValueError("⚠️ MONGO_URI not set")

# ------------------ MONGO ------------------
client = MongoClient(MONGO_URI)
db = client.get_database()
users_collection = db.users
posts_collection = db.posts
client.server_info()
print("✅ MongoDB Connected")

# ------------------ HELPERS ------------------
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def image_to_base64(file):
    return base64.b64encode(file.read()).decode('utf-8')

# ------------------ ROUTES ------------------

# 🔥 ROOT → SIGNUP FIRST
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("signup"))

# 🔐 DASHBOARD (PROTECTED)
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("signup"))

    user_id = session.get("user_id")
    username = session.get("username")

    all_posts = list(posts_collection.find().sort("timestamp", -1))
    for post in all_posts:
        post["is_owner"] = str(post.get("user_id")) == str(user_id)

    return render_template("dashboard.html", posts=all_posts, username=username)

# ------------------ AUTH ------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        if not username:
            return render_template("signup.html", error="Username required")

        if users_collection.find_one({"username": username}):
            return render_template("signup.html", error="Username already exists")

        user = {"username": username, "created_at": datetime.utcnow()}
        result = users_collection.insert_one(user)

        session["username"] = username
        session["user_id"] = str(result.inserted_id)

        return redirect(url_for("dashboard"))

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        user = users_collection.find_one({"username": username})

        if not user:
            return render_template("login.html", error="User not found")

        session["username"] = user["username"]
        session["user_id"] = str(user["_id"])
        return redirect(url_for("dashboard"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("signup"))

# ------------------ POSTS ------------------
@app.route("/create", methods=["GET", "POST"])
def create_post():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")

        if not title or not content:
            return render_template("create.html", error="All fields required")

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
                image_type = file.filename.rsplit('.', 1)[1].lower()

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

@app.route("/delete/<post_id>")
def delete_post(post_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    posts_collection.delete_one({
        "_id": ObjectId(post_id),
        "user_id": ObjectId(session["user_id"])
    })

    return redirect(url_for("dashboard"))

# ------------------ HEALTH ------------------
@app.route("/health")
def health():
    return "OK", 200

# ------------------ RUN ------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
