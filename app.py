from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import time
from dotenv import load_dotenv
import os
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rhysverse.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

GOOGLE_BOOKS_API = "https://www.googleapis.com/books/v1/volumes"
API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY")
GENRES = ["Fiction", "Science", "History", "Romance", "Fantasy", "Biography", "Technology", "Children"]

MOODS = [
    {"name": "Melancholic", "emoji": "🌧️", "description": "Stories that sit with sadness, loss, and the quiet ache of being human.", "color": "#6b7fd7", "query": "melancholic literary fiction loneliness grief"},
    {"name": "Romantic", "emoji": "🌹", "description": "Love in all its forms — passionate, tender, bittersweet.", "color": "#e8677a", "query": "romance love story passionate novel"},
    {"name": "Dark & Mysterious", "emoji": "🖤", "description": "Shadows, secrets, and stories that unsettle you in the best way.", "color": "#9b59b6", "query": "dark mystery thriller psychological suspense"},
    {"name": "Fantasy", "emoji": "✨", "description": "Worlds beyond imagination, magic, and epic adventures.", "color": "#f39c12", "query": "fantasy epic magic adventure novel"},
    {"name": "Cozy", "emoji": "☕", "description": "Warm, comforting reads perfect for a quiet afternoon.", "color": "#e67e22", "query": "cozy comfort feel good heartwarming novel"},
    {"name": "Thought Provoking", "emoji": "🧠", "description": "Books that make you question everything you thought you knew.", "color": "#1abc9c", "query": "philosophical thought provoking intellectual literary fiction"},
]

QUOTES = [
    {"text": "Not all those who wander are lost.", "author": "J.R.R. Tolkien"},
    {"text": "I took a deep breath and listened to the old brag of my heart: I am, I am, I am.", "author": "Sylvia Plath"},
    {"text": "We accept the love we think we deserve.", "author": "Stephen Chbosky"},
    {"text": "A reader lives a thousand lives before he dies. The man who never reads lives only one.", "author": "George R.R. Martin"},
    {"text": "The only way out of the labyrinth of suffering is to forgive.", "author": "John Green"},
    {"text": "Words are, in my not-so-humble opinion, our most inexhaustible source of magic.", "author": "J.K. Rowling"},
]

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    bookshelf = db.relationship('BookShelf', backref='user', lazy=True)

