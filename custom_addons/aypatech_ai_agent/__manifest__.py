# -*- coding: utf-8 -*-
{
    "name": "AI Agent - AI Chatbot, GPT, Claude, Gemini & MCP Server",
    "summary": "AI chat agents, MCP server and client, skills, automation, schedules and scheduled reports, on native Odoo data",
    "description": """
AI Agent
=================
Multi-provider AI chat agents that read and act on your own Odoo data:
an MCP server and client, reusable skills, chatter @-mentions, server-action
and schedule-driven automation, scheduled reports delivered by e-mail and
Telegram, a cost and usage dashboard, and voice input and output. No
WooCommerce, no BI: just the AI agent platform, standalone.
    """,
    "version": "20.0.1.0.0",
    "category": "Productivity",
    "author": "Saman Abedi",
    "maintainer": "Saman Abedi",
    "website": "https://itisabedi.com",
    "support": "itisabedi@outlook.com",
    "price": 0,
    "currency": "EUR",
    "license": "OPL-1",
    "images": ["static/description/banner.png"],
    "depends": [
        "base",
        "base_setup",
        "mail",
        "base_automation",
        "web",
        "bus",
    ],
    "external_dependencies": {
        "python": [
            "requests",
            "croniter",
        ],
    },
    "data": [
        "mcp/security/ir.access.csv",
        "mcp/data/tool.xml",
        "mcp/data/prompt.xml",
        "mcp/views/key.xml",
        "mcp/views/generate_key.xml",
        "mcp/views/show_key.xml",
        "mcp/views/log.xml",
        "mcp/views/notification.xml",
        "mcp/views/session.xml",
        "mcp/views/tool.xml",
        "mcp/views/prompt.xml",
        "mcp/views/connect.xml",
        "mcp/views/res_users.xml",
        "mcp/views/playground.xml",

        "mcp_client/security/ir.access.csv",
        "mcp_client/views/mcp_client_server.xml",

        "ai/security/ir.access.csv",
        "ai/data/provider.xml",
        "ai/data/model.xml",
        "ai/data/agent.xml",
        "ai/data/ir_model.xml",
        "ai/data/ir_cron.xml",
        "ai/data/space.xml",

        "ai/views/ir_model.xml",
        "ai/views/provider.xml",
        "ai/views/model.xml",
        "ai/views/agent.xml",
        "ai/views/approval.xml",
        "ai/views/mcp_tool_log.xml",
        "ai/views/space.xml",
        "ai/views/session.xml",
        "ai/views/chat.xml",
        "ai/views/res_users.xml",

        "skills/security/ir.access.csv",

        "skills/data/skill.xml",
        "skills/views/skill.xml",

        "chatter/data/space.xml",
        "chatter/data/skill.xml",
        "chatter/views/ai_agent.xml",
        "chatter/views/skill.xml",
        "chatter/views/mail_compose_message.xml",

        "automation/data/ir_actions.xml",
        "automation/views/ir_actions_server.xml",
        "automation/views/base_automation.xml",

        "schedule/security/ir.access.csv",
        "schedule/data/space.xml",
        "schedule/views/schedule.xml",
        "schedule/views/session.xml",

        "reports/security/ir.access.csv",
        "reports/data/ir_cron.xml",
        "reports/report/report_templates.xml",
        "reports/views/report_schedule.xml",
        "reports/views/report_run.xml",

        "dashboard/views/usage_dashboard.xml",

        "ai/data/defaults.xml",
        "ai/views/res_config_settings.xml",
        "views/menus.xml",
        "views/app_templates.xml",
    ],
    "installable": True,
    "application": True,
    "demo": [
        "ai/demo/agent.xml",
        "ai/demo/session.xml",
        "skills/demo/skill.xml",
        "automation/demo/ir_actions_server.xml",
        "automation/demo/base_automation.xml",
        "schedule/demo/schedule.xml",
        "schedule/demo/session.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "aypatech_ai_agent/static/src/mcp/core/message.xml",
            "aypatech_ai_agent/static/src/mcp/playground/**/*",
            "aypatech_ai_agent/static/lib/ai/markdown-it/markdown-it.js",
            "aypatech_ai_agent/static/src/ai/chat/**/*",
            "aypatech_ai_agent/static/src/ai/components/**/*",
            "aypatech_ai_agent/static/src/ai/core/**/*",
            "aypatech_ai_agent/static/src/ai/views/adjust.js",
            "aypatech_ai_agent/static/src/ai/views/context.js",
            "aypatech_ai_agent/static/src/ai/views/fields/**/*",
            "aypatech_ai_agent/static/src/ai/views/form/**/*",
            "aypatech_ai_agent/static/src/ai/views/kanban/**/*",
            "aypatech_ai_agent/static/src/ai/views/list/**/*",
            "aypatech_ai_agent/static/src/ai/webclient/**/*",
            ("remove", "aypatech_ai_agent/static/src/ai/**/*.dark.scss"),
            "aypatech_ai_agent/static/src/skills/**/*",
            "aypatech_ai_agent/static/src/chatter/**/*",
            "aypatech_ai_agent/static/src/schedule/views/fields/**/*",
            "aypatech_ai_agent/static/src/schedule/chat/**/*",
        ],
        "web.assets_backend_lazy": [
            "aypatech_ai_agent/static/src/ai/views/graph/**/*",
            "aypatech_ai_agent/static/src/ai/views/pivot/**/*",
        ],
        "web.assets_web_dark": [
            "aypatech_ai_agent/static/src/ai/**/*.dark.scss",
        ],
        "web.assets_tests": [
            "aypatech_ai_agent/static/tests/mcp/tours/**/*",
            "aypatech_ai_agent/static/tests/chatter/tours/chatter_tour.js",
            "aypatech_ai_agent/static/tests/schedule/tours/schedule_tour.js",
        ],
        "web.assets_unit_tests": [
            "aypatech_ai_agent/static/tests/mcp/**/*.test.js",
            "aypatech_ai_agent/static/tests/ai/**/*.test.js",
            "aypatech_ai_agent/static/tests/skills/**/*.test.js",
            "aypatech_ai_agent/static/tests/chatter/**/*.test.js",
            "aypatech_ai_agent/static/tests/schedule/**/*.test.js",
        ],
    },
}
