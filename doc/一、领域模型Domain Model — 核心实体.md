# 一、领域模型（Domain Model — 核心实体）

## 1、Person（person_profile）

- 概念：与用户有关的“人”的长期档案。每个人用不变的 `id` 唯一标识；其它属性（姓名、别名、岗位、标签、说明）可修改。
- 主要用途：作为分析时检索与上下文拼装的事实源。
- 关键属性（语义）：
  - `id`（UUID）— 主键，不变
  - `name`（文本）— 当前显示名（可变）
  - `aliases`（文本数组 / jsonb）— 别名集合
  - `profile_json`（jsonb）— 侧写/附加结构（性格标签、常见反应、已观测模式等）
  - `deleted`（smallint）— 0/1 软删除
  - `created_time`, `updated_time`

## 2、Event / Fact（event_record）

- 概念：原始事实、对话、邮件片段、现场观察等“发生过的事情”。事件一经记录，原文不应被覆盖（可追加注释），但允许 metadata 更新（例如关联人物）。
- 主要用途：用于向量索引（检索）、提供证据链。
- 关键属性（语义）：
  - `id`（UUID）
  - `title`（短文本，可选）
  - `event_date`（timestamp）— 事件发生时间或记录时间
  - `text`（text）— 原始文本（不可随意替换）
  - `person_id`（UUID 可空）— 关联人
  - `metadata`（jsonb）— 额外字段（source、author、tags、sensitivity）
  - `embedding_id`（nullable, for vector mapping）或单独向量表引用
  - `deleted`（smallint）— 0/1
  - `created_time`, `updated_time`

## 3、Analysis（analysis_result）

- 概念：一次用户输入触发的完整分析记录（输入、检索上下文、模型 prompt、模型输出、模型元数据、cloud调用记录、repair次 数等）。**是 append-only 的核心资产**（可以更新 status 或追加 notes，但不要覆盖历史关键字段）。
- 主要用途：可回溯地重现每次分析，供审计与检索参考。
- 关键属性（语义）：
  - `id`（UUID）
  - `scenario_text`（text）— 用户原始输入
  - `context_overrides`（jsonb|null）— 用户追加/覆盖上下文
  - `matched_profiles_ids`（uuid[] 或 jsonb）— 当次匹配的 profile id 列表（快照）
  - `retrieved_event_ids`（uuid[] 或 jsonb）
  - `prompt_summary`（text）或 `prompt_template_id`（若模板化）
  - `json_output`（jsonb）— 结构化输出
  - `text_output`（text）— 人类摘要
  - `model_meta`（jsonb）— { model_name, model_version, local_or_cloud }
  - `confidence_score`（float）
  - `repair_attempts`（int）
  - `used_cloud`（smallint 0/1）
  - `cloud_calls_meta`（jsonb|null）
  - `status`（text enum：processing/done/failed/requires_human_review）
  - `deleted`（smallint）— 0/1（按你要求保留）
  - `created_time`, `updated_time`
  - `notes`（jsonb array）— 后续追加说明（时间戳 + text）

## 4、Audit / Log（audit_log）

- 概念：append-only 审计流水，记录系统重要操作（analysis 创建、cloud consent、repair 尝试、delete/restore 操作、preference 更改等）。不可被普通 CRUD 改写。
- 主要用途：合规、回溯、调试。
- 关键属性：
  - `id`（UUID）
  - `action_type`（text）— 例如 analysis.create / cloud.consent / repair.attempt / profile.update / profile.delete
  - `entity_type`（text）— person/event/analysis/preferences
  - `entity_id`（uuid|null）
  - `payload_hash`（text|null）— 变更或模型 output 的哈希
  - `meta`（jsonb）— 任意结构化数据
  - `created_time`（timestamp）

## 5、System Preferences（system_preferences）

- 概念：本地系统配置（单用户存），包括 `allow_cloud` 等。
- 关键属性：
  - `id`（UUID）
  - `allow_cloud`（smallint 0/1）
  - `preferred_local_model`（text）
  - `updated_time`

> 备注：向量（embeddings）数据可以采用外部向量库（Qdrant）或 pgvector 扩展；在最小实现中只需在 `event_record` 写入 `embedding_id` 或在 `vector_store` 写向量，后期迁移方便。

------

# 二、生命周期（Lifecycle / 状态迁移规则）

> 说明：用整数 `deleted`（0 = 正常，1 = 删除/不可用）表示软删除。时间字段 `created_time/updated_time` 全表通用。

## 1、Person（person_profile）

- 初始：创建（deleted = 0）
- 可变：`name` / `aliases` / `profile_json` / `tags` 等可随时修改（`id` 不变）
- 删除：调用删除 API → `deleted = 1`, `deleted_at = now()`（仍保留关联 event 与 analysis）
- 恢复：将 `deleted = 0`（需要审计记录）
- 注意：修改记录应写 audit_log（action_type = profile.update）

