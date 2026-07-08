-- ============================================================
-- 英语学习平台 - 完整建表语句 (PostgreSQL)
-- 使用方法：
--   1. 创建数据库: CREATE DATABASE wanna-word;
--   2. 执行此文件:  \i db.sql
--   3. 初始化数据:  cd learn-service && python -m app.init_db
-- ============================================================

-- ============================================================
-- 1. 用户表
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(100) NOT NULL UNIQUE,
    nick_name     VARCHAR(100) NOT NULL DEFAULT '',
    password_hash VARCHAR(255) NOT NULL DEFAULT '',
    avatar_base64 TEXT,
    role          VARCHAR(20) NOT NULL DEFAULT 'user',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 2. 词库表（支持父子层级）
-- ============================================================
CREATE TABLE IF NOT EXISTS word_books (
    id         SERIAL PRIMARY KEY,
    parent_id  INTEGER REFERENCES word_books(id) ON DELETE SET NULL,
    name       VARCHAR(120) NOT NULL,
    type       INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 3. 单词条目表
-- ============================================================
CREATE TABLE IF NOT EXISTS word_entries (
    id              SERIAL PRIMARY KEY,
    book_id         INTEGER NOT NULL REFERENCES word_books(id) ON DELETE CASCADE,
    source_entry_id INTEGER,
    word            VARCHAR(120) NOT NULL,
    phonetic0       VARCHAR(120),
    phonetic1       VARCHAR(120),
    synos           JSONB NOT NULL DEFAULT '[]',
    etymology       JSONB NOT NULL DEFAULT '[]',
    inflections     JSONB,
    e2e             JSONB,
    exams_src       JSONB,
    rel_words       JSONB,
    lang_type       VARCHAR(16) NOT NULL DEFAULT 'en',
    trans           JSONB NOT NULL DEFAULT '[]',
    sentences       JSONB NOT NULL DEFAULT '[]',
    phrases         JSONB NOT NULL DEFAULT '[]',
    entry_type      VARCHAR(20) NOT NULL DEFAULT 'word',
    sequence        INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 4. 文章本表（支持父子层级）
-- ============================================================
CREATE TABLE IF NOT EXISTS article_books (
    id         SERIAL PRIMARY KEY,
    parent_id  INTEGER REFERENCES article_books(id) ON DELETE SET NULL,
    name       VARCHAR(120) NOT NULL,
    type       INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 5. 文章表
-- ============================================================
CREATE TABLE IF NOT EXISTS article (
    id           SERIAL PRIMARY KEY,
    parent_id    INTEGER REFERENCES article_books(id) ON DELETE SET NULL,
    type         VARCHAR(30) NOT NULL DEFAULT 'story',
    input        JSONB NOT NULL DEFAULT '{}',
    title_en     VARCHAR(255) NOT NULL DEFAULT '',
    title_zh     VARCHAR(255) NOT NULL DEFAULT '',
    content_en   TEXT NOT NULL DEFAULT '',
    content_zh   TEXT NOT NULL DEFAULT '',
    audio_src    VARCHAR(512) NOT NULL DEFAULT '',
    lrc_position JSONB,
    question     JSONB,
    name_list    JSONB,
    quote        JSONB,
    model        VARCHAR(100) NOT NULL DEFAULT 'deepseek-chat',
    gen_type     VARCHAR(20),
    gen_input    JSONB,
    ai_response  JSONB,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 6. AI 配置表
-- ============================================================
CREATE TABLE IF NOT EXISTS ai_configs (
    id              SERIAL PRIMARY KEY,
    "group"         VARCHAR(20),
    base_url        VARCHAR(255),
    api_key         VARCHAR(255),
    model           VARCHAR(50) NOT NULL DEFAULT 'deepseek-chat',
    is_default_mode BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 索引
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_word_entries_book_id ON word_entries(book_id);
CREATE INDEX IF NOT EXISTS idx_word_entries_word    ON word_entries(word);
CREATE INDEX IF NOT EXISTS idx_word_books_parent_id ON word_books(parent_id);
CREATE INDEX IF NOT EXISTS idx_article_books_parent_id ON article_books(parent_id);
CREATE INDEX IF NOT EXISTS idx_article_parent_id    ON article(parent_id);

-- ============================================================
-- 更新时间触发器
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN SELECT unnest(ARRAY['users', 'word_books', 'word_entries', 'article_books', 'article', 'ai_configs'])
    LOOP
        EXECUTE format(
            'CREATE TRIGGER set_updated_at BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()',
            tbl
        );
    END LOOP;
END;
$$;

-- ============================================================
-- 初始数据：默认管理员 admin
-- 密码由 Python 生成，请运行以下命令完成初始化：
--   cd learn-service && python -m app.init_db
-- ============================================================
-- INSERT INTO users (username, nick_name, password_hash, role)
-- VALUES ('admin', '管理员', '<bcrypt_hash>', 'admin');
-- SELECT setval('users_id_seq', COALESCE((SELECT MAX(id) FROM users), 1));

-- ============================================================
-- 使用示例：插入数据后同步自增序列
-- ============================================================
-- SELECT setval('users_id_seq',        COALESCE((SELECT MAX(id) FROM users),        1));
-- SELECT setval('word_books_id_seq',   COALESCE((SELECT MAX(id) FROM word_books),   1));
-- SELECT setval('word_entries_id_seq', COALESCE((SELECT MAX(id) FROM word_entries), 1));
-- SELECT setval('article_books_id_seq',COALESCE((SELECT MAX(id) FROM article_books),1));
-- SELECT setval('article_id_seq',      COALESCE((SELECT MAX(id) FROM article),      1));
-- SELECT setval('ai_configs_id_seq',   COALESCE((SELECT MAX(id) FROM ai_configs),   1));
