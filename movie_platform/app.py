from flask import Flask, render_template, request, redirect, url_for, session
from db_config import get_db_connection
import random

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Login route 
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        # 'next' parameter to find where the user was trying to go
        next_page = request.args.get('next', '/')  # Default to '/' if no next parameter exists
        return render_template('login.html', next=next_page, error=None)

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Query the database to check for matching credentials
        cursor.execute('SELECT * FROM login WHERE username = %s AND pass = %s', (username, password))
        user = cursor.fetchone()

        if user:
            # Successfully logged in, store user in session
            session['user'] = user['username']
            cursor.close()
            conn.close()

            # Get the next URL from the form (which contains the original page the user wanted to visit)
            next_url = request.form.get('next')  
            return redirect(next_url)
        else:
            cursor.close()
            conn.close()

            # If authentication fails, show an error message
            error_message = "Invalid username or password. Please try again."
            return render_template('login.html', next=request.form.get('next', '/'), error=error_message)


# Logout route
@app.route('/logout')
def logout():
    next_page = request.args.get('next', request.referrer)
    session.pop('user', None)  # Remove user from session
    if next_page and ('/movie/' in next_page or '/movies' in next_page or '/' in next_page):
        return redirect(next_page)  # Redirect to the previous page they were on
    else:
        return redirect('/')


