import os

import bcrypt
from twilio.rest import TwilioRestClient
from flask.ext.login import LoginManager
from flask import Flask
from flask import request
from flask import redirect
from flask import url_for
from flask import render_template
from flask.ext.login import login_user
from flask.ext.login import logout_user
from flask.ext.login import current_user
from flask.ext.login import login_required
from pymongo import Connection

from konfig import Konfig

app = Flask(__name__)
konf = Konfig()
app.secret_key = konf.secret_key

connection = Connection(konf.mongo_url)

login_manager = LoginManager()
login_manager.setup_app(app)

twilio = TwilioRestClient()


@login_manager.user_loader
def load_user(user_id):
    return User(user_id)


class User:
    def __init__(self, user_id):
        self.id = user_id.lower()
        self.db = connection.tfa.users
        self.account = self.db.find_one({'uid': self.id})

    def create(self):
        self.db.insert({'uid': self.id})
        self.account = self.db.find_one({'uid': self.id})

    def save(self):
        self.db.save(self.account)

    def password_valid(self, pwd):
        pwd_hash = self.account['password_hash']
        return bcrypt.hashpw(pwd, pwd_hash) == pwd_hash

    # The methods below are required by flask-login
    def is_authenticated(self):
        """Always return true - we don't do any account verification"""
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id


@app.route("/", methods=['GET', 'POST'])
def main_page():
    opts = {}
    if request.method == 'GET':
        return render_template('main_page.html', opts=opts)
    user = User(request.form['username'])
    if not user.account or not user.password_valid(request.form['password']):
        opts['invalid_username_or_password'] = True
        return render_template('main_page.html', opts=opts)
    login_user(user)
    return redirect(url_for('user'))


@app.route("/sign-up", methods=['GET', 'POST'])
def sign_up():
    opts = {}
    if request.method == 'GET':
        return render_template('sign_up.html', opts=opts)
    user = User(request.form['username'])
    if user.account:
        opts['username_exists'] = True
        return render_template('sign_up.html', opts=opts)
    if request.form['password1'] != request.form['password2']:
        opts['passwords_do_not_match'] = True
        return render_template('sign_up.html', opts=opts)
    user.create()
    pwd_hash = bcrypt.hashpw(request.form['password1'], bcrypt.gensalt())
    user.account['password_hash'] = pwd_hash
    user.save()
    login_user(user)
    return redirect(url_for('user'))


@app.route("/user")
@login_required
def user():
    opts = {'user': current_user,
            'logged_in': True}
    return render_template('user.html', opts=opts)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('main_page'))

if __name__ == "__main__":
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    if port == 5000:
        app.debug = True
    app.run(host='0.0.0.0', port=port)
