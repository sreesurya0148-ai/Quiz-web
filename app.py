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

    cur.execute("SELECT COUNT(*) FROM questions")
    question_count = cur.fetchone()[0]
    if question_count == 0:
        default_questions = [
            ("What is the capital of France?", "Berlin", "Madrid", "Paris", "Rome", "Paris"),
            ("Which planet is known as the Red Planet?", "Mars", "Venus", "Jupiter", "Saturn", "Mars"),
            ("What is the largest ocean on Earth?", "Atlantic", "Indian", "Pacific", "Arctic", "Pacific"),
            ("Who wrote 'Romeo and Juliet'?", "Mark Twain", "William Shakespeare", "Jane Austen", "Charles Dickens", "William Shakespeare"),
            ("What is 8 x 7?", "54", "56", "64", "72", "56"),
        ]
        cur.executemany(
            "INSERT INTO questions (question, op1, op2, op3, op4, answer) VALUES (?, ?, ?, ?, ?, ?)",
            default_questions
        )

    conn.commit()
    conn.close()

init_db()

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]
        role = request.form.get("role", "student")

        conn = sqlite3.connect("quiz.db")
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=? AND password=? AND role= ?", (u, p, role))
        user = cur.fetchone()
        conn.close()

        if user:
            session["user"] = u
            session["role"] = role
            session["qno"] = 0
            session["score"] = 0

            if role == "admin":
                return redirect("/admin")
            else:
                return redirect("/quiz")

        error = "Invalid username, password, or role"

    return render_template("login.html", error=error)

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        conn = sqlite3.connect("quiz.db")
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (u,))
        existing = cur.fetchone()

        if existing:
            error = "Username already exists"
        else:
            cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                        (u, p, "student"))
            conn.commit()
            conn.close()
            return redirect("/")

        conn.close()

    return render_template("register.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- ADMIN ----------------
@app.route("/admin")
def admin():
    if session.get("role") != "admin":
        return redirect("/")
    return render_template("admin.html")

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

    return render_template("create quiz.html")

# ---------------- QUIZ ----------------
@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    if session.get("user") is None or session.get("role") != "student":
        return redirect("/")

    if "qno" not in session:
        session["qno"] = 0
        session["score"] = 0

    conn = sqlite3.connect("quiz.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM questions")
    data = cur.fetchall()
    conn.close()

    if not data:
        return render_template("quizz.html", q=(None, "No questions available", "", "", "", ""), feedback=None,
                               question_number=0, total_questions=0)

    feedback = None
    if request.method == "POST":
        selected = request.form.get("answer")
        correct = data[session["qno"]][6]

        if selected == correct:
            session["score"] += 1
            feedback = "Correct!"
        else:
            feedback = "Wrong!"

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
    return render_template("quizz.html", q=q, feedback=feedback,
                           question_number=session["qno"] + 1, total_questions=len(data))

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

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)