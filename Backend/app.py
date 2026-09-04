from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os, json, re

# ===== Flask + MySQL =====
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASS = os.environ.get("MYSQL_PASS", "")
MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_DB   = os.environ.get("MYSQL_DB", "ecs_learning")

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SQLALCHEMY_DATABASE_URI"] = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASS}@{MYSQL_HOST}/{MYSQL_DB}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "dev-secret-change-me"

db = SQLAlchemy(app)

# ===========================
# Password Policy
# ===========================
PWD_POLICY_REGEX = re.compile(r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[^A-Za-z0-9]).{10,}$')
def is_password_valid(pwd: str) -> bool:
    return bool(PWD_POLICY_REGEX.match(pwd or ""))

# ===========================
# MODELS
# ===========================
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    phone = db.Column(db.String(50))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="user")
    active = db.Column(db.Boolean, default=True)
    points = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)

class Lesson(db.Model):
    __tablename__ = "lessons"
    id = db.Column(db.Integer, primary_key=True)
    module = db.Column(db.String(120), default="Cyber Safety Basics")
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text)
    video = db.Column(db.String(300))

class Quiz(db.Model):
    __tablename__ = "quizzes"
    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    question = db.Column(db.String(400), nullable=False)
    options_json = db.Column(db.Text, nullable=False)
    correct_index = db.Column(db.Integer, nullable=False)

class UserLesson(db.Model):
    __tablename__ = "user_lessons"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    completed = db.Column(db.Boolean, default=False)

class Achievement(db.Model):
    __tablename__ = "achievements"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True)
    description = db.Column(db.String(300))

class UserAchievement(db.Model):
    __tablename__ = "user_achievements"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievements.id'), nullable=False)

class ForumPost(db.Model):
    __tablename__ = "forum_posts"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    text = db.Column(db.Text, nullable=False)
    ts = db.Column(db.String(40), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))

class SupportMessage(db.Model):
    __tablename__ = "support_messages"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    from_admin = db.Column(db.Boolean, default=False)
    text = db.Column(db.Text, nullable=False)
    ts = db.Column(db.String(40), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))

# ===========================
# SIMPLE SESSION
# ===========================
SESSIONS = {}
def current_user():
    ip = request.remote_addr
    uid = SESSIONS.get(ip)
    if not uid: return None
    return db.session.get(User, uid)

# ===========================
# ROUTES
# ===========================
@app.route("/")
def home():
    return render_template("index.html")

# ---------------------
# FAQ PAGE
# ---------------------
@app.route("/faq")
def faq_page():
    return render_template("faq.html")


@app.route("/static/<path:path>")
def send_static(path):
    return send_from_directory("static", path)

# ===========================
# AUTH
# ===========================
@app.post("/api/register")
def api_register():
    data = request.get_json() or {}
    name = data.get("name","").strip()
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()
    pwd = data.get("password") or ""

    if not name or not email or not pwd:
        return jsonify(ok=False, msg="Missing fields"), 400

    if not is_password_valid(pwd):
        return jsonify(ok=False, msg="Weak password"), 400

    if User.query.filter_by(email=email).first():
        return jsonify(ok=False, msg="user_exists"), 409

    u = User(name=name, email=email, phone=phone,
             password_hash=generate_password_hash(pwd))
    db.session.add(u)
    db.session.commit()
    return jsonify(ok=True)

@app.post("/api/login")
def api_login():
    data = request.get_json() or {}
    ident = (data.get("id") or "").strip().lower()
    pwd = data.get("password") or ""

    u = User.query.filter((User.email==ident)|(User.phone==ident)).first()
    if not u or not u.active:
        return jsonify(ok=False, msg="not_found_or_inactive"), 404

    if not check_password_hash(u.password_hash, pwd):
        return jsonify(ok=False, msg="wrong_password"), 401

    SESSIONS[request.remote_addr] = u.id

    if u.role == "admin":
        return jsonify(ok=True, redirect="/admin/lessons")

    return jsonify(ok=True, redirect="/")

@app.post("/api/logout")
def api_logout():
    SESSIONS.pop(request.remote_addr, None)
    return jsonify(ok=True)

# ===========================
# SESSION
# ===========================
@app.get("/api/session")
def api_session():
    u = current_user()
    if not u:
        return jsonify(ok=False)
    return jsonify(ok=True, user={
        "id": u.id, "name": u.name, "email": u.email,
        "points": u.points, "level": u.level, "role": u.role
    })

# ===========================
# CONTENT
# ===========================
@app.get("/api/content")
def api_content():
    modules = {}
    for l in Lesson.query.order_by(Lesson.id).all():
        modules.setdefault(l.module, []).append({
            "id": l.id, "title": l.title, "body": l.body, "video": l.video
        })

    return jsonify({"modules": [{"title": m, "lessons": modules[m]} for m in modules]})

