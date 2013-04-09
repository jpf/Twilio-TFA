import os
import StringIO
import urlparse

import bcrypt
from twilio.rest import TwilioRestClient
from flask.ext.login import LoginManager
from flask import Flask
from flask import Response
from flask import request
from flask import redirect
from flask import url_for
from flask import render_template
from flask import session
from flask.ext.login import login_user
from flask.ext.login import logout_user
from flask.ext.login import current_user
from flask.ext.login import login_required
from pymongo import Connection

from konfig import Konfig
from totp_auth import TotpAuth

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
        if self.account and 'totp_secret' in self.account:
            self.totp = TotpAuth(self.account['totp_secret'])

    def create(self):
        auth = TotpAuth()
        self.db.insert({'uid': self.id,
                        'totp_secret': auth.secret})
        self.account = self.db.find_one({'uid': self.id})

    def save(self):
        self.db.save(self.account)

    def password_valid(self, pwd):
        pwd_hash = self.account['password_hash']
        return bcrypt.hashpw(pwd, pwd_hash) == pwd_hash

    def send_sms(self, ok_to_send=False):
        if 'totp_enabled_via_sms' in self.account:
            ok_to_send = True
        if ok_to_send:
            token = self.totp.generate_token()
            msg = "Use this code to log in: %s" % token
            try:
                phone_number = self.account['phone_number']
                rv = twilio.sms.messages.create(to=phone_number,
                                                from_=konf.twilio_from_number,
                                                body=msg)
            except:
                return False
            if rv:
                return rv.status != 'failed'
        return False

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
    totp_enabled = False
    for type in ['totp_enabled_via_app', 'totp_enabled_via_sms']:
        if type in user.account:
            totp_enabled = user.account[type]
    if totp_enabled:
        session['uid'] = user.get_id()
        session['stage'] = 'password-validated'
        return redirect(url_for('verify_tfa'))
    else:
        login_user(user)
        return redirect(url_for('user'))


@app.route("/sign-up", methods=['GET', 'POST'])
def sign_up():
    # FIXME: Test for the 'ideal case', render_template otherwise
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


@app.route("/verify-tfa", methods=['GET', 'POST'])
def verify_tfa():
    user = User(session['uid'])
    opts = {'user': user}
    if request.method == 'GET':
        opts['sms_sent'] = user.send_sms()
        return render_template('verify_tfa.html', opts=opts)
    if not session['uid']:
        opts['error-no-username'] = True
        return render_template('verify_tfa.html', opts=opts)
    if session['stage'] != 'password-validated':
        opts['error-unverified-password'] = True
        return render_template('verify_tfa.html', opts=opts)
    if user.totp.valid(request.form['token']):
        login_user(user)
        session['stage'] = 'logged-in'
        return redirect(url_for('user'))
    else:
        opts['error-invalid-token'] = True
        return render_template('verify_tfa.html', opts=opts)


@app.route("/enable-tfa-via-app", methods=['GET', 'POST'])
@login_required
def enable_tfa_via_app():
    opts = {'user': current_user}
    if request.method == 'GET':
        return render_template('enable_tfa_via_app.html', opts=opts)
    token = request.form['token']
    if token and current_user.totp.valid(token):
        current_user.account['totp_enabled_via_app'] = True
        current_user.save()
        return render_template('enable_tfa_via_app.html', opts=opts)
    else:
        opts['token_error'] = True
        return render_template('enable_tfa_via_app.html', opts=opts)


@app.route('/auth-qr-code.png')
@login_required
def auth_qr_code():
    """generate a QR code with the users TOTP secret

    We do this to reduce the risk of leaking
    the secret over the wire in plaintext"""
    #FIXME: This logic should really apply site-wide
    domain = urlparse.urlparse(request.url).netloc
    if not domain:
        domain = 'example.com'
    username = "%s@%s" % (current_user.id, domain)
    qrcode = current_user.totp.qrcode(username)
    stream = StringIO.StringIO()
    qrcode.save(stream)
    image = stream.getvalue()
    return Response(image, mimetype='image/png')


@app.route("/enable-tfa-via-sms", methods=['GET', 'POST'])
@login_required
def enable_tfa_via_sms():
    opts = {'user': current_user}
    if request.method == 'GET':
        return render_template('enable_tfa_via_sms.html', opts=opts)
    if 'phone_number' in request.form and request.form['phone_number']:
        current_user.account['phone_number'] = request.form['phone_number']
        current_user.save()
        opts['sms_sent'] = current_user.send_sms(ok_to_send=True)
        opts['phone_number_updated'] = True
        return render_template('enable_tfa_via_sms.html', opts=opts)
    token = request.form['token']
    if token and current_user.totp.valid(token):
        current_user.account['totp_enabled_via_sms'] = True
        current_user.save()
        return render_template('enable_tfa_via_sms.html', opts=opts)
    else:
        opts['token_error'] = True
        return render_template('enable_tfa_via_sms.html', opts=opts)


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