## 2、Event（event_record）

- 初始：创建（deleted = 0）
- 不可覆写原文：`text` 为事实原文，原则上不直接覆盖（可新增 `metadata.edits[]` 或在 `notes` 追加更正）
- 允许变更：`person_id`、`metadata`、`tags` 等可更改
- 删除：软删除（deleted = 1）
- 恢复：可通过 admin 操作设置回 `deleted = 0`（写审计）

## 3、Analysis（analysis_result）

- 初始：创建，`status = processing`，`repair_attempts = 0`
- Repair Loop：若校验失败，后端增加 `repair_attempts++` 并保存每次尝试（写入 audit_log）
- 成功：`status = done`，写入 json_output/text_output、confidence、model_meta 等
- 失败：若达到最大尝试且无云 fallback → `status = requires_human_review` 或 `failed`（区分不可用 vs 需人工）
- 云 fallback：若用户同意并云调用成功 → 写 `used_cloud = 1` 与 `cloud_calls_meta`，并更新 status
- 删除：允许软删除（deleted = 1），但审计记录保留

## 4、Audit（audit_log）

- 永不过期、追加写入
- 不允许普通用户/普通 API 删除或修改（仅运维/DB 管理员有权限）

## 5、Preferences（system_preferences）

- 可更新（UI 设置），每次变更写入 audit_log（action_type = preferences.update）

------

# 三、最小数据库表（Postgres）——推荐建表 SQL（可直接用作初始建库）

> 说明：下列 SQL 为可直接执行的建表草案，使用 `uuid` 主键（`pgcrypto` 的 `gen_random_uuid()` 或 `uuid_generate_v4()`）。`deleted` 用 SMALLINT，默认 0；时间字段使用 `timestamp with time zone`。`jsonb` 用于半结构数据。根据你环境可微调。

```
-- =======================================================
-- 第一部分：环境准备 (需要以 postgres 超级用户运行)
-- =======================================================
-- 1. 创建数据库
-- 如果数据库已存在，这一步会报错，你可以手动忽略或先执行 
DROP DATABASE IF EXISTS pdis;
CREATE DATABASE pdis;

-- 2. 创建用户并设置密码
CREATE USER pdis_master WITH ENCRYPTED PASSWORD '123456';

-- 3. 授予数据库所有权限给该用户
GRANT ALL PRIVILEGES ON DATABASE pdis TO pdis_master;

-- 切换到新创建的数据库 (在 psql 命令行工具中使用 \c)
-- 如果你在 Navicat/DBeaver 中，请先手动连接新创建的 pdis，再执行下面的语句
\c pdis;

-- =======================================================
-- 第二部分：数据库内部初始化 (在 pdis 中执行)
-- =======================================================

-- 4. 启用 UUID 扩展
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 5. 确保该用户在 public schema 下有操作权限
GRANT ALL ON SCHEMA public TO pdis_master;

---------------------------------------------------------
-- 1. 人物档案表 (person_profile)
---------------------------------------------------------
CREATE TABLE person_profile (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  aliases jsonb DEFAULT '[]'::jsonb,
  profile_json jsonb DEFAULT '{}'::jsonb,
  tags text[] DEFAULT ARRAY[]::text[],
  sensitivity smallint DEFAULT 0,
  deleted smallint NOT NULL DEFAULT 0,
  created_time timestamptz NOT NULL DEFAULT now(),
  updated_time timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE person_profile IS '与用户有关的“人”的长期档案';
COMMENT ON COLUMN person_profile.name IS '当前显示名';
COMMENT ON COLUMN person_profile.profile_json IS '侧写（性格标签、常见反应等）';

---------------------------------------------------------
-- 2. 事件记录表 (event_record)
---------------------------------------------------------
CREATE TABLE event_record (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text,
  event_date timestamptz,
  text text NOT NULL,
  person_id uuid REFERENCES person_profile(id) ON DELETE SET NULL,
  metadata jsonb DEFAULT '{}'::jsonb,
  embedding_id text,
  sensitivity smallint DEFAULT 0,
  deleted smallint NOT NULL DEFAULT 0,
  created_time timestamptz NOT NULL DEFAULT now(),
  updated_time timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE event_record IS '原始事实、对话、观察等记录';

---------------------------------------------------------
-- 3. 分析结果表 (analysis_result)
---------------------------------------------------------
CREATE TABLE analysis_result (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_text text NOT NULL,
  context_overrides jsonb,
  matched_profiles jsonb DEFAULT '[]'::jsonb,
  retrieved_event_ids jsonb DEFAULT '[]'::jsonb,
  prompt_summary text,
  json_output jsonb,
  text_output text,
  model_meta jsonb,
  confidence_score double precision,
  repair_attempts int DEFAULT 0,
  used_cloud smallint DEFAULT 0,
  status text NOT NULL DEFAULT 'processing',
  deleted smallint NOT NULL DEFAULT 0,
  created_time timestamptz NOT NULL DEFAULT now(),
  updated_time timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE analysis_result IS 'AI 触发的分析记录快照';

---------------------------------------------------------
-- 4. 审计日志 (audit_log)
---------------------------------------------------------
CREATE TABLE audit_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  action_type text NOT NULL,
  entity_type text,
  entity_id uuid,
  payload_hash text,
  meta jsonb,
  created_time timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE audit_log IS '只读审计流水';

---------------------------------------------------------
-- 5. 系统配置 (system_preferences)
---------------------------------------------------------
CREATE TABLE system_preferences (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  key text UNIQUE,
  value jsonb,
  updated_time timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE system_preferences IS '系统全局配置项';

-- 插入默认配置
INSERT INTO system_preferences (key, value) VALUES
  ('allow_cloud', '{"value": false}'),
  ('preferred_local_model', '{"value": "qwen3-8b"}')
ON CONFLICT (key) DO NOTHING;

-- 6. 将所有新建表的权限授予该用户（防止权限缺失）
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO pdis_master;
```

