"""
Management commands for account related activities (including oauth)
"""

import datetime

from adsws.modules.oauth2server.models import OAuthToken, OAuthClient
from adsws.core import db
from adsws.accounts import create_app

from flask.ext.script import Manager

accounts_manager = Manager(create_app())
accounts_manager.__doc__ = __doc__  # Overwrite default docstring

@accounts_manager.command
def cleanup_tokens(app_override=None):
    """
    Cleans expired oauth2tokens from the database defined in
    app.config['SQLALCHEMY_DATABASE_URI']
    :param app_override: flask.app instance to use instead of manager.app
    :return: None
    """

    if app_override is not None:
        app = app_override
    else:
        app = accounts_manager.app

    with app.app_context():
        tokens = db.session.query(OAuthToken).filter(
            OAuthToken.expires <= datetime.datetime.now()
        ).all()
        deletions = 0

        for token in tokens:
            db.session.delete(token)
            deletions += 1
        try:
            db.session.commit()
        except Exception, e:
            db.session.rollback()
            app.logger.error("Could not cleanup expired oauth2tokens. "
                             "Database error; rolled back: {0}".format(e))
        app.logger.info("Deleted {0} expired oauth2tokens".format(deletions))


@accounts_manager.command
def cleanup_clients(app_override=None, timedelta="days=31"):
    """
    Cleans expired oauth2clients that are older than a specified date in the
    database defined in app.config['SQLALCHEMY_DATABASE_URI']
    :param app_override: flask.app instance to use instead of manager.app
    :param timedelta: String representing the datetime.timedelta against which
            to compare client's last_activity ["days=31"].
    :type timedelta: basestring
    :return: None
    """

    if app_override is not None:
        app = app_override
    else:
        app = accounts_manager.app

    td = {timedelta.split('=')[0]: float(timedelta.split('=')[1])}
    td = datetime.timedelta(**td)

    with app.app_context():
        clients = db.session.query(OAuthClient).filter(
            OAuthClient.last_activity <= datetime.datetime.now()-td
        ).all()
        deletions = 0

        for client in clients:
            db.session.delete(client)
            deletions += 1
        try:
            db.session.commit()
        except Exception, e:
            db.session.rollback()
            app.logger.error("Could not cleanup expired oauth2clients. "
                             "Database error; rolled back: {0}".format(e))
        app.logger.info("Deleted {0} oauth2clients whose last_activity was "
                        "at least {1} old".format(deletions, timedelta))


