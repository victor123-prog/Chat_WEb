from flask import Flask, request, render_template, redirect, url_for, session
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
import google.generativeai as genai
import os

app = Flask(__name__)

## Variable d'environement 
app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")

## creation de la table users si elle n'existe pas déjà
def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) NOT NULL,
            email VARCHAR(150) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

init_db()

# ──────────────────────────────────────────
#  Connexion PostgreSQL
# ──────────────────────────────────────────

# ──────────────────────────────────────────
#  Page d'accueil → Login
# ──────────────────────────────────────────

@app.route("/")
def home():
    return render_template("login.html")


# ──────────────────────────────────────────
#  Connexion
# ──────────────────────────────────────────

@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"]
    password = request.form["password"]

    try:

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()  # Ne pas fermer la connexion ici, elle est utilisée dans d'autres parties

        if user and check_password_hash(user[3], password):
            session["user_id"] = user[0]
            session["username"] = user[1]
            return redirect(url_for("chat"))
        else:
            return render_template("login.html", error="Identifiants incorrects.")

    except psycopg2.Error as e:
        return render_template("login.html", error=f"Erreur base de données : {e}")


# ──────────────────────────────────────────
#  Inscription
# ──────────────────────────────────────────

@app.route("/register", methods=["GET"])
def register():
    return render_template("register.html")


@app.route("/register", methods=["POST"])
def save_user():
    username = request.form["username"]
    email = request.form["email"]
    password = request.form["password"]
    hashed_password = generate_password_hash(password)

    try:

        conn = psycopg2.connect(
            DATABASE_URL
        )
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users(username, email, password) VALUES(%s, %s, %s)",
            (username, email, hashed_password)
        )
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("home"))

    except psycopg2.errors.UniqueViolation:
        return render_template("register.html", error="Cet email est déjà utilisé.")

    except psycopg2.Error as e:
        return render_template("register.html", error=f"Erreur base de données : {e}")


# ──────────────────────────────────────────
#  Chat (page protégée)
# ──────────────────────────────────────────

@app.route("/chat")
def chat():
    if "user_id" not in session:
        return redirect(url_for("home"))
    return render_template("chat.html")


# ──────────────────────────────────────────
#  Envoi de message à Ollama
# ──────────────────────────────────────────

@app.route("/send", methods=["POST"])
def send():

    if "user_id" not in session:
        return "Non autorisé", 401

    message = request.form["message"]

    try:

        response = model.generate_content(message)

        return response.text

    except Exception as e:
        return f"Erreur Gemini : {e}", 500

# ──────────────────────────────────────────
#  Déconnexion
# ──────────────────────────────────────────

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ──────────────────────────────────────────
#  Lancement
# ──────────────────────────────────────────

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )