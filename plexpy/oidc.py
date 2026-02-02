# -*- coding: utf-8 -*-

#  This file is part of Tautulli.
#
#  Tautulli is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Tautulli is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Tautulli.  If not, see <http://www.gnu.org/licenses/>.

from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import cherrypy
import jwt
import requests

import plexpy
from plexpy import logger


class OIDCClient(object):
    """Minimal OpenID Connect helper using the Authorization Code flow.

    Notes:
      - We rely on the token endpoint and (optionally) the userinfo endpoint
        and avoid verifying the ID token signature to keep dependencies light.
        TLS to the IdP is required and assumed.
    """

    def __init__(self):
        if not plexpy.CONFIG.OIDC_ISSUER_URL:
            raise cherrypy.HTTPError(500, 'OIDC issuer not configured.')

        self.issuer = plexpy.CONFIG.OIDC_ISSUER_URL.rstrip('/')
        self.client_id = plexpy.CONFIG.OIDC_CLIENT_ID
        self.client_secret = plexpy.CONFIG.OIDC_CLIENT_SECRET
        self.scopes = plexpy.CONFIG.OIDC_SCOPES or 'openid email profile'

        # Discover endpoints
        self._discovery = self._fetch_discovery()
        self.authorization_endpoint = self._discovery.get('authorization_endpoint')
        self.token_endpoint = self._discovery.get('token_endpoint')
        self.userinfo_endpoint = self._discovery.get('userinfo_endpoint')

        if not self.authorization_endpoint or not self.token_endpoint:
            raise cherrypy.HTTPError(500, 'OIDC discovery missing endpoints.')

    def _fetch_discovery(self):
        url = self.issuer + '/.well-known/openid-configuration'
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error('OIDC :: Failed to fetch discovery: %s', e)
            raise cherrypy.HTTPError(500, 'Failed to fetch OIDC discovery.')

    @staticmethod
    def _default_redirect_uri():
        # Prefer configured explicit redirect, else compute from current request
        if plexpy.CONFIG.OIDC_REDIRECT_URI:
            return plexpy.CONFIG.OIDC_REDIRECT_URI
        base = cherrypy.request.base.rstrip('/')
        root = plexpy.HTTP_ROOT
        if not root.startswith('/'):
            root = '/' + root
        return base + root + 'auth/oidc/callback'

    def build_authorization_url(self, state, nonce, redirect_uri=None, extra_params=None):
        redirect_uri = redirect_uri or self._default_redirect_uri()
        params = {
            'client_id': self.client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': self.scopes,
            'state': state,
            'nonce': nonce,
        }
        if extra_params:
            params.update(extra_params)
        return self.authorization_endpoint + '?' + urlencode(params)

    def exchange_code_for_tokens(self, code, redirect_uri=None):
        redirect_uri = redirect_uri or self._default_redirect_uri()
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': self.client_id,
        }
        auth = None
        if self.client_secret:
            # Use HTTP Basic auth when client secret exists
            auth = (self.client_id, self.client_secret)
        else:
            # Public client: send client_id in body only
            data['client_id'] = self.client_id

        try:
            r = requests.post(self.token_endpoint, data=data, auth=auth, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error('OIDC :: Token exchange failed: %s', e)
            raise cherrypy.HTTPError(401, 'OIDC token exchange failed.')

    def fetch_userinfo(self, access_token):
        if not self.userinfo_endpoint:
            return None
        headers = {'Authorization': 'Bearer ' + access_token}
        try:
            r = requests.get(self.userinfo_endpoint, headers=headers, timeout=10)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            logger.warn('OIDC :: Failed to load userinfo: %s', e)
        return None


STATE_COOKIE = 'tautulli_oidc_state'


def _make_state_cookie(redirect_uri, remember_me, nonce, state):
    exp = datetime.now(tz=timezone.utc) + timedelta(minutes=5)
    payload = {
        'redirect_uri': redirect_uri or '',
        'remember_me': 1 if remember_me else 0,
        'nonce': nonce,
        'state': state,
        'exp': exp,
    }
    token = jwt.encode(payload, plexpy.CONFIG.JWT_SECRET, algorithm='HS256')

    cherrypy.response.cookie[STATE_COOKIE] = token
    cherrypy.response.cookie[STATE_COOKIE]['max-age'] = 300
    cherrypy.response.cookie[STATE_COOKIE]['path'] = plexpy.HTTP_ROOT.rstrip('/') or '/'
    cherrypy.response.cookie[STATE_COOKIE]['httponly'] = True
    cherrypy.response.cookie[STATE_COOKIE]['samesite'] = 'lax'


def _pop_state_cookie():
    cookie = cherrypy.request.cookie.get(STATE_COOKIE)
    if not cookie:
        return None
    token = cookie.value
    try:
        payload = jwt.decode(token, plexpy.CONFIG.JWT_SECRET, algorithms=['HS256'])
    except Exception:
        return None

    # Clear cookie
    cherrypy.response.cookie[STATE_COOKIE] = ''
    cherrypy.response.cookie[STATE_COOKIE]['max-age'] = 0
    cherrypy.response.cookie[STATE_COOKIE]['path'] = plexpy.HTTP_ROOT.rstrip('/') or '/'
    return payload
