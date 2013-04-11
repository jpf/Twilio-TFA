import sys
import StringIO
import datetime
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

import Image

from totp_auth import TotpAuth


class TestTOTPAuth(unittest.TestCase):

    def setUp(self):
        self.test_token = 'AAAAAAAAAAAAAAAA'

    def tearDown(self):
        pass

    def test_base_case(self):
        auth = TotpAuth()

        self.assertEquals(16, len(auth.secret))

        token = auth.generate_token()
        self.assertEquals(6, len(str(token)))

        rv = auth.valid(token)
        self.assertTrue(rv)

    def test_qrcode_generation(self):
        auth = TotpAuth(self.test_token)
        expected_image = Image.open('tests/assets/test_example_com.png')
        expected_stream = StringIO.StringIO()
        expected_image.save(expected_stream, format='PNG')
        expected = expected_stream.getvalue()

        actual_image = auth.qrcode('test@example.com')
        actual_stream = StringIO.StringIO()
        actual_image.save(actual_stream)
        actual = actual_stream.getvalue()

        self.assertEqual(expected, actual)

    # def test_validates_known_token(self):
    #     """
    #     Validates a token from a known, fixed, time.
    #     """
    #     known_time = 872835282
    #     expected_token = 139539
    #     pass

    def test_validates_token_for_right_now(self):
        auth = TotpAuth(self.test_token)
        token = auth.totp.now()
        self.assertTrue(auth.valid(token))

    def test_validates_token_for_30_seconds_ago(self):
        auth = TotpAuth(self.test_token)
        now = datetime.datetime.now()
        past_unixtime = int(now.strftime('%s')) - 30
        past = datetime.datetime.fromtimestamp(past_unixtime)
        token = auth.totp.at(past)
        self.assertTrue(auth.valid(token))

    def test_invalidates_token_for_60_seconds_ago(self):
        auth = TotpAuth(self.test_token)
        now = datetime.datetime.now()
        past_unixtime = int(now.strftime('%s')) - 60
        past = datetime.datetime.fromtimestamp(past_unixtime)
        token = auth.totp.at(past)
        self.assertFalse(auth.valid(token))