### 设计要点与建议

1. **UUID 主键**：跨系统复制/迁移更方便。
2. **jsonb 用法**：对半结构化字段（profile_json、metadata、matched_profiles）使用 jsonb，方便后续迭代。
3. **deleted 为 smallint（0/1）**：按你要求实现软删除。查询默认需加 `WHERE deleted = 0`。
4. **时间字段**：`created_time`、`updated_time`；后端应在更新时维护 `updated_time`（或通过 trigger 维护）。
5. **审计表为 append-only**：应用层不允许 delete/update（DB 权限控制）。
6. **向量/embedding**：如采用 pgvector，可在 `event_record` 添加 `embedding vector` 字段；若使用外部 Qdrant，则存 `embedding_id` 并将 metadata（event_id）写入向量库。向量表可后置实现。
7. **索引**：按常用查询加索引（status、created_time、person_id、deleted 等）。
8. **权限**：大多数敏感操作（删除/restore/clear audit）仅允许 admin/运维；你的一期可仅在本地暴露 API。

------

```
-- 保证数据正确性、可用性、权限、安全
-- 确认扩展与权限
CREATE EXTENSION IF NOT EXISTS vector;
-- 为高频查询添加索引
CREATE INDEX idx_person_deleted ON person_profile(deleted);
CREATE INDEX idx_person_name ON person_profile USING gin (to_tsvector('simple', name));
CREATE INDEX idx_event_person ON event_record(person_id);
CREATE INDEX idx_event_deleted ON event_record(deleted);
CREATE INDEX idx_analysis_status_created ON analysis_result(status, created_time);
CREATE INDEX idx_audit_created ON audit_log(created_time);
-- 如果用 pgvector 在 event_record 增加向量列：
ALTER TABLE event_record ADD COLUMN IF NOT EXISTS embedding vector(1536); 
CREATE INDEX IF NOT EXISTS idx_event_embedding ON event_record USING ivfflat(embedding) WITH (lists = 100);
-- 保证 updated_time 自动维护（触发器）
CREATE OR REPLACE FUNCTION trigger_set_updated_time()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_time = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_person_updated_time
  BEFORE UPDATE ON person_profile
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_time();

CREATE TRIGGER trg_event_updated_time
  BEFORE UPDATE ON event_record
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_time();

CREATE TRIGGER trg_analysis_updated_time
  BEFORE UPDATE ON analysis_result
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_time();
```

## 五、你现在下一步**唯一正确的动作**

### Step 1：至少写 1 个 model（最小可用）

你先别一次写 5 个，我们先打通链路。

#### `app/db/models/person.py`

```
from sqlalchemy import Column, Text, SmallInteger, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from app.db.base import Base

class PersonProfile(Base):
    __tablename__ = "person_profile"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    profile_json = Column(JSONB, default=dict)
    deleted = Column(SmallInteger, nullable=False, default=0)
    created_time = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_time = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
```

并确保：

```
app/db/models/__init__.py   存在
```

------

### Step 2：验证 import（非常关键）

```
python -c "from app.db.models import person; print('OK')"
```

看到 `OK`，才能继续。

------

### Step 3：设置 DATABASE_URL（你已经会了）

```
export DATABASE_URL=postgresql+psycopg2://pdis_master:123456@127.0.0.1:5432/pdis
```

------

### Step 4：生成迁移（这一步才有意义）

```
alembic revision --autogenerate -m "baseline person"
```

alembic stamp head

生成完整 5 表 ORM，与当前数据库完全对齐（含索引 + vector）

pip install pgvector