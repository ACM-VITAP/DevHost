import os
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, send_from_directory
)
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime, date
from bson.objectid import ObjectId

# ================== APP CONFIG ================== #

app = Flask(__name__)
app.secret_key = "secret_admin_key"

app.config["MONGO_URI"] = (
    "mongodb+srv://charanachanta2:Charan1114@cluster0.ysxk5ry.mongodb.net/ACM"
    "?retryWrites=true&w=majority&appName=Cluster0"
)

app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20MB hard limit

mongo = PyMongo(app)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

ALLOWED_EXTENSIONS = {"zip", "ppt", "pptx", "pdf"}

# ================== HELPERS ================== #

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrap

def admin_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        user = mongo.db.users.find_one({"_id": ObjectId(session["user_id"])})
        if user["role"] != "admin":
            flash("Admin access only")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return wrap

# ================== CREATE ADMIN ================== #

def create_admin():
    if not mongo.db.users.find_one({"email": "admin"}):
        mongo.db.users.insert_one({
            "name": "Admin",
            "email": "admin",
            "password": generate_password_hash("acmvitap"),
            "role": "admin",
            "bio": "",
            "age": "",
            "gender": ""
        })

create_admin()

# ================== AUTH ================== #

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = mongo.db.users.find_one({"email": request.form["email"]})
        if user and check_password_hash(user["password"], request.form["password"]):
            session["user_id"] = str(user["_id"])
            return redirect(url_for("home"))
        flash("Invalid credentials")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        mongo.db.users.insert_one({
            "name": request.form["name"],
            "email": request.form["email"],
            "password": generate_password_hash(request.form["password"]),
            "role": "participant",
            "bio": "",
            "age": "",
            "gender": ""
        })
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ================== HOME ================== #

@app.route("/home")
@login_required
def home():
    user = mongo.db.users.find_one({"_id": ObjectId(session["user_id"])})
    return render_template("home.html", user=user)

# ================== EVENTS ================== #

@app.route("/events")
@login_required
def events():
    events = mongo.db.events.find()
    return render_template("events.html", events=events)

# ================== ADMIN DASHBOARD ================== #

@app.route("/admin", methods=["GET", "POST"])
@login_required
@admin_required
def admin():
    if request.method == "POST":
        mongo.db.events.insert_one({
            "title": request.form["title"],
            "description": request.form["description"],
            "start_date": datetime.strptime(request.form["start"], "%Y-%m-%d"),
            "end_date": datetime.strptime(request.form["end"], "%Y-%m-%d")
        })
        flash("Event created")

    events = mongo.db.events.find()
    return render_template("admin.html", events=events)

@app.route("/admin/event/delete/<event_id>")
@login_required
@admin_required
def delete_event(event_id):
    mongo.db.events.delete_one({"_id": ObjectId(event_id)})
    mongo.db.problem_statements.delete_many({"event_id": event_id})
    mongo.db.submissions.delete_many({"event_id": event_id})
    flash("Event deleted")
    return redirect(url_for("admin"))

# ================== PROBLEMS (ADMIN) ================== #

@app.route("/admin/problems/<event_id>", methods=["GET", "POST"])
@login_required
@admin_required
def admin_problems(event_id):
    if request.method == "POST":
        mongo.db.problem_statements.insert_one({
            "event_id": event_id,
            "title": request.form["title"],
            "description": request.form["description"],
            "max_size_mb": 20
        })
        flash("Problem added")

    event = mongo.db.events.find_one({"_id": ObjectId(event_id)})
    problems = mongo.db.problem_statements.find({"event_id": event_id})

    return render_template("admin_problems.html", event=event, problems=problems)

