import { SESSION_READ_FIELDS } from '@aypatech_ai_agent/ai/chat/session/use_ai_session';

if (!SESSION_READ_FIELDS.includes('resume_at')) {
    SESSION_READ_FIELDS.push('resume_at');
}
