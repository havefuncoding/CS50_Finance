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
    """Show portfolio of stocks : Table displays
    | Symbol | Name           | Shares | Price      | Total    |
    | GOOGL  | Alphabet, Inc. | 2      | $1291.01   | $2582.02 |
    | MSFT   | Microsoft Corp.| 5      | $144.06    | $720.30  |
    | CASH   |                |        |            | $6697.68 |  # Cash remaining
    ------------------------------------------------------------
                                                      $10000.00   # Default balance 10K

    Note that the 'Price' column reflects current market price and not price paid
    And the 'Total' column reflects purchased market price (price paid)
    """

    # Get user id
    user_id = session["user_id"]

    # Query for the cash (remaining) in user table for current session user
    cash_remaining = db.execute(f"SELECT cash FROM users WHERE id = {user_id}")
    cash_remaining = cash_remaining[0]['cash']  # Grab just the value from return format, [{'cash': #####}]

    # Query for the portfolio of current user
    portfolio = db.execute(
        f"SELECT p.symbol, t.name, p.shares, p.paid_total FROM portfolios p left join transactions t on p.transaction_id = t.id WHERE p.user_id = '{user_id}'")

    # Calculate cost of portfolio (total amount paid to purchase all stocks in portfolio)
    portfolio_sum = 0

    # Sum all balances, cash remaining + cash used (cost of all stock purchases)
    sum_all = cash_remaining
    for item in portfolio:
        item['current_price_formatted'] = "{:.2f}".format(lookup(item['symbol'])['price'])      # Add formatted to 2 decimal
        item['paid_total_formatted'] = "{:.2f}".format(item['paid_total'])                      # Add formatted to 2 decimal
        sum_all += item['paid_total']

    return render_template("index.html", portfolio=portfolio, cash_remaining="{:.2f}".format(cash_remaining), sum_all="{:.2f}".format(sum_all))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    # Track current user
    user_id = session["user_id"]

    # If the method is POST, take the form arguments
    if request.method == "POST":
        stock = lookup(request.form.get("symbol"))      # Ensure stock object is vali
        if not stock:
            return apology("invalid symbol")

        symbol = stock['symbol']                        # Extract the symbol from stock
        name = stock['name']                            # Extract the company name
        price = stock['price']                          # Extract the per-share price
        shares = float(request.form.get("shares"))      # Extract the number of shares

        if shares < 0:
            return apology("enter valid number")        # Return error if number less than 0

        # Calculate the cost to buy N shares
        cost_to_buy = stock['price'] * shares

        # Query the DB for data of session user
        user_id = session["user_id"]                    # Extract the current user id
        user = db.execute(f"SELECT * FROM users WHERE id = {user_id}")  # Store user info into object
        available_funds = user[0]['cash']               # Extract the remaining cash of user

        if available_funds < cost_to_buy:               # Return error if cash insufficient to make purchase
            return apology("insufficient funds")

        # Log transaction, returns transaction id, retain this for future query use
        transaction_id = db.execute(
            f"INSERT INTO transactions (symbol, name, price, count, buy_or_sell, user_id) VALUES ('{symbol}', '{name}', {price}, {shares}, 'b', {user_id})")

        # Get list of all stocks in user portfolio
        portfolio_stocks = db.execute(f"SELECT symbol FROM portfolios WHERE user_id = {user_id}")
        portfolio_stock_symbols = [stock['symbol'] for stock in portfolio_stocks]   # Extract just the symbols

        # If added stock is not new (if stock pre-exists in user portfolio before lates transaction)
        # Then update the purchased shares count and cost invested in purchase(s)
        if stock['symbol'] in portfolio_stock_symbols:
            db.execute(
                f"UPDATE portfolios SET shares = shares + {shares}, transaction_id = {transaction_id}, paid_total = paid_total + {cost_to_buy} WHERE user_id = {user_id} and symbol = '{symbol}'")
        # Otherwise insert new entry for new stock in portfolio
        else:
            db.execute(
                f"INSERT INTO portfolios (user_id, transaction_id, symbol, shares, paid_total) VALUES ({user_id}, {transaction_id}, '{symbol}', {shares}, {cost_to_buy})")

        # Update cash
        db.execute(f"UPDATE users SET cash = cash - {cost_to_buy} WHERE id = {user_id}")

        # Flash successful purchase message and redirect to index.html (page displaying table of user portfolio)
        flash("Bought!")
        return redirect("/")

    # Else if the method is GET, if user navigated to page without submitting form, then simplay navigate to buy.html
    else:
        return render_template("buy.html")


@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""

    # Check/verify the username proposed for new user
    username = request.args.get("username")
    username_available = len(db.execute(f"SELECT username FROM users WHERE username = '{username}'")) == 0  # Check if in DB
    status = False if len(username) < 2 or not username_available else True                                 # Add check for length

    # Return boolean status of if username is valid and available
    return jsonify(status)


