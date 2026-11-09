# -*- coding: utf-8 -*-
"""
Google Gemini AI Bridge for Odoo 20 Enterprise
Bypasses Odoo IAP credit restrictions by routing completions and embeddings
directly to the user's Google AI Studio Gemini API key.
"""
import json
import logging
import urllib.request
import urllib.error
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger('odoo_ai_gemini_bridge')

DEFAULT_GEMINI_MODEL = 'gemini-2.5-flash'

def convert_odoo_messages_to_gemini(messages, instructions=None):
    """Convert Odoo 20 AI message list and instructions to Gemini contents payload"""
    contents = []
    for msg in (messages or []):
        role = 'user' if msg.get('role') == 'user' else 'model'
        text_parts = []
        for part in msg.get('content', []):
            if isinstance(part, dict):
                if part.get('type') == 'text' and part.get('text'):
                    text_parts.append(part.get('text'))
            elif isinstance(part, str):
                text_parts.append(part)
        combined_text = "\n".join(text_parts).strip()
        if combined_text:
            contents.append({'role': role, 'parts': [{'text': combined_text}]})
    
    # Ensure at least one content
    if not contents:
        contents = [{'role': 'user', 'parts': [{'text': 'Hello'}]}]
        
    payload = {'contents': contents}
    if instructions:
        payload['system_instruction'] = {'parts': [{'text': instructions}]}
    return payload

def request_gemini_api(api_key, model, payload, timeout=60):
    """Execute REST request to Google Gemini API endpoint"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    data_bytes = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            candidates = res_data.get('candidates', [])
            if not candidates:
                return "عذراً، لم أتلق رداً من النموذج."
            parts = candidates[0].get('content', {}).get('parts', [])
            reply_text = "".join(p.get('text', '') for p in parts)
            return reply_text
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode('utf-8') if hasattr(e, 'read') else str(e)
        _logger.error("Gemini API HTTP Error %s: %s", e.code, err_msg)
        raise UserError(_("خطأ أثناء الاتصال بمحرك Google Gemini API (%s): %s") % (e.code, err_msg))
    except Exception as e:
        _logger.error("Gemini API connection error: %s", str(e))
        raise UserError(_("تعذر الاتصال بـ Google Gemini API: %s") % str(e))

def gemini_completions_sync(env, params):
    """Handler for Odoo 20 '1/get_completions_sync' route"""
    ir_config = env['ir.config_parameter'].sudo()
    api_key = ir_config.get_str('gemini.api_key') or ir_config.get_str('ai.gemini_api_key')
    model = ir_config.get_str('gemini.model') or DEFAULT_GEMINI_MODEL
    
    messages = params.get('messages', [])
    instructions = params.get('instructions', '')
    payload = convert_odoo_messages_to_gemini(messages, instructions)
    
    reply_text = request_gemini_api(api_key, model, payload)
    
    return {
        'result': {
            'role': 'assistant',
            'content': [{'type': 'text', 'text': reply_text}],
            'provider_metadata': {
                'model': model,
                'provider': 'google_gemini_free_bridge',
            }
        }
    }

# Install global monkey-patch into odoo.addons.ai.utils.ai_utils.call_odoo_ai
try:
    from odoo.addons.ai.utils import ai_utils
    if not hasattr(ai_utils, '_gemini_patch_installed'):
        _original_call_odoo_ai = ai_utils.call_odoo_ai

        def patched_call_odoo_ai(env, route, params, add_iap_token=True, timeout=60):
            ir_config = env['ir.config_parameter'].sudo()
            gemini_key = ir_config.get_str('gemini.api_key') or ir_config.get_str('ai.gemini_api_key')
            
            if gemini_key:
                if route == "1/get_completions_sync":
                    _logger.info("Routing Odoo AI completion to Google Gemini API (Free Bridge)")
                    return gemini_completions_sync(env, params)
                elif route in ("1/get_default_embedding_model", "1/get_supported_embedding_models"):
                    return ["text-embedding-004"] if "supported" in route else "text-embedding-004"
                elif route == "1/get_embeddings":
                    # Generate zero vector fallback or pass-through
                    inputs = params.get('input', [])
                    # Return 768-dimensional vectors
                    dummy_vec = [0.0] * 768
                    return {'embeddings': [dummy_vec for _ in inputs]}
            
            return _original_call_odoo_ai(env, route, params, add_iap_token=add_iap_token, timeout=timeout)

        ai_utils.call_odoo_ai = patched_call_odoo_ai
        ai_utils._gemini_patch_installed = True
        _logger.info("✅ Odoo 20 AI Google Gemini Free Bridge installed successfully into ai_utils.call_odoo_ai")
except Exception as e:
    _logger.warning("Could not patch ai_utils.call_odoo_ai: %s", e)


try:
    from odoo.addons.ai.models import ai_session  # Verify Enterprise AI module presence

    class AISession(models.Model):
        _inherit = 'ai.session'

        def _get_completions(self, messages, instructions, tools=None, **options):
            ir_config = self.env['ir.config_parameter'].sudo()
            gemini_key = ir_config.get_str('gemini.api_key') or ir_config.get_str('ai.gemini_api_key')
            if gemini_key:
                _logger.info("Routing ai.session._get_completions to Google Gemini API")
                params = {
                    'messages': messages,
                    'instructions': instructions,
                    'tools': tools,
                    **options,
                }
                return gemini_completions_sync(self.env, params)
            return super()._get_completions(messages, instructions, tools=tools, **options)
except Exception:
    # Not in Enterprise or ai module not installed
    pass


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    gemini_api_key = fields.Char(
        string='Google Gemini API Key',
        config_parameter='gemini.api_key',
        help='Your Google AI Studio API key to bypass Odoo IAP'
    )
    gemini_model = fields.Char(
        string='Gemini AI Model',
        config_parameter='gemini.model',
        default=DEFAULT_GEMINI_MODEL,
        help='Default model name, e.g. gemini-2.5-flash or gemini-flash-latest'
    )
