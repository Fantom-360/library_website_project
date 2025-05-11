from flask import Flask, render_template, url_for, request, redirect, session, send_from_directory
import sqlite3
import hashlib
import logging
import os
from datetime import datetime
from werkzeug.utils import secure_filename

if os.path.exists('better/logs/report.log'):
    with open('better/logs/report.log', 'w') as file:
        file.close()
    
logging.basicConfig(
    filename='better/logs/report.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
def get_db():
    db = sqlite3.connect("better/library.db", check_same_thread=False)
    db.row_factory = sqlite3.Row
    return db

app = Flask(__name__)
password_hash = hashlib.sha256()
app.secret_key = 'something123'

db = get_db()
cursor = db.cursor()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error_message = None
    if request.method == 'POST':
        identifier = request.form.get('identifier')
        password = request.form.get('password')

        query = "SELECT * FROM users WHERE email = ? OR username = ?"
        cursor.execute(query, (identifier, identifier))
        user = cursor.fetchone()

        if user:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            if password_hash == user['password']:
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['email'] = user['email']
                logging.info(f"User {user['username']} ({user['email']}) logged in successfully")
                return redirect(url_for('user'))
            else:
                logging.warning(f"Incorect password for user {identifier}")
                error_message = "Your password is incorect try again"
        else:
            logging.warning(f"Login attempt for non-existent email: {identifier}")
            error_message = "No user with that email or username"
        
    return render_template("login.html", error_message=error_message)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method  == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        password_hash = hashlib.sha256(password.encode()).hexdigest()

        query = "INSERT INTO users (username, email, password) VALUES (?, ?, ?)"
        value = (username, email, password_hash)
        try:
            cursor.execute(query, value)
            db.commit()
            print("the register was succesfull")
            logging.info(f"User {username} with email: {email} Registered")
            return redirect(url_for('login'))
        except Exception as e:
            print("something went wrong when updating the database")
            logging.error(f"Error ocured with writing to database: {e}")

    return render_template('register.html')

@app.route('/logout')
def logout():
    user_email = session.get('email', 'Unknown')
    logging.info(f"User {user_email} logged out")
    session.clear()
    return redirect(url_for('home'))

@app.route('/user')
def user():
    if 'user_id' not in session:
        logging.warning("Unauthorized access to /user")
        return redirect(url_for('login'))
    
    username = session.get('username')

    return render_template("user.html", username=username)

@app.route('/user/favorite')
def favorite():
    if 'user_id' not in session:
        logging.warning("Unauthorized access to /user")
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    query = """
        SELECT b.id, b.title
        FROM favorites f
        JOIN books b ON f.book_id = b.id
        WHERE f.user_id = ?
    """

    cursor.execute(query, (user_id,))
    fav_books = cursor.fetchall()

    return render_template("favorites.html", fav_books=fav_books)

@app.route('/user/history')
def borrow_history():
    if 'user_id' not in session:
        logging.warning("Unauthorized access to /user")
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    query = """
        SELECT b.title, bb.borrowed_at, bb.returned_at
        FROM borrowed_books bb
        JOIN books b ON bb.book_id = b.id
        WHERE bb.user_id = ?
    """
    cursor.execute(query, (user_id,))
    history = cursor.fetchall()
    return render_template("history.html", history=history)

@app.route('/books')
def books():
    query = "SELECT id, title FROM books"
    cursor.execute(query)
    books = cursor.fetchall()
    return render_template("books.html", books=books)

@app.route('/books/<int:book_id>')
def book_details(book_id):
    query = "SELECT * FROM books WHERE id = ?"
    cursor.execute(query, (book_id,))
    book = cursor.fetchone()

    if not book:
        logging.warning(f"Book: {book} was not founf")
        return "Book not found", 404
    
    return render_template("book_details.html", book=book)

@app.route('/books/borrow/<int:book_id>', methods=['POST'])
def borrow_book(book_id):
   if 'user_id' not in session:
        logging.warning("Unauthorized access to /user")
        return redirect(url_for('login'))
   
   user_id = session['user_id']


   cursor.execute("SELECT * FROM books WHERE id = ?")
   book = cursor.fetchone()
   if not book or not book['pdf_file']:
       logging.warning(f"book id: {book_id} PDF is missing")
       return "book not found or missing PDF"
 
   cursor.execute("INSERT INTO borrowed_books (user_id, book_id) VALUES (?, ?)", (user_id, book_id))
   db.commit()
   return send_from_directory('static/pdfs', book['pdf_file'], as_attachment=True)

#@app.route('/books/return/<int:book_id>', methods=['POST'])
#def return_book(book_id):
#    if 'user_id' not in session:
#        logging.warning("Unauthorized access to /user")
#        return redirect(url_for('login'))
#    
#    user_id = session['user_id']
#
#    query = """
#        UPDATE borrowed_books
#        SET returned_at = ?
#        WHERE user_id = ? AND book_id = ? AND returned_at IS NULL
#    """
#    now = datetime.now()
#    cursor.execute(query, (now, user_id, book_id))
#    db.commit()
#    logging.info(f"User {user_id} returned book {book_id}")
#    return redirect(url_for('borrow_history'))
    
@app.route('/search')
def search():
    query = request.args.get('query')

    if not query:
        return redirect(url_for('books'))

    like_pattern = f"%{query}%"
    sql = """
        SELECT * FROM books
        WHERE title LIKE ? OR author LIKE ?
    """
    cursor.execute(sql, (like_pattern, like_pattern))
    results = cursor.fetchall()

    return render_template("search_results.html", books=results, search_term=query)

@app.route('/login/admin', methods=['GET', 'POST'])
def admin_login():
    error_message = None
    if request.method == 'POST':
        admin_password = request.form.get('password')
        admin_email = request.form.get('email')

        query = "SELECT * FROM users WHERE email = ? AND is_admin = TRUE"
        cursor.execute(query, (admin_email,))
        admin_user = cursor.fetchone()


        if admin_user:
            hashed_input = hashlib.sha256(admin_password.encode()).hexdigest()
            if hashed_input == admin_user['password']:
                session['admin_id'] = admin_user['id']
                session['admin_email'] = admin_user['email']
                logging.info(f"Admin {admin_user['email']} logged in successfully")
                return redirect(url_for('admin_dashboard'))
            else:
                logging.warning(f"Wrong admin password for {admin_email}")
                error_message = "Incorrect password"
        else:
            logging.warning(f"Admin login failed: {admin_email} not found or not an admin")
            error_message = "NO admin account with that email"

    return render_template("admin_login.html", error_message=error_message)

@app.route('/admin')
def admin_dashboard():
    if 'admin_id' not in session:
        logging.warning("Unauthorized access to /admin")
        return redirect(url_for('admin_login'))
        
    cursor.execute("SELECT COUNT(*) AS total_users FROM users")
    total_users = cursor.fetchone()['total_users']

    cursor.execute("SELECT COUNT(*) AS total_books FROM books")
    total_books = cursor.fetchone()['total_books']

    cursor.execute("SELECT COUNT(*) AS total_borrows FROM borrowed_books")
    borrow_stats = cursor.fetchone()['total_borrows']

    cursor.execute("""
        SELECT COUNT(*) AS online_users 
        FROM users 
        WHERE last_seen >= datetime('now', '-5 minutes')
    """)
    online_users = cursor.fetchone()['online_users']

    return render_template("admin_dashboard.html",
                           total_users=total_users,
                           total_books=total_books,
                           online_users=online_users,
                           borrow_stats=borrow_stats)

@app.route('/admin/books/add', methods=['GET', 'POST'])
def add_book():
    error_message = None

    if 'admin_id' not in session:
        logging.warning("Unauthorized admin book add attempt")
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        description = request.form.get('description')
        published_year = request.form.get('published_year')
        genre = request.form.get('genre')
        cover_image = request.files.get('cover_image')
        pdf_file= request.files.get('pdf_file')

        if pdf_file and pdf_file.filename != '':
            pdf_filename = secure_filename(pdf_file.filename)
            pdf_path = os.path.join('static','pdfs', pdf_filename)
            pdf_file.save(pdf_path)

        filename = None
        if cover_image and cover_image.filename != '':
            filename = secure_filename(cover_image.filename)
            cover_image.save(os.path.join('static', 'images', filename))

        query = """
            INSERT INTO books (title, author, description, published_year, genre, is_available, cover_image, pdf_file)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

        values = (title, author, description, published_year, genre, True, filename, pdf_filename)

        try:
            cursor.execute(query, values)
            db.commit()
            logging.info(f"Admin added book: {title}")
            return redirect(url_for('books'))
        except Exception as e:
            logging.error(f"Error adding book: {e}")
            error_message = "Error adding book"

    return render_template("add_book.html", error_message=error_message)

@app.route('/admin/books/update/<int:book_id>', methods=['GET', 'POST'])
def update_book(book_id):
    book = None
    if 'admin_id' not in session:
        logging.warning("Unauthorized admin book add attempt")
        return redirect(url_for('admin_login'))
    
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    book = cursor.fetchone()

    if not book:
        error_message = "Book not found"

    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        description = request.form.get('description')
        published_year = request.form.get('published_year')
        genre = request.form.get('genre')
        new_image = request.files.get('cover_image')
        new_pdf = request.files.get('pdf_file')
        pdf_filename = book['pdf_file']

        if new_pdf and new_pdf.filename != '':
            pdf_filename = secure_filename(new_pdf.filename)
            new_pdf.save(os.path.join('static', 'pdfs', pdf_filename))

        if new_image and new_image.filename != '':
            filename = secure_filename(new_image.filename)
            new_image.save(os.path.join('static', 'images', filename))
        else:
            filename = book['cover_image']

        update_query = """
            UPDATE books SET
            title = ?,
            author = ?,
            description = ?,
            published_year = ?,
            genre = ?,
            cover_image = ?,
            pdf_file = ?
            WHERE id = ?
        """
        values = (title, author, description, published_year, genre, filename, pdf_filename, book_id)

        try:
            cursor.execute(update_query, values)
            db.commit()
            logging.info(f"Book {book_id} updated by admin")
            return redirect(url_for('book_details', book_id=book_id))
        except Exception as e:
            logging.error(f"Error updating book {book_id}: {e}")
            return render_template("update_book.html", book=book, error_message="Something went wrong")
        
    return render_template("update_book.html", book=book, error_message=error_message)

@app.route('/admin/books/remove/<int:book_id>', methods=['GET', 'POST'])
def remove_book(book_id):
    if 'admin_id' not in session:
        logging.warning("Unauthorized admin book add attempt")
        return redirect(url_for('admin_login'))
    
    try:
        query = "DELETE FROM books WHERE id = ?"
        cursor.execute(query, (book_id,))
        db.commit()
        logging.info(f"Book {book_id} removed by admin")
        return redirect(url_for('books'))
    except Exception as e:
        logging.error(f"Error removing book {book_id}: {e}")
        return "something went wrong"

@app.route('/about_us')
def about_us():
    return render_template('about_us.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.before_request
def update_last_seen():
    now = datetime.now()
    if 'user_id' in session:
        cursor.execute("UPDATE users SET last_seen = ? WHERE id = ?", (now, session['user_id']))
        db.commit()
    elif 'admin_id' in session:
        cursor.execute("UPDATE users SET last_seen = ? WHERE id = ?", (now, session['admin_id']))
        db.commit()

if __name__ == "__main__":
    app.run(debug=True)