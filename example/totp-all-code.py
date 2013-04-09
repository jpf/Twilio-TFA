# Based on the pyotp: https://github.com/nathforge/pyotp
import base64
import hashlib
import hmac
import datetime
import time


class OTP(object):
    def __init__(self, secret, digits=6):
        self.secret = secret

    def int_to_bytestring(self, int, padding=8):
        """
        Turns an integer to the OATH specified
        bytestring, which is fed to the HMAC
        along with the secret
        """
        result = []
        while int != 0:
            result.append(chr(int & 0xFF))
            int = int >> 8
        return ''.join(reversed(result)).rjust(padding, '\0')

    def generate_otp(self, input):
        """
        @param [Integer] input the number used seed the HMAC
        Usually either the counter, or the computed integer
        based on the Unix timestamp
        """
        hmac_hash = hmac.new(
            base64.b32decode(self.secret, casefold=True),
            self.int_to_bytestring(input),
            hashlib.sha1,
        ).digest()

        offset = ord(hmac_hash[19]) & 0xf
        code = ((ord(hmac_hash[offset]) & 0x7f) << 24 |
                (ord(hmac_hash[offset + 1]) & 0xff) << 16 |
                (ord(hmac_hash[offset + 2]) & 0xff) << 8 |
                (ord(hmac_hash[offset + 3]) & 0xff))
        # '6' is number of integers in the OTP
        return code % 10 ** 6


class TOTP(OTP):
    def __init__(self, *args, **kwargs):
        """
        @option options [Integer] internval (30) the interval in seconds
            This defaults to 30 which is standard.
        """
        self.interval = kwargs.pop('interval', 30)
        super(TOTP, self).__init__(*args, **kwargs)

    def timecode(self, for_time):
        i = time.mktime(for_time.timetuple())
        return int(i / self.interval)

    def now(self):
        """
        Generate the current time OTP
        @return [Integer] the OTP as an integer
        """
        return self.generate_otp(self.timecode(datetime.datetime.now()))

if __name__ == "__main__":
    secret = "AAAAAAAAAAAAAAAA"
    totp = TOTP(secret)
    print "TOTP token for secret '%s' is: %s" % (secret, totp.now())
