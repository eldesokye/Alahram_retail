from __future__ import annotations

import base64
import json

from odoo import http
from odoo.http import Response, request


class VoiceController(http.Controller):
    """Speech-to-text and text-to-speech endpoints for the chat composer."""

    def _provider(self):
        provider = request.env.company.wooai_default_provider_id
        if not provider:
            provider = request.env['aypatech_wooai.provider']._get_default()
        return provider

    @http.route('/aypatech_ai_agent/voice/transcribe', type='http', auth='user', methods=['POST'], csrf=False)
    def transcribe(self, **kwargs):
        """Transcribe an uploaded audio recording to text."""
        upload = request.httprequest.files.get('audio')
        if not upload:
            return Response(json.dumps({'error': 'No audio file uploaded.'}), status=400, content_type='application/json')
        provider = self._provider()
        if not provider or not provider.supports_speech_to_text():
            return Response(
                json.dumps({'error': 'No configured provider supports speech-to-text.'}),
                status=400,
                content_type='application/json',
            )
        try:
            text = provider.transcribe(
                upload.read(),
                upload.filename,
                upload.mimetype,
                language=kwargs.get('language'),
            )
        except Exception as error:  # noqa: BLE001 — surface as a JSON error to the composer
            return Response(json.dumps({'error': str(error)}), status=400, content_type='application/json')
        return Response(json.dumps({'text': text}), content_type='application/json')

    @http.route('/aypatech_ai_agent/voice/speak', type='http', auth='user', methods=['POST'], csrf=False)
    def speak(self, **kwargs):
        """Render posted text to speech and return the audio bytes."""
        text = (kwargs.get('text') or '').strip()
        if not text:
            return Response(json.dumps({'error': 'No text provided.'}), status=400, content_type='application/json')
        provider = self._provider()
        if not provider or not provider.supports_text_to_speech():
            return Response(
                json.dumps({'error': 'No configured provider supports text-to-speech.'}),
                status=400,
                content_type='application/json',
            )
        try:
            audio, mimetype = provider.synthesize(
                text,
                voice=kwargs.get('voice'),
                language=kwargs.get('language'),
            )
        except Exception as error:  # noqa: BLE001
            return Response(json.dumps({'error': str(error)}), status=400, content_type='application/json')
        return Response(audio, content_type=mimetype)
