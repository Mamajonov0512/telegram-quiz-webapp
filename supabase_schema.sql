-- ====================================================================
-- SUPABASE POSTGRESQL SCHEMA FOR TELEGRAM QUIZ WEB APP
-- ====================================================================
-- Ushbu SQL kodini Supabase boshqaruv panelidagi "SQL Editor" bo'limida
-- ishga tushiring (Run tugmasini bosing).
-- ====================================================================

-- 1. Allowed Users (Ruxsat berilgan foydalanuvchilar jadvali)
CREATE TABLE IF NOT EXISTS allowed_users (
    telegram_id BIGINT PRIMARY KEY,
    full_name TEXT DEFAULT '',
    username TEXT DEFAULT '',
    added_by BIGINT DEFAULT 0,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    is_active INTEGER DEFAULT 1,
    notes TEXT DEFAULT '',
    allowed_sections TEXT DEFAULT 'ALL'
);

CREATE INDEX IF NOT EXISTS idx_allowed_users_active ON allowed_users(is_active);

-- 2. Questions (Savollar bazasi)
CREATE TABLE IF NOT EXISTS questions (
    id BIGSERIAL PRIMARY KEY,
    question_text TEXT NOT NULL,
    option_a TEXT NOT NULL,
    option_b TEXT NOT NULL,
    option_c TEXT NOT NULL,
    option_d TEXT NOT NULL,
    correct_option VARCHAR(10) NOT NULL,
    explanation TEXT DEFAULT '',
    category TEXT DEFAULT 'Umumiy',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_questions_category ON questions(category);

-- 3. Test Results (Topshirilgan test natijalari)
CREATE TABLE IF NOT EXISTS test_results (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    full_name TEXT DEFAULT '',
    username TEXT DEFAULT '',
    total_questions INTEGER NOT NULL,
    correct_answers INTEGER NOT NULL,
    wrong_answers INTEGER NOT NULL,
    score_percentage DOUBLE PRECISION NOT NULL,
    time_spent_seconds INTEGER NOT NULL,
    completed_at TIMESTAMPTZ DEFAULT NOW(),
    answers_json TEXT DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_test_results_telegram_id ON test_results(telegram_id);
CREATE INDEX IF NOT EXISTS idx_test_results_completed_at ON test_results(completed_at DESC);

-- 4. Settings (Platforma umumiy sozlamalari)
CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR(255) PRIMARY KEY,
    value TEXT NOT NULL
);

-- 5. Test Sessions (Faol test sessiyalari va aralashtirilgan savollar)
CREATE TABLE IF NOT EXISTS test_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    category TEXT DEFAULT 'Barchasi',
    questions_count INTEGER NOT NULL,
    duration_minutes INTEGER NOT NULL,
    session_data TEXT NOT NULL,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    is_submitted INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_test_sessions_telegram_id ON test_sessions(telegram_id);

-- 6. Sections (Bo'limlar jadvali)
CREATE TABLE IF NOT EXISTS sections (
    id BIGSERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sections_name ON sections(name);

-- 7. Boshlang'ich sozlamalarni kiritish
INSERT INTO settings (key, value) VALUES
    ('whitelist_enabled', 'true'),
    ('questions_per_test', '50'),
    ('duration_minutes', '50'),
    ('pass_percentage', '60'),
    ('shuffle_questions', 'true'),
    ('shuffle_options', 'true'),
    ('anti_cheat_enabled', 'true'),
    ('category_filter_enabled', 'true'),
    ('max_questions_limit', '500')
ON CONFLICT (key) DO NOTHING;
