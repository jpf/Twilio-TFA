Basic instructions for running this code.

    $ git clone <the url for this repository>
    $ cd Twilio-TFA
    $ virtualenv venv --distribute
    $ source venv/bin/activate
    $ pip install -r requirements.txt 
    $ mv .env.example .env
    $ $EDITOR .env
    $ foreman start

Then, visit the URL that foreman shows you.

To install in Heroku, do the above, but then run:

    $ heroku create
    $ heroku config:set <run for every line in .env>
    $ heroku open

[![githalytics.com alpha](https://cruel-carlota.pagodabox.com/19586f0a1672bae0394f696672645aec "githalytics.com")](http://githalytics.com/jpf/Twilio-TFA)