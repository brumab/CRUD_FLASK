import os
import pymysql
from flask import Flask, render_template, request, redirect, url_for, flash, session
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or "dev_secret_key_123"

# # =========================
# # Conexões MySQL
# # =========================
# def conn_server():
#     return pymysql.connect(
#         host=os.getenv("MYSQL_HOST", "localhost"),
#         user=os.getenv("MYSQL_USER", "root"),
#         password=os.getenv("MYSQL_PASSWORD", ""),
#         port=int(os.getenv("MYSQL_PORT", 3306)),
#         cursorclass=pymysql.cursors.DictCursor
#     )

# =========================
# Conexão MySQL (Aiven)
# =========================
def get_db_connection():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DB"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        cursorclass=pymysql.cursors.DictCursor,
        ssl={"ssl": {}}  # 🔒 SSL obrigatório Aiven
    )

def conn_db():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DB", "flask_crud"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        cursorclass=pymysql.cursors.DictCursor
    )

# =========================
# Inicialização automática
# =========================
def init_db():
    conn = conn_server()
    cur = conn.cursor()
    cur.execute("CREATE DATABASE IF NOT EXISTS flask_crud")
    conn.commit()
    cur.close()
    conn.close()

def init_tables():
    conn = conn_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE,
            password VARCHAR(255)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100),
            email VARCHAR(100),
            phone VARCHAR(20)
        )
    """)

    cur.execute("SELECT * FROM users WHERE username='admin'")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (username, password) VALUES (%s,%s)",
            ("admin", generate_password_hash("admin123"))
        )

    conn.commit()
    cur.close()
    conn.close()

@app.before_request
def setup():
    if not hasattr(app, "ready"):
        init_db()
        init_tables()
        app.ready = True

# =========================
# Login
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        conn = conn_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s", (request.form["username"],))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and check_password_hash(user["password"], request.form["password"]):
            session["user"] = user["username"]
            return redirect(url_for("index"))

        flash("Usuário ou senha inválidos")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# =========================
# STUDENTS CRUD + BUSCA
# =========================
@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login"))

    search = request.args.get("search", "")

    conn = conn_db()
    cur = conn.cursor()

    if search:
        cur.execute("""
            SELECT * FROM students
            WHERE name LIKE %s OR email LIKE %s
            ORDER BY id DESC
        """, (f"%{search}%", f"%{search}%"))
    else:
        cur.execute("SELECT * FROM students ORDER BY id DESC")

    students = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("index.html", students=students, search=search)

@app.route("/students/add", methods=["POST"])
def add_student():
    conn = conn_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO students (name,email,phone) VALUES (%s,%s,%s)",
        (request.form["name"], request.form["email"], request.form["phone"])
    )
    conn.commit()
    cur.close()
    conn.close()

    flash("Aluno cadastrado com sucesso!")
    return redirect(url_for("index"))

@app.route("/students/update", methods=["POST"])
def update_student():
    conn = conn_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE students SET name=%s, email=%s, phone=%s WHERE id=%s
    """, (
        request.form["name"],
        request.form["email"],
        request.form["phone"],
        request.form["id"]
    ))
    conn.commit()
    cur.close()
    conn.close()

    flash("Aluno atualizado!")
    return redirect(url_for("index"))

@app.route("/students/delete/<int:id>")
def delete_student(id):
    conn = conn_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM students WHERE id=%s", (id,))
    conn.commit()
    cur.close()
    conn.close()

    flash("Aluno excluído!")
    return redirect(url_for("index"))

# =========================
# Start
# =========================
if __name__ == "__main__":
    app.run(debug=True)
