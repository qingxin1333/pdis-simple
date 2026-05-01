import datetime
import json
import os
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _pbkdf2_sha256(password: str, iterations: int = 260_000) -> str:
    import hashlib
    import secrets

    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${dk.hex()}"


def _verify_pbkdf2_sha256(password: str, password_hash: str) -> bool:
    import hashlib

    try:
        parts = password_hash.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        stored_dk = parts[3]
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return dk.hex() == stored_dk
    except Exception:
        return False


def _vector_literal(vec: List[float]) -> str:
    return "[" + ",".join(f"{float(x):.8f}" for x in vec) + "]"


@dataclass(frozen=True)
class DbUser:
    id: str
    email: str
    display_name: str


class PostgresStore:
    def __init__(self, database_url: str):
        self.database_url = database_url
        try:
            import psycopg2  # type: ignore
            from psycopg2.extras import RealDictCursor  # type: ignore
        except Exception as e:
            raise RuntimeError("缺少 PostgreSQL 驱动：请安装 psycopg2-binary。") from e

        self._psycopg2 = psycopg2
        self._RealDictCursor = RealDictCursor

    def _connect(self):
        return self._psycopg2.connect(self.database_url)

    def ensure_schema(self) -> None:
        ddl = """
        CREATE EXTENSION IF NOT EXISTS vector;

        CREATE TABLE IF NOT EXISTS app_user (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          email text NOT NULL UNIQUE,
          password_hash text NOT NULL,
          display_name text NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS auth_session (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL,
          created_at timestamptz NOT NULL DEFAULT now(),
          expires_at timestamptz NOT NULL,
          revoked_at timestamptz,
          CONSTRAINT auth_session_user_id_fkey FOREIGN KEY (user_id) REFERENCES app_user(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS chat_session (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id uuid NOT NULL,
          mode text NOT NULL CHECK (mode IN ('SMART_ANALYSIS', 'RELATION_MGMT', 'BEHAVIOR_PRED', 'DECISION_ASSIST')),
          title text,
          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT chat_session_user_id_fkey FOREIGN KEY (user_id) REFERENCES app_user(id) ON DELETE CASCADE
        );

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

        CREATE INDEX IF NOT EXISTS idx_memory_chunk_user_kind_time
          ON memory_chunk (user_id, kind, created_at DESC);

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
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(ddl)

    def ensure_default_user(self, email: str, display_name: str) -> DbUser:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=self._RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, email, display_name FROM app_user WHERE email=%s LIMIT 1",
                    (email,),
                )
                row = cur.fetchone()
                if row:
                    return DbUser(
                        id=str(row["id"]),
                        email=row["email"],
                        display_name=row["display_name"],
                    )

                user_id = str(uuid.uuid4())
                password_hash = _pbkdf2_sha256(os.getenv("PDIS_DEFAULT_USER_PASSWORD", "pdis-local"))
                now = _now()
                cur.execute(
                    """
                    INSERT INTO app_user (id, email, password_hash, display_name, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (user_id, email, password_hash, display_name, now, now),
                )
                return DbUser(id=user_id, email=email, display_name=display_name)

    def register_user(self, email: str, password: str, display_name: str) -> DbUser:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=self._RealDictCursor) as cur:
                cur.execute(
                    "SELECT id FROM app_user WHERE email=%s LIMIT 1",
                    (email,),
                )
                if cur.fetchone():
                    raise ValueError("邮箱已被注册")

                user_id = str(uuid.uuid4())
                password_hash = _pbkdf2_sha256(password)
                now = _now()
                cur.execute(
                    """
                    INSERT INTO app_user (id, email, password_hash, display_name, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (user_id, email, password_hash, display_name, now, now),
                )
                return DbUser(id=user_id, email=email, display_name=display_name)

    def verify_user(self, email: str, password: str) -> Optional[DbUser]:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=self._RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, email, password_hash, display_name FROM app_user WHERE email=%s LIMIT 1",
                    (email,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                if not _verify_pbkdf2_sha256(password, row["password_hash"]):
                    return None
                return DbUser(
                    id=str(row["id"]),
                    email=row["email"],
                    display_name=row["display_name"],
                )

    def create_session(self, user_id: str, expires_hours: int = 24) -> str:
        session_id = str(uuid.uuid4())
        now = _now()
        expires_at = now + datetime.timedelta(hours=expires_hours)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO auth_session (id, user_id, created_at, expires_at)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (session_id, user_id, now, expires_at),
                )
        return session_id

    def get_session_user(self, session_id: str) -> Optional[DbUser]:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=self._RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT s.user_id, u.email, u.display_name
                    FROM auth_session s
                    JOIN app_user u ON s.user_id = u.id
                    WHERE s.id = %s
                      AND s.expires_at > now()
                      AND s.revoked_at IS NULL
                    LIMIT 1
                    """,
                    (session_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return DbUser(
                    id=str(row["user_id"]),
                    email=row["email"],
                    display_name=row["display_name"],
                )

    def revoke_session(self, session_id: str) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE auth_session SET revoked_at = now() WHERE id = %s",
                    (session_id,),
                )
                return cur.rowcount > 0

    def get_person_profile(self, user_id: str, person_key: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=self._RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT p.id AS person_id, p.person_key, p.display_name, p.relationship, p.role,
                           v.version_no, v.mbti_type, v.mbti_confidence, v.portrait
                    FROM person_profile p
                    LEFT JOIN LATERAL (
                      SELECT *
                      FROM person_profile_version
                      WHERE person_id = p.id
                      ORDER BY version_no DESC
                      LIMIT 1
                    ) v ON true
                    WHERE p.user_id=%s AND p.person_key=%s
                    LIMIT 1
                    """,
                    (user_id, person_key),
                )
                row = cur.fetchone()
                if not row:
                    return None
                portrait = row.get("portrait")
                if isinstance(portrait, str):
                    try:
                        portrait = json.loads(portrait)
                    except Exception:
                        portrait = {}
                row["portrait"] = portrait or {}
                return dict(row)

    def upsert_person_profile(
        self,
        user_id: str,
        person_key: str,
        display_name: str,
        relationship: Optional[str] = None,
        role: Optional[str] = None,
    ) -> str:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=self._RealDictCursor) as cur:
                cur.execute(
                    "SELECT id FROM person_profile WHERE user_id=%s AND person_key=%s LIMIT 1",
                    (user_id, person_key),
                )
                row = cur.fetchone()
                now = _now()
                if row:
                    person_id = str(row["id"])
                    cur.execute(
                        """
                        UPDATE person_profile
                        SET display_name=%s, relationship=%s, role=%s, updated_at=%s
                        WHERE id=%s
                        """,
                        (display_name, relationship, role, now, person_id),
                    )
                    return person_id

                person_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO person_profile (id, user_id, person_key, display_name, relationship, role, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (person_id, user_id, person_key, display_name, relationship, role, now, now),
                )
                return person_id

    def insert_person_profile_version(
        self,
        person_id: str,
        portrait: Dict[str, Any],
        mbti_type: Optional[str],
        mbti_confidence: Optional[float],
        portrait_embedding: Optional[List[float]] = None,
    ) -> Tuple[str, int]:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=self._RealDictCursor) as cur:
                cur.execute(
                    "SELECT COALESCE(MAX(version_no), 0) AS v FROM person_profile_version WHERE person_id=%s",
                    (person_id,),
                )
                row = cur.fetchone()
                next_v = int(row["v"]) + 1
                version_id = str(uuid.uuid4())
                now = _now()

                if portrait_embedding:
                    vec_literal = _vector_literal(portrait_embedding)
                    cur.execute(
                        """
                        INSERT INTO person_profile_version
                          (id, person_id, version_no, mbti_type, mbti_confidence, portrait, portrait_embedding, created_at)
                        VALUES
                          (%s, %s, %s, %s, %s, %s, %s::vector, %s)
                        """,
                        (
                            version_id,
                            person_id,
                            next_v,
                            mbti_type,
                            mbti_confidence,
                            json.dumps(portrait, ensure_ascii=False),
                            vec_literal,
                            now,
                        ),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO person_profile_version
                          (id, person_id, version_no, mbti_type, mbti_confidence, portrait, created_at)
                        VALUES
                          (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            version_id,
                            person_id,
                            next_v,
                            mbti_type,
                            mbti_confidence,
                            json.dumps(portrait, ensure_ascii=False),
                            now,
                        ),
                    )

                return version_id, next_v

    def insert_decision_record(
        self,
        user_id: str,
        scenario_summary: str,
        user_input: str,
        structured_result: Dict[str, Any],
        persons_involved: Any,
        model_trace: Optional[Dict[str, Any]] = None,
    ) -> str:
        decision_id = str(uuid.uuid4())
        now = _now()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO decision_record
                      (id, user_id, user_input, scenario_summary, persons_involved, feasibility, confidence,
                       key_reasons, execution_plan, risks, suggested_scripts, model_trace, created_at)
                    VALUES
                      (%s, %s, %s, %s, %s::jsonb, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s)
                    """,
                    (
                        decision_id,
                        user_id,
                        user_input,
                        scenario_summary,
                        json.dumps(persons_involved, ensure_ascii=False),
                        structured_result.get("feasibility", ""),
                        float(structured_result.get("confidence") or 0),
                        json.dumps(structured_result.get("key_reasons", []), ensure_ascii=False),
                        json.dumps(structured_result.get("execution_plan", []), ensure_ascii=False),
                        json.dumps(structured_result.get("risks", []), ensure_ascii=False),
                        json.dumps(structured_result.get("suggested_scripts", []), ensure_ascii=False),
                        json.dumps(model_trace or {}, ensure_ascii=False),
                        now,
                    ),
                )
        return decision_id

    def upsert_memory_chunk(
        self,
        user_id: str,
        kind: str,
        content: str,
        embedding: Optional[List[float]] = None,
        ref_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        memory_id = str(uuid.uuid4())
        now = _now()
        meta = metadata or {}

        with self._connect() as conn:
            with conn.cursor() as cur:
                if embedding:
                    vec_literal = _vector_literal(embedding)
                    cur.execute(
                        """
                        INSERT INTO memory_chunk (id, user_id, kind, ref_id, content, metadata, embedding, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::vector, %s)
                        """,
                        (
                            memory_id,
                            user_id,
                            kind,
                            ref_id,
                            content,
                            json.dumps(meta, ensure_ascii=False),
                            vec_literal,
                            now,
                        ),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO memory_chunk (id, user_id, kind, ref_id, content, metadata, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
                        """,
                        (
                            memory_id,
                            user_id,
                            kind,
                            ref_id,
                            content,
                            json.dumps(meta, ensure_ascii=False),
                            now,
                        ),
                    )
        return memory_id

    def semantic_search(
        self,
        user_id: str,
        query_embedding: List[float],
        kind: Optional[str] = None,
        top_k: int = 6,
    ) -> List[Dict[str, Any]]:
        vec_literal = _vector_literal(query_embedding)
        sql = """
        SELECT id, kind, ref_id, content, metadata, created_at,
               (embedding <=> %s::vector) AS distance
        FROM memory_chunk
        WHERE user_id=%s
          AND embedding IS NOT NULL
        """
        params: List[Any] = [vec_literal, user_id]
        if kind:
            sql += " AND kind=%s"
            params.append(kind)
        sql += " ORDER BY embedding <=> %s::vector LIMIT %s"
        params.extend([vec_literal, top_k])

        with self._connect() as conn:
            with conn.cursor(cursor_factory=self._RealDictCursor) as cur:
                cur.execute(sql, tuple(params))
                rows = cur.fetchall() or []
                return [dict(r) for r in rows]

