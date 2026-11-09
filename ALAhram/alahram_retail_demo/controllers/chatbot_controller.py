# -*- coding: utf-8 -*-
"""
Al Ahram Cookware — AI Chatbot Controller & REST API
====================================================
Exposes:
1. REST API endpoint: /api/alahram/chat
2. Interactive Web Chatbot interface: /alahram/chat
"""

import json
import logging
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class AlAhramChatbotController(http.Controller):

    @http.route(
        ['/api/alahram/chat'],
        type='http',
        auth='public',
        methods=['GET', 'POST', 'OPTIONS'],
        csrf=False,
        cors='*'
    )
    def api_alahram_chat(self, **kwargs):
        """
        Universal REST API endpoint for Al Ahram AI Chatbot.
        Accepts GET query parameters or POST JSON payload.
        Tied directly to Odoo 20 Enterprise database and Google Gemini 2.5 Flash.
        """
        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        }

        if request.httprequest.method == 'OPTIONS':
            return Response(status=200, headers=headers)

        question = ''
        history = []

        if request.httprequest.method == 'POST':
            try:
                data = {}
                if hasattr(request, 'get_json_data'):
                    try:
                        data = request.get_json_data() or {}
                    except Exception:
                        data = {}
                if not data:
                    raw_body = request.httprequest.get_data(as_text=True) or request.httprequest.data.decode('utf-8')
                    if raw_body:
                        data = json.loads(raw_body)
                if isinstance(data, dict):
                    question = data.get('question') or data.get('message') or data.get('prompt') or ''
                    history = data.get('history', [])
            except Exception as e:
                _logger.warning("Error parsing JSON payload in /api/alahram/chat: %s", str(e))

        if not question:
            question = kwargs.get('question') or kwargs.get('message') or kwargs.get('prompt') or ''

        if not question or not question.strip():
            return Response(
                json.dumps({
                    'status': 'error',
                    'message': 'يرجى إرسال سؤال صالح في حقل question أو message',
                }, ensure_ascii=False),
                status=400,
                headers=headers
            )

        # Call the Al Ahram Chatbot Service
        try:
            service = request.env['alahram.chatbot.service'].sudo()
            result = service.ask_ai(
                question=question.strip(),
                history=history,
                channel='api',
                user_id=request.env.user.id if request.env.user and request.env.user.id != request.env.ref('base.public_user').id else None
            )
            return Response(
                json.dumps(result, ensure_ascii=False),
                status=200,
                headers=headers
            )
        except Exception as e:
            _logger.exception("Chatbot API Exception: %s", str(e))
            return Response(
                json.dumps({
                    'status': 'error',
                    'message': f"خطأ داخلي في معالجة طلب الذكاء الاصطناعي: {str(e)}",
                }, ensure_ascii=False),
                status=500,
                headers=headers
            )

    @http.route(
        ['/alahram/chat'],
        type='http',
        auth='public',
        website=False,
        methods=['GET'],
        csrf=False
    )
    def render_web_chatbot(self, **kwargs):
        """
        Renders the standalone interactive Arabic AI Chatbot application.
        Directly tied with live database queries and real-time streaming UI.
        """
        html_page = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>شات بوت الأهرام الذكي | Al Ahram Cookware AI Assistant</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #0f766e;
            --primary-hover: #115e59;
            --primary-light: #ccfbf1;
            --accent: #d97706;
            --bg-dark: #0f172a;
            --bg-card: #1e293b;
            --bg-chat: #0b1329;
            --text-light: #f8fafc;
            --text-muted: #94a3b8;
            --border: #334155;
            --user-bubble: #1e3a8a;
            --bot-bubble: #1e293b;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Cairo', sans-serif;
        }

        body {
            background-color: var(--bg-chat);
            color: var(--text-light);
            display: flex;
            height: 100vh;
            overflow: hidden;
        }

        /* Sidebar */
        .sidebar {
            width: 320px;
            background: var(--bg-dark);
            border-left: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            padding: 20px;
            gap: 20px;
        }

        .brand-header {
            display: flex;
            align-items: center;
            gap: 12px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border);
        }

        .brand-logo {
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, #0d9488, #d97706);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            box-shadow: 0 4px 12px rgba(13, 148, 136, 0.3);
        }

        .brand-info h1 {
            font-size: 16px;
            font-weight: 800;
            color: #f1f5f9;
        }

        .brand-info p {
            font-size: 11px;
            color: var(--accent);
            font-weight: 600;
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(16, 185, 129, 0.1);
            color: #34d399;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            border: 1px solid rgba(16, 185, 129, 0.2);
        }

        .status-dot {
            width: 8px;
            height: 8px;
            background-color: #10b981;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(1.2); }
            100% { opacity: 1; transform: scale(1); }
        }

        .quick-actions h3 {
            font-size: 13px;
            color: var(--text-muted);
            margin-bottom: 10px;
            font-weight: 700;
        }

        .prompt-btn {
            background: var(--bg-card);
            border: 1px solid var(--border);
            color: #cbd5e1;
            padding: 10px 14px;
            border-radius: 10px;
            font-size: 13px;
            text-align: right;
            cursor: pointer;
            margin-bottom: 8px;
            width: 100%;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .prompt-btn:hover {
            background: rgba(13, 148, 136, 0.15);
            border-color: #0d9488;
            color: #fff;
            transform: translateX(-3px);
        }

        .nav-back-btn {
            margin-top: auto;
            background: rgba(255, 255, 255, 0.05);
            color: #94a3b8;
            text-decoration: none;
            padding: 10px;
            border-radius: 8px;
            text-align: center;
            font-size: 13px;
            font-weight: 600;
            border: 1px solid var(--border);
            transition: all 0.2s;
        }

        .nav-back-btn:hover {
            background: var(--primary);
            color: #fff;
            border-color: var(--primary);
        }

        /* Main Chat Area */
        .chat-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: var(--bg-chat);
            position: relative;
        }

        .chat-header {
            padding: 16px 24px;
            background: var(--bg-dark);
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .chat-header h2 {
            font-size: 16px;
            font-weight: 700;
        }

        .chat-messages {
            flex: 1;
            padding: 24px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 16px;
            scroll-behavior: smooth;
        }

        .message-row {
            display: flex;
            gap: 12px;
            max-width: 85%;
        }

        .message-row.user {
            align-self: flex-start;
            flex-direction: row-reverse;
        }

        .message-row.bot {
            align-self: flex-end;
            flex-direction: row;
        }

        .avatar {
            width: 38px;
            height: 38px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            flex-shrink: 0;
        }

        .avatar.bot {
            background: #0d9488;
            color: #fff;
            box-shadow: 0 2px 8px rgba(13, 148, 136, 0.4);
        }

        .avatar.user {
            background: #2563eb;
            color: #fff;
        }

        .bubble {
            padding: 14px 18px;
            border-radius: 14px;
            font-size: 14.5px;
            line-height: 1.7;
        }

        .message-row.user .bubble {
            background: var(--user-bubble);
            color: #ffffff;
            border-top-right-radius: 4px;
        }

        .message-row.bot .bubble {
            background: var(--bot-bubble);
            color: #f1f5f9;
            border-top-left-radius: 4px;
            border: 1px solid var(--border);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        }

        .time-tag {
            font-size: 11px;
            color: #64748b;
            margin-top: 6px;
            display: block;
            text-align: left;
        }

        /* Typing indicator */
        .typing-indicator {
            display: none;
            gap: 6px;
            padding: 12px 18px;
            background: var(--bot-bubble);
            border-radius: 14px;
            border: 1px solid var(--border);
            width: fit-content;
        }

        .typing-dot {
            width: 8px;
            height: 8px;
            background: #0d9488;
            border-radius: 50%;
            animation: bounce 1.4s infinite ease-in-out;
        }

        .typing-dot:nth-child(2) { animation-delay: 0.2s; }
        .typing-dot:nth-child(3) { animation-delay: 0.4s; }

        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); opacity: 0.4; }
            40% { transform: scale(1); opacity: 1; }
        }

        /* Input Form */
        .chat-input-area {
            padding: 16px 24px;
            background: var(--bg-dark);
            border-top: 1px solid var(--border);
        }

        .input-form {
            display: flex;
            gap: 12px;
            align-items: center;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 6px 14px;
            transition: border-color 0.2s;
        }

        .input-form:focus-within {
            border-color: #0d9488;
            box-shadow: 0 0 0 2px rgba(13, 148, 136, 0.2);
        }

        .chat-input {
            flex: 1;
            background: transparent;
            border: none;
            color: #fff;
            font-size: 14px;
            outline: none;
            padding: 8px 0;
            resize: none;
            max-height: 120px;
        }

        .chat-input::placeholder {
            color: #64748b;
        }

        .send-btn {
            background: var(--primary);
            color: #fff;
            border: none;
            padding: 10px 18px;
            border-radius: 8px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 14px;
        }

        .send-btn:hover {
            background: var(--primary-hover);
        }

        .send-btn:disabled {
            background: #334155;
            cursor: not-allowed;
            opacity: 0.6;
        }

        @media (max-width: 768px) {
            .sidebar { display: none; }
        }
    </style>
