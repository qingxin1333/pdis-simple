# PDIS 技术栈使用流程文档

## 一、技术栈概览

PDIS项目采用以下技术栈：
- **Python** - 主要编程语言
- **FastAPI** - Web框架（规划中）
- **PostgreSQL + pgvector** - 数据库及向量扩展
- **本地Ollama大模型** - AI推理能力
- **Redis** - 任务队列/缓存（可选）

---

## 二、PostgreSQL + pgvector 向量数据库使用流程

### 2.1 数据库初始化与向量扩展

**代码位置**: `process/postgres_store.py` → `ensure_schema()` 方法

```python
def ensure_schema(self) -> None:
    ddl = """
    CREATE EXTENSION IF NOT EXISTS vector;  -- 启用pgvector扩展
    
    -- 创建人物档案版本表，包含768维向量字段
    CREATE TABLE IF NOT EXISTS person_profile_version (
      ...
      portrait_embedding vector(768),  -- 768维向量存储
      ...
    );
    
    -- 创建记忆块表，包含768维向量字段
    CREATE TABLE IF NOT EXISTS memory_chunk (
      ...
      embedding vector(768) NULL,  -- 768维向量存储
      ...
    );
    
    -- 创建HNSW索引用于高效向量检索
    CREATE INDEX idx_memory_embedding_hnsw 
      ON memory_chunk USING hnsw (embedding vector_cosine_ops);
    
    CREATE INDEX idx_profile_version_embedding_hnsw 
      ON person_profile_version USING hnsw (portrait_embedding vector_cosine_ops);
    """
```

**说明**：
- 启用PostgreSQL的vector扩展
- 创建包含768维向量字段的表
- 使用HNSW（Hierarchical Navigable Small World）索引加速向量相似度搜索
- 使用余弦距离（`vector_cosine_ops`）作为相似度度量

---

### 2.2 向量生成（Embedding）

**代码位置**: `process/ollama_client.py` → `embed()` 方法

```python
@staticmethod
def embed(text: str, model_name: str = MODEL_EMBEDDING) -> Optional[List[float]]:
    """将文本转换为768维向量"""
    for url in (f"{base}/api/embeddings", f"{base}/api/embed"):
        response = requests.post(
            url,
            json={"model": model_name, "prompt": text},
            timeout=REQUEST_TIMEOUT,
        )
        payload = response.json()
        vec = payload.get("embedding")
        # 返回768维浮点数列表
        if isinstance(vec, list) and vec and isinstance(vec[0], (int, float)):
            return [float(x) for x in vec]
    return None
```

**说明**：
- 调用本地Ollama的embedding模型（默认为`nomic-embed-text`）
- 将输入文本转换为768维向量
- 每个数值代表文本在某个语义维度上的特征

---

### 2.3 添加人物档案向量

**代码位置**: `main.py` → `_generate_missing_profiles()` 方法

```python
def _generate_missing_profiles(self, decomposed: Dict[str, Any]):
    """生成缺失的人物档案并存储向量"""
    for person in decomposed.get("identified_persons", []):
        person_key = person["person_key"]
        
        # 1. 通过LLM生成人物档案
        profile = self.llm_c.generate_profile(
            person_key=person_key,
            description=person["description"]
        )
        
        # 2. 保存人物基本信息到PostgreSQL
        person_id = self.store.upsert_person_profile(
            self.user_id,
            person_key=person_key,
            display_name=display_name,
        )
        
        # 3. 生成人物档案的向量表示
        emb = OllamaClient.embed(json.dumps(profile, ensure_ascii=False)[:2000])
        
        # 4. 保存人物档案版本，包含向量
        self.store.insert_person_profile_version(
            person_id=person_id,
            portrait=profile,
            mbti_type=mbti.get("type") or None,
            mbti_confidence=mbti.get("confidence"),
            portrait_embedding=emb,  # 存储768维向量
        )
```

**存储实现**: `process/postgres_store.py` → `insert_person_profile_version()`

```python
def insert_person_profile_version(
    self,
    person_id: str,
    portrait: Dict[str, Any],
    mbti_type: Optional[str],
    mbti_confidence: Optional[float],
    portrait_embedding: Optional[List[float]] = None,
) -> Tuple[str, int]:
    """插入人物档案版本，包含向量"""
    if portrait_embedding:
        vec_literal = _vector_literal(portrait_embedding)  # 将向量转换为PostgreSQL格式
        cur.execute(
            """
            INSERT INTO person_profile_version
              (id, person_id, version_no, mbti_type, mbti_confidence, portrait, portrait_embedding, created_at)
            VALUES
              (%s, %s, %s, %s, %s, %s, %s::vector, %s)
            """,
            (version_id, person_id, next_v, mbti_type, mbti_confidence, 
             json.dumps(portrait, ensure_ascii=False), vec_literal, now),
        )
```

