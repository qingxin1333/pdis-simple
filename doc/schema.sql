-- PDIS 数据库建表语句
-- PostgreSQL 15+

-- 启用 vector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 用户表
CREATE TABLE IF NOT EXISTS app_user (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text NOT NULL UNIQUE,
  password_hash text NOT NULL,
  display_name text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- 认证会话表
CREATE TABLE IF NOT EXISTS auth_session (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL,
  revoked_at timestamptz,
  CONSTRAINT auth_session_user_id_fkey FOREIGN KEY (user_id) REFERENCES app_user(id) ON DELETE CASCADE
);

-- 聊天会话表
CREATE TABLE IF NOT EXISTS chat_session (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  mode text NOT NULL CHECK (mode IN ('SMART_ANALYSIS', 'RELATION_MGMT', 'BEHAVIOR_PRED', 'DECISION_ASSIST')),
  title text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT chat_session_user_id_fkey FOREIGN KEY (user_id) REFERENCES app_user(id) ON DELETE CASCADE
);

-- 聊天消息表
CREATE TABLE IF NOT EXISTS chat_message (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL,
  role text NOT NULL CHECK (role IN ('user', 'assistant', 'tool')),
  content text NOT NULL,
  tool_name text,
  tool_payload jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT chat_message_session_id_fkey FOREIGN KEY (session_id) REFERENCES chat_session(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chat_message_session_time ON chat_message (session_id, created_at);

-- 决策记录表
CREATE TABLE IF NOT EXISTS decision_record (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  session_id uuid,
  user_input text NOT NULL,
  scenario_summary text NOT NULL,
  persons_involved jsonb NOT NULL DEFAULT '[]'::jsonb,
  feasibility text NOT NULL CHECK (feasibility IN ('可行', '有条件可行', '不可行')),
  confidence float4 NOT NULL DEFAULT 0,
  key_reasons jsonb NOT NULL DEFAULT '[]'::jsonb,
  execution_plan jsonb NOT NULL DEFAULT '[]'::jsonb,
  risks jsonb NOT NULL DEFAULT '[]'::jsonb,
  suggested_scripts jsonb NOT NULL DEFAULT '[]'::jsonb,
  model_trace jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT decision_record_user_id_fkey FOREIGN KEY (user_id) REFERENCES app_user(id) ON DELETE CASCADE,
  CONSTRAINT decision_record_session_id_fkey FOREIGN KEY (session_id) REFERENCES chat_session(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_decision_record_user_time ON decision_record (user_id, created_at DESC);

-- 人物档案表
CREATE TABLE IF NOT EXISTS person_profile (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  person_key text NOT NULL,
  display_name text NOT NULL,
  relationship text,
  role text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT person_profile_user_id_fkey FOREIGN KEY (user_id) REFERENCES app_user(id) ON DELETE CASCADE,
  CONSTRAINT person_profile_user_id_person_key_key UNIQUE (user_id, person_key)
);

CREATE INDEX IF NOT EXISTS idx_person_profile_user_updated ON person_profile (user_id, updated_at DESC);

-- 人物档案版本表
CREATE TABLE IF NOT EXISTS person_profile_version (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id uuid NOT NULL,
  version_no int4 NOT NULL,
  mbti_type text,
  mbti_confidence float4,
  portrait jsonb NOT NULL,
  portrait_embedding vector(768),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT person_profile_version_person_id_fkey FOREIGN KEY (person_id) REFERENCES person_profile(id) ON DELETE CASCADE,
  CONSTRAINT person_profile_version_person_id_version_no_key UNIQUE (person_id, version_no)
);

-- 交互事件表
CREATE TABLE IF NOT EXISTS interaction_event (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  person_id uuid,
  title text NOT NULL,
  event_time timestamptz,
  content text NOT NULL,
  outcome text,
  source text,
  sensitivity bool NOT NULL DEFAULT true,
  embedding vector(768),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT interaction_event_user_id_fkey FOREIGN KEY (user_id) REFERENCES app_user(id) ON DELETE CASCADE,
  CONSTRAINT interaction_event_person_id_fkey FOREIGN KEY (person_id) REFERENCES person_profile(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_event_user_time ON interaction_event (user_id, created_at DESC);

-- 记忆块表
CREATE TABLE IF NOT EXISTS memory_chunk (
  id uuid PRIMARY KEY,
  user_id uuid NOT NULL,
  kind text NOT NULL,
  ref_id text NULL,
  content text NOT NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  embedding vector(768) NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_memory_chunk_user_kind_time ON memory_chunk (user_id, kind, created_at DESC);

-- 向量索引（HNSW）
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname = current_schema() AND indexname = 'idx_memory_embedding_hnsw'
  ) THEN
    EXECUTE 'CREATE INDEX idx_memory_embedding_hnsw ON memory_chunk USING hnsw (embedding vector_cosine_ops)';
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname = current_schema() AND indexname = 'idx_profile_version_embedding_hnsw'
  ) THEN
    EXECUTE 'CREATE INDEX idx_profile_version_embedding_hnsw ON person_profile_version USING hnsw (portrait_embedding vector_cosine_ops)';
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname = current_schema() AND indexname = 'idx_event_embedding_hnsw'
  ) THEN
    EXECUTE 'CREATE INDEX idx_event_embedding_hnsw ON interaction_event USING hnsw (embedding vector_cosine_ops)';
  END IF;
END$$;