</head>
<body>

    <!-- Sidebar -->
    <div class="sidebar">
        <div class="brand-header">
            <div class="brand-logo">🍳</div>
            <div class="brand-info">
                <h1>الأهرام للأدوات المنزلية</h1>
                <p>مساعد الأعمال والذكاء الاصطناعي</p>
            </div>
        </div>

        <div class="status-badge">
            <span class="status-dot"></span>
            متصل بـ Odoo 20 + Gemini 2.5 Flash
        </div>

        <div class="quick-actions">
            <h3>⚡ أسئلة سريعة جاهزة</h3>
            <button class="prompt-btn" onclick="sendQuickPrompt('عايز أجهز باكدج عروسة متكامل بميزانية 20,000 ج.م من أطقم الجرانيت والصواني')">
                👰 تجهيز باكدج عروسة بميزانية
            </button>
            <button class="prompt-btn" onclick="sendQuickPrompt('إيه أقل 5 فروع في المبيعات لشهر أكتوبر حسب بيانات النظام؟')">
                📊 أقل فروع المبيعات لشهر أكتوبر
            </button>
            <button class="prompt-btn" onclick="sendQuickPrompt('إيه المنتجات المتوفرة حالياً في المستودعات والأسعار الرسمية؟')">
                📦 قائمة المنتجات والأسعار الرسمية
            </button>
            <button class="prompt-btn" onclick="sendQuickPrompt('ما هي مميزات أطقم الجرانيت الصحي 4 مم لشركة الأهرام مقارنة بغيرها؟')">
                🍳 مميزات طقم الجرانيت الصحي 4مم
            </button>
            <button class="prompt-btn" onclick="sendQuickPrompt('إيه المنتجات اللي ناقصة في فرع سيدي جابر ومحتاجة تحويل فوري؟')">
                🚚 نواقص فرع سيدي جابر
            </button>
        </div>

        <a href="/odoo" class="nav-back-btn">⬅️ العودة إلى لوحة تحكم أودو</a>
    </div>

    <!-- Main Chat Area -->
    <div class="chat-container">
        <div class="chat-header">
            <h2>💬 محادثة مباشرة مع الذكاء الاصطناعي (AI Chatbot)</h2>
            <span style="font-size: 12px; color: #94a3b8;">قاعدة البيانات: odoo20</span>
        </div>

        <div class="chat-messages" id="chatMessages">
            <!-- Initial Welcome Message -->
            <div class="message-row bot">
                <div class="avatar bot">🤖</div>
                <div class="bubble">
                    <p><strong>أهلاً بك في المساعد الذكي التفاعلي لشركة الأهرام للأدوات المنزلية! 🍳</strong></p>
                    <p style="margin-top: 6px;">أنا متصل مباشرة بقاعدة بيانات <strong>Odoo 20 Enterprise</strong> الحية ومدعوم بـ <strong>Google Gemini Flash</strong> مجاناً وبدون أي رصيد IAP.</p>
                    <p style="margin-top: 6px;">يمكنك سؤالي عن أي شيء في العمل: <em>تجهيز باقات العرائس، أرصدة المنتجات في الفروع، أسعار أطقم الجرانيت، أو تحليلات المبيعات</em>. كيف يمكنني خدمتك اليوم؟</p>
                    <span class="time-tag">الآن</span>
                </div>
            </div>

            <!-- Typing indicator -->
            <div class="typing-indicator" id="typingIndicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>

        <!-- Chat Input -->
        <div class="chat-input-area">
            <form class="input-form" id="chatForm" onsubmit="handleSend(event)">
                <input 
                    type="text" 
                    class="chat-input" 
                    id="chatInput" 
                    placeholder="اكتب استفسارك هنا وسيقوم الذكاء الاصطناعي بالبحث في قاعدة البيانات والرد فوراً..."
                    autocomplete="off"
                    required
                />
                <button type="submit" class="send-btn" id="sendBtn">
                    <span>إرسال</span>
                    <span>🚀</span>
                </button>
            </form>
        </div>
    </div>

    <script>
        const chatMessages = document.getElementById('chatMessages');
        const chatInput = document.getElementById('chatInput');
        const sendBtn = document.getElementById('sendBtn');
        const typingIndicator = document.getElementById('typingIndicator');

        let conversationHistory = [];

        function scrollToBottom() {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        function appendMessage(sender, htmlContent) {
            const row = document.createElement('div');
            row.className = `message-row ${sender}`;

            const avatar = document.createElement('div');
            avatar.className = `avatar ${sender}`;
            avatar.innerHTML = sender === 'user' ? '👤' : '🤖';

            const bubble = document.createElement('div');
            bubble.className = 'bubble';
            bubble.innerHTML = htmlContent;

            const timeTag = document.createElement('span');
            timeTag.className = 'time-tag';
            timeTag.innerText = new Date().toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
            bubble.appendChild(timeTag);

            row.appendChild(avatar);
            row.appendChild(bubble);

            // Insert before typing indicator
            chatMessages.insertBefore(row, typingIndicator);
            scrollToBottom();
        }

        async function handleSend(e) {
            if (e) e.preventDefault();
            const text = chatInput.value.trim();
            if (!text) return;

            // Clear input & disable send
            chatInput.value = '';
            chatInput.disabled = true;
            sendBtn.disabled = true;

            // Render User Message
            appendMessage('user', `<p>${escapeHtml(text)}</p>`);

            // Show Typing Indicator
            typingIndicator.style.display = 'flex';
            scrollToBottom();

            try {
                // Call Odoo Backend REST API
                const response = await fetch('/api/alahram/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        question: text,
                        history: conversationHistory
                    })
                });

                const data = await response.json();
                typingIndicator.style.display = 'none';

                if (data.status === 'success') {
                    appendMessage('bot', data.html || data.reply);
                    conversationHistory.push({ role: 'user', text: text });
                    conversationHistory.push({ role: 'model', text: data.reply });
                } else {
                    appendMessage('bot', `<p style="color: #f87171;">⚠️ ${data.message || 'حدث خطأ غير متوقع'}</p>`);
                }
            } catch (err) {
                typingIndicator.style.display = 'none';
                appendMessage('bot', `<p style="color: #f87171;">تعذر الاتصال بالخادم: ${err.message}</p>`);
            } finally {
                chatInput.disabled = false;
                sendBtn.disabled = false;
                chatInput.focus();
                scrollToBottom();
            }
        }

        function sendQuickPrompt(promptText) {
            chatInput.value = promptText;
            handleSend();
        }

        function escapeHtml(text) {
            return text
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }
    </script>
</body>
</html>"""
        return html_page