# ===========================
# LESSON COMPLETE + ACHIEVEMENTS
# ===========================
@app.post("/api/lesson/complete")
def api_lesson_complete():
    u = current_user()
    if not u:
        return jsonify(ok=False, msg="not_logged"), 401

    lesson_id = (request.get_json() or {}).get("lesson_id")
    lesson = db.session.get(Lesson, lesson_id)
    if not lesson:
        return jsonify(ok=False, msg="no_lesson"), 404

    row = UserLesson.query.filter_by(user_id=u.id, lesson_id=lesson_id).first()
    if not row:
        row = UserLesson(user_id=u.id, lesson_id=lesson_id, completed=True)
        db.session.add(row)
    else:
        row.completed = True

    u.points += 50
    u.level = 1 + u.points // 200

    new_ach = []

    # Achievement لكل درس
    lesson_ach_name = f"Lesson {lesson_id} Complete"
    exists = UserAchievement.query.join(Achievement).filter(
        UserAchievement.user_id==u.id,
        Achievement.name==lesson_ach_name
    ).first()

    if not exists:
        ach = Achievement.query.filter_by(name=lesson_ach_name).first()
        if not ach:
            ach = Achievement(name=lesson_ach_name, description=f"You completed lesson {lesson_id}")
            db.session.add(ach)
            db.session.commit()

        db.session.add(UserAchievement(user_id=u.id, achievement_id=ach.id))
        new_ach.append(lesson_ach_name)

    # First Steps
    first_exists = UserAchievement.query.join(Achievement).filter(
        UserAchievement.user_id==u.id,
        Achievement.name=="First Steps"
    ).first()

    if not first_exists:
        ach = Achievement.query.filter_by(name="First Steps").first()
        if ach:
            db.session.add(UserAchievement(user_id=u.id, achievement_id=ach.id))
            new_ach.append("First Steps")

    # All Done
    total_lessons = Lesson.query.count()
    completed = UserLesson.query.filter_by(user_id=u.id, completed=True).count()

    if completed == total_lessons:
        all_done_exists = UserAchievement.query.join(Achievement).filter(
            UserAchievement.user_id==u.id,
            Achievement.name=="All Done"
        ).first()

        if not all_done_exists:
            ach = Achievement.query.filter_by(name="All Done").first()
            if ach:
                db.session.add(UserAchievement(user_id=u.id, achievement_id=ach.id))
                new_ach.append("All Done")

    db.session.commit()

    progress_pct = int((completed / total_lessons) * 100) if total_lessons else 0

    return jsonify(ok=True,
                   points=u.points,
                   level=u.level,
                   progress_pct=progress_pct,
                   new_achievements=new_ach)

# ===========================
# QUIZZES + ACHIEVEMENTS
# ===========================
@app.get("/api/quizzes/<int:lesson_id>")
def api_get_quizzes(lesson_id):
    qs = Quiz.query.filter_by(lesson_id=lesson_id).all()
    return jsonify([{
        "id": q.id,
        "lesson_id": q.lesson_id,
        "question": q.question,
        "options_json": q.options_json
    } for q in qs])

@app.post("/api/submit_quiz/<int:lesson_id>")
def api_submit_quiz(lesson_id):
    u = current_user()
    if not u:
        return jsonify(ok=False, msg="not_logged"), 401

    answers = (request.get_json() or {}).get("answers") or []
    qs = Quiz.query.filter_by(lesson_id=lesson_id).all()

    score = 0
    for i, q in enumerate(qs):
        try:
            if int(answers[i]) == q.correct_index:
                score += 1
        except:
            pass

    total = len(qs)
    passed = score >= max(1, total) * 0.6
    new_ach = []

    # Achievement لكل Quiz
    quiz_ach_name = f"Quiz {lesson_id} Passed"
    exists = UserAchievement.query.join(Achievement).filter(
        UserAchievement.user_id==u.id,
        Achievement.name==quiz_ach_name
    ).first()

    if passed and not exists:
        ach = Achievement.query.filter_by(name=quiz_ach_name).first()
        if not ach:
            ach = Achievement(name=quiz_ach_name, description=f"You passed quiz {lesson_id}")
            db.session.add(ach)
            db.session.commit()

        db.session.add(UserAchievement(user_id=u.id, achievement_id=ach.id))
        new_ach.append(quiz_ach_name)

    # Quiz Whiz
    if total > 0 and score == total:
        perfect_exists = UserAchievement.query.join(Achievement).filter(
            UserAchievement.user_id==u.id,
            Achievement.name=="Quiz Whiz"
        ).first()
        if not perfect_exists:
            ach = Achievement.query.filter_by(name="Quiz Whiz").first()
            if ach:
                db.session.add(UserAchievement(user_id=u.id, achievement_id=ach.id))
                new_ach.append("Quiz Whiz")

    if passed:
        u.points += 50
        u.level = 1 + u.points // 200

    db.session.commit()

    return jsonify(ok=True,
                   score=score,
                   total=total,
                   result="Passed" if passed else "Failed",
                   points=u.points,
                   level=u.level,
                   new_achievements=new_ach)

# ===========================
# ACHIEVEMENTS LIST
# ===========================
@app.get("/api/user/achievements")
def api_user_ach():
    u = current_user()
    if not u:
        return jsonify({"badges":[]})

    rows = UserAchievement.query.filter_by(user_id=u.id).all()
    ids = [r.achievement_id for r in rows]
    badges = Achievement.query.filter(Achievement.id.in_(ids)).all() if ids else []

    return jsonify({"badges":[{"name": b.name, "description": b.description} for b in badges]})

# ===========================
# FORUM
# ===========================
@app.get("/api/forum")
def api_forum_list():
    posts = ForumPost.query.order_by(ForumPost.id.desc()).all()
    arr = []
    for p in posts:
        u = db.session.get(User, p.user_id)
        arr.append({
            "by": u.name if u else "Unknown",
            "text": p.text,
            "ts": p.ts
        })
    return jsonify(arr)

@app.post("/api/forum")
def api_forum_post():
    u = current_user()
    if not u:
        return jsonify(ok=False, msg="not_logged"), 401

    txt = (request.get_json() or {}).get("content","").strip()
    if not txt:
        return jsonify(ok=False, msg="empty"), 400

    db.session.add(ForumPost(user_id=u.id, text=txt))
    db.session.commit()
    return jsonify(ok=True)
# ===========================
# ADMIN
# ===========================

def require_admin():
    u = current_user()
    if not u or u.role != "admin":
        return None, (jsonify(ok=False, error="forbidden"), 403)
    return u, None

# ---------------------------
# ADMIN PAGES
# ---------------------------

@app.route("/admin/lessons")
def admin_lessons_page():
    u = current_user()
    if not u or u.role != "admin":
        return "Access denied", 403
    return render_template("admin_lessons.html")


@app.route("/admin/dashboard")
def admin_dashboard_page():
    u = current_user()
    if not u or u.role != "admin":
        return "Access denied", 403
    return render_template("admin_dashboard.html")

# ---------------------------
# ADMIN – LESSON MANAGEMENT
# ---------------------------

@app.get("/api/admin/lessons")
def api_admin_lessons():
    u, err = require_admin()
    if err: 
        return err

    rows = Lesson.query.order_by(Lesson.id.desc()).all()
    return jsonify(ok=True, items=[
        {
            "id": r.id,
            "title": r.title,
            "module": r.module,
            "body": r.body,
            "video": r.video
        } for r in rows
    ])


@app.post("/api/admin/lessons")
def api_admin_add_lesson():
    u, err = require_admin()
    if err: 
        return err

    data = request.get_json() or {}
    title = data.get("title", "").strip()
    module = data.get("module", "").strip()
    body = data.get("body", "").strip()
    video = data.get("video", "").strip()

    if not title or not module or not body:
        return jsonify(ok=False, error="missing_fields"), 400

    row = Lesson(title=title, module=module, body=body, video=video)
    db.session.add(row)
    db.session.commit()

    return jsonify(ok=True, id=row.id)


@app.put("/api/admin/lessons/<int:lesson_id>")
def api_admin_update_lesson(lesson_id):
    u, err = require_admin()
    if err: 
        return err

    data = request.get_json() or {}
    r = db.session.get(Lesson, lesson_id)

    if not r:
        return jsonify(ok=False, error="not_found"), 404

    r.title = data.get("title", "").strip()
    r.module = data.get("module", "").strip()
    r.body = data.get("body", "").strip()
    r.video = data.get("video", "").strip()

    db.session.commit()
    return jsonify(ok=True)


@app.delete("/api/admin/lessons/<int:lesson_id>")
def api_admin_delete_lesson(lesson_id):
    u, err = require_admin()
    if err: 
        return err

    r = db.session.get(Lesson, lesson_id)
    if not r:
        return jsonify(ok=False, error="not_found"), 404

    db.session.delete(r)
    db.session.commit()
    return jsonify(ok=True)