**流程说明**：
1. LLM分析人物描述，生成结构化档案（MBTI类型、性格特征等）
2. 将档案JSON字符串转换为768维向量
3. 存储到`person_profile_version`表的`portrait_embedding`字段
4. 支持版本化，每次更新档案都会生成新版本

---

### 2.4 添加记忆块向量

**代码位置**: `main.py` → `_persist_memory()` 方法

```python
def _persist_memory(self, user_input: str, decomposed: Dict[str, Any], final_result: Dict[str, Any]):
    """将对话内容持久化为向量记忆"""
    
    # 1. 存储用户输入向量
    self_input_emb = OllamaClient.embed(user_input[:4000])
    self.store.upsert_memory_chunk(
        user_id=self.user_id,
        kind="chat_input",
        content=user_input[:4000],
        embedding=self_input_emb,  # 存储768维向量
    )
    
    # 2. 存储场景摘要向量
    scenario = decomposed.get("scenario_summary", "") or ""
    if scenario:
        scenario_emb = OllamaClient.embed(scenario[:2000])
        self.store.upsert_memory_chunk(
            user_id=self.user_id,
            kind="scenario",
            content=scenario[:2000],
            embedding=scenario_emb,
        )
    
    # 3. 存储决策结果向量
    structured = final_result.get("structured") or {}
    decision_brief = json.dumps(structured, ensure_ascii=False)[:2000]
    decision_emb = OllamaClient.embed(decision_brief)
    self.store.upsert_memory_chunk(
        user_id=self.user_id,
        kind="decision",
        content=decision_brief,
        embedding=decision_emb,
    )
```

**存储实现**: `process/postgres_store.py` → `upsert_memory_chunk()`

```python
def upsert_memory_chunk(
    self,
    user_id: str,
    kind: str,
    content: str,
    embedding: Optional[List[float]] = None,
    ref_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """插入或更新记忆块，包含向量"""
    if embedding:
        vec_literal = _vector_literal(embedding)
        cur.execute(
            """
            INSERT INTO memory_chunk (id, user_id, kind, ref_id, content, metadata, embedding, created_at)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::vector, %s)
            """,
            (memory_id, user_id, kind, ref_id, content, 
             json.dumps(meta, ensure_ascii=False), vec_literal, now),
        )
```

**流程说明**：
- 将用户输入、场景摘要、决策结果分别转换为向量
- 存储到`memory_chunk`表，标记类型（`kind`字段）
- 支持后续的语义检索和相似度匹配

---

### 2.5 向量语义检索

**代码位置**: `main.py` → `_retrieve_memory_context()` 方法

```python
def _retrieve_memory_context(self, user_input: str) -> str:
    """从记忆中检索相关上下文"""
    
    # 1. 将用户输入转换为向量
    emb = OllamaClient.embed(user_input[:4000])
    if not emb:
        return ""
    
    # 2. 在PostgreSQL中进行语义搜索
    try:
        hits = self.store.semantic_search(self.user_id, emb, top_k=6)
    except Exception as e:
        return ""
    
    # 3. 格式化检索结果
    lines = []
    for h in hits:
        kind = h.get("kind", "")
        content = (h.get("content") or "").strip()
        if not content:
            continue
        lines.append(f"[{kind}] {content[:400]}")
    
    return "\n".join(lines)
```

**检索实现**: `process/postgres_store.py` → `semantic_search()`

```python
def semantic_search(
    self,
    user_id: str,
    query_embedding: List[float],
    kind: Optional[str] = None,
    top_k: int = 6,
) -> List[Dict[str, Any]]:
    """使用向量相似度进行语义检索"""
    vec_literal = _vector_literal(query_embedding)
    sql = """
    SELECT id, kind, ref_id, content, metadata, created_at,
           (embedding <=> %s::vector) AS distance  -- 余弦距离
    FROM memory_chunk
    WHERE user_id=%s
      AND embedding IS NOT NULL
    """
    params: List[Any] = [vec_literal, user_id]
    
    if kind:
        sql += " AND kind=%s"
        params.append(kind)
    
    # 按距离排序，返回最相似的top_k条
    sql += " ORDER BY embedding <=> %s::vector LIMIT %s"
    params.extend([vec_literal, top_k])
    
    with self._connect() as conn:
        with conn.cursor(cursor_factory=self._RealDictCursor) as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall() or []
            return [dict(r) for r in rows]
```

