# -*- coding: utf-8 -*-
"""
    manage
    ~~~~~~

    Manager module
"""

import os
import flask
from flask.ext.script import Manager
from adsws.accounts.manage import accounts_manager

manager = Manager(flask.Flask('manager'))

manager.add_command("accounts", accounts_manager)

@manager.command
def generate_secret_key():
    """
    Generate a random string suitable for using a the SECRET_KEY value
    """
    key = "'{0}{1}'".format(os.urandom(15), os.urandom(15))
    print "\nSECRET_KEY = '{0}'\n".format(key.encode('hex'))


@manager.command
def profile(length=25, profile_dir=None):
    """Start the application under the code profiler."""
    from wsgi import application
    from werkzeug.contrib.profiler import ProfilerMiddleware
    application.app.wsgi_app = ProfilerMiddleware(application.app.wsgi_app, restrictions=[length],
                                      profile_dir=profile_dir)
    application.app.run()


if __name__ == "__main__":
    manager.run()