import os
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, send_from_directory, jsonify
)
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime, date, timedelta
from bson.objectid import ObjectId
from bson.errors import InvalidId

import judge


def _normalize_output(text):
    """Normalizes trivial, meaningless formatting noise before comparing judge
    output - CRLF vs LF line endings, trailing whitespace on each line, and
    leading/trailing blank lines - without touching meaningful internal
    spacing (column alignment in problems like the pizza bill still matters
    and is still enforced)."""
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)

# Load a local .env file if present (python-dotenv). This only affects local
# dev - on Render/Railway/Heroku/Vercel you set these in the platform's own
# env var settings instead, and this call is a harmless no-op there since
# there's no .env file in the deployed image/bundle.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ================== APP CONFIG ================== #

app = Flask(__name__)

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    if os.environ.get("VERCEL") or os.environ.get("RENDER") or os.environ.get("DYNO") or os.environ.get("RAILWAY_ENVIRONMENT"):
        # Running on a known PaaS with no SECRET_KEY set - fail loudly instead
        # of silently starting with a guessable key (breaks session security,
        # and a random-per-boot key breaks sessions across multiple workers).
        raise RuntimeError(
            "SECRET_KEY environment variable is not set. "
            "Set it in your platform's environment variables before deploying."
        )
    app.logger.warning(
        "SECRET_KEY not set - using an insecure dev-only default. "
        "This is fine for local testing, but set SECRET_KEY before deploying."
    )
    SECRET_KEY = "dev-only-insecure-key-change-me"
app.secret_key = SECRET_KEY

MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    if os.environ.get("VERCEL") or os.environ.get("RENDER") or os.environ.get("DYNO") or os.environ.get("RAILWAY_ENVIRONMENT"):
        raise RuntimeError(
            "MONGO_URI environment variable is not set. "
            "Set it in your platform's environment variables before deploying."
        )
    app.logger.warning(
        "MONGO_URI not set - defaulting to a local MongoDB instance for dev "
        "(mongodb://localhost:27017/DevHost). Set MONGO_URI before deploying."
    )
    MONGO_URI = "mongodb://localhost:27017/DevHost"
app.config["MONGO_URI"] = MONGO_URI

if os.environ.get("VERCEL"):
    # Vercel's filesystem is read-only except /tmp, and /tmp is wiped between
    # invocations - files saved here will NOT persist. This just stops the
    # app from crashing on import; file-upload submissions still won't
    # survive on Vercel. Use the Docker deploy path if you need real
    # persistent uploads.
    app.config["UPLOAD_FOLDER"] = "/tmp/uploads"
else:
    app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20MB hard limit

mongo = PyMongo(app)
try:
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
except OSError as e:
    app.logger.error(f"Could not create upload folder {app.config['UPLOAD_FOLDER']!r}: {e}")

ALLOWED_EXTENSIONS = {"zip", "ppt", "pptx", "pdf"}
CONTEST_DURATION_MINUTES = 45

# ================== HELPERS ================== #

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def to_object_id(id_str):
    """Safely convert a string to ObjectId, returns None if invalid."""
    try:
        return ObjectId(id_str)
    except (InvalidId, TypeError):
        return None

def problem_category(problem):
    """Contest grouping: explicitly tagged problems win; legacy data falls back
    to the existing three code + three file problem split."""
    category = (problem.get("contest_category") or "").strip().lower()
    if category in {"java", "java basics", "sorting"}:
        return "java" if category != "sorting" else "sorting"
    return "sorting" if problem.get("problem_type") == "code" else "java"

def contest_started_at(event_id):
    key = f"contest_started_{event_id}"
    raw = session.get(key)
    if raw:
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            session.pop(key, None)
    started = datetime.now()
    session[key] = started.isoformat()
    return started

def contest_status(event_id):
    started = contest_started_at(event_id)
    ends = started + timedelta(minutes=CONTEST_DURATION_MINUTES)
    remaining = max(0, int((ends - datetime.now()).total_seconds()))
    submissions = list(mongo.db.submissions.find({"user_id": session["user_id"], "event_id": event_id}))
    chosen = set()
    for submission in submissions:
        selected_problem = mongo.db.problem_statements.find_one({"_id": to_object_id(submission.get("problem_id"))})
        if selected_problem:
            chosen.add(problem_category(selected_problem))
    return {"started_at": started, "ends_at": ends, "remaining_seconds": remaining,
            "java_done": "java" in chosen, "sorting_done": "sorting" in chosen,
            "complete": {"java", "sorting"}.issubset(chosen)}

