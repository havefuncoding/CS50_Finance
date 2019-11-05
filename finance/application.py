import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    return apology("TODO")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    return apology("TODO")


@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""
    return jsonify("TODO")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        # Quote response example, {'name': 'Apple, Inc.', 'price': 257.955, 'symbol': 'AAPL'}
        quote = lookup(request.form.get("symbol"))
        if not quote:
            return apology("invalid symbol")                # Return error if symbol missing or invalid
        else:
            return render_template("quote.html", company=quote['name'], price=quote['price'], symbol=quote['symbol'])

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
	# POST : Submitting Form
        if not request.form.get("username"):
            return apology("must provide username")         # Return error if no username provided
        else:
            username = request.form.get("username")

        if not request.form.get("password"):
            return apology("must provide password")         # Return error if no password providee
        else:
            password = request.form.get("password")

        if not request.form.get("confirmation") or request.form.get("confirmation") != request.form.get("password"):
            return apology("passwords must match")          # Return error if password != confirmation
        else:
            confirmation = request.form.get("confirmation")

        hashed_password = generate_password_hash(password)  # Otherwise hash password

        is_new_user = len(db.execute(f"SELECT id FROM users WHERE username = '{username}'")) == 0
        if not is_new_user:
            return apology("username taken")                # Return error if username already in DB
        else:
            db.execute("INSERT INTO users(username, hash) VALUES(:username, :hash)",
                        username=username, hash=hashed_password)

            new_user = db.execute(f"SELECT id FROM users WHERE username = '{username}'")
            if not new_user:
                return apology("failed to add new user")    # Ensure user added to db
            else:
                new_user_id = new_user[0]['id']
                session["user_id"] = new_user[0]['id']      # And add user session

        return redirect(url_for("index"))                   # Then redirect back to index.html

    # GET : Navigating to Register page
    else:
        return render_template("register.html")             # Navigate user to register page


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    return apology("TODO")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)




##############################  - TESTING -  ######################################
def print_exaggerated(print_value, print_note="LOOK! -> "):
    print("\n\n\n\n\n")
    print("************\n", print_note, print_value, "\n************")
    print("\n\n\n\n\n")
