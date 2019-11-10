### C$50 Finance tl;dr 
https://docs.cs50.net/2019/x/psets/8/finance/finance.html

#### Setup 
```sh
### Modules to import (Incomplete)
$ pip install cs50
$ pip install flask
$ pip install flask-session
$ pip install sqlite

### Steps to run application
$ cd finance
$ export FLASK_APP=application.py
$ export FLASK_DEBUG=1
$ export API_KEY=<your key> 
```

### TODOS
- itsdangerous import error with 'want_bytes', Git Issues [here](https://github.com/fengsp/flask-session/issues/89) and [here](https://github.com/infobyte/faraday/issues/299)
    - > itsdangerous 1.1.0 was just released and contains a fix for this. Flask-Session should still be fixed so it doesn't rely on this, but it won't fail for now. You can unpin the requirement, or at least pin to itsdangerous~=1.1.0 instead.

----

#### References:

- Use regex to verify password [StackOverflow](https://stackoverflow.com/a/2990682/4443518)
```sh
import re
password = raw_input("Enter string to test: ")
if re.match(r'[A-Za-z0-9@#$%^&+=]{8,}', password):
    # match
else:
    # no match
```



