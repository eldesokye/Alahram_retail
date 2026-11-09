from __future__ import annotations

import inspect
import json
import logging
import os

from markupsafe import Markup

from odoo import http
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import request

from . import api as api_registry
from .terms import ui_terms

_logger = logging.getLogger(__name__)
USER_GROUP = api_registry.GROUPS['user']
APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'static', 'app')


def _asset_version(module_version):
    """Return a cache-busting version string derived from the newest asset mtime."""
    newest = 0
    for folder, _dirs, files in os.walk(APP_DIR):
        for name in files:
            newest = max(newest, int(os.path.getmtime(os.path.join(folder, name))))
    return '%s.%s' % (module_version or '1', newest)


class AIAppController(http.Controller):
    """Standalone AI Agent web app: its own page, its own JSON API, no backend chrome."""

    @http.route('/aypatech_ai/app', type='http', auth='user', methods=['GET'])
    def ai_app(self, **kwargs):
        env = request.env
        if not env.user.has_group(USER_GROUP):
            return request.redirect('/odoo')
        module = env['ir.module.module'].sudo().search([('name', '=', 'aypatech_ai_agent')], limit=1)
        lang = env['res.lang'].sudo().search([('code', '=', env.lang or 'en_US')], limit=1)
        config = {
            'csrf': request.csrf_token(),
            'api': '/aypatech_ai/app/api/',
            'lang': env.lang or 'en_US',
            'direction': lang.direction or 'ltr',
            'terms': ui_terms(env),
        }
        return request.render('aypatech_ai_agent.ai_app_page', {
            'doctype': Markup('<!DOCTYPE html>'),
            'config_json': Markup(json.dumps(config).replace('</', '<\\/')),
            'asset_version': _asset_version(module.latest_version),
            'direction': lang.direction or 'ltr',
            'html_lang': (env.lang or 'en_US').replace('_', '-'),
        })

    @http.route('/aypatech_ai/app/api/<string:method>', type='http', auth='user', methods=['POST'])
    def ai_api(self, method, **kwargs):
        entry = api_registry.get_method(method)
        if not entry:
            return request.make_json_response({'error': 'Unknown method'}, status=404)
        func, group = entry
        if not request.env.user.has_group(group):
            return request.make_json_response(
                {'error': request.env._('You do not have access to this action.'), 'code': 'access'},
                status=403,
            )
        try:
            params = json.loads(request.httprequest.get_data() or b'{}')
        except ValueError:
            params = {}
        params = params if isinstance(params, dict) else {}
        try:
            inspect.signature(func).bind(request.env, **params)
        except TypeError as exc:
            _logger.warning('Bad parameters for %s: %s', method, exc)
            return request.make_json_response({'error': 'Invalid parameters'}, status=400)
        try:
            result = func(request.env, **params)
        except (UserError, ValidationError, AccessError) as exc:
            request.env.cr.rollback()
            return request.make_json_response({'error': str(exc.args[0] if exc.args else exc)})
        return request.make_json_response({'result': result})
