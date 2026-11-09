from __future__ import annotations

import base64

from odoo import _, api, models
from odoo.exceptions import UserError

from odoo.addons.aypatech_ai_agent.ai.tools.attachment import (
    ALLOWED_MIMETYPES,
    DEFAULT_MAX_UPLOAD_BYTES,
    DEFAULT_TEXT_INLINE_LIMIT_KB,
    IMAGE_MIMETYPES,
    PDF_MIMETYPE,
    TEXT_MIMETYPES,
)


class IrAttachment(models.Model):
    """Validate, describe, and materialize attachments for AI consumption."""

    _inherit = 'ir.attachment'

    # ------------------------------------
    # Helper
    # ------------------------------------

    @api.model
    def _wooai_max_size_bytes(self) -> int:
        """Return the configured maximum upload size in bytes."""
        return (
            self.env['ir.config_parameter']
            .sudo()
            .get_int('web.max_file_upload_size', DEFAULT_MAX_UPLOAD_BYTES)
        )

    @api.model
    def _wooai_text_inline_limit_bytes(self) -> int:
        """Return the inline-text size threshold in bytes."""
        return DEFAULT_TEXT_INLINE_LIMIT_KB * 1024

    @api.model
    def _wooai_strategy_for(self, mimetype: str) -> str | None:
        """Return the materialization strategy for a mimetype, or ``None``."""
        if mimetype in IMAGE_MIMETYPES:
            return 'image'
        if mimetype == PDF_MIMETYPE:
            return 'file'
        if mimetype in TEXT_MIMETYPES:
            return 'inline_text'
        return None

    @api.model
    def _wooai_check_mimetype(self, mimetype: str) -> None:
        """Raise when the mimetype is not in the allow-list.

        :raise UserError: when the mimetype is unsupported
        """
        if mimetype not in ALLOWED_MIMETYPES:
            raise UserError(
                _(
                    'Attachment type %(mime)s is not supported. Allowed: %(allowed)s.',
                    mime=mimetype or '(unknown)',
                    allowed=', '.join(sorted(ALLOWED_MIMETYPES)),
                )
            )

    @api.model
    def _wooai_check_size(self, size: int) -> None:
        """Raise when the byte size exceeds the configured limit.

        :raise UserError: when the size is over the limit
        """
        if size > (limit := self._wooai_max_size_bytes()):
            raise UserError(
                _(
                    'Attachment exceeds the %(limit)s MiB size limit.',
                    limit=limit // (1024 * 1024),
                )
            )

    @api.model
    def _wooai_store_binary(
        self,
        filename: str,
        mimetype: str,
        data_b64: str,
        res_id: int | None = None,
    ) -> IrAttachment:
        """Create a session attachment from a base64 payload, checking only its size.

        The mimetype allow-list guards what the *model* may ingest, which is a
        narrower question than what may be stored: an XLSX export has no
        ingest strategy, yet the user must still be able to download it.

        :raise UserError: when the payload is not valid base64
        """
        try:
            raw = base64.b64decode(data_b64 or '', validate=True)
        except ValueError as error:
            raise UserError(
                _('Attachment data is not valid base64: %s', error)
            ) from error
        self._wooai_check_size(len(raw))
        return self.create(
            {
                'name': filename or 'upload',
                'raw': raw,
                'mimetype': mimetype,
                'res_model': 'aypatech_wooai.session',
                'res_id': res_id or 0,
            }
        )

    @api.model
    def _wooai_create_from_upload(
        self,
        filename: str,
        mimetype: str,
        data_b64: str,
        res_id: int | None = None,
    ) -> IrAttachment:
        """Create a session attachment from an uploaded base64 payload.

        :raise UserError: when the mimetype is not one the model can ingest
        """
        self._wooai_check_mimetype(mimetype)
        return self._wooai_store_binary(filename, mimetype, data_b64, res_id=res_id)

    def _wooai_validate(self) -> None:
        """Check read access, mimetype, and size on each record."""
        for record in self:
            record.check_access('read')
            record._wooai_check_mimetype(record.mimetype)
            record._wooai_check_size(record.file_size or 0)

    def _wooai_describe(self) -> dict:
        """Return a lightweight descriptor of this attachment."""
        return {
            'id': self.id,
            'filename': self.name,
            'mimetype': self.mimetype,
            'size': self.file_size or 0,
        }

    def _wooai_materialize(self) -> dict:
        """Return a content block for this attachment per its strategy."""
        self._wooai_validate()
        # Odoo 20 returns a lazy ``BinaryValue``/``LocalBinaryFile`` proxy for
        # filestore-backed attachments rather than plain ``bytes``; coerce it
        # eagerly so ``len()``, slicing and ``.decode()`` below behave as on
        # a real ``bytes`` object.
        raw = bytes(self.raw or b'')
        strategy = self._wooai_strategy_for(self.mimetype)
        block = {
            'type': 'aypatech_wooai_attachment',
            'attachment_id': self.id,
            'filename': self.name,
            'mimetype': self.mimetype,
            'strategy': strategy,
        }
        if strategy == 'inline_text':
            limit = self._wooai_text_inline_limit_bytes()
            truncated = len(raw) > limit
            if truncated:
                raw = raw[:limit]
            block['inline_text'] = raw.decode('utf-8', errors='replace')
            block['truncated'] = truncated
        else:
            block['data_b64'] = base64.b64encode(raw).decode('ascii')
        return block