# Index route
@app.route("/")
def index():
    conn = get_db_connection()

    # Fetch all movies from the database with poster links
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT 
            movies.id, 
            movies.movie_name,
            (SELECT MAX(posters.link) 
             FROM posters 
             WHERE posters.id = movies.id) AS poster_link
        FROM movies
    """)
    all_movies = cursor.fetchall()

    cursor.close()
    conn.close()

    # Select 5 random movies
    random_movies = random.sample(all_movies, 5)

    # Pass the random movies to the template
    return render_template("index.html", movies=random_movies)


# All movies route
@app.route("/movies")
def list_movies():
    genre = request.args.get('genre', '')
    language = request.args.get('language', '')

    # SQL query to fetch movies along with posters and comma separated genres and languages
    query = """
        SELECT 
            movies.id, 
            movies.movie_name, 
            movies.movie_date, 
            movies.movie_length, 
            movies.movie_rating,
            (SELECT GROUP_CONCAT(DISTINCT genres.genre SEPARATOR ', ') 
            FROM genres 
            WHERE genres.id = movies.id) AS genres,
            (SELECT GROUP_CONCAT(DISTINCT languages.film_language SEPARATOR ', ') 
            FROM languages 
            WHERE languages.id = movies.id) AS languages,
            (SELECT MAX(posters.link) 
            FROM posters 
            WHERE posters.id = movies.id) AS poster_link
        FROM movies
    """
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query)
    movies = cursor.fetchall()

    # Fetch distinct genres and languages for the filter options
    cursor.execute("SELECT DISTINCT genre FROM genres")
    genres = cursor.fetchall()

    cursor.execute("SELECT DISTINCT film_language FROM languages")
    languages = cursor.fetchall()
    
    cursor.close()
    conn.close()

    # Pass the movies data and filter options to the template
    return render_template("movie_list.html", movies=movies, genres=genres, languages=languages, selected_genre=genre, selected_language=language)


# Search route
@app.route('/search', methods=['GET'])
def search_movies():
    query = request.args.get('query', '')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # SQL query to fetch movies along with posters and comma separated genres and languages according to the searched movie name
    sql = """
        SELECT 
            movies.id, 
            movies.movie_name, 
            movies.movie_date, 
            movies.movie_length, 
            movies.movie_rating,
            (SELECT GROUP_CONCAT(DISTINCT genre SEPARATOR ', ') 
             FROM genres 
             WHERE genres.id = movies.id) AS genres,
            (SELECT GROUP_CONCAT(DISTINCT film_language SEPARATOR ', ') 
             FROM languages 
             WHERE languages.id = movies.id) AS languages,
            (SELECT MAX(posters.link) 
             FROM posters 
             WHERE posters.id = movies.id) AS poster_link
        FROM movies
        WHERE movies.movie_name LIKE %s
    """

    cursor.execute(sql, (f'%{query}%',))
    movies = cursor.fetchall()

    # Fetch distinct genres and languages for the filter options
    cursor.execute("SELECT DISTINCT genre FROM genres")
    genres = cursor.fetchall()

    cursor.execute("SELECT DISTINCT film_language FROM languages")
    languages = cursor.fetchall()

    cursor.close()
    conn.close()

    # Pass the flag for no movies found
    no_movies = len(movies) == 0

    return render_template('movie_list.html', movies=movies, genres=genres, languages=languages, no_movies=no_movies)


# Filter route 
@app.route('/filter', methods=['GET'])
def filter_movies():
    # Parameters for filter
    genre = request.args.get('genre', '')
    language = request.args.get('language', '')
    year_min = request.args.get('year_min', None, type=int)
    year_max = request.args.get('year_max', None, type=int)
    runtime_min = request.args.get('runtime_min', None, type=int)
    runtime_max = request.args.get('runtime_max', None, type=int)
    rating_min = request.args.get('rating_min', None, type=float)
    rating_max = request.args.get('rating_max', None, type=float)

    # SQL query for fetching movie details 
    query = """
        SELECT 
            movies.id, 
            movies.movie_name, 
            movies.movie_date, 
            movies.movie_length, 
            movies.movie_rating,
            (SELECT GROUP_CONCAT(DISTINCT genre SEPARATOR ', ') 
             FROM genres 
             WHERE genres.id = movies.id) AS genres,
            (SELECT GROUP_CONCAT(DISTINCT film_language SEPARATOR ', ') 
             FROM languages 
             WHERE languages.id = movies.id) AS languages,
            (SELECT MAX(posters.link) 
             FROM posters 
             WHERE posters.id = movies.id) AS poster_link
        FROM movies
        WHERE 1=1
    """
    params = []

    # Filtering conditions
    if genre:
        query += " AND EXISTS (SELECT 1 FROM genres WHERE genres.id = movies.id AND genres.genre = %s)"
        params.append(genre)

    if language:
        query += " AND EXISTS (SELECT 1 FROM languages WHERE languages.id = movies.id AND languages.film_language = %s)"
        params.append(language)

    if year_min is not None:
        query += " AND movies.movie_date >= %s"
        params.append(year_min)

    if year_max is not None:
        query += " AND movies.movie_date <= %s"
        params.append(year_max)

    if runtime_min is not None:
        query += " AND movies.movie_length >= %s"
        params.append(runtime_min)

    if runtime_max is not None:
        query += " AND movies.movie_length <= %s"
        params.append(runtime_max)

    if rating_min is not None:
        query += " AND movies.movie_rating >= %s"
        params.append(rating_min)

    if rating_max is not None:
        query += " AND movies.movie_rating <= %s"
        params.append(rating_max)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, tuple(params))
    movies = cursor.fetchall()

    # Fetch distinct genres and languages for the filter options
    cursor.execute("SELECT DISTINCT genre FROM genres")
    genres = cursor.fetchall()

    cursor.execute("SELECT DISTINCT film_language FROM languages")
    languages = cursor.fetchall()

    cursor.close()
    conn.close()

    # Pass the flag for no movies found
    no_movies = len(movies) == 0

    return render_template('movie_list.html', movies=movies, genres=genres, languages=languages, no_movies=no_movies)


# Add route
@app.route('/add_movie', methods=['GET', 'POST'])
def add_movie():
    # Check for user
    if 'user' not in session:
        return redirect(url_for('login', next=request.url))   # Redirect to login if not logged in
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        movie_id = request.form['id']
        movie_name = request.form['movie_name']
        movie_date = request.form['movie_date']
        tagline = request.form['tagline']
        description = request.form['movie_description']
        movie_length = request.form['movie_length']
        movie_rating = request.form['movie_rating']

        actor_names = request.form.getlist('actor_name[]')
        actor_roles = request.form.getlist('actor_role[]')

        crew_names = request.form.getlist('crew_name[]')
        crew_roles = request.form.getlist('crew_role[]') 

        countries = request.form.get('countries', '').split(',')   
        genres = request.form.get('genres', '').split(',') 
        languages = request.form.get('languages', '').split(',')  
        themes = request.form.get('themes', '').split(',') 
        studio = request.form['studio']
        poster_link = request.form['poster_link']

        cursor.execute("""
            INSERT INTO movies (id, movie_name, movie_date, tagline, movie_description, movie_length, movie_rating)
            VALUES (%s, %s, %s, %s, %s, %s, %s) 
        """, (movie_id, movie_name, movie_date, tagline, description, movie_length, movie_rating))
        

        for actor_name, actor_role in zip(actor_names, actor_roles):
            cursor.execute("INSERT INTO actors (id, actor_name, actor_role) VALUES (%s, %s, %s)", 
                           (movie_id, actor_name, actor_role))
        for country in countries:
            if country.strip():
                cursor.execute("INSERT INTO countries (id, country) VALUES (%s, %s)", (movie_id, country.strip()))

        for crew_name, crew_role in zip(crew_names, crew_roles):
            cursor.execute("INSERT INTO crew (id, crew_role, crew_name) VALUES (%s, %s, %s)",
                           (movie_id, crew_role, crew_name))

        for genre in genres:
            if genre.strip():
                cursor.execute("INSERT INTO genres (id, genre) VALUES (%s, %s)", (movie_id, genre.strip()))

        for language in languages:
            if language.strip():
                cursor.execute("INSERT INTO languages (id, film_language) VALUES (%s, %s)", (movie_id, language.strip()))

        for theme in themes:
            if theme.strip():
                cursor.execute("INSERT INTO themes (id, theme) VALUES (%s, %s)", (movie_id, theme.strip()))

        if studio.strip():
            cursor.execute("INSERT INTO studios (id, studio) VALUES (%s, %s)", (movie_id, studio.strip()))

        if poster_link.strip():
            cursor.execute("INSERT INTO posters (id, link) VALUES (%s, %s)", (movie_id, poster_link.strip()))

        conn.commit()
        cursor.close()
        conn.close()

        return redirect('/movies')

    return render_template('add_movie.html')


# Route for update 
@app.route('/update_movie/<int:movie_id>', methods=['GET', 'POST'])
def update_movie(movie_id):
    if 'user' not in session:
        return redirect(url_for('login', next=request.url))   # Redirect to login if not logged in
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM movies WHERE id = %s", (movie_id,))
    existing_movie = cursor.fetchone()

    if existing_movie is None:
        return "Movie not found!", 404  

    if request.method == 'POST':
        movie_name = request.form.get('movie_name', existing_movie[1])  
        movie_date = request.form.get('movie_date', existing_movie[2]) 
        tagline = request.form.get('tagline', existing_movie[3])  
        description = request.form.get('movie_description', existing_movie[4]) 
        movie_length = request.form.get('movie_length', existing_movie[5]) 
        movie_rating = request.form.get('movie_rating', existing_movie[6]) 

        cursor.execute("""
            UPDATE movies
            SET movie_name = %s, movie_date = %s, tagline = %s, movie_description = %s,
                movie_length = %s, movie_rating = %s
            WHERE id = %s
        """, (
            movie_name,
            movie_date,
            tagline,
            description,
            movie_length,
            movie_rating,
            movie_id
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return redirect('/movies')

    else:
        
        cursor.execute("SELECT * FROM movies WHERE id = %s", (movie_id,))
        movie = cursor.fetchone()
        conn.close()

        if movie is None:
            return "Movie not found", 404 

        return render_template('update_movie.html', movie=movie)


# Delete route
@app.route('/delete_movie/<int:movie_id>', methods=['POST'])
def delete_movie(movie_id):
    if 'user' not in session:
        return redirect(url_for('login', next=url_for('movies')))     
    conn = get_db_connection()
    cursor = conn.cursor()


    cursor.execute("DELETE FROM actors WHERE id = %s", (movie_id,))
    cursor.execute("DELETE FROM countries WHERE id = %s", (movie_id,))
    cursor.execute("DELETE FROM crew WHERE id = %s", (movie_id,))
    cursor.execute("DELETE FROM genres WHERE id = %s", (movie_id,))
    cursor.execute("DELETE FROM languages WHERE id = %s", (movie_id,))
    cursor.execute("DELETE FROM themes WHERE id = %s", (movie_id,))
    cursor.execute("DELETE FROM studios WHERE id = %s", (movie_id,))
    cursor.execute("DELETE FROM posters WHERE id = %s", (movie_id,))
    cursor.execute("DELETE FROM movies WHERE id = %s", (movie_id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect('/movies')


# Movie detail route
@app.route('/movie/<int:id>', methods=['GET'])
def movie_details(id):
    conn = get_db_connection()

    # Fetch every detail about movie
    cursor1 = conn.cursor(dictionary=True)
    cursor1.execute("""
        SELECT 
            movies.id, 
            movies.movie_name, 
            movies.movie_date, 
            movies.movie_length, 
            movies.movie_rating,
            movies.movie_description,
            movies.tagline,
            -- Genre subquery
            (SELECT GROUP_CONCAT(DISTINCT genre SEPARATOR ', ') 
             FROM genres 
             WHERE genres.id = movies.id) AS genres,
            -- Language subquery
            (SELECT GROUP_CONCAT(DISTINCT film_language SEPARATOR ', ') 
             FROM languages 
             WHERE languages.id = movies.id) AS languages,
            -- Poster subquery (ensure only 1 poster link is returned)
            (SELECT posters.link 
             FROM posters 
             WHERE posters.id = movies.id 
             LIMIT 1) AS poster_link,
            -- Studio subquery
            (SELECT studios.studio 
             FROM studios 
             WHERE studios.id = movies.id 
             LIMIT 1) AS studio
        FROM movies
        WHERE movies.id = %s
    """, (id,))
    movie = cursor1.fetchone()
    cursor1.fetchall()  
    cursor1.close()

    if not movie:
        conn.close()
        return render_template('404.html'), 404

    # Fetch actors
    cursor2 = conn.cursor(dictionary=True)
    cursor2.execute("""
        SELECT actor_name, actor_role 
        FROM actors 
        WHERE id = %s
    """, (id,))
    actors = cursor2.fetchall()
    cursor2.fetchall()  
    cursor2.close()

    # Fetch crew members
    cursor3 = conn.cursor(dictionary=True)
    cursor3.execute("""
        SELECT crew_name, crew_role 
        FROM crew 
        WHERE id = %s
    """, (id,))
    crew = cursor3.fetchall()
    cursor3.fetchall()  
    cursor3.close()

    # Fetch themes
    cursor4 = conn.cursor(dictionary=True)
    cursor4.execute("""
        SELECT theme 
        FROM themes 
        WHERE id = %s
    """, (id,))
    themes = [row['theme'] for row in cursor4.fetchall()]
    cursor4.fetchall()  
    cursor4.close()

    conn.close()

    return render_template('movie_detail.html', movie=movie, actors=actors, crew=crew, themes=themes)

if __name__ == '__main__':
    app.run(debug=True)