@app.route("/check_symbol", methods=["GET"])
def check_quote():
    """Return true if username available, else false, in JSON format"""

    # Get symbol from form
    symbol = request.args.get("symbol")

    # Lookup symbol
    # Quote response example, {'name': 'Apple, Inc.', 'price': 257.955, 'symbol': 'AAPL'}
    stock = lookup(symbol)

    # Return stock company name if symbol is valid else return False
    if stock:
        return jsonify(stock['name'])
    else:
        return jsonify(False)


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    # Get user id from current session
    user_id = session["user_id"]

    # Get transactions for current user
    transactions = db.execute(
        f"SELECT symbol, count, price, timestamp FROM transactions WHERE user_id = {user_id} order by timestamp desc")

    # String-format 'price' data to 2 decimal places for html display
    for transaction in transactions:
        transaction['price_formatted'] = "{:.2f}".format(transaction['price'])

    # Navigate to history page (containing list of transactions for current user)
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
        username = request.form.get("username")
        rows = db.execute(f"SELECT * FROM users WHERE username = '{username}'")

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

    # If user submitted form, verify form args and render error or data for submitted args
    if request.method == "POST":
        # Store quote object
        # Quote response example, {'name': 'Apple, Inc.', 'price': 257.955, 'symbol': 'AAPL'}
        quote = lookup(request.form.get("symbol"))

        # If quote is null, return error indicating symbol not valid
        if not quote:
            return apology("invalid symbol")

        # Otherwise redirect to quote page with data
        else:
            return render_template("quote.html", company=quote['name'], price=quote['price'], symbol=quote['symbol'])

    # If user navigated to page, render the form page
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # If user submitted form, verify forma args and render error or data for submitted args
    if request.method == "POST":
        # Extract form args into variables
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirmation")

        # Return error if form submitted with missing fields
        if not username or not password or not confirm_password:
            return apology("missing field(s)")

        # Return error if username already in username already registered
        username_taken = len(db.execute(f"SELECT username FROM users WHERE username = '{username}'")) > 0
        if (username_taken):
            return apology("username taken")

        # Return error if passwords do not match
        if password != confirm_password:
            return apology("passwords do not match")

        # Checking if username is valid&available now handled within check(), from html, using ajax
        # So move directly to hasing user password
        hashed_password = generate_password_hash(password)

        # And insert new user into users table in finance db
        db.execute(f"INSERT INTO users(username, hash) VALUES('{username}', '{hashed_password}')")

        # Then redirect user back to index page (displaying user portfolio defaulted to 10K starting balance)
        return redirect("/")

    # If user has directly navigated to page, display form fields
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    # Whether POST or GET, extract symbols of stocks in current user's current portfolio
    user_id = session["user_id"]                                                        # Extract current user id
    data = db.execute(f"SELECT symbol FROM portfolios WHERE user_id = {user_id}")       # Query data of current user
    symbols = [item['symbol'] for item in data]                                         # Compile symbols of stocks in portfolio

    # If user submitted form, process submitted args
    if request.method == "POST":

        # Extract additional useful data into variables
        symbol = request.form.get("symbol")                                             # Extract stock symbol for sale
        shares_to_sell = int(request.form.get("shares"))                                # Extract number of shares for sale

        # Return error if either argument not supplied on submission
        if not symbol or not shares_to_sell:
            return apology("incomplete fields")

        # Return error if number shares of stock in current user portfolio is greater than the number of shares intended for sale
        shares_owned = db.execute(f"SELECT shares FROM portfolios WHERE user_id = {user_id} and symbol = '{symbol}'")[0]['shares']
        if shares_owned < shares_to_sell:
            return apology("too many shares")

        # Otherwise store the stock info into object variable
        stock = lookup(symbol)
        name = stock['name']                                    # From which, extract stock name
        price_per_share = stock['price']                        # ...and extract stock name
        earnings_on_sale = price_per_share * shares_to_sell     # ...and calculate earnings on sale

        # Update/log transaction and hold on to its ID returned after db.execute()
        transaction_id = db.execute(
            f"INSERT INTO transactions (symbol, name, price, count, buy_or_sell, user_id) VALUES ('{symbol}', '{name}', {price_per_share}, {shares_to_sell * -1}, 's', {user_id})")

        # Update shares in portfolios
        db.execute(
            f"UPDATE portfolios SET shares = shares - {shares_to_sell}, transaction_id = {transaction_id}, paid_total = paid_total - {earnings_on_sale} WHERE user_id = {user_id} and symbol = '{symbol}'")

        # Update cash
        db.execute(f"UPDATE users SET cash = cash + {earnings_on_sale} WHERE id = '{user_id}'")

        # Flask success message
        flash("Sold!")

        return redirect("/")

    # Else if user navigated to form, display form fields
    else:
        return render_template("sell.html", symbols=symbols)


