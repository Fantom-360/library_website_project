from flask import Flask, render_template, url_for, request, redirect, session, send_from_directory, g
import hashlib
import os
import plotly.graph_objs as go
import plotly
import json
import mysql.connector
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import time

def get_db():
    if 'db' not in g:
        g.db = mysql.connector.connect(
            user=f'{os.getenv('DB_USER')}',
            password = f'{os.getenv('DB_PASSWORD')}',
            host = f'{os.getenv('DB_HOST')}',
            database = 'uwu-library'
        )
        return g.db
    
app = Flask(__name__)
password_hash = hashlib.sha256()
app.secret_key = 'something123'

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
    except Exception as e:
        print(f"An Error occured with the database {e}")
        error_message = "There is a problem with connection to database"
        return render_template("user.html", error_message=error_message)
    error_message = None
    if request.method == 'POST':
        identifier = request.form.get('identifier')
        password = request.form.get('password')

        query = "SELECT * FROM users WHERE email = %s OR username = %s"
        cursor.execute(query, (identifier, identifier))
        user = cursor.fetchone()

        if user:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            if password_hash == user['password']:
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['email'] = user['email']
                print(f"User {user['username']} ({user['email']}) logged in successfully")
                return redirect(url_for('user'))
            else:
                print(f"Incorect password for user {identifier}")
                error_message = "Your password is incorect try again"
        else:
            print(f"Login attempt for non-existent email: {identifier}")
            error_message = "No user with that email or username"
        
    return render_template("login.html", error_message=error_message)

@app.route('/register', methods=['GET', 'POST'])
def register():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
    except Exception as e:
        print(f"An Error occured with the database {e}")
        error_message = "There is a problem with connection to database"
        return render_template("user.html", error_message=error_message)
    if request.method  == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if password != confirm_password:
            error_message = "Womp Womp the paswords arent the same"
            return render_template('register.html', error_message=error_message)
        
        now = datetime.now().isoformat()
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        query = "INSERT INTO users (username, email, password, created_at) VALUES (%s, %s, %s, %s)"
        value = (username, email, password_hash, now)
        try:
            cursor.execute(query, value)
            conn.commit()
            print("the register was succesfull")
            print(f"User {username} with email: {email} Registered")
            return redirect(url_for('login'))
        except Exception as e:
            print("something went wrong when updating the database")
            print(f"Error ocured with writing to database: {e}")

    return render_template('register.html')

@app.route('/logout')
def logout():
    user_email = session.get('email', 'Unknown')
    print(f"User {user_email} logged out")
    session.clear()
    return redirect(url_for('home'))

@app.route('/user')
def user():
    if 'user_id' not in session:
        print("Unauthorized access to /user")
        return redirect(url_for('login'))
    
    username = session.get('username')

    return render_template("user.html", username=username)