**流程说明**：
1. 将查询文本转换为768维向量
2. 使用PostgreSQL的`<=>`操作符计算余弦距离
3. HNSW索引加速检索，返回最相似的top_k条记录
4. 支持按类型（`kind`）过滤（如只检索决策记录）

---

## 三、完整使用流程示例

### 3.1 用户发起决策分析

```
用户输入: "我想和老板谈加薪"
    ↓
main.py → run_full_pipeline()
    ↓
```

### 3.2 记忆检索（RAG）

```
main.py → _retrieve_memory_context()
    ↓
ollama_client.py → embed()  # 将用户输入转为向量
    ↓
postgres_store.py → semantic_search()  # 在PostgreSQL中搜索相似历史
    ↓
返回相关历史决策/人物/事件作为上下文
```

### 3.3 人物档案生成与向量化

```
main.py → _generate_missing_profiles()
    ↓
llm_c_profile_generator.py → generate_profile()  # LLM生成人物档案
    ↓
ollama_client.py → embed()  # 将档案JSON转为向量
    ↓
postgres_store.py → insert_person_profile_version()  # 存储向量
    ↓
postgres_store.py → ensure_schema()  # HNSW索引自动生效
```

### 3.4 决策分析与记忆沉淀

```
llm_d_decision_analyzer.py → analyze_decision()  # LLM决策分析
    ↓
main.py → _persist_memory()  # 沉淀本次对话
    ↓
ollama_client.py → embed()  # 分别为输入/场景/决策生成向量
    ↓
postgres_store.py → upsert_memory_chunk()  # 存储向量
    ↓
后续查询可通过semantic_search()召回
```

---

## 四、关键技术点总结

### 4.1 为什么选择pgvector而非独立向量数据库？

- **简化架构**：无需额外的Qdrant/Milvus服务
- **数据一致性**：向量和结构化数据在同一数据库，事务一致性有保障
- **降低运维成本**：只需维护PostgreSQL一个服务
- **性能足够**：HNSW索引在中小规模数据下性能优秀

### 4.2 768维向量的来源

- 使用`nomic-embed-text`模型（Ollama本地运行）
- 这是BERT类模型的标准输出维度
- 平衡了语义表达能力和计算成本

### 4.3 HNSW索引的优势

- **检索速度快**：O(log n)复杂度
- **内存效率高**：相比暴力搜索大幅降低内存占用
- **支持动态更新**：可以随时添加新向量

### 4.4 余弦距离（`<=>`操作符）

- 取值范围：[0, 2]，0表示完全相同，2表示完全相反
- 适合文本语义相似度计算
- 不受向量长度影响

---

## 五、代码位置索引

| 功能 | 文件路径 | 方法/类 |
|------|---------|---------|
| 向量生成 | `process/ollama_client.py` | `OllamaClient.embed()` |
| 数据库初始化 | `process/postgres_store.py` | `PostgresStore.ensure_schema()` |
| HNSW索引创建 | `process/postgres_store.py` | `ensure_schema()` 内的DDL |
| 人物档案向量存储 | `process/postgres_store.py` | `insert_person_profile_version()` |
| 记忆块向量存储 | `process/postgres_store.py` | `upsert_memory_chunk()` |
| 语义检索 | `process/postgres_store.py` | `semantic_search()` |
| 人物档案生成 | `main.py` | `_generate_missing_profiles()` |
| 记忆检索调用 | `main.py` | `_retrieve_memory_context()` |
| 记忆沉淀 | `main.py` | `_persist_memory()` |

---

## 六、扩展说明

### 6.1 未来可支持的向量检索场景

1. **相似人物匹配**：根据描述查找性格相似的人物
2. **历史决策复用**：找到相似场景的历史决策建议
3. **事件关联**：发现相关联的互动事件

### 6.2 向量维度调整

如需更换embedding模型，需同步修改：
- `process/config.py` 中的 `MODEL_EMBEDDING`
- PostgreSQL表定义中的 `vector(768)` 维度
- HNSW索引无需修改（自适应）

---

**文档版本**: v1.0  
**最后更新**: 2026-05-09  
**维护者**: PDIS项目组
