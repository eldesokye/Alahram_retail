from __future__ import annotations

import base64
import logging

import requests

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Providers known to offer a speech-to-text and/or text-to-speech REST API.
STT_PROVIDERS = {'openai', 'google'}
TTS_PROVIDERS = {'openai', 'google'}


class AIProviderVoice(models.Model):
    """Speech-to-text and text-to-speech helpers for the configured providers.

    Mirrors the text request contract: one method per direction, dispatched
    by provider name, so a chat composer can transcribe a recording or read
    an answer aloud without caring which provider is configured.
    """

    _inherit = 'aypatech_wooai.provider'

    # Capability

    def supports_speech_to_text(self) -> bool:
        self.ensure_one()
        return self.name in STT_PROVIDERS

    def supports_text_to_speech(self) -> bool:
        self.ensure_one()
        return self.name in TTS_PROVIDERS

    # Speech to text

    def transcribe(self, audio: bytes, filename: str, mimetype: str, language: str | None = None) -> str:
        """Transcribe an audio recording to text.

        :raise UserError: when this provider has no speech-to-text API, or
            the request fails
        """
        self.ensure_one()
        if self.name == 'openai':
            return self._openai_transcribe(audio, filename, mimetype, language)
        if self.name == 'google':
            return self._google_transcribe(audio, mimetype, language)
        raise UserError(
            _('%(provider)s has no speech-to-text API.', provider=self.display_name)
        )

    def _openai_transcribe(self, audio: bytes, filename: str, mimetype: str, language: str | None) -> str:
        key = self.sudo().api_key
        if not key:
            raise UserError(_('%(provider)s API key is not configured.', provider=self.display_name))
        data = {'model': 'gpt-4o-mini-transcribe'}
        if language:
            data['language'] = language
        try:
            response = requests.post(
                'https://api.openai.com/v1/audio/transcriptions',
                headers={'Authorization': f'Bearer {key}'},
                data=data,
                files={'file': (filename or 'audio.webm', audio, mimetype or 'audio/webm')},
                timeout=self.request_timeout or 60,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise UserError(
                _('Transcription failed: %(error)s', error=str(error)[:300])
            ) from error
        return (response.json() or {}).get('text', '')

    def _google_transcribe(self, audio: bytes, mimetype: str, language: str | None) -> str:
        key = self.sudo().api_key
        if not key:
            raise UserError(_('%(provider)s API key is not configured.', provider=self.display_name))
        encoding = 'WEBM_OPUS' if 'webm' in (mimetype or '') else 'LINEAR16'
        body = {
            'config': {
                'encoding': encoding,
                'languageCode': language or 'en-US',
            },
            'audio': {'content': base64.b64encode(audio).decode()},
        }
        try:
            response = requests.post(
                f'https://speech.googleapis.com/v1/speech:recognize?key={key}',
                json=body,
                timeout=self.request_timeout or 60,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise UserError(
                _('Transcription failed: %(error)s', error=str(error)[:300])
            ) from error
        results = (response.json() or {}).get('results') or []
        return ' '.join(
            (result.get('alternatives') or [{}])[0].get('transcript', '')
            for result in results
        ).strip()

    # Text to speech

    def synthesize(self, text: str, voice: str | None = None, language: str | None = None) -> tuple[bytes, str]:
        """Render text to speech, returning ``(audio_bytes, mimetype)``.

        :raise UserError: when this provider has no text-to-speech API, or
            the request fails
        """
        self.ensure_one()
        if self.name == 'openai':
            return self._openai_synthesize(text, voice)
        if self.name == 'google':
            return self._google_synthesize(text, voice, language)
        raise UserError(
            _('%(provider)s has no text-to-speech API.', provider=self.display_name)
        )

    def _openai_synthesize(self, text: str, voice: str | None) -> tuple[bytes, str]:
        key = self.sudo().api_key
        if not key:
            raise UserError(_('%(provider)s API key is not configured.', provider=self.display_name))
        try:
            response = requests.post(
                'https://api.openai.com/v1/audio/speech',
                headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
                json={
                    'model': 'gpt-4o-mini-tts',
                    'voice': voice or 'alloy',
                    'input': text,
                    'response_format': 'mp3',
                },
                timeout=self.request_timeout or 60,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise UserError(
                _('Speech synthesis failed: %(error)s', error=str(error)[:300])
            ) from error
        return response.content, 'audio/mpeg'

    def _google_synthesize(self, text: str, voice: str | None, language: str | None) -> tuple[bytes, str]:
        key = self.sudo().api_key
        if not key:
            raise UserError(_('%(provider)s API key is not configured.', provider=self.display_name))
        body = {
            'input': {'text': text},
            'voice': {
                'languageCode': language or 'en-US',
                'name': voice or None,
            },
            'audioConfig': {'audioEncoding': 'MP3'},
        }
        body['voice'] = {k: v for k, v in body['voice'].items() if v}
        try:
            response = requests.post(
                f'https://texttospeech.googleapis.com/v1/text:synthesize?key={key}',
                json=body,
                timeout=self.request_timeout or 60,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise UserError(
                _('Speech synthesis failed: %(error)s', error=str(error)[:300])
            ) from error
        audio_b64 = (response.json() or {}).get('audioContent', '')
        return base64.b64decode(audio_b64) if audio_b64 else b'', 'audio/mpeg'
