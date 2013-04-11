import datetime

import pyotp
import qrcode


class TotpAuth:
    def __init__(self, secret=None):
        if secret is None:
            secret = pyotp.random_base32()
        self.secret = secret
        self.totp = pyotp.TOTP(secret)

    def generate_token(self):
        return self.totp.now()

    def valid(self, token):
        token = int(token)
        now = datetime.datetime.now()
        time30secsago = now + datetime.timedelta(seconds=-30)
        try:
            valid_now = self.totp.verify(token)
            valid_past = self.totp.verify(token, for_time=time30secsago)
            return valid_now or valid_past
        except:
            return False

    def qrcode(self, username):
        uri = self.totp.provisioning_uri(username)
        return qrcode.make(uri)
