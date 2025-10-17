# app.py
# EazyMovieDownload - single-file Flask app ready for deployment
# Features:
# - Register / Login (SQLite)
# - Protected "Go to Movies" page requiring login
# - Loading animation + redirect to Pluto Movies
# - Dark / Light theme toggle (saved in localStorage)
# - Ad placeholders (paste ad scripts where indicated)
# - Modern responsive styling
# NOTE: Replace SECRET_KEY before production

from flask import Flask, render_template_string, request, redirect, url_for, session, g, flash
import sqlite3, os
from werkzeug.security import generate_password_hash, check_password_hash

# ---------- CONFIG ----------
DATABASE = os.environ.get("EMD_DATABASE", "users.db")
SECRET_KEY = os.environ.get("EMD_SECRET_KEY", "replace_with_a_strong_random_secret")
PLUTO_MOVIES_URL = os.environ.get("EMD_PLUTO_URL", "https://pluto.tv/")
app = Flask(__name__)
app.secret_key = SECRET_KEY

# ---------- TEMPLATES (inline) ----------
layout = """
<!doctype html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{{ title or "EazyMovieDownload" }}</title>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;500;700;900&display=swap" rel="stylesheet">
  <style>
    :root{
      --accent:#e50914;
      --radius:12px;
      --glass: rgba(255,255,255,0.03);
    }
    [data-theme="dark"]{
      --bg:#070708;--card:#0f0f10;--text:#efefef;--muted:#bdbdbd;--muted-2:#8a8a8a
    }
    [data-theme="light"]{
      --bg:#f6f7fb;--card:#ffffff;--text:#0b0b0b;--muted:#5b6170;--muted-2:#7b8190
    }
    *{box-sizing:border-box}
    body{margin:0;font-family:Poppins,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;background:var(--bg);color:var(--text);-webkit-font-smoothing:antialiased}
    .wrap{max-width:1024px;margin:32px auto;padding:20px}
    .card{background:var(--card);border-radius:var(--radius);padding:20px;box-shadow:0 10px 30px rgba(0,0,0,0.25)}
    header{display:flex;align-items:center;gap:12px}
    .brand{font-weight:900;font-size:1.6rem;color:var(--accent);letter-spacing:0.6px}
    .tag{font-weight:500;color:var(--muted);font-size:.9rem}
    nav{margin-top:12px;display:flex;gap:12px;flex-wrap:wrap}
    a.link{color:var(--accent);text-decoration:none;font-weight:600}
    .right{margin-left:auto;display:flex;gap:10px;align-items:center}
    .btn{background:var(--accent);color:#fff;border:0;padding:10px 14px;border-radius:10px;cursor:pointer;font-weight:700}
    .ghost{background:transparent;border:1px solid rgba(255,255,255,0.06);padding:8px 12px;border-radius:10px;color:var(--muted);cursor:pointer}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin-top:18px}
    .tile{background:linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));padding:14px;border-radius:10px}
    input,select{width:100%;padding:12px;border-radius:8px;border:1px solid rgba(0,0,0,0.08);background:transparent;color:var(--text)}
    label{font-size:0.85rem;color:var(--muted);display:block;margin-bottom:6px}
    form{margin-top:12px;display:flex;flex-direction:column;gap:12px}
    .small{font-size:0.85rem;color:var(--muted)}
    .ad-box{margin-top:14px;padding:12px;border-radius:10px;background:var(--glass);color:var(--muted);text-align:center}
    footer{margin-top:20px;text-align:center;color:var(--muted);font-size:0.85rem}
    /* loader fullscreen */
    .loader-wrap{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;background:var(--bg);z-index:9999;flex-direction:column}
    .spinner{width:72px;height:72px;border-radius:50%;border:8px solid rgba(255,255,255,0.07);border-top:8px solid var(--accent);animation:spin 1s linear infinite;margin-bottom:14px}
    @keyframes spin{to{transform:rotate(360deg)}}
    /* responsive */
    @media (max-width:640px){
      .brand{font-size:1.2rem}
      .wrap{margin:16px}
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <header>
        <div>
          <div class="brand">EazyMovieDownload</div>
          <div class="tag">Quick access • Login required • Ads ready</div>
        </div>
        <div class="right">
          <div class="small" style="margin-right:8px">{{ session.get('user_email') or '' }}</div>
          <button class="ghost" onclick="toggleTheme()">Toggle Theme</button>
        </div>
      </header>

      <nav>
        <a class="link" href="{{ url_for('index') }}">Home</a>
        {% if not session.get('user_id') %}
          <a class="link" href="{{ url_for('login') }}">Login</a>
          <a class="link" href="{{ url_for('register') }}">Register</a>
        {% else %}
          <a class="link" href="{{ url_for('go') }}">Go to Movies</a>
          <a class="link" href="{{ url_for('logout') }}">Logout</a>
        {% endif %}
      </nav>

      {% with messages = get_flashed_messages() %}
        {% if messages %}
          <div style="margin-top:12px;padding:10px;border-radius:8px;background:rgba(0,0,0,0.05);color:var(--accent)">{{ messages[0] }}</div>
        {% endif %}
      {% endwith %}

      {% block content %}{% endblock %}
    </div>

    <footer>© 2025 EazyMovieDownload — Ads placeholders available. Host & domain instructions in README.</footer>
  </div>

<script>
  // theme handling
  (function(){
    const saved = localStorage.getItem('emd_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
  })();
  function toggleTheme(){
    const cur = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = cur === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('emd_theme', next);
  }
</script>
</body>
</html>
"""

