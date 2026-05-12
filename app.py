import os
from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()

    cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS questions (id INTEGER PRIMARY KEY, question TEXT, op1 TEXT, op2 TEXT, op3 TEXT, op4 TEXT, answer TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS scores (id INTEGER PRIMARY KEY, username TEXT, score INTEGER)")

    # Default admin
    cur.execute("INSERT OR IGNORE INTO users VALUES (1, 'admin', 'admin123', 'admin')")

    conn.commit()
    conn.close()

init_db()

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        conn = sqlite3.connect("quiz.db")
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p))
        user = cur.fetchone()
        conn.close()

        if user:
            session["user"] = u
            session["role"] = user[3]

            if user[3] == "admin":
                return redirect("/admin")
            else:
                return redirect("/quiz")

    return render_template("login.html")

# ---------------- ADMIN ----------------
@app.route("/admin")
def admin():
    if session.get("role") != "admin":
        return redirect("/")
    return render_template("admin.html")

# REGISTER STUDENT
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        conn = sqlite3.connect("quiz.db")
        cur = conn.cursor()
        
        # Check if user already exists
        cur.execute("SELECT * FROM users WHERE username=?", (u,))
        if cur.fetchone():
            conn.close()
            return render_template("register.html", error="Username already exists")
        
        # Create new student user
        cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    (u, p, "student"))
        conn.commit()
        conn.close()
        
        return redirect("/")
    
    return render_template("register.html")

# CREATE QUIZ
@app.route("/create", methods=["GET", "POST"])
def create():
    if session.get("role") != "admin":
        return redirect("/")
    
    if request.method == "POST":
        q = request.form["q"]
        op1 = request.form["op1"]
        op2 = request.form["op2"]
        op3 = request.form["op3"]
        op4 = request.form["op4"]
        ans = request.form["ans"]

        conn = sqlite3.connect("quiz.db")
        cur = conn.cursor()
        cur.execute("INSERT INTO questions (question, op1, op2, op3, op4, answer) VALUES (?, ?, ?, ?, ?, ?)",
                    (q, op1, op2, op3, op4, ans))
        conn.commit()
        conn.close()
        
        return render_template("create_quiz.html", success="Question added successfully!")

    return render_template("create_quiz.html")

# ---------------- QUIZ ----------------
@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    if session.get("role") != "student":
        return redirect("/")
    
    if "qno" not in session:
        session["qno"] = 0
        session["score"] = 0
        session["feedback"] = None

    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM questions")
    data = cur.fetchall()
    conn.close()

    if not data:
        return "<h2 style='text-align:center; margin-top:50px;'>No questions available. Please check back later.</h2>"

    if request.method == "POST":
        selected = request.form.get("answer")
        correct = data[session["qno"]][6]

        if selected == correct:
            session["score"] += 1
            session["feedback"] = "Correct!"
        else:
            session["feedback"] = "Wrong!"

        session["qno"] += 1

    if session["qno"] >= len(data):
        score = session["score"]

        conn = sqlite3.connect("quiz.db")
        cur = conn.cursor()
        cur.execute("INSERT INTO scores (username, score) VALUES (?, ?)",
                    (session["user"], score))
        conn.commit()
        conn.close()

        return redirect("/result")

    q = data[session["qno"]]
    feedback = session.pop("feedback", None)
    return render_template("quiz.html", q=q, question_number=session["qno"]+1, total_questions=len(data), feedback=feedback)

# ---------------- RESULT ----------------
@app.route("/result")
def result():
    score = session.get("score", 0)
    session.clear()
    return render_template("result.html", score=score)

# ---------------- LEADERBOARD ----------------
@app.route("/leaderboard")
def leaderboard():
    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()
    cur.execute("SELECT username, MAX(score) FROM scores GROUP BY username ORDER BY MAX(score) DESC")
    data = cur.fetchall()
    conn.close()

    return render_template("leaderboard.html", data=data)

# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ERROR HANDLERS
@app.errorhandler(404)
def not_found(error):
    return redirect("/")

# RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True)