@app.route("/admin/problems/edit/<problem_id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_problem(problem_id):
    problem = mongo.db.problem_statements.find_one({"_id": ObjectId(problem_id)})

    if request.method == "POST":
        mongo.db.problem_statements.update_one(
            {"_id": ObjectId(problem_id)},
            {"$set": {
                "title": request.form["title"],
                "description": request.form["description"],
                "max_size_mb": 20
            }}
        )
        flash("Problem updated")
        return redirect(url_for("admin_problems", event_id=problem["event_id"]))

    return render_template("edit_problem.html", problem=problem)

@app.route("/admin/problems/delete/<problem_id>")
@login_required
@admin_required
def delete_problem(problem_id):
    problem = mongo.db.problem_statements.find_one({"_id": ObjectId(problem_id)})
    mongo.db.problem_statements.delete_one({"_id": ObjectId(problem_id)})
    mongo.db.submissions.delete_many({"problem_id": problem_id})
    flash("Problem deleted")
    return redirect(url_for("admin_problems", event_id=problem["event_id"]))

# ================== PROBLEMS (USER) ================== #

@app.route("/problems/<event_id>")
@login_required
def problems(event_id):
    event = mongo.db.events.find_one({"_id": ObjectId(event_id)})

    if date.today() < event["start_date"].date():
        flash("Problems not released yet")
        return redirect(url_for("events"))

    problems = mongo.db.problem_statements.find({"event_id": event_id})
    return render_template("problems.html", event=event, problems=problems)

# ================== SUBMISSION ================== #

@app.route("/submit/<problem_id>", methods=["GET", "POST"])
@login_required
def submit(problem_id):
    problem = mongo.db.problem_statements.find_one({"_id": ObjectId(problem_id)})

    existing = mongo.db.submissions.find_one({
        "user_id": session["user_id"],
        "problem_id": problem_id
    })
    if existing:
        flash("You already submitted for this problem")
        return redirect(url_for("home"))

    if request.method == "POST":
        file = request.files["file"]

        if not file or not allowed_file(file.filename):
            flash("Invalid file")
            return redirect(request.url)

        file.seek(0, os.SEEK_END)
        size_mb = file.tell() / (1024 * 1024)
        file.seek(0)

        if size_mb > problem["max_size_mb"]:
            flash(f"File exceeds {problem['max_size_mb']} MB limit")
            return redirect(request.url)

        filename = f"{session['user_id']}_{secure_filename(file.filename)}"
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        mongo.db.submissions.insert_one({
            "user_id": session["user_id"],
            "problem_id": problem_id,
            "event_id": problem["event_id"],
            "filename": filename,
            "submitted_at": datetime.now(),
            "marks": None,
            "remarks": ""
        })

        flash("Submission successful")
        return redirect(url_for("home"))

    return render_template("submit.html", problem=problem)

# ================== FILE VIEW ================== #

@app.route("/uploads/<filename>")
@login_required
def view_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# ================== EVALUATION ================== #

@app.route("/evaluation")
@login_required
@admin_required
def evaluation():
    submissions = []

    for s in mongo.db.submissions.find():
        user = mongo.db.users.find_one({"_id": ObjectId(s["user_id"])})
        problem = mongo.db.problem_statements.find_one({"_id": ObjectId(s["problem_id"])})

        s["user_name"] = user["name"]
        s["problem_title"] = problem["title"]
        submissions.append(s)

    return render_template("evaluation.html", submissions=submissions)

@app.route("/evaluate/<submission_id>", methods=["POST"])
@login_required
@admin_required
def evaluate(submission_id):
    mongo.db.submissions.update_one(
        {"_id": ObjectId(submission_id)},
        {"$set": {
            "marks": int(request.form["marks"]),
            "remarks": request.form["remarks"]
        }}
    )
    flash("Evaluation saved")
    return redirect(url_for("evaluation"))

# ================== RANKINGS ================== #

@app.route("/rankings/<event_id>")
@login_required
def rankings(event_id):
    pipeline = [
        {"$match": {
            "event_id": event_id,
            "marks": {"$ne": None}
        }},
        {"$group": {
            "_id": "$user_id",
            "total_marks": {"$sum": "$marks"}
        }},
        {"$sort": {"total_marks": -1}}
    ]

    results = list(mongo.db.submissions.aggregate(pipeline))
    leaderboard = []

    for rank, r in enumerate(results, start=1):
        user = mongo.db.users.find_one({"_id": ObjectId(r["_id"])})
        leaderboard.append({
            "rank": rank,
            "name": user["name"],
            "score": r["total_marks"]
        })

    return render_template("rankings.html", leaderboard=leaderboard)

# ================== PROFILE ================== #

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    uid = ObjectId(session["user_id"])

    if request.method == "POST":
        mongo.db.users.update_one(
            {"_id": uid},
            {"$set": {
                "name": request.form["name"],
                "bio": request.form["bio"],
                "age": request.form["age"],
                "gender": request.form["gender"]
            }}
        )

    user = mongo.db.users.find_one({"_id": uid})
    return render_template("profile.html", user=user)

# ================== RUN ================== #

if __name__ == "__main__":
    app.run(debug=True)
