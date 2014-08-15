# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function

import os
import logging

from flask import url_for

from adsws.testsuite import FlaskAppTestCase, make_test_suite, \
    run_test_suite
from adsws.core import db

from mock import MagicMock
from flask_oauthlib.client import prepare_request
try:
    from six.moves.urllib.parse import urlparse
except ImportError:
    from urllib.parse import urlparse

from .helpers import create_client

logging.basicConfig(level=logging.DEBUG)

from adsws import api 

class OAuth2ProviderTestCase(FlaskAppTestCase):
    def create_app(self):
        try:
            #app = super(OAuth2ProviderTestCase, self).create_app()
            app = api.create_app()
            app.testing = True
            app.config.update(dict(
                OAUTH2_CACHE_TYPE='simple',
            ))
            client = create_client(app, 'oauth2test')
            client.http_request = MagicMock(
                side_effect=self.patch_request(app)
            )
            return app
        except Exception as e:
            print(e)
            raise

    def patch_request(self, app):
        test_client = app.test_client()

        def make_request(uri, headers=None, data=None, method=None):
            uri, headers, data, method = prepare_request(
                uri, headers, data, method
            )
            if not headers and data is not None:
                headers = {
                    'Content-Type': ' application/x-www-form-urlencoded'
                }

            # test client is a `werkzeug.test.Client`
            parsed = urlparse(uri)
            uri = '%s?%s' % (parsed.path, parsed.query)
            resp = test_client.open(
                uri, headers=headers, data=data, method=method
            )
            # for compatible
            resp.code = resp.status_code
            return resp, resp.data
        return make_request

    def setUp(self):
        super(OAuth2ProviderTestCase, self).setUp()
        # Set environment variable DEBUG to true, to allow testing without
        # SSL in oauthlib.
        if self.app.config.get('SITE_SECURE_URL').startswith('http://'):
            self.os_debug = os.environ.get('OAUTHLIB_INSECURE_TRANSPORT', '')
            os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'

        from ..models import Client
        from adsws.users.models import User

        self.base_url = self.app.config.get('SITE_SECURE_URL')

        # Create needed objects
        u = User(
            email='info@adslabs.org'
        )
        u.password = "tester"

        u2 = User(
            email='abuse@adslabs.org'
        )
        u2.password = "tester2"

        db.session.add(u)
        db.session.add(u2)
        db.session.commit()

        c1 = Client(
            client_id='dev',
            client_secret='dev',
            name='dev',
            description='',
            is_confidential=False,
            user_id=u.id,
            _redirect_uris='%s/oauth2test/authorized' % self.base_url,
            _default_scopes="user"
        )

        c2 = Client(
            client_id='confidential',
            client_secret='confidential',
            name='confidential',
            description='',
            is_confidential=True,
            user_id=u.id,
            _redirect_uris='%s/oauth2test/authorized' % self.base_url,
            _default_scopes="user"
        )

        db.session.add(c1)
        db.session.add(c2)

        db.session.commit()

        self.objects = [u, u2, c1, c2]

        # Create a personal access token as well.
        from ..models import Token
        self.personal_token = Token.create_personal(
            'test-personal', 1, scopes=[], is_internal=True
        )

    def tearDown(self):
        super(OAuth2ProviderTestCase, self).tearDown()
        # Set back any previous value of DEBUG environment variable.
        if self.app.config.get('SITE_SECURE_URL').startswith('http://'):
            os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = self.os_debug
        self.base_url = None

        for o in self.objects:
            db.session.delete(o)
        db.session.commit()

    def parse_redirect(self, location):
        from werkzeug.urls import url_parse, url_decode, url_unparse
        scheme, netloc, script_root, qs, anchor = url_parse(location)
        return (
            url_unparse((scheme, netloc, script_root, '', '')),
            url_decode(qs)
        )

    def test_client_salt(self):
        from ..models import Client

        c = Client(
            name='Test something',
            is_confidential=True,
            user_id=1,
        )

        c.gen_salt()
        assert len(c.client_id) == \
            self.app.config.get('OAUTH2_CLIENT_ID_SALT_LEN')
        assert len(c.client_secret) == \
            self.app.config.get('OAUTH2_CLIENT_SECRET_SALT_LEN')

        db.session.add(c)
        db.session.commit()

    def test_auth_flow(self):
        # Go to login - should redirect to oauth2 server for login an
        # authorization
        r = self.client.get('/oauth2test/test-ping')

        # First login on provider site
        self.login("tester", "tester")

        r = self.client.get('/oauth2test/login')
        self.assertStatus(r, 302)
        next_url, data = self.parse_redirect(r.location)

        # Authorize page
        r = self.client.get(next_url, query_string=data)
        self.assertStatus(r, 200)

        # User confirms request
        data['confirm'] = 'yes'
        data['scope'] = 'user'
        data['state'] = ''

        r = self.client.post(next_url, data=data)
        self.assertStatus(r, 302)
        next_url, data = self.parse_redirect(r.location)
        assert next_url == '%s/oauth2test/authorized' % self.base_url
        assert 'code' in data

        # User is redirected back to client site.
        # - The client view /oauth2test/authorized will in the
        #   background fetch the access token.
        r = self.client.get(next_url, query_string=data)
        self.assertStatus(r, 200)

        # Authentication flow has now been completed, and the access
        # token can be used to access protected resources.
        r = self.client.get('/oauth2test/test-ping')
        self.assert200(r)
        self.assertEqual(r.json, dict(ping='pong'))

        # Authentication flow has now been completed, and the access
        # token can be used to access protected resources.
        r = self.client.get('/oauth2test/test-ping')
        self.assert200(r)
        self.assertEqual(r.json, dict(ping='pong'))

        r = self.client.get('/oauth2test/test-info')
        self.assert200(r)
        assert r.json.get('client') == 'dev'
        assert r.json.get('user') == self.objects[0].id
        assert r.json.get('scopes') == [u'user']

        # Access token doesn't provide access to this URL.
        r = self.client.get('/oauth2test/test-invalid')
        self.assertStatus(r, 403)

        # # Now logout
        r = self.client.get('/oauth2test/logout')
        self.assertStatus(r, 200)
        assert r.data == "logout"

        # And try to access the information again
        r = self.client.get('/oauth2test/test-ping')
        self.assert403(r)

    def test_auth_flow_denied(self):
        # First login on provider site
        self.login("tester", "tester")

        r = self.client.get('/oauth2test/login')
        self.assertStatus(r, 302)
        next_url, data = self.parse_redirect(r.location)

        # Authorize page
        r = self.client.get(next_url, query_string=data)
        self.assertStatus(r, 200)

        # User rejects request
        data['confirm'] = 'no'
        data['scope'] = 'user'
        data['state'] = ''

        r = self.client.post(next_url, data=data)
        self.assertStatus(r, 302)
        next_url, data = self.parse_redirect(r.location)
        assert next_url == '%s/oauth2test/authorized' % self.base_url
        assert data.get('error') == 'access_denied'

        # Returned
        r = self.client.get(next_url, query_string=data)
        self.assert200(r)
        assert r.data == "Access denied: error=access_denied"

    def test_personal_access_token(self):
        r = self.client.get(
            '/oauth/ping',
            query_string="access_token=%s" % self.personal_token.access_token
        )
        self.assert200(r)
        self.assertEqual(r.json, dict(ping='pong'))

        # Access token is not valid for this scope.
        r = self.client.get('/oauth/info')
        self.assertStatus(r, 403)

    def test_settings_index(self):
        # Create a remote account (linked account)
        r = self.client.get(
            url_for('oauth2server_settings.index'),
            base_url=self.app.config.get('SITE_SECURE_URL'),
        )
        self.assertStatus(r, 401)
        self.login("tester", "tester")

        res = self.client.get(
            url_for('oauth2server_settings.index'),
            base_url=self.app.config.get('SITE_SECURE_URL'),
        )
        self.assert200(res)

        res = self.client.get(
            url_for('oauth2server_settings.client_new'),
            base_url=self.app.config.get('SITE_SECURE_URL'),
        )
        self.assert200(res)

        res = self.client.post(
            url_for('oauth2server_settings.client_new'),
            base_url=self.app.config.get('SITE_SECURE_URL'),
            data=dict(
                name='Test',
                description='Test description',
                website='http://invenio-software.org',
            )
        )

        self.assertStatus(res, 302)


TEST_SUITE = make_test_suite(OAuth2ProviderTestCase)


if __name__ == "__main__":
    run_test_suite(TEST_SUITE)
