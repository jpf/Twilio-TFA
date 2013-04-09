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
        try:
            return self.totp.verify(int(token))
        except:
            return False

    def qrcode(self, username):
        uri = self.totp.provisioning_uri(username)
        return qrcode.make(uri)