@app.route('/user/delete', methods=['POST'])
def delete_account():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
    except Exception as e:
        print(f"An Error occured with the database {e}")
        error_message = "There is a problem with connection to database"
        return render_template("user.html", error_message=error_message)
    if 'user_id' not in session:
        print("Unauthorized attempt to delete account")
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_email = session.get('email', 'unknown')

    # Optional: Delete borrowed_books, favorites, etc. too
    cursor.execute("DELETE FROM borrowed_books WHERE user_id = %s", (user_id,))
    cursor.execute("DELETE FROM favorites WHERE user_id = %s", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()

    print(f"User {user_email} deleted their account.")
    session.clear()
    return redirect(url_for('home'))

@app.route('/user/change_password', methods=['GET', 'POST'])
def change_password():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
    except Exception as e:
        print(f"An Error occured with the database {e}")
        error_message = "There is a problem with connection to database"
        return render_template("user.html", error_message=error_message)
    error_message = None
    if 'user_id' not in session:
        print("Unauthorized attempt to delete account")
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        user_id = session['user_id']
        cursor.execute("SELECT password FROM users WHERE id = %s", (user_id,))
        old_rem_password = cursor.fetchone()
        old_rem_password = old_rem_password['password']
        current_password  = request.form.get('current_password')
        hash_current_password = hashlib.sha256(current_password.encode()).hexdigest()
        new_password =  request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # if old_rem_password == old_password and new_password == confirm_password:
        if old_rem_password != hash_current_password:
            error_message = "Womp Womp your password is wrong"
            return render_template("change_password.html", error_message=error_message, postN_password=new_password, confirmN_password=confirm_password)
        
        if new_password != confirm_password:
            error_message = "HEY you dont have it the same"
            return render_template("change_password.html", error_message=error_message)

        new_password = hashlib.sha256(new_password.encode()).hexdigest()
        try:
            cursor.execute("UPDATE users SET password = %s WHERE user_id = %s", (new_password, user_id))
            conn.commit()
            nice_message = "password succesfully changed"
        except Exception as e:
            print(f"an Error {e} ocured when connecting to database")
            error_message = "password not changed Error with database. Contact backend wizard"
            return render_template('change_password.html', error_message=error_message)

        return render_template('user.html',error_message=nice_message)
    
    return render_template('change_password.html')

@app.route('/user/favorite')
def favorite():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
    except Exception as e:
        print(f"An Error occured with the database {e}")
        error_message = "There is a problem with connection to database"
        return render_template("user.html", error_message=error_message)
    if 'user_id' not in session:
        print("Unauthorized access to /user")
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    query = """
        SELECT b.id, b.title
        FROM favourites f
        JOIN books b ON f.book_id = b.id
        WHERE f.user_id = %s
    """

    cursor.execute(query, (user_id,))
    fav_books = cursor.fetchall()

    return render_template("favorites.html", fav_books=fav_books)

@app.route('/user/history')
def borrow_history():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
    except Exception as e:
        print(f"An Error occured with the database {e}")
        error_message = "There is a problem with connection to database"
        return render_template("user.html", error_message=error_message)
    if 'user_id' not in session:
        print("Unauthorized access to /user")
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    query = """
        SELECT b.title, bb.borrowed_at, bb.returned_at
        FROM borrowed_books bb
        JOIN books b ON bb.book_id = b.id
        WHERE bb.user_id = %s
        """
    try:
        cursor.execute(query, (user_id,))
        history = cursor.fetchall()
    except:
        print("database problem")
        return render_template("history.html")
    return render_template("history.html", history=history)

@app.route('/books')
def books():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
    except Exception as e:
        print(f"An Error occured with the database {e}")
        error_message = "There is a problem with connection to database"
        return render_template("user.html", error_message=error_message)
    cursor.execute("SELECT id, title FROM books")
    books = cursor.fetchall()
    return render_template("books.html", books=books)

@app.route('/books/<int:book_id>')
def book_details(book_id):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
    except Exception as e:
        print(f"An Error occured with the database {e}")
        error_message = "There is a problem with connection to database"
        return render_template("user.html", error_message=error_message)
    if request.method == 'POST' and 'user_id' in session:
        review_text = request.form.get('review')
        user_id = session['user_id']
        query = "INSERT INTO review (user_id, book_id, review_text) VALUES (%s, %s, %s)"
        cursor.execute(query, (user_id, book_id, review_text))
        conn.commit()
    
    # Get book details
    cursor.execute("SELECT * FROM books WHERE id = %s", (book_id,))
    book = cursor.fetchone()

    if not book:
        print(f"Book: {book} was not founf")
        return "Book not found", 404
    
    # Fetch reviews for this book
    cursor.execute("""
        SELECT r.review_text, r.created_at, u.username
        FROM review r
        JOIN users u ON r.user_id = u.id
        WHERE r.book_id = %s
        ORDER BY r.created_at DESC
    """, (book_id,))
    reviews = cursor.fetchall()

    return render_template("book_details.html", book=book, reviews=reviews)

@app.route('/books/borrow/<int:book_id>', methods=['POST'])
def borrow_book(book_id):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
    except Exception as e:
        print(f"An Error occured with the database {e}")
        error_message = "There is a problem with connection to database"
        return render_template("user.html", error_message=error_message)
   
    if 'user_id' not in session:
        print("Unauthorized access to /user")
        return redirect(url_for('login'))
   
    user_id = session['user_id']


    cursor.execute("SELECT * FROM books WHERE id = %s")
    book = cursor.fetchone()
    if not book or not book['pdf_file']:
        print(f"book id: {book_id} PDF is missing")
        return "book not found or missing PDF"
 
    now = datetime.now().isoformat()
    cursor.execute("INSERT INTO borrowed_books (user_id, book_id, borrowed_at) VALUES (%s, %s, %s)", (user_id, book_id, now))
    conn.commit()
    return send_from_directory('static/pdfs', book['pdf_file'], as_attachment=True)

@app.route('/search')
def search():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
    except Exception as e:
        print(f"An Error occured with the database {e}")
        error_message = "There is a problem with connection to database"
        return render_template("user.html", error_message=error_message)
    
    query = request.args.get('query')

    if not query:
        return redirect(url_for('books'))

    like_pattern = f"%{query}%"
    sql = """
        SELECT * FROM books
        WHERE title LIKE %s OR author LIKE %s
    """
    cursor.execute(sql, (like_pattern, like_pattern))
    results = cursor.fetchall()

    return render_template("search_results.html", books=results, search_term=query)

@app.route('/login/admin', methods=['GET', 'POST'])
def admin_login():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
    except Exception as e:
        print(f"An Error occured with the database {e}")
        error_message = "There is a problem with connection to database"
        return render_template("user.html", error_message=error_message)
    error_message = None
    if request.method == 'POST':
        admin_password = request.form.get('password')
        admin_email = request.form.get('email')

        query = "SELECT * FROM users WHERE email = %s AND is_admin = TRUE"
        cursor.execute(query, (admin_email,))
        admin_user = cursor.fetchone()


        if admin_user:
            hashed_input = hashlib.sha256(admin_password.encode()).hexdigest()
            if hashed_input == admin_user['password']:
                session['admin_id'] = admin_user['id']
                session['admin_email'] = admin_user['email']
                print(f"Admin {admin_user['email']} logged in successfully")
                return redirect(url_for('admin_dashboard'))
            else:
                print(f"Wrong admin password for {admin_email}")
                error_message = "Incorrect password"
        else:
            print(f"Admin login failed: {admin_email} not found or not an admin")
            error_message = "NO admin account with that email"

    return render_template("admin_login.html", error_message=error_message)

@app.route('/admin')
def admin_dashboard():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
    except Exception as e:
        print(f"An Error occured with the database {e}")
        error_message = "There is a problem with connection to database"
        return render_template("user.html", error_message=error_message)
    if 'admin_id' not in session:
        print("Unauthorized access to /admin")
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
        WHERE last_seen >= NOW() - INTERVAL 5 MINUTE
    """)
    online_users = cursor.fetchone()['online_users']

    return render_template("admin_dashboard.html",
                           total_users=total_users,
                           total_books=total_books,
                           online_users=online_users,
                           borrow_stats=borrow_stats
                           )

@app.route('/admin/books/add', methods=['GET', 'POST'])
def add_book():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
    except Exception as e:
        print(f"An Error occured with the database {e}")
        error_message = "There is a problem with connection to database"
        return render_template("user.html", error_message=error_message)
    error_message = None

    if 'admin_id' not in session:
        print("Unauthorized admin book add attempt")
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
            INSERT INTO books (title, author, description, published_year, genre, cover_image, pdf_file)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        values = (title, author, description, published_year, genre, True, filename, pdf_filename)

        try:
            cursor.execute(query, values)
            conn.commit()
            print(f"Admin added book: {title}")
            return redirect(url_for('books'))
        except Exception as e:
            print(f"Error adding book: {e}")
            error_message = "Error adding book"

    return render_template("add_book.html", error_message=error_message)

@app.route('/admin/books/update/<int:book_id>', methods=['GET', 'POST'])
def update_book(book_id):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
    except Exception as e:
        print(f"An Error occured with the database {e}")
        error_message = "There is a problem with connection to database"
        return render_template("user.html", error_message=error_message)
    book = None
    if 'admin_id' not in session:
        print("Unauthorized admin book add attempt")
        return redirect(url_for('admin_login'))
    
    cursor.execute("SELECT * FROM books WHERE id = %s", (book_id,))
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
            title = %s,
            author = %s,
            description = %s,
            published_year = %s,
            genre = %s,
            cover_image = %s,
            pdf_file = %s
            WHERE id = %s
        """
        values = (title, author, description, published_year, genre, filename, pdf_filename, book_id)

        try:
            cursor.execute(update_query, values)
            conn.commit()
            print(f"Book {book_id} updated by admin")
            return redirect(url_for('book_details', book_id=book_id))
        except Exception as e:
            print(f"Error updating book {book_id}: {e}")
            return render_template("update_book.html", book=book, error_message="Something went wrong")
        
    return render_template("update_book.html", book=book, error_message=error_message)

@app.route('/admin/books/remove/<int:book_id>', methods=['GET', 'POST'])
def remove_book(book_id):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
    except Exception as e:
        print(f"An Error occured with the database {e}")
        return render_template("admin_dashboard.html")
    if 'admin_id' not in session:
        print("Unauthorized admin book add attempt")
        return redirect(url_for('admin_login'))
    
    try:
        query = "DELETE FROM books WHERE id = %s"
        cursor.execute(query, (book_id,))
        conn.commit()
        print(f"Book {book_id} removed by admin")
        return redirect(url_for('books'))
    except Exception as e:
        print(f"Error removing book {book_id}: {e}")
        return "something went wrong"

@app.route('/about_us')
def about_us():
    return render_template('about_us.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

#---Before---#

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

@app.before_request
def update_last_seen():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
    except Exception as e:
        print(f"An Error occured with the database {e}")
    if 'user_id' in session:
        user_id = session.get('user_id')
        now = datetime.now()
        try:
            cursor.execute("UPDATE users SET last_seen = %s WHERE id = %s", (now, user_id))
            conn.commit()
        except Exception as e:
            print(f"Failed to update last_seen: {e}")

if __name__ == "__main__":
    app.run(debug=False, port=8000, host="0.0.0.0")