@app.route("/withdraw_funds", methods=["GET", "POST"])
@login_required
def withdraw_funds():
    """Withdraw funds from account."""

    # If user submitted form, verify form args and render error or data for submitted args
    if request.method == "POST":
        user_id = session["user_id"]

        # Query for current_balance, db.execute() returns format, [{'cash': 5452.37}]
        current_balance = db.execute(f"SELECT cash FROM users where id = {user_id}")[0]['cash']
        withdraw_amount = float(request.form.get("withdraw_amount"))

        if not withdraw_amount:                 # Return error if input empty
            return apology("missing amount")

        if withdraw_amount > current_balance:   # Return error if remaining cash less than withdraw amount
            return apology("maximum withdraw amount is " + current_balance)

        # Update cash
        db.execute(f"UPDATE users SET cash = cash - {withdraw_amount} WHERE id = '{user_id}'")

        # Log transaction with -1 count, and type to "w" for withdraw action
        # TODO: Update transactions.buy_or_sell to transactions.type
        transaction_id = db.execute(
            f"INSERT INTO transactions (symbol, name, price, count, buy_or_sell, user_id) VALUES ('CASH', 'CASH', {withdraw_amount}, {-1}, 'w', {user_id})")

        return redirect("/")                    # Finally return user to index/portfolio page

    # If user navigated to page, render the withdraw funds page
    else:
        return render_template("withdraw_funds.html")


@app.route("/add_funds", methods=["GET", "POST"])
@login_required
def add_funds():
    """Add funds to account."""

    # If user submitted form, verify form args and render error or data for submitted args
    if request.method == "POST":
        user_id = session["user_id"]

        # Get the add amount from form
        add_amount = float(request.form.get("add_amount"))

        if not add_amount:                 # Return error if input empty
            return apology("missing amount")

        # Update cash
        db.execute(f"UPDATE users SET cash = cash + {add_amount} WHERE id = '{user_id}'")

        # Log transaction with +1 count, and type to "a" for add action
        # TODO: Update transactions.buy_or_sell to transactions.type
        transaction_id = db.execute(
            f"INSERT INTO transactions (symbol, name, price, count, buy_or_sell, user_id) VALUES ('CASH', 'CASH', {add_amount}, {1}, 'a', {user_id})")

        return redirect("/")                    # Finally return user to index/portfolio page

    # If user navigated to page, render the withdraw funds page
    else:
        return render_template("add_funds.html")


@app.route("/change_username", methods=["GET", "POST"])
@login_required
def change_username():
    """Change username"""

    # If POST, check and update username
    if request.method == "POST":

        # Get the current user's id from session
        user_id = session["user_id"]

        # Get data for current user from backend
        user_entry = db.execute(f"SELECT * from users WHERE id = {user_id}")[0]

        # Get the current and new usernames
        current_username = user_entry["username"]
        new_username = request.form.get("username")

        # Check if new username is available
        new_username_available = len(db.execute(f"SELECT id FROM users WHERE username = '{new_username}'")) == 0

        # Validate password once more before updating in backend
        password_verified = check_password_hash(user_entry["hash"], request.form.get("password"))
        print_exaggerated(password_verified, "Check if passwords match: ")

        if not new_username_available:
            flash("Username already taken")
            return redirect(url_for("change_username"))

        if not password_verified:
            flash("Password invalid")
            return redirect(url_for("change_username"))

        # If new username available and password verified, then upate in backend, and flash success message
        if new_username_available and password_verified:
            db.execute(f"UPDATE users SET username = '{new_username}' WHERE id = {user_id}")
            flash("Username updated successfully!")

        return redirect("/")

    # If GET, navigate user to change_username page
    else:
        return render_template("change_username.html")


@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    """Change password"""

    # If POST, check and update username
    if request.method == "POST":

        # Get the current user's id from session
        user_id = session["user_id"]

        # Get data for current user from backend
        user_entry = db.execute(f"SELECT * from users WHERE id = {user_id}")[0]

        # Check that user inputs current password correctly
        password_hash_in_db = user_entry["hash"]
        password_hashed_from_form = generate_password_hash(request.form.get("password_old"))
        if password_hash_in_db != password_hashed_from_form:
            flash("Failed to validate current password")
            return redirect(url_for("change_password"))

        # Check that new password is different from current password, via their hashes
        new_password_hashed_from_form = generate_password_hash(request.form.get("password_new"))
        if password_hashed_from_form == new_password_hashed_from_form:
            flash("New password cannot be same as the old password")
            return redirect(url_for("change_password"))

        # Otherwise print something else for testing
        flash("Looks good")
        return redirect(url_for("change_password"))


    # If GET, navigate user to change_password page
    else:
        return render_template("change_password.html")


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
