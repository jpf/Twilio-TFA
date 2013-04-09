import sys
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest
from twilio import TwilioRestException
from mock import MagicMock
from mock import ANY
import mongomock
import app as flask_app
from totp_auth import TotpAuth


class TestFlaskApp(unittest.TestCase):

    def setUp(self):
        users = [{'uid': "user.app_no.sms_no",
                  'password_hash': (
                      "$2a$12$a7rvlb1mKlMT4xQp7qW9p.W"
                      "UkKm3gluuUor8/rvUu3BcB7xWoxr1a")
                  },
                 {'uid': "user.app_no.sms_yes",
                  'phone_number': "(415) 555-1212",
                  'totp_secret': "NVHWYJ4OV75YW3WC",
                  'totp_enabled_via_sms': True,
                  'password_hash': (
                      "$2a$12$X0wec23GmmicEe/eYNOM/um"
                      "KJoTivALHjhg5q/qJ9LtkV4mtri9Au")
                  },
                 {'uid': "user.app_yes.sms_no",
                  'totp_secret': "VRZQO34R4LHUH634",
                  'totp_enabled_via_app': True,
                  'password_hash': (
                      "$2a$12$1ocOVI64R1L4vBJTLaYPjOg"
                      "8PYqXzLoFPVf.vh7ZJ8QCv7U7.DIP6")
                  },
                 {'uid': "user.app_yes.sms_yes",
                  'totp_secret': "BOXB6K2SJCR5L7CR",
                  'totp_enabled_via_app': True,
                  'phone_number': "(415) 555-1213",
                  'totp_enabled_via_sms': True,
                  'password_hash': (
                      "$2a$12$hW5/YxlP9RzbUN0k05.nsOt"
                      "gDslFYjf34U2PH7JG6OeJacIFjx.e.")
                  },
                 {'uid': "user2",
                  'totp_secret': "R6LPJTVQXJFRYNDJ",
                  'password_hash': (
                      "$2a$12$ISrqiMAN9JIo7zA/qbPVIuP"
                      "rQN/ebVCKamM/HFth9Ka63PmyZ2S8q")
                  },
                 {'uid': "user",
                  'totp_secret': "R6LPJTVQXJFRYNDJ",
                  'password_hash': (
                      "$2a$12$J2dTN4wMH7nbVDgkYq/d8uT"
                      "siTw3DQHNF5Py98Mf27PJvnqkE94iK")
                  }]

        connection = mongomock.Connection()
        db = connection['tfa'].users
        self.db = db
        for user in users:
            db.insert(user)
        test_config = {'secret_key': 'testing',
                       'twilio_from_number': '+14155551212'}
        flask_app.konf.use_dict(test_config)
        flask_app.connection = connection

        flask_app.twilio = MagicMock(name='mock_twilio')
        create_sms_mock = MagicMock(name='mock_twilio.sms.messages.create')

        def side_effect(*args, **kwargs):
            """Simulate errors on bad inputs"""
            for num in ['Fake', '+14155551212']:
                if kwargs['to'] == num:
                    raise TwilioRestException

        create_sms_mock.side_effect = side_effect
        flask_app.twilio.sms.messages.create = create_sms_mock
        self.create_sms_mock = create_sms_mock

        self.app = flask_app.app.test_client()

    def tearDown(self):
        pass

    def test_has_default_route(self):
        path = "/"
        rv = self.app.get(path)
        self.assertEquals("200 OK", rv.status)
        self.assertIn("Don't have an account?", rv.data)

    def test_main_page(self):
        path = "/"
        rv = self.app.get(path)
        self.assertEquals("200 OK", rv.status)
        # has "log in" link
        self.assertIn("Log in", rv.data)
        # has "sign up " link
        self.assertIn("Sign up", rv.data)
        # has text explaining example
        text = ("This is a demonstration of how "
                "to add TOTP based Two Factor Authentication "
                "to an existing application.")
        self.assertIn(text, rv.data)
        # has link to GitHub repo
        # self.assertEquals('href="https://github.com/"', rv.data)

    def login(self, username, password):
        return self.app.post('/', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def sign_up(self, username, password1, password2):
        return self.app.post('/sign-up', data=dict(
            username=username,
            password1=password1,
            password2=password2
        ), follow_redirects=True)

    def logout(self):
        return self.app.get('/logout', follow_redirects=True)

    def test_sign_in(self):
        # Form gives error if username or password is bad
        rv = self.login('user', 'badpassword')
        self.assertIn("Incorrect Username or Password.", rv.data)
        rv = self.login('baduser', 'password')
        self.assertIn("Incorrect Username or Password.", rv.data)
        rv = self.login('baduser', 'badpassword')
        self.assertIn("Incorrect Username or Password.", rv.data)
        rv = self.login('user', 'password')
        self.assertIn("You are logged in", rv.data)
        self.logout()

    def test_one_sign_in_with_tfa(self):
        """If TFA enabled, user redirected to a "Verify TFA" page"""
        rv = self.login('user.app_no.sms_yes', 'password')
        self.assertIn("Account Verification", rv.data)
        self.logout()

    def test_sign_up(self):
        """Person enters username and password on signup page"""
        # Error prompt if passwords don't match
        rv = self.sign_up('newuser', 'password', 'passwordd')
        self.assertIn("Passwords do not match", rv.data)
        # Success
        rv = self.sign_up('newuser', 'password', 'password')
        self.assertIn("You are logged in", rv.data)
        # Error prompt if username already exists
        rv = self.sign_up('user', 'password', 'password')
        self.assertIn("That username is already in use", rv.data)

    def test_sign_up_case_insensitive(self):
        rv = self.sign_up('CaseInsensitive', 'password', 'password')
        self.assertIn("You are logged in", rv.data)
        # Error prompt if username already exists
        self.logout()
        rv = self.login('caseinsensitive', 'password')
        self.assertIn("You are logged in", rv.data)

    def test_logged_in_no_tfa(self):
        """User presented with page 'you are logged in!'"""
        # Page has "You are logged in!"
        rv = self.login('user', 'password')
        self.assertIn("You are logged in", rv.data)

        # Page has "Enable Two Factor Authentication" if TFA isn't enabled
        self.assertIn("Enable app based authentication", rv.data)
        # Page has "Enable SMS Authentication" if SMS auth isn't enabled
        self.assertIn("Enable SMS based authentication", rv.data)
        # Page has "log out" link
        self.assertIn("Log out", rv.data)

    def test_sign_in_tfa_permutations(self):
        # app: no
        # sms: no
        rv = self.login('user.app_no.sms_no', 'password')
        self.assertIn("You are logged in", rv.data)
        self.logout()

        # app: no
        # sms: yes
        rv = self.login('user.app_no.sms_yes', 'password')
        self.assertNotIn("You are logged in", rv.data)
        self.assertIn("Account Verification", rv.data)
        self.assertNotIn("Google Authenticator", rv.data)
        self.assertIn("SMS that was just sent to you", rv.data)
        self.assertIn("Enter your verification code here", rv.data)
        self.logout()

        # app: yes
        # sms: no
        rv = self.login('user.app_yes.sms_no', 'password')
        self.assertNotIn("You are logged in", rv.data)
        self.assertIn("Account Verification", rv.data)
        self.assertIn("Google Authenticator", rv.data)
        self.assertNotIn("SMS that was just sent to you", rv.data)
        self.assertIn("Enter your verification code here", rv.data)
        self.logout()

        # app: yes
        # sms: yes
        rv = self.login('user.app_yes.sms_yes', 'password')
        self.assertNotIn("You are logged in", rv.data)
        self.assertIn("Account Verification", rv.data)
        self.assertIn("Google Authenticator", rv.data)
        self.assertIn("SMS that was just sent to you", rv.data)
        self.assertIn("Enter your verification code here", rv.data)
        self.logout()

    # def test_logged_in_permutations(self):
    #     # app: no
    #     # SMS: no
    #     rv = self.login('user.tfa_no.sms_no', 'password')
    #     self.assertIn("You are logged in", rv.data)
    #     self.assertIn("Enable Two Factor Authentication", rv.data)
    #     self.assertIn("Enable SMS Authentication", rv.data)
    #     self.logout()
    #
    #     # app: no
    #     # SMS: yes
    #     rv = self.login('user.tfa_no.sms_yes', 'password')
    #     self.assertIn("You are logged in", rv.data)
    #     self.assertIn("Enable Two Factor Authentication", rv.data)
    #     self.assertIn("Disable SMS Authentication", rv.data)
    #     self.logout()
    #
    #     # app: yes
    #     # SMS: no
    #     rv = self.login('user.tfa_yes.sms_no', 'password')
    #     self.assertIn("You are logged in", rv.data)
    #     self.assertIn("Disable Two Factor Authentication", rv.data)
    #     self.assertIn("Enable SMS Authentication", rv.data)
    #     self.logout()
    #
    #     # app: yes
    #     # SMS: yes
    #     rv = self.login('user.tfa_yes.sms_yes', 'password')
    #     self.assertIn("You are logged in", rv.data)
    #     self.assertIn("Disable Two Factor Authentication", rv.data)
    #     self.assertIn("Disable SMS Authentication", rv.data)
    #     self.logout()

    def test_enable_tfa_via_app(self):
        self.login('user', 'password')
        path = "/enable-tfa-via-app"
        rv = self.app.get(path)
        self.assertIn("200 OK", rv.status)

        self.assertIn("Install Google Authenticator", rv.data)
        self.assertIn("Open the Google Authenticator app", rv.data)
        self.assertIn('Tap menu, then tap "Set up account"', rv.data)
        self.assertIn('then tap "Scan a barcode"', rv.data)
        self.assertIn("scan the barcode below", rv.data)
        text = ("Once you have scanned the barcode, "
                "enter the 6-digit code below")
        self.assertIn(text, rv.data)
        self.assertIn("Submit", rv.data)
        self.assertIn("Cancel", rv.data)

    def make_token(self, username):
        user = self.db.find_one({'uid': username})
        auth = TotpAuth(user['totp_secret'])
        return auth.generate_token()

    def test_enable_tfa_via_app_setup(self):
        self.login('user', 'password')
        token = self.make_token('user')
        rv = self.app.post('/enable-tfa-via-app', data=dict(
            token=token
        ), follow_redirects=True)
        self.assertIn('You are set up', rv.data)
        self.assertIn('via Google Authenticator', rv.data)

        self.login('user2', 'password')
        bad_token = str(int(token) + 1)
        rv = self.app.post('/enable-tfa-via-app', data=dict(
            token=bad_token
        ), follow_redirects=True)
        self.assertIn('There was an error verifying your token', rv.data)

    def enable_sms_auth(self, phone_number):
        return self.app.post('/enable-tfa-via-sms', data=dict(
            phone_number=phone_number
        ), follow_redirects=True)

    def test_enable_sms_auth(self):
        self.login('user', 'password')
        rv = self.enable_sms_auth('+14155551212')
        self.assertIn("200 OK", rv.status)
        self.assertIn("Enter your mobile phone number", rv.data)
        self.assertIn("A 6-digit verification code will be sent", rv.data)
        self.assertIn("Enter your verification code", rv.data)
        self.assertIn("Submit and verify", rv.data)
        self.assertIn("Cancel", rv.data)

    def test_enable_sms_auth_validation(self):
        self.login('user', 'password')

        # submit a bad phone number to the form
        for num in ['Fake', '+14155551212']:
            # make sure we get an error
            rv = self.enable_sms_auth(num)
            self.assertIn('There was an error sending', rv.data)

        # submit a good phone number to the form
        num = '+14158675309'
        self.enable_sms_auth(num)
        # make sure the SMS method mock was called
        self.create_sms_mock.assert_called_with(to=num,
                                                from_='+14155551212',
                                                body=ANY)

        # take the contents of the call to the SMS mock
        called_with = self.create_sms_mock.call_args
        body = called_with[1]['body']
        # 'Use this code to log in: 123456'
        token = body.split(': ')[1]
        # submit the contents in the form
        rv = self.app.post('/enable-tfa-via-sms', data=dict(
            token=token
        ), follow_redirects=True)
        # test for success
        self.assertIn('You are set up', rv.data)
        self.assertIn('via Twilio SMS', rv.data)

        self.logout()
        self.login('user2', 'password')
        self.enable_sms_auth(num)

        # send back a bad number (old token + 1)
        bad_token = str(int(token) + 1)
        rv = self.app.post('/enable-tfa-via-sms', data=dict(
            token=bad_token
        ), follow_redirects=True)
        self.assertIn('There was an error verifying your token', rv.data)