class BookShelf(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    cover = db.Column(db.String(300), nullable=True)
    year = db.Column(db.String(10), nullable=True)
    status = db.Column(db.String(20), default='want_to_read')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

cache = {}
CACHE_DURATION = 300

def fetch_books(query, max_results=12):
    now = time.time()
    if query in cache and now - cache[query]["time"] < CACHE_DURATION:
        return cache[query]["data"]
    try:
        response = requests.get(GOOGLE_BOOKS_API, params={
            "q": query, "maxResults": max_results, "orderBy": "relevance", "key": API_KEY
        }, timeout=5)
        data = response.json()
        items = data.get("items", [])
        books = []
        for item in items:
            info = item.get("volumeInfo", {})
            cover = info.get("imageLinks", {}).get("thumbnail", "").replace("http://", "https://")
            if cover:
                books.append({
                    "id": item.get("id"),
                    "title": info.get("title", "Untitled"),
                    "author": info.get("authors", ["Unknown"])[0],
                    "year": info.get("publishedDate", "")[:4],
                    "cover": cover
                })
        cache[query] = {"data": books, "time": now}
        return books
    except:
        return []

GENRE_QUERIES = {
    "Fiction": "popular fiction novel",
    "Science": "popular science book",
    "History": "popular history book",
    "Romance": "romance novel bestseller",
    "Fantasy": "fantasy novel bestseller",
    "Biography": "biography memoir bestseller",
    "Technology": "technology programming book",
    "Children": "children book popular"
}

@app.route("/")
def home():
    import random
    trending = fetch_books("bestseller fiction", max_results=12)
    quote = random.choice(QUOTES)
    return render_template("index.html", genres=GENRES, trending=trending, fiction=[], quote=quote)

@app.route("/search")
def search():
    query = request.args.get("q", "")
    genre = request.args.get("genre", "")
    books = []
    if genre and query:
        search_term = f"{query} {GENRE_QUERIES.get(genre, genre)}"
    elif genre:
        search_term = GENRE_QUERIES.get(genre, genre)
    elif query:
        search_term = query
    else:
        search_term = ""
    if search_term:
        books = fetch_books(search_term)
    return render_template("index.html", books=books, query=query, genre=genre, genres=GENRES)

@app.route("/book/<book_id>")
def book_detail(book_id):
    response = requests.get(f"{GOOGLE_BOOKS_API}/{book_id}", params={"key": API_KEY})
    data = response.json()
    info = data.get("volumeInfo", {})
    book = {
        "id": book_id,
        "title": info.get("title", "Untitled"),
        "authors": ", ".join(info.get("authors", ["Unknown"])),
        "year": info.get("publishedDate", "")[:4],
        "cover": info.get("imageLinks", {}).get("thumbnail", "").replace("http://", "https://"),
        "description": info.get("description", "Tidak ada deskripsi."),
        "categories": ", ".join(info.get("categories", ["Tidak diketahui"])),
        "rating": info.get("averageRating", "N/A"),
        "pages": info.get("pageCount", "N/A"),
        "publisher": info.get("publisher", "Unknown"),
    }
    in_shelf = False
    if current_user.is_authenticated:
        in_shelf = BookShelf.query.filter_by(user_id=current_user.id, book_id=book_id).first() is not None
    return render_template("book_detail.html", book=book, in_shelf=in_shelf)

@app.route("/mood")
def mood():
    return render_template("mood.html", moods=MOODS)

@app.route("/mood/<mood_name>")
def mood_books(mood_name):
    mood = next((m for m in MOODS if m["name"].lower().replace(" & ", "-").replace(" ", "-") == mood_name), None)
    if not mood:
        return redirect("/mood")
    books = fetch_books(mood["query"], max_results=12)
    return render_template("mood_books.html", mood=mood, books=books)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect("/")
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        if User.query.filter_by(username=username).first():
            flash("Username sudah dipakai.", "error")
            return redirect("/register")
        if User.query.filter_by(email=email).first():
            flash("Email sudah dipakai.", "error")
            return redirect("/register")
        hashed = generate_password_hash(password)
        user = User(username=username, email=email, password=hashed)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Akun berhasil dibuat!", "success")
        return redirect("/")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect("/")
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Login berhasil!", "success")
            return redirect("/")
        flash("Email atau password salah.", "error")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")

@app.route("/bookshelf")
@login_required
def bookshelf():
    books = BookShelf.query.filter_by(user_id=current_user.id).all()
    return render_template("bookshelf.html", books=books)

@app.route("/bookshelf/add", methods=["POST"])
@login_required
def add_to_shelf():
    book_id = request.form.get("book_id")
    title = request.form.get("title")
    author = request.form.get("author")
    cover = request.form.get("cover")
    year = request.form.get("year")
    existing = BookShelf.query.filter_by(user_id=current_user.id, book_id=book_id).first()
    if not existing:
        book = BookShelf(user_id=current_user.id, book_id=book_id, title=title, author=author, cover=cover, year=year)
        db.session.add(book)
        db.session.commit()
        flash("Buku ditambahkan ke bookshelf!", "success")
    else:
        flash("Buku sudah ada di bookshelf.", "info")
    return redirect(f"/book/{book_id}")

@app.route("/bookshelf/remove/<int:id>")
@login_required
def remove_from_shelf(id):
    book = BookShelf.query.get_or_404(id)
    if book.user_id == current_user.id:
        db.session.delete(book)
        db.session.commit()
        flash("Buku dihapus dari bookshelf.", "success")
    return redirect("/bookshelf")

if __name__ == "__main__":
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html"), 404
    with app.app_context():
        db.create_all()
    app.run(debug=True)