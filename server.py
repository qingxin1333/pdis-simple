import uuid
from pathlib import Path
from typing import Optional
import json

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from main import PDISPipeline
from process.config import DATABASE_URL
from process.postgres_store import PostgresStore


app = FastAPI(title="PDIS", version="0.1")
app.mount("/static", StaticFiles(directory="web"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = None
if DATABASE_URL:
    try:
        store = PostgresStore(DATABASE_URL)
        store.ensure_schema()
    except Exception as e:
        print(f"⚠️ Postgres 初始化失败: {e}")


class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AgentRunRequest(BaseModel):
    text: str
    mode: str | None = None
    attachments: list[str] | None = None


def get_session_id(request: Request) -> Optional[str]:
    return request.cookies.get("session_id")


def get_current_user(session_id: Optional[str] = Depends(get_session_id)):
    if not store:
        raise HTTPException(status_code=503, detail="数据库未配置")
    if not session_id:
        raise HTTPException(status_code=401, detail="未登录")
    user = store.get_session_user(session_id)
    if not user:
        raise HTTPException(status_code=401, detail="会话无效或已过期")
    return user


@app.get("/", response_class=HTMLResponse)
def index():
    with open("web/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/login", response_class=HTMLResponse)
def login_page():
    with open("web/login.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/api/v1/auth/register")
def register(req: RegisterRequest, response: Response):
    if not store:
        raise HTTPException(status_code=503, detail="数据库未配置")
    try:
        user = store.register_user(req.email, req.password, req.display_name)
        session_id = store.create_session(user.id)
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            max_age=86400,
            samesite="lax"
        )
        return {"user": {"id": user.id, "email": user.email, "display_name": user.display_name}}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/auth/login")
def login(req: LoginRequest, response: Response):
    if not store:
        raise HTTPException(status_code=503, detail="数据库未配置")
    user = store.verify_user(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    session_id = store.create_session(user.id)
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        max_age=86400,
        samesite="lax"
    )
    return {"user": {"id": user.id, "email": user.email, "display_name": user.display_name}}


@app.post("/api/v1/auth/logout")
def logout(response: Response, session_id: Optional[str] = Depends(get_session_id)):
    if session_id and store:
        store.revoke_session(session_id)
    response.delete_cookie("session_id")
    return {"ok": True}


@app.get("/api/v1/auth/me")
def get_me(current_user = Depends(get_current_user)):
    return {"user": {"id": current_user.id, "email": current_user.email, "display_name": current_user.display_name}}


@app.post("/api/v1/attachments/upload")
async def upload_attachments(files: list[UploadFile] = File(...), current_user = Depends(get_current_user)):
    base = Path("uploads")
    base.mkdir(parents=True, exist_ok=True)
    out = []
    for f in files:
        fid = str(uuid.uuid4())
        suffix = Path(f.filename or "").suffix
        safe = (suffix[:10] if suffix else "")
        path = base / f"{fid}{safe}"
        content = await f.read()
        path.write_bytes(content)
        out.append(
            {
                "file_ref": str(path),
                "filename": f.filename or "",
                "size": len(content),
                "content_type": f.content_type or "",
            }
        )
    return {"files": out}


@app.post("/api/v1/agent/run")
def agent_run(req: AgentRunRequest, current_user = Depends(get_current_user)):
    text = req.text
    attachments = req.attachments or []
    if attachments:
        evidence_lines = []
        for ref in attachments[:6]:
            p = Path(ref)
            if not p.exists() or not p.is_file():
                continue
            name = p.name
            ext = p.suffix.lower()
            if ext in [".txt", ".md", ".log"]:
                try:
                    raw = p.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    raw = ""
                raw = raw.strip().replace("\r\n", "\n")
                if raw:
                    evidence_lines.append(f"[附件:{name}]\n{raw[:2000]}")
                else:
                    evidence_lines.append(f"[附件:{name}]（文本为空或无法读取）")
            else:
                evidence_lines.append(f"[附件:{name}]（已上传）")
        if evidence_lines:
            text = text.rstrip() + "\n\n" + "\n\n".join(evidence_lines) + "\n"

    pipeline = PDISPipeline(user_id=current_user.id)
    result = pipeline.run_full_pipeline(text, return_structured=True)
    return result


def generate_stream(pipeline, text):
    """生成流式响应"""
    try:
        # 发送开始标记
        yield f"data: {json.dumps({'type': 'start', 'content': '正在分析...'})}\n\n"

        # 执行完整流程
        result = pipeline.run_full_pipeline(text, return_structured=True)

        # 发送推理过程
        plan_summary = result.get('plan_summary', [])
        if plan_summary:
            yield f"data: {json.dumps({'type': 'thinking', 'content': '执行计划：' + ' → '.join(plan_summary)})}\n\n"

        tool_runs = result.get('tool_runs', [])
        for tool in tool_runs:
            status = tool.get('status', 'unknown')
            tool_name = tool.get('tool', 'unknown')
            if status == 'ok':
                yield f"data: {json.dumps({'type': 'thinking', 'content': '✓ ' + tool_name})}\n\n"
            else:
                error_msg = tool.get('error', '失败')
                yield f"data: {json.dumps({'type': 'thinking', 'content': '✗ ' + tool_name + ': ' + error_msg})}\n\n"

        # 发送最终结果
        final_answer = result.get('result', {}).get('client_report', '')
        yield f"data: {json.dumps({'type': 'final', 'content': final_answer})}\n\n"

        # 发送完成标记
        yield f"data: {json.dumps({'type': 'done', 'plan_summary': plan_summary, 'tool_runs': tool_runs, 'memory_context': result.get('memory_context', '')})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"


@app.post("/api/v1/agent/run/stream")
def agent_run_stream(req: AgentRunRequest, current_user = Depends(get_current_user)):
    text = req.text
    attachments = req.attachments or []
    if attachments:
        evidence_lines = []
        for ref in attachments[:6]:
            p = Path(ref)
            if not p.exists() or not p.is_file():
                continue
            name = p.name
            ext = p.suffix.lower()
            if ext in [".txt", ".md", ".log"]:
                try:
                    raw = p.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    raw = ""
                raw = raw.strip().replace("\r\n", "\n")
                if raw:
                    evidence_lines.append(f"[附件:{name}]\n{raw[:2000]}")
                else:
                    evidence_lines.append(f"[附件:{name}]（文本为空或无法读取）")
            else:
                evidence_lines.append(f"[附件:{name}]（已上传）")
        if evidence_lines:
            text = text.rstrip() + "\n\n" + "\n\n".join(evidence_lines) + "\n"

    pipeline = PDISPipeline(user_id=current_user.id)
    return StreamingResponse(
        generate_stream(pipeline, text),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

