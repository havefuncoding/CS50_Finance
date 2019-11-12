import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""

    # Contact API
    try:
        api_key = os.environ.get("API_KEY")
        response = requests.get(f"https://cloud-sse.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key}")
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        quote = response.json()
        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"]
        }
    except (KeyError, TypeError, ValueError):
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"


###########################  Additional Helpers ###################################

def password_works(password):
    """Password should comprise 8-64 characters inclusive, with
    at least 1 of each: lowercase, uppercase, number, special character"""

    if len(password) < 8 or len(password) > 64:
        return False

    contains_lowercase = False
    contains_uppercase = False
    contains_number = False
    contains_special = False

    for char in password:
        ascii_position = ord(char)
        # 32   is ' '   to   64   is '@'
        # 91   is '['   to   96   is '`'
        # 123  is '{'   to   126  is '~'
        if ascii_position < 32 or ascii_position > 126:
            return False

        contains_lowercase = True if char.islower() else contains_lowercase
        contains_uppercase = True if char.isupper() else contains_uppercase
        contains_number = True if char.isdigit() else contains_number

        if ((ascii_position >= 32 and ascii_position <= 64) or
            (ascii_position >= 91 and ascii_position <= 96) or
            (ascii_position >= 123 and ascii_position <= 126)):
            contains_special = True

    return contains_lowercase and contains_uppercase and contains_number and contains_special
