from __future__ import annotations

import json
from collections.abc import Callable

from odoo.addons.aypatech_ai_agent.ai.providers.base import ProviderBase


class OpenAICompatibleProvider(ProviderBase):
    """Adapter for providers exposing an OpenAI-style Chat Completions API.

    Groq, Mistral, xAI, DeepSeek, OpenRouter and Ollama all speak this wire
    format (``POST {base_url}/chat/completions``) with only the base URL,
    model names and a couple of capability flags differing — this base class
    carries the conversion between the canonical input format and Chat
    Completions messages/tool calls, and the streaming/non-streaming
    dispatch, once for all of them.
    """

    supports_image_generation = False
    supports_code_interpreter = False
    supports_reasoning_effort = False

    reasoning_error_tokens = ('reasoning', 'effort')

    # Contract

    def headers(self) -> dict:
        """Return the bearer-token headers; subclasses with no key override this."""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

    def request(
        self,
        inputs,
        tools_schema=None,
        text_schema=None,
        on_delta=None,
        model=None,
        enable_web_search=False,
        enable_image_generation=False,
        enable_code_interpreter=False,
        extra=None,
    ) -> dict:
        """Build and run a Chat Completions request, dispatching to streaming when requested."""
        model = self.model_for(model)
        messages = self._inputs_to_messages(inputs)
        body = {
            'model': model,
            'messages': messages,
        }
        if self.max_tokens:
            body['max_tokens'] = self.max_tokens
        effort = (extra or {}).get('reasoning_effort')
        if effort and self.supports_reasoning_effort:
            body['reasoning_effort'] = effort
        tools = self._tools_to_chat(tools_schema)
        if tools:
            body['tools'] = tools
            body['tool_choice'] = 'auto'
        if text_schema:
            body['response_format'] = {
                'type': 'json_schema',
                'json_schema': {
                    'name': text_schema.get('name', 'response'),
                    'schema': text_schema['schema'],
                    'strict': True,
                },
            }
        return self._invoke_with_reasoning_retry(
            model,
            lambda callback: self._invoke(body, callback),
            on_delta,
            ((body, ('reasoning_effort',)),),
        )

    # Dispatch

    def _invoke(self, body: dict, on_delta: Callable | None) -> dict:
        """Dispatch the request to the streaming or non-streaming path."""
        if callable(on_delta):
            return self._stream(body, on_delta)
        return self._parse_response(self._post_json('/chat/completions', body))

    # Input conversion

    @classmethod
    def _inputs_to_messages(cls, inputs) -> list[dict]:
        """Convert canonical inputs into Chat Completions messages."""
        messages = []
        system_parts = []
        for item in cls._strip_cache_markers(inputs):
            item_type = item.get('type')
            role = item.get('role')
            if role == 'system':
                text = cls._text_from_content(item.get('content'))
                if text:
                    system_parts.append(text)
                continue
            if item_type == 'function_call':
                messages.append({
                    'role': 'assistant',
                    'content': None,
                    'tool_calls': [{
                        'id': item.get('call_id'),
                        'type': 'function',
                        'function': {
                            'name': item.get('name'),
                            'arguments': item.get('arguments') or '{}',
                        },
                    }],
                })
                continue
            if item_type == 'function_call_output':
                output = item.get('output')
                if not isinstance(output, str):
                    output = json.dumps(output, default=str)
                messages.append({
                    'role': 'tool',
                    'tool_call_id': item.get('call_id'),
                    'content': output,
                })
                continue
            if role in ('user', 'assistant'):
                messages.append({
                    'role': role,
                    'content': cls._content_to_chat(item.get('content')),
                })
        if system_parts:
            messages.insert(0, {'role': 'system', 'content': '\n\n'.join(system_parts)})
        return messages

    @staticmethod
    def _text_from_content(content) -> str:
        """Return the plain-text concatenation of a canonical content payload."""
        if isinstance(content, str):
            return content
        parts = []
        for block in content or []:
            if isinstance(block, dict) and block.get('text'):
                parts.append(block['text'])
        return '\n'.join(p for p in parts if p)

    @classmethod
    def _content_to_chat(cls, content):
        """Convert canonical content blocks into Chat Completions content parts."""
        if isinstance(content, str):
            return content
        parts = []
        for block in content or []:
            if not isinstance(block, dict):
                continue
            block_type = block.get('type')
            if block_type == 'input_image':
                parts.append({
                    'type': 'image_url',
                    'image_url': {'url': block.get('image_url') or ''},
                })
            elif block_type == 'aypatech_wooai_attachment':
                parts.append({'type': 'text', 'text': cls._attachment_to_text(block)})
            elif block_type == 'aypatech_wooai_thinking':
                continue
            elif block.get('text'):
                parts.append({'type': 'text', 'text': block['text']})
        if not parts:
            return ''
        if len(parts) == 1 and parts[0].get('type') == 'text':
            return parts[0]['text']
        return parts

    @staticmethod
    def _attachment_to_text(block: dict) -> str:
        """Render an unsupported attachment block as inline text, images included.

        Chat Completions attachments beyond images have no first-class
        upload path across these providers, so files are inlined as text.
        """
        if block.get('strategy') == 'image':
            return '[image attached]'
        filename = block.get('filename') or 'attachment'
        mimetype = block.get('mimetype') or 'application/octet-stream'
        text = block.get('inline_text') or ''
        prefix = f'--- File: {filename} ({mimetype}) ---\n'
        if block.get('truncated'):
            text += '\n[truncated]'
        return prefix + text

    # Tool conversion

    @staticmethod
    def _tools_to_chat(tools_schema) -> list[dict]:
        """Convert canonical flat tool schemas into Chat Completions tool definitions."""
        if not tools_schema:
            return []
        seen = set()
        out = []
        for tool in tools_schema:
            name = tool['name']
            if name in seen:
                continue
            seen.add(name)
            out.append({
                'type': 'function',
                'function': {
                    'name': name,
                    'description': tool.get('description') or '',
                    'parameters': tool.get('parameters') or {'type': 'object', 'properties': {}},
                },
            })
        return out

    # Parse

    def _parse_response(self, payload: dict) -> dict:
        """Parse a non-streaming Chat Completions response."""
        choices = payload.get('choices') or []
        choice = choices[0] if choices else {}
        message = choice.get('message') or {}
        tool_calls = []
        carry_inputs = []
        for call in message.get('tool_calls') or []:
            function = call.get('function') or {}
            args, parse_error = self._parse_tool_arguments(function.get('arguments'))
            tool_calls.append({
                'call_id': call.get('id'),
                'name': function.get('name'),
                'arguments': args,
                '_parse_error': parse_error,
            })
            carry_inputs.append({
                'type': 'function_call',
                'call_id': call.get('id'),
                'name': function.get('name'),
                'arguments': function.get('arguments') or '{}',
            })
        text = (message.get('content') or '').strip() if isinstance(message.get('content'), str) else ''
        if text:
            carry_inputs.insert(0, {
                'type': 'message',
                'role': 'assistant',
                'content': [{'type': 'output_text', 'text': text}],
            })
        usage = payload.get('usage') or {}
        result = {
            'text': text,
            'tool_calls': tool_calls,
            'carry_inputs': carry_inputs,
            'usage': self._usage(
                input_tokens=usage.get('prompt_tokens'),
                output_tokens=usage.get('completion_tokens'),
                cache_read_tokens=(usage.get('prompt_tokens_details') or {}).get('cached_tokens'),
            ),
        }
        if choice.get('finish_reason') == 'length':
            self._apply_truncation(result, limit=self.max_tokens)
        return result

    # Streaming

    def _stream(self, body: dict, on_delta) -> dict:
        """Stream a Chat Completions request, emitting deltas and assembling the final result."""
        body = {**body, 'stream': True, 'stream_options': {'include_usage': True}}
        text_parts = []
        tool_calls_by_index: dict[int, dict] = {}
        usage = {}
        finish_reason = None
        for event in self._post_stream('/chat/completions', body):
            choices = event.get('choices') or []
            if 'usage' in event and event.get('usage'):
                usage = event['usage']
            if not choices:
                continue
            choice = choices[0]
            delta = choice.get('delta') or {}
            if choice.get('finish_reason'):
                finish_reason = choice['finish_reason']
            if content := delta.get('content'):
                text_parts.append(content)
                self._call_on_delta(on_delta, 'text', {'delta': content})
            for call in delta.get('tool_calls') or []:
                index = call.get('index', 0)
                entry = tool_calls_by_index.setdefault(
                    index, {'call_id': None, 'name': None, 'arguments': ''},
                )
                if call.get('id'):
                    entry['call_id'] = call['id']
                function = call.get('function') or {}
                if function.get('name'):
                    entry['name'] = function['name']
                    self._call_on_delta(
                        on_delta, 'tool_start',
                        {'call_id': entry['call_id'], 'name': entry['name']},
                    )
                if args_delta := function.get('arguments'):
                    entry['arguments'] += args_delta
                    self._call_on_delta(
                        on_delta, 'tool_args',
                        {'call_id': entry['call_id'], 'delta': args_delta},
                    )
        tool_calls = []
        carry_inputs = []
        for entry in tool_calls_by_index.values():
            args, parse_error = self._parse_tool_arguments(entry['arguments'])
            tool_calls.append({
                'call_id': entry['call_id'],
                'name': entry['name'],
                'arguments': args,
                '_parse_error': parse_error,
            })
            carry_inputs.append({
                'type': 'function_call',
                'call_id': entry['call_id'],
                'name': entry['name'],
                'arguments': entry['arguments'] or '{}',
            })
        final_text = ''.join(text_parts).strip()
        if final_text:
            carry_inputs.insert(0, {
                'type': 'message',
                'role': 'assistant',
                'content': [{'type': 'output_text', 'text': final_text}],
            })
        result = {
            'text': final_text,
            'tool_calls': tool_calls,
            'carry_inputs': carry_inputs,
            'usage': self._usage(
                input_tokens=usage.get('prompt_tokens'),
                output_tokens=usage.get('completion_tokens'),
                cache_read_tokens=(usage.get('prompt_tokens_details') or {}).get('cached_tokens'),
            ),
        }
        if finish_reason == 'length':
            self._apply_truncation(result, on_delta, self.max_tokens)
        return result