def contest_problem_allowed(problem):
    status = contest_status(problem["event_id"])
    category = problem_category(problem)
    if status["remaining_seconds"] <= 0:
        return False, "The 45-minute contest has ended."
    if status[f"{category}_done"]:
        return False, f"You have already selected your {category.title()} question."
    return True, ""

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
        oid = to_object_id(session.get("user_id"))
        user = mongo.db.users.find_one({"_id": oid}) if oid else None
        if not user or user.get("role") != "admin":
            flash("Admin access only")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return wrap

# ================== CREATE ADMIN ================== #

def create_admin():
    try:
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
    except Exception as e:
        # Don't let a Mongo connectivity issue at boot take down every route.
        app.logger.error(f"create_admin failed (check MONGO_URI / Atlas network access): {e}")

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
        if mongo.db.users.find_one({"email": request.form["email"]}):
            flash("An account with that email already exists")
            return redirect(url_for("register"))

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
    oid = to_object_id(session["user_id"])
    user = mongo.db.users.find_one({"_id": oid}) if oid else None
    if not user:
        session.clear()
        flash("Your session is no longer valid, please log in again")
        return redirect(url_for("login"))
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
        try:
            start = datetime.strptime(request.form["start"], "%Y-%m-%d")
            end = datetime.strptime(request.form["end"], "%Y-%m-%d")
        except ValueError:
            flash("Invalid date format")
            return redirect(url_for("admin"))

        mongo.db.events.insert_one({
            "title": request.form["title"],
            "description": request.form["description"],
            "start_date": start,
            "end_date": end
        })
        flash("Event created")

    events = mongo.db.events.find()
    return render_template("admin.html", events=events)

@app.route("/admin/event/delete/<event_id>")
@login_required
@admin_required
def delete_event(event_id):
    oid = to_object_id(event_id)
    if not oid:
        flash("Invalid event")
        return redirect(url_for("admin"))

    mongo.db.events.delete_one({"_id": oid})
    mongo.db.problem_statements.delete_many({"event_id": event_id})
    mongo.db.submissions.delete_many({"event_id": event_id})
    flash("Event deleted")
    return redirect(url_for("admin"))

# ================== PROBLEMS (ADMIN) ================== #

@app.route("/admin/problems/<event_id>", methods=["GET", "POST"])
@login_required
@admin_required
def admin_problems(event_id):
    event_oid = to_object_id(event_id)
    event = mongo.db.events.find_one({"_id": event_oid}) if event_oid else None
    if not event:
        flash("Event not found")
        return redirect(url_for("admin"))

    if request.method == "POST":
        problem_type = request.form.get("problem_type", "file")

        doc = {
            "event_id": event_id,
            "title": request.form["title"],
            "description": request.form["description"],
            "problem_type": problem_type,
            "difficulty": request.form.get("difficulty", "Medium"),
            "max_size_mb": 20,
        }

        if problem_type == "code":
            doc.update({
                "constraints": request.form.get("constraints", ""),
                "input_format": request.form.get("input_format", ""),
                "output_format": request.form.get("output_format", ""),
                "sample_input": request.form.get("sample_input", "").replace("\r\n", "\n"),
                "sample_output": request.form.get("sample_output", "").replace("\r\n", "\n"),
                "time_limit_ms": int(request.form.get("time_limit_ms") or 3000),
                "starter_code": {
                    "python3": request.form.get("starter_python", ""),
                    "c": request.form.get("starter_c", ""),
                    "cpp": request.form.get("starter_cpp", ""),
                    "java": request.form.get("starter_java", ""),
                }
            })

        result = mongo.db.problem_statements.insert_one(doc)

        # Auto-seed the sample I/O as a visible sample test case, if given.
        if problem_type == "code" and doc.get("sample_input") and doc.get("sample_output"):
            mongo.db.test_cases.insert_one({
                "problem_id": str(result.inserted_id),
                "input": doc["sample_input"],
                "output": doc["sample_output"],
                "is_sample": True,
                "order": 1
            })

        flash("Problem added")

    problems = list(mongo.db.problem_statements.find({"event_id": event_id}))
    return render_template("admin_problems.html", event=event, problems=problems)