index_html = """
{% extends "layout" %}
{% block content %}
  <div style="margin-top:16px">
    <h2 style="margin:6px 0 4px">Welcome to EazyMovieDownload</h2>
    <p class="small">Please register or log in to continue to recommended movies. This site redirects to Pluto TV after the login flow.</p>

    <div class="grid">
      <div class="tile">
        <div style="height:140px;background:linear-gradient(180deg,#111,#222);border-radius:8px;display:flex;align-items:center;justify-content:center;color:var(--muted)">Featured Poster</div>
        <h3 style="margin:10px 0 4px">Featured Picks</h3>
        <p class="small">Curated suggestions and trailers — coming soon.</p>
      </div>

      <div class="tile">
        <h3 style="margin-top:6px">Get Access</h3>
        <p class="small">You must be signed in to continue to movies.</p>
        <a class="btn" href="{{ url_for('login') }}" style="display:inline-block;margin-top:8px">Sign in</a>
      </div>
    </div>

    <div class="ad-box">
      <!-- AD PLACEHOLDER #1 - paste your ad network script here (AdSense / Adsterra) -->
      Ad Space — paste ad script here when ready.
    </div>
  </div>
{% endblock %}
"""

login_html = """
{% extends "layout" %}
{% block content %}
  <div style="margin-top:14px">
    <h2>Login</h2>
    <form method="post">
      <label>Email</label>
      <input name="email" type="email" placeholder="you@example.com" required>
      <label>Password</label>
      <input name="password" type="password" placeholder="Your password" required>
      <button class="btn" type="submit">Login</button>
    </form>
    <p class="small" style="margin-top:8px">Don't have an account? <a class="link" href="{{ url_for('register') }}">Register here</a></p>
  </div>
{% endblock %}
"""

register_html = """
{% extends "layout" %}
{% block content %}
  <div style="margin-top:14px">
    <h2>Create an account</h2>
    <form method="post">
      <label>Email</label>
      <input name="email" type="email" placeholder="you@example.com" required>
      <label>Password (min 6 chars)</label>
      <input name="password" type="password" placeholder="Choose a password" required>
      <button class="btn" type="submit">Register</button>
    </form>
    <p class="small" style="margin-top:8px">After registering you will be able to click <strong>Go to Movies</strong>.</p>
    <div class="ad-box" style="margin-top:10px">
      <!-- AD PLACEHOLDER #2 -->
      Ad Space — paste ad code here.
    </div>
  </div>
{% endblock %}
"""

go_html = """
{% extends "layout" %}
{% block content %}
  <div style="margin-top:16px;text-align:center">
    <h2>Entering Cinema...</h2>
    <p class="small">We prepare your experience — this improves ad visibility and creates a smooth transition.</p>

    <div class="loader-wrap" id="loader">
      <div class="spinner"></div>
      <div class="small">Entering Cinema…</div>
    </div>

    <script>
      // show loader then redirect
      setTimeout(function(){
        // start fade (hide loader)
        var el = document.getElementById('loader');
        el.style.transition = 'opacity .5s ease';
        el.style.opacity = '0';
        setTimeout(function(){ window.location.href = "{{ external_url }}"; }, 600);
      }, 2600);
    </script>

    <div style="margin-top:14px" class="ad-box">
      <!-- AD PLACEHOLDER #3 - paste interstitial/banner ad script here -->
      Ad Space — paste ad script here.
    </div>
  </div>
{% endblock %}
"""

# ---------- DB helpers ----------
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        need_init = not os.path.exists(DATABASE)
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        if need_init:
            init_db()
    return db

def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute("""
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
      )
    """)
    db.commit()
    db.close()

@app.teardown_appcontext
def close_conn(exc):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# ---------- Routes ----------
@app.route('/')
def index():
    return render_template_string(index_html, title="Home")

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        pw = request.form['password']
        if len(pw) < 6:
            flash("Password must be at least 6 characters.")
            return redirect(url_for('register'))
        db = get_db()
        try:
            db.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)",
                       (email, generate_password_hash(pw)))
            db.commit()
            flash("Account created. Please log in.")
            return redirect(url_for('login'))
        except Exception:
            flash("Account with that email may already exist.")
            return redirect(url_for('register'))
    return render_template_string(register_html, title="Register")

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        pw = request.form['password']
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user['password_hash'], pw):
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            flash("Welcome back!")
            return redirect(url_for('go'))
        flash("Invalid email or password.")
        return redirect(url_for('login'))
    return render_template_string(login_html, title="Login")

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('index'))

@app.route('/go')
def go():
    if not session.get('user_id'):
        flash("Please log in first.")
        return redirect(url_for('login'))
    return render_template_string(go_html, title="Redirecting...", external_url=PLUTO_MOVIES_URL)

# ---------- run ----------
if __name__ == "__main__":
    if not os.path.exists(DATABASE):
        init_db()
    # Bind to 0.0.0.0 so hosting providers (and local testing) can access
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)