# ---------------------------
# ADMIN – DELETE USER
# ---------------------------
@app.delete("/api/admin/users/<int:uid>")
def api_admin_delete_user(uid):
    u, err = require_admin()
    if err:
        return err

    usr = db.session.get(User, uid)
    if not usr:
        return jsonify(ok=False, error="not_found"), 404

    # احذف كل بياناته المرتبطة
    UserLesson.query.filter_by(user_id=uid).delete()
    UserAchievement.query.filter_by(user_id=uid).delete()
    ForumPost.query.filter_by(user_id=uid).delete()
    SupportMessage.query.filter_by(user_id=uid).delete()

    db.session.delete(usr)
    db.session.commit()

    return jsonify(ok=True)


# ---------------------------
# ADMIN – USERS LIST
# ---------------------------

@app.get("/api/admin/users")
def api_admin_users():
    u, err = require_admin()
    if err:
        return err

    users = User.query.order_by(User.id).all()
    output = []

    for usr in users:
        lessons_completed = UserLesson.query.filter_by(user_id=usr.id, completed=True).count()
        total_lessons = Lesson.query.count()
        quizzes_passed = UserAchievement.query.join(Achievement).filter(
            UserAchievement.user_id == usr.id,
            Achievement.name.like("Quiz%")
        ).count()

        progress = int((lessons_completed / total_lessons) * 100) if total_lessons else 0

        output.append({
            "id": usr.id,
            "name": usr.name,
            "email": usr.email,
            "role": usr.role,
            "active": usr.active,
            "points": usr.points,
            "level": usr.level,
            "progress": progress,
            "lessons_completed": lessons_completed,
            "quizzes_passed": quizzes_passed
        })

    return jsonify(ok=True, users=output)


# ---------------------------
# ADMIN – TOGGLE USER ACTIVE
# ---------------------------

@app.post("/api/admin/users/toggle/<int:uid>")
def api_admin_toggle_user(uid):
    u, err = require_admin()
    if err:
        return err

    usr = db.session.get(User, uid)
    if not usr:
        return jsonify(ok=False, error="not_found")

    usr.active = not usr.active
    db.session.commit()

    return jsonify(ok=True, active=usr.active)

# ---------------------------
# ADMIN – PROMOTE USER TO ADMIN
# ---------------------------

@app.post("/api/admin/users/make_admin/<int:uid>")
def api_admin_make_admin(uid):
    u, err = require_admin()
    if err:
        return err

    usr = db.session.get(User, uid)
    if not usr:
        return jsonify(ok=False, error="not_found")

    usr.role = "admin"
    db.session.commit()

    return jsonify(ok=True)

# ===========================
# SUPPORT CHAT ADMIN
# ===========================
@app.route("/admin/support")
def admin_support_page():
    u = current_user()
    if not u or u.role != "admin":
        return "Access denied", 403
    return render_template("admin_support.html")

@app.get("/api/admin/support/users")
def api_admin_support_users():
    u, err = require_admin()
    if err: return err

    rows = db.session.query(User.id, User.name).join(SupportMessage).group_by(User.id).all()
    return jsonify(ok=True, users=[{"id": r.id, "name": r.name} for r in rows])

@app.get("/api/admin/support/messages/<int:uid>")
def api_admin_support_messages(uid):
    u, err = require_admin()
    if err: return err

    msgs = SupportMessage.query.filter_by(user_id=uid).order_by(SupportMessage.id).all()
    return jsonify(ok=True, messages=[{
        "id": m.id,
        "from_admin": m.from_admin,
        "text": m.text,
        "ts": m.ts
    } for m in msgs])

@app.post("/api/admin/support/send/<int:uid>")
def api_admin_support_send(uid):
    u, err = require_admin()
    if err: return err

    text = (request.get_json() or {}).get("text","").strip()
    if not text:
        return jsonify(ok=False)

    msg = SupportMessage(user_id=uid, from_admin=True, text=text)
    db.session.add(msg)
    db.session.commit()
    return jsonify(ok=True)

# ===========================
# SUPPORT USER SIDE
# ===========================
@app.get("/api/support")
def api_support_messages():
    u = current_user()
    if not u:
        return jsonify(ok=False, msg="not_logged"), 401

    msgs = SupportMessage.query.filter_by(user_id=u.id).order_by(SupportMessage.id).all()
    return jsonify(ok=True, messages=[{
        "id": m.id,
        "from_admin": m.from_admin,
        "text": m.text,
        "ts": m.ts
    } for m in msgs])

@app.post("/api/support")
def api_support_post():
    u = current_user()
    if not u:
        return jsonify(ok=False, msg="not_logged"), 401

    text = (request.get_json() or {}).get("text","").strip()
    if not text:
        return jsonify(ok=False, msg="empty"), 400

    db.session.add(SupportMessage(user_id=u.id, text=text, from_admin=False))
    db.session.commit()
    return jsonify(ok=True)

# ===========================
# RUN
# ===========================
if __name__ == "__main__":
    app.run(debug=True)