@app.route("/admin/problems/edit/<problem_id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_problem(problem_id):
    oid = to_object_id(problem_id)
    problem = mongo.db.problem_statements.find_one({"_id": oid}) if oid else None
    if not problem:
        flash("Problem not found")
        return redirect(url_for("admin"))

    if request.method == "POST":
        problem_type = request.form.get("problem_type", problem.get("problem_type", "file"))

        update = {
            "title": request.form["title"],
            "description": request.form["description"],
            "problem_type": problem_type,
            "difficulty": request.form.get("difficulty", "Medium"),
            "max_size_mb": 20,
        }

        if problem_type == "code":
            update.update({
                "constraints": request.form.get("constraints", ""),
                "input_format": request.form.get("input_format", ""),
                "output_format": request.form.get("output_format", ""),
                "sample_input": request.form.get("sample_input", "").replace("\r\n", "\n"),
                "sample_output": request.form.get("sample_output", "").replace("\r\n", "\n"),
                "time_limit_ms": int(request.form.get("time_limit_ms") or 3000),
                "starter_code": {
                    "python3": request.form.get("starter_python", ""),
                    "c": request.form.get("starter_c", ""),
                    "cpp": request.form.get("starter_cpp", ""),
                    "java": request.form.get("starter_java", ""),
                }
            })

        mongo.db.problem_statements.update_one({"_id": oid}, {"$set": update})
        flash("Problem updated")
        return redirect(url_for("admin_problems", event_id=problem["event_id"]))

    return render_template("edit_problem.html", problem=problem)

@app.route("/admin/problems/delete/<problem_id>")
@login_required
@admin_required
def delete_problem(problem_id):
    oid = to_object_id(problem_id)
    problem = mongo.db.problem_statements.find_one({"_id": oid}) if oid else None
    if not problem:
        flash("Problem not found")
        return redirect(url_for("admin"))

    mongo.db.problem_statements.delete_one({"_id": oid})
    mongo.db.submissions.delete_many({"problem_id": problem_id})
    mongo.db.test_cases.delete_many({"problem_id": problem_id})
    flash("Problem deleted")
    return redirect(url_for("admin_problems", event_id=problem["event_id"]))

# ================== TEST CASES (ADMIN) ================== #

@app.route("/admin/testcases/<problem_id>", methods=["GET", "POST"])
@login_required
@admin_required
def admin_testcases(problem_id):
    oid = to_object_id(problem_id)
    problem = mongo.db.problem_statements.find_one({"_id": oid}) if oid else None
    if not problem:
        flash("Problem not found")
        return redirect(url_for("home"))

    if request.method == "POST":
        next_order = mongo.db.test_cases.count_documents({"problem_id": problem_id}) + 1
        mongo.db.test_cases.insert_one({
            "problem_id": problem_id,
            "input": request.form.get("input", "").replace("\r\n", "\n"),
            "output": request.form.get("output", "").replace("\r\n", "\n"),
            "is_sample": "is_sample" in request.form,
            "order": next_order
        })
        flash("Test case added")
        return redirect(url_for("admin_testcases", problem_id=problem_id))

    tests = list(mongo.db.test_cases.find({"problem_id": problem_id}).sort("order", 1))
    return render_template("admin_testcases.html", problem=problem, tests=tests)

@app.route("/admin/testcases/delete/<test_id>")
@login_required
@admin_required
def delete_testcase(test_id):
    oid = to_object_id(test_id)
    test = mongo.db.test_cases.find_one({"_id": oid}) if oid else None
    if not test:
        flash("Test case not found")
        return redirect(url_for("home"))

    mongo.db.test_cases.delete_one({"_id": oid})
    flash("Test case deleted")
    return redirect(url_for("admin_testcases", problem_id=test["problem_id"]))

# ================== PROBLEMS (USER) ================== #

@app.route("/problems/<event_id>")
@login_required
def problems(event_id):
    oid = to_object_id(event_id)
    event = mongo.db.events.find_one({"_id": oid}) if oid else None
    if not event:
        flash("Event not found")
        return redirect(url_for("events"))

    if date.today() < event["start_date"].date():
        flash("Problems not released yet")
        return redirect(url_for("events"))

    problems = list(mongo.db.problem_statements.find({"event_id": event_id}))
    contest = contest_status(event_id)
    if contest["remaining_seconds"] <= 0:
        session.clear()
        flash("The 45-minute contest has ended. Please log in again.")
        return redirect(url_for("login"))
    for p in problems:
        p["contest_category"] = problem_category(p)
        sub = mongo.db.submissions.find_one({
            "user_id": session["user_id"],
            "problem_id": str(p["_id"])
        })
        if not sub:
            p["status"] = "todo"
        elif p.get("problem_type", "file") == "code":
            p["status"] = "solved" if sub.get("verdict") == "Accepted" else "attempted"
        else:
            p["status"] = "solved"

    return render_template("problems.html", event=event, problems=problems, contest=contest,
                           contest_duration_minutes=CONTEST_DURATION_MINUTES)

# ================== SOLVE (CODE EDITOR) ================== #

@app.route("/solve/<problem_id>")
@login_required
def solve(problem_id):
    oid = to_object_id(problem_id)
    problem = mongo.db.problem_statements.find_one({"_id": oid}) if oid else None
    if not problem:
        flash("Problem not found")
        return redirect(url_for("home"))

    if problem.get("problem_type", "file") != "code":
        return redirect(url_for("submit", problem_id=problem_id))

    samples = list(mongo.db.test_cases.find(
        {"problem_id": problem_id, "is_sample": True}
    ).sort("order", 1))

    last_submission = mongo.db.submissions.find_one(
        {"user_id": session["user_id"], "problem_id": problem_id},
        sort=[("submitted_at", -1)]
    )

    return render_template(
        "solve.html",
        problem=problem,
        samples=samples,
        starter=problem.get("starter_code", {}) or {},
        last_submission=last_submission,
        contest=contest_status(problem["event_id"])
    )

@app.route("/api/run/<problem_id>", methods=["POST"])
@login_required
def api_run(problem_id):
    oid = to_object_id(problem_id)
    problem = mongo.db.problem_statements.find_one({"_id": oid}) if oid else None
    if not problem:
        return jsonify({"error": "Problem not found"}), 404

    data = request.get_json(silent=True) or {}
    language = data.get("language", "python3")
    code = data.get("code", "")
    stdin_text = data.get("stdin", "")

    if not code.strip():
        return jsonify({"error": "Write some code before running"}), 400

    time_limit = (problem.get("time_limit_ms", 3000) / 1000.0) + 1  # headroom for custom runs
    result = judge.run_code(language, code, stdin_text, time_limit_sec=time_limit)
    return jsonify(result)

@app.route("/api/submit_code/<problem_id>", methods=["POST"])
@login_required
def api_submit_code(problem_id):
    oid = to_object_id(problem_id)
    problem = mongo.db.problem_statements.find_one({"_id": oid}) if oid else None
    if not problem:
        return jsonify({"error": "Problem not found"}), 404

    data = request.get_json(silent=True) or {}
    language = data.get("language", "python3")
    code = data.get("code", "")

    if not code.strip():
        return jsonify({"error": "Write some code before submitting"}), 400

    tests = list(mongo.db.test_cases.find({"problem_id": problem_id}).sort("order", 1))
    if not tests:
        return jsonify({"error": "No test cases configured for this problem yet"}), 400

    # Same +1s headroom as /api/run, so Submit isn't stricter than Run for
    # identical code - on CPU-throttled hosts (e.g. Render free tier) the two
    # endpoints previously used different effective limits, which could make
    # a submission time out even though the sample "Run" passed fine.
    time_limit = (problem.get("time_limit_ms", 3000) / 1000.0) + 1
    results = []
    passed = 0
    compile_error = None

    prepared = judge.prepare(language, code)
    if prepared.get("compile_error"):
        compile_error = prepared["compile_error"]
    else:
        try:
            for i, t in enumerate(tests, start=1):
                r = judge.run_prepared(prepared, t.get("input", ""), time_limit_sec=time_limit)

                ok = _normalize_output(r.get("stdout")) == _normalize_output(t.get("output"))
                if ok:
                    passed += 1

                entry = {
                    "index": i,
                    "is_sample": bool(t.get("is_sample")),
                    "passed": ok,
                    "timed_out": bool(r.get("timed_out")),
                }
                # Only leak the actual input/expected/output back to the client for
                # sample cases, so hidden test cases stay hidden after a submission.
                if t.get("is_sample"):
                    entry.update({
                        "input": t.get("input", ""),
                        "expected": t.get("output", ""),
                        "actual": r.get("stdout", ""),
                        "stderr": r.get("stderr", "")[:2000],
                    })
                results.append(entry)
        finally:
            judge.cleanup(prepared)

    total = len(tests)
    if compile_error:
        verdict = "Compile Error"
        marks = 0
    elif passed == total:
        verdict = "Accepted"
        marks = 100
    else:
        verdict = "Wrong Answer"
        marks = round((passed / total) * 100) if total else 0

    mongo.db.submissions.update_one(
        {"user_id": session["user_id"], "problem_id": problem_id},
        {"$set": {
            "user_id": session["user_id"],
            "problem_id": problem_id,
            "event_id": problem["event_id"],
            "contest_category": problem_category(problem),
            "language": language,
            "code": code,
            "verdict": verdict,
            "passed": passed,
            "total": total,
            "marks": marks,
            "remarks": "",
            "submitted_at": datetime.now(),
        }},
        upsert=True
    )

    return jsonify({
        "verdict": verdict,
        "passed": passed,
        "total": total,
        "marks": marks,
        "compile_error": compile_error,
        "results": results
    })

# ================== SUBMISSION ================== #

@app.route("/submit/<problem_id>", methods=["GET", "POST"])
@login_required
def submit(problem_id):
    oid = to_object_id(problem_id)
    problem = mongo.db.problem_statements.find_one({"_id": oid}) if oid else None
    if not problem:
        flash("Problem not found")
        return redirect(url_for("home"))

    if problem.get("problem_type", "file") == "code":
        return redirect(url_for("solve", problem_id=problem_id))

    existing = mongo.db.submissions.find_one({
        "user_id": session["user_id"],
        "problem_id": problem_id
    })
    if existing:
        flash("You already submitted for this problem")
        return redirect(url_for("home"))

    if request.method == "POST":
        file = request.files.get("file")

        if not file or not file.filename or not allowed_file(file.filename):
            flash("Invalid file")
            return redirect(request.url)

        file.seek(0, os.SEEK_END)
        size_mb = file.tell() / (1024 * 1024)
        file.seek(0)

        if size_mb > problem.get("max_size_mb", 20):
            flash(f"File exceeds {problem.get('max_size_mb', 20)} MB limit")
            return redirect(request.url)

        filename = f"{session['user_id']}_{secure_filename(file.filename)}"
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        mongo.db.submissions.insert_one({
            "user_id": session["user_id"],
            "problem_id": problem_id,
            "event_id": problem["event_id"],
            "contest_category": problem_category(problem),
            "filename": filename,
            "submitted_at": datetime.now(),
            "marks": None,
            "remarks": ""
        })

        flash("Submission successful")
        return redirect(url_for("home"))

    return render_template("submit.html", problem=problem, contest=contest_status(problem["event_id"]))

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
    oid = to_object_id(session["user_id"])
    current_user = mongo.db.users.find_one({"_id": oid})

    submissions = []
    for s in mongo.db.submissions.find():
        user_oid = to_object_id(s.get("user_id"))
        problem_oid = to_object_id(s.get("problem_id"))

        user = mongo.db.users.find_one({"_id": user_oid}) if user_oid else None
        problem = mongo.db.problem_statements.find_one({"_id": problem_oid}) if problem_oid else None

        s["user_name"] = user["name"] if user else "Unknown user"
        s["problem_title"] = problem["title"] if problem else "Unknown problem"
        submissions.append(s)

    return render_template("evaluation.html", submissions=submissions, user=current_user)

@app.route("/evaluate/<submission_id>", methods=["POST"])
@login_required
@admin_required
def evaluate(submission_id):
    oid = to_object_id(submission_id)
    if not oid:
        flash("Invalid submission")
        return redirect(url_for("evaluation"))

    try:
        marks = int(request.form["marks"])
    except (ValueError, KeyError):
        flash("Marks must be a number")
        return redirect(url_for("evaluation"))

    mongo.db.submissions.update_one(
        {"_id": oid},
        {"$set": {
            "marks": marks,
            "remarks": request.form.get("remarks", "")
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
        oid = to_object_id(r["_id"])
        user = mongo.db.users.find_one({"_id": oid}) if oid else None
        leaderboard.append({
            "rank": rank,
            "name": user["name"] if user else "Unknown user",
            "score": r["total_marks"]
        })

    return render_template("rankings.html", leaderboard=leaderboard)

# ================== PROFILE ================== #

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    oid = to_object_id(session["user_id"])
    if not oid:
        session.clear()
        return redirect(url_for("login"))

    if request.method == "POST":
        mongo.db.users.update_one(
            {"_id": oid},
            {"$set": {
                "name": request.form["name"],
                "bio": request.form["bio"],
                "age": request.form["age"],
                "gender": request.form["gender"]
            }}
        )

    user = mongo.db.users.find_one({"_id": oid})
    if not user:
        session.clear()
        return redirect(url_for("login"))

    return render_template("profile.html", user=user)

# ================== ERROR HANDLERS ================== #

@app.errorhandler(404)
def not_found(e):
    return "Page not found", 404

@app.errorhandler(500)
def server_error(e):
    app.logger.error(f"Server error: {e}")
    return "Something went wrong. Please try again shortly.", 500

# ================== RUN ================== #

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug_mode)