import os
import time

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
    user_id=session["user_id"]

    cash_remaining = round(db.execute("SELECT cash FROM users WHERE id = :user_id",
                                user_id = user_id)[0]['cash'], 2)                   # Funds available

    sum_all = cash_remaining                                                        # Add to running sum

    portfolio = db.execute("SELECT p.symbol, t.name, p.shares, p.paid_total " +
                            "FROM portfolios p " +
                                "left join transactions t on p.transaction_id = t.id "
                            "WHERE p.user_id = :user_id",
                            user_id = user_id)                                      # Get portfolio data

    for item in portfolio:
        item['current_price'] = lookup(item['symbol'])['price']                     # Add current/latest price
        print_exaggerated("{:.2f}".format(item['paid_total']), "+++++++++++")
        item['paid_total_formatted'] = "{:.2f}".format(item['paid_total'])

        sum_all += item['paid_total']                                               # And add to sum, past paid amt

    return render_template("index.html", portfolio=portfolio, cash_remaining="{:.2f}".format(cash_remaining), sum_all="{:.2f}".format(sum_all))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":
        stock = lookup(request.form.get("symbol"))
        if not stock:
            return apology("invalid symbol")

        symbol = stock['symbol']                        # Stock symbol
        name = stock['name']                            # Stock name
        price = stock['price']                          # Stock price
        shares = int(request.form.get("shares"))        # Number of shares
        cost_to_buy = stock['price'] * shares           # Cost to buy
        user_id = session["user_id"]                    # User id
        user = db.execute("SELECT * FROM users WHERE id = :user_id", user_id=user_id) # User object
        available_funds = user[0]['cash']               # User available funds

        print(symbol, name, price, shares, cost_to_buy, user_id, user, available_funds)

        if available_funds < cost_to_buy:               # Return error if insufficient funds
            return apology("insufficient funds")

        # Log transaction
        transaction_id = db.execute("INSERT INTO transactions (symbol, name, price, count, buy_or_sell, user_id) " +
                                    "VALUES (:symbol, :name, :price, :count, :buy_or_sell, :user_id)",
                                    symbol=symbol,
                                    name=name,
                                    price=price,
                                    count=shares,
                                    buy_or_sell='b',
                                    user_id=user_id)


        # Check if current transaction stock in current portfolio
        portfolio_stocks = db.execute("SELECT symbol FROM portfolios WHERE user_id = :user_id",
                                        user_id=session["user_id"])

        portfolio_stock_symbols = [stock['symbol'] for stock in portfolio_stocks]

        # If existing in current portfolio, update shares count and latest transaction_if
        if stock['symbol'] in portfolio_stock_symbols:
            db.execute("UPDATE portfolios SET shares = shares + :count, transaction_id = :transaction_id, paid_total = paid_total + :cost " +
                        "WHERE user_id = :user_id and symbol = :symbol",
                        count=shares,
                        user_id=session['user_id'],
                        transaction_id=transaction_id,
                        cost=cost_to_buy,
                        symbol=symbol)

        # Otherwise insert new entry for new stock in portfolio
        else:
            db.execute("INSERT INTO portfolios (user_id, transaction_id, symbol, shares, paid_total) " +
                        "VALUES (:user_id, :transaction_id, :symbol, :shares, :paid_total)",
                        user_id=session['user_id'],
                        transaction_id=transaction_id,
                        symbol=stock['symbol'],
                        paid_total=cost_to_buy,
                        shares=shares)

        # Update cash
        db.execute("UPDATE users SET cash = cash - :cost WHERE id = :user_id", cost=cost_to_buy, user_id=session["user_id"])

        flash("Bought!")
        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""

    username = request.args.get("username")

    username_available = len(db.execute("SELECT username FROM users WHERE username = :username",
                                    username=username)) == 0

    if not username_available or len(username) < 1:
        return jsonify(False)
    else:
        return jsonify(True)


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    transactions = db.execute("SELECT symbol, count, price, timestamp FROM transactions WHERE user_id = :user_id",
                              user_id = session["user_id"])
    for transaction in transactions:
        transaction['price_formatted'] = "{:.2f}".format(transaction['price'])

    return render_template("history.html", transactions=transactions)

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
            return apology("invalid symbol")
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
            print_exaggerated("DO NOTHING")
            #return apology("username taken")                # Return error if username already in DB
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
    user_id = session["user_id"]
    data = db.execute("SELECT symbol FROM portfolios WHERE user_id = :user_id",
                        user_id = user_id)
    symbols = [item['symbol'] for item in data]             # Collect symbols for select dropdown menu

    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares_to_sell = int(request.form.get("shares"))
        if not symbol or not shares_to_sell:                # Return error if inputs missing
            return apology("invalid symbol/shares data")

        shares_owned = db.execute("SELECT shares FROM portfolios " +
                                "WHERE user_id = :user_id and symbol = :symbol",
                                user_id = user_id,
                                symbol = symbol)[0]['shares']

        if shares_owned < shares_to_sell:
            return apology("too many shares")               # Error if trying to sell more than owned


        stock = lookup(symbol)                     # Get stock object

        name = stock['name']                                # Stock name

        price_per_share = stock['price']                    # Stock price per share
        earnings_on_sale = price_per_share * shares_to_sell # Calculate earnings on sale

        # Log transaction
        transaction_id = db.execute("INSERT INTO transactions (symbol, name, price, count, buy_or_sell, user_id) " +
                                    "VALUES (:symbol, :name, :price, :count, :buy_or_sell, :user_id)",
                                    symbol=symbol,
                                    name=name,
                                    price=price_per_share,
                                    count=shares_to_sell * -1,
                                    buy_or_sell='s',
                                    user_id=user_id)


        # Update shares in portfolios
        db.execute("UPDATE portfolios SET shares = shares - :count, transaction_id = :transaction_id, paid_total = paid_total - :earnings " +
                        "WHERE user_id = :user_id and symbol = :symbol",
                        count=shares_to_sell,
                        user_id=session['user_id'],
                        transaction_id=transaction_id,
                        earnings=earnings_on_sale,
                        symbol=symbol)


        # Update cash
        db.execute("UPDATE users SET cash = cash + :earnings WHERE id = :user_id",
                    earnings = earnings_on_sale,
                    user_id=user_id)

        flash("Sold!")

        return redirect("/")

    else:
        return render_template("sell.html", symbols=symbols)

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
    time.sleep(1)
    print("\n\n\n\n\n")
