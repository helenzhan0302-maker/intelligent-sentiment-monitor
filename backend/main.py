"""智能舆情监测平台 — v0.4.0
后端: 搜索 + 规则评分 + API + SSE + 独立报告 + JWT 认证 + 搜索历史
"""
import os
import re
import json
import uuid
import time
import asyncio
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from auth import (
    init_db, register_user, login_user, verify_token,
    save_search, get_history, get_history_detail,
)

load_dotenv()

# ── 配置 ─────────────────────────────────────────────────────
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
BING_API_KEY = os.getenv("BING_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/anthropic")

MAX_RESULTS = 20
HTTP_TIMEOUT = 20.0

# ── 域名权威白名单 ────────────────────────────────────────────
DOMAIN_AUTHORITY = {
    "xinhuanet.com": 10, "people.com.cn": 10, "cctv.com": 10,
    "reuters.com": 10, "bloomberg.com": 9, "apnews.com": 9,
    "bbc.com": 9, "cnn.com": 9, "wsj.com": 9, "ft.com": 9,
    "36kr.com": 9, "techcrunch.com": 9, "theverge.com": 8,
    "wired.com": 8, "arstechnica.com": 8, "jiqizhixin.com": 8,
    "infoq.cn": 8, "huxiu.com": 7, "pingwest.com": 7,
    "geekpark.net": 7, "tech.sina.com.cn": 7, "tech.qq.com": 7,
    "tech.163.com": 7, "ithome.com": 6, "leiphone.com": 6,
    "donews.com": 5, "cnbeta.com": 5, "sohu.com": 5,
    "theinformation.com": 8, "technologyreview.com": 8,
}

# ── 评分权重 ──────────────────────────────────────────────────
WEIGHTS = {
    "authority": 0.25,
    "timeliness": 0.20,
    "importance": 0.25,
    "impact": 0.20,
    "relevance": 0.10,
}

# ── FastAPI App ──────────────────────────────────────────────
app = FastAPI(title="智能舆情监测平台", version="0.4.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic Models ──────────────────────────────────────────
class SearchRequest(BaseModel):
    keywords: list[str] = Field(..., min_length=1, max_length=10)


class NewsItem(BaseModel):
    id: str
    title: str
    url: str
    source: str
    snippet: str
    published_at: str | None = None
    scores: dict
    total_score: float
    rank: int


class SearchResponse(BaseModel):
    keywords: list[str]
    total: int
    duration_seconds: float
    results: list[NewsItem]
    history_id: str | None = None


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=32)
    password: str = Field(..., min_length=6, max_length=64)
    invite_code: str


class LoginRequest(BaseModel):
    username: str
    password: str


# ── Startup ────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    init_db()


# ── Auth Dependency ────────────────────────────────────────────
async def get_current_user(authorization: str = Header(None)):
    """JWT Bearer token 验证，返回 user_id"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供有效的认证令牌")
    token = authorization.replace("Bearer ", "")
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="认证令牌无效或已过期")
    return payload["sub"]


# ── 搜索函数 ─────────────────────────────────────────────────
def _parse_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""


def _get_authority(domain: str) -> float:
    for d, score in sorted(DOMAIN_AUTHORITY.items(), key=lambda x: -len(x[0])):
        if d in domain:
            return float(score)
    return 3.0


async def search_serper(keyword: str, num: int = 10) -> list[dict]:
    """Serper.dev 搜索"""
    if not SERPER_API_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.post(
                "https://google.serper.dev/news",
                json={"q": keyword, "num": num, "gl": "cn", "hl": "zh-cn"},
                headers={"X-API-KEY": SERPER_API_KEY},
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data.get("news", [])[:num]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "source": item.get("source", ""),
                    "snippet": item.get("snippet", ""),
                    "published_at": item.get("date", ""),
                })
            return results
    except Exception as e:
        print(f"[Serper] Error: {e}")
        return []


async def search_bing(keyword: str, num: int = 10) -> list[dict]:
    """Bing News API 搜索"""
    if not BING_API_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.get(
                "https://api.bing.microsoft.com/v7.0/news/search",
                params={"q": keyword, "count": num, "mkt": "zh-CN"},
                headers={"Ocp-Apim-Subscription-Key": BING_API_KEY},
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data.get("value", [])[:num]:
                results.append({
                    "title": item.get("name", ""),
                    "url": item.get("url", ""),
                    "source": item.get("provider", [{}])[0].get("name", ""),
                    "snippet": item.get("description", ""),
                    "published_at": item.get("datePublished", ""),
                })
            return results
    except Exception as e:
        print(f"[Bing] Error: {e}")
        return []


async def search_deepseek(keyword: str, num: int = 10) -> list[dict]:
    """DeepSeek fallback: 让 LLM 列出当前热点新闻"""
    if not DEEPSEEK_API_KEY:
        return []

    today = datetime.now().strftime("%Y-%m-%d")
    prompt = f"""Today is {today}. Please list {num} real, recent news articles about "{keyword}".
Focus on articles from the past 24-48 hours from credible sources.

Return ONLY a JSON array:
[{{"title": "...", "url": "...", "source": "...", "snippet": "...", "published_at": "..."}}]

No markdown, no explanation. Ensure all URLs are real, verifiable news URLs."""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{DEEPSEEK_BASE_URL}/v1/messages",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 4096,
                    "temperature": 0.1,
                    "thinking": {"type": "disabled"},
                },
            )
            resp.raise_for_status()
            data = resp.json()

            # Extract text from Anthropic-compatible format
            content_blocks = data.get("content", [data.get("message", {}).get("content", "")])
            if isinstance(content_blocks, str):
                text = content_blocks
            else:
                text = "".join(
                    b.get("text", "") for b in content_blocks
                    if isinstance(b, dict) and b.get("type") == "text"
                )

            # Parse JSON from response
            text = text.strip()
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

            import json
            results = json.loads(text)
            if isinstance(results, dict) and "articles" in results:
                results = results["articles"]
            return results[:num] if isinstance(results, list) else []
    except Exception as e:
        print(f"[DeepSeek] Fallback search error: {e}")
        return []


def _dedup_results(results: list[dict]) -> list[dict]:
    """去重: URL 精确 + 标题前 30 字模糊"""
    seen_urls = set()
    seen_titles = set()
    deduped = []
    for item in results:
        url = item.get("url", "")
        title_prefix = item.get("title", "")[:30]
        if url and url in seen_urls:
            continue
        if title_prefix and title_prefix in seen_titles:
            continue
        seen_urls.add(url)
        seen_titles.add(title_prefix)
        deduped.append(item)
    return deduped


async def search_news(keywords: list[str]) -> list[dict]:
    """搜索入口: 多关键词并行 → 双源并行 → 合并去重"""
    all_results = []

    for kw in keywords:
        # Serper + Bing 并行
        serper_task = search_serper(kw, MAX_RESULTS)
        bing_task = search_bing(kw, MAX_RESULTS)
        serper_r, bing_r = await asyncio.gather(serper_task, bing_task)
        combined = serper_r + bing_r

        if not combined:
            # DeepSeek fallback
            combined = await search_deepseek(kw, MAX_RESULTS)

        all_results.extend(combined)

    # 去重 + 截断
    deduped = _dedup_results(all_results)
    return deduped[:MAX_RESULTS]


# ── 评分函数 ─────────────────────────────────────────────────
def _score_timeliness(published_at: str | None) -> float:
    """时效性评分: 越新越高 (1-10)"""
    if not published_at:
        return 5.0
    try:
        # Try ISO format
        pub_date = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        if pub_date.tzinfo:
            pub_date = pub_date.replace(tzinfo=None)
        now = datetime.now()
        diff_hours = (now - pub_date).total_seconds() / 3600
        if diff_hours <= 1:
            return 10.0
        elif diff_hours <= 4:
            return 9.0
        elif diff_hours <= 12:
            return 8.0
        elif diff_hours <= 24:
            return 7.0
        elif diff_hours <= 48:
            return 5.0
        elif diff_hours <= 72:
            return 3.0
        else:
            return 2.0
    except Exception:
        return 5.0


def _score_importance(title: str, snippet: str, authority: float) -> float:
    """重要性评分 (1-10)"""
    score = 5.0
    # 标题长度 (太短没信息，太长可能标题党)
    title_len = len(title)
    if 20 <= title_len <= 80:
        score += 1.5
    elif 80 < title_len <= 120:
        score += 0.5
    # 摘要丰富度
    if len(snippet) > 100:
        score += 1.5
    elif len(snippet) > 50:
        score += 1.0
    # 来源权威性加成
    if authority >= 8:
        score += 1.5
    elif authority >= 6:
        score += 0.5
    return min(10.0, max(1.0, score))


def _score_impact(title: str, snippet: str, keywords: list[str]) -> float:
    """影响度评分: 关键词命中 + 标题冲击力 (1-10)"""
    score = 3.0
    title_lower = title.lower()
    snippet_lower = snippet.lower()

    # 关键词命中数
    hits = 0
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower in title_lower:
            hits += 2
        elif kw_lower in snippet_lower:
            hits += 1
    score += min(hits * 1.5, 5.0)

    # 冲击力关键词
    impact_words = ["突破", "发布", "重大", "历史", "首次", "万亿", "收购",
                    "上市", "暴跌", "暴涨", "裁员", "融资", "政策", "制裁",
                    "launch", "breakthrough", "revolutionary", "record"]
    for w in impact_words:
        if w in title_lower:
            score += 0.3

    return min(10.0, max(1.0, score))


def _score_relevance(title: str, snippet: str, keywords: list[str]) -> float:
    """相关性评分: 关键词在标题中的权重 (1-10)"""
    score = 3.0
    text = title + " " + snippet
    text_lower = text.lower()
    for kw in keywords:
        kw_lower = kw.lower()
        count = text_lower.count(kw_lower)
        if count > 0:
            score += min(count, 5) * 1.0
    return min(10.0, max(1.0, score))


def score_results(results: list[dict], keywords: list[str]) -> list[dict]:
    """5 维规则评分，返回排序结果"""
    for item in results:
        domain = _parse_domain(item.get("url", ""))
        authority = _get_authority(domain)
        timeliness = _score_timeliness(item.get("published_at"))
        importance = _score_importance(
            item.get("title", ""), item.get("snippet", ""), authority
        )
        impact = _score_impact(
            item.get("title", ""), item.get("snippet", ""), keywords
        )
        relevance = _score_relevance(
            item.get("title", ""), item.get("snippet", ""), keywords
        )

        total = round(
            authority * WEIGHTS["authority"]
            + timeliness * WEIGHTS["timeliness"]
            + importance * WEIGHTS["importance"]
            + impact * WEIGHTS["impact"]
            + relevance * WEIGHTS["relevance"],
            2,
        )

        item["id"] = item.get("id") or str(uuid.uuid4())
        item["source"] = item.get("source") or domain
        item["scores"] = {
            "权威性": round(authority, 1),
            "时效性": round(timeliness, 1),
            "重要性": round(importance, 1),
            "影响度": round(impact, 1),
            "相关性": round(relevance, 1),
        }
        item["total_score"] = total

    # 排序
    results.sort(key=lambda x: x["total_score"], reverse=True)
    for i, item in enumerate(results):
        item["rank"] = i + 1

    return results


# ── API Endpoints ────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "0.4.0",
        "serper_configured": bool(SERPER_API_KEY),
        "bing_configured": bool(BING_API_KEY),
        "deepseek_configured": bool(DEEPSEEK_API_KEY),
    }


# ── Auth Endpoints ─────────────────────────────────────────────
@app.post("/api/auth/register")
async def auth_register(req: RegisterRequest):
    """注册新用户（需邀请码）"""
    try:
        user = register_user(req.username, req.password, req.invite_code)
        token = create_token(user["user_id"])
        return {"token": token, "user": user}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/login")
async def auth_login(req: LoginRequest):
    """用户登录"""
    try:
        result = login_user(req.username, req.password)
        return result
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


# ── History Endpoints (需认证) ─────────────────────────────────
@app.get("/api/history")
async def history_list(user_id: str = Depends(get_current_user)):
    """获取搜索历史列表"""
    items = get_history(user_id)
    return {"items": items, "total": len(items)}


@app.get("/api/history/{history_id}")
async def history_detail(history_id: str, user_id: str = Depends(get_current_user)):
    """获取搜索历史详情"""
    detail = get_history_detail(user_id, history_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="历史记录不存在")
    return detail


# ── JWT Token 生成（内部使用）──────────────────────────────────
def create_token(user_id: str) -> str:
    from auth import create_token as _create_token
    return _create_token(user_id)


# ── Protected Search Endpoints ─────────────────────────────────
@app.post("/api/search", response_model=SearchResponse)
async def search(req: SearchRequest, user_id: str = Depends(get_current_user)):
    """搜索 + 评分 → 返回排序结果（需认证）"""
    import time
    t0 = time.time()

    try:
        results = await search_news(req.keywords)
        scored = score_results(results, req.keywords)
        duration = round(time.time() - t0, 1)

        # 保存搜索历史
        history_id = None
        try:
            response_json = json.dumps({
                "keywords": req.keywords,
                "total": len(scored),
                "duration_seconds": duration,
                "results": scored,
            }, ensure_ascii=False)
            history_id = save_search(user_id, req.keywords, response_json)
        except Exception as e:
            print(f"[History] Save failed: {e}")

        return SearchResponse(
            keywords=req.keywords,
            total=len(scored),
            duration_seconds=duration,
            results=scored,
            history_id=history_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── LLM 深度报告生成 ─────────────────────────────────────────
REPORT_PROMPT = """你是一位资深行业战略分析师。请根据以下新闻信息，撰写一份深度分析报告。

**新闻标题**: {title}
**来源**: {source}
**摘要**: {snippet}

请生成一份 Markdown 格式的分析报告，包含以下四个章节：

## 📌 事件概述
用 200-300 字概括事件要点（5W1H：发生了什么、涉及谁、何时何地、为什么重要）。

## 🏭 行业影响分析
用 300-400 字分析该事件对相关行业的短期和长期影响。

## ⚔️ 竞争格局变化
用 200-300 字分析该事件如何改变市场竞争态势。

## 🔮 趋势预判
用 200-300 字预判未来发展方向，给出 2-3 个关键信号值得关注。

---
*本报告由系统自动生成，仅供参考*"""


async def generate_single_report(news_item: dict) -> dict | None:
    """调用 DeepSeek 为单条新闻生成深度分析报告"""
    prompt = REPORT_PROMPT.format(
        title=news_item.get("title", ""),
        source=news_item.get("source", ""),
        snippet=news_item.get("snippet", ""),
    )

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                f"{DEEPSEEK_BASE_URL}/v1/messages",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 3072,
                    "temperature": 0.7,
                    "thinking": {"type": "disabled"},
                },
            )
            resp.raise_for_status()
            data = resp.json()

            content_blocks = data.get("content", [])
            text = "".join(
                b.get("text", "") for b in content_blocks
                if isinstance(b, dict) and b.get("type") == "text"
            )

            return {
                "id": str(uuid.uuid4()),
                "news_item_id": news_item.get("id", ""),
                "title": f"📊 深度分析: {news_item.get('title', '')}",
                "content_md": text.strip(),
                "word_count": len(text),
            }
    except Exception as e:
        print(f"[Report] Generation failed: {e}")
        return None


# ── Top N 综合深度报告 ─────────────────────────────────────────
COMBINED_REPORT_PROMPT = """你是一位资深行业战略分析师。以下是关于同一主题领域的最新 Top 新闻资讯，请将它们作为一个整体，撰写一份综合深度分析报告。

{news_items}

请生成一份 Markdown 格式的综合分析报告，包含以下四个章节：

## 📌 热点总览
用 300-400 字综合概述这些新闻反映的核心趋势和共同主题，分析背后的驱动因素和信号意义。

## 🔍 各事件要点
逐条简要分析每条新闻的关键信息（每条 150-200 字），包括事件本身、涉及方、以及为什么值得关注。

## ⚔️ 交叉影响与竞争格局
用 300-400 字分析这些事件之间的关联性和相互影响，以及它们对市场竞争格局的合力效应。

## 🔮 趋势预判
用 300-400 字预判未来 3-6 个月的行业发展趋势，给出 3-5 个值得持续关注的关键信号。

---
*本报告由系统自动生成，仅供参考*"""


async def generate_combined_report(items: list[dict]) -> dict | None:
    """调用 DeepSeek 为多条新闻生成一份综合深度分析报告"""
    # 组装新闻列表文本
    news_text_parts = []
    for i, item in enumerate(items, 1):
        news_text_parts.append(
            f"**新闻 {i}**\n"
            f"- 标题: {item.get('title', '')}\n"
            f"- 来源: {item.get('source', '')}\n"
            f"- 摘要: {item.get('snippet', '')}\n"
        )
    news_text = "\n".join(news_text_parts)
    prompt = COMBINED_REPORT_PROMPT.format(news_items=news_text)

    # 取第一条新闻标题作为报告主题
    main_topic = items[0].get("title", "综合资讯") if items else "综合资讯"

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{DEEPSEEK_BASE_URL}/v1/messages",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 4096,
                    "temperature": 0.7,
                    "thinking": {"type": "disabled"},
                },
            )
            resp.raise_for_status()
            data = resp.json()

            content_blocks = data.get("content", [])
            text = "".join(
                b.get("text", "") for b in content_blocks
                if isinstance(b, dict) and b.get("type") == "text"
            )

            return {
                "id": str(uuid.uuid4()),
                "title": f"📊 Top {len(items)} 综合深度分析: {main_topic[:50]}",
                "content_md": text.strip(),
                "word_count": len(text),
            }
    except Exception as e:
        print(f"[CombinedReport] Generation failed: {e}")
        return None


# ── SSE Streaming Endpoint ───────────────────────────────────
@app.get("/api/search/stream")
async def search_stream(
    keywords: str = Query(..., description="逗号分隔的关键词"),
    token: str = Query(None, description="JWT token（EventSource 不支持 Header，通过 query 传递）"),
    authorization: str = Header(None),
):
    """SSE 流式端点: 实时推送搜索 + 评分进度（需认证）"""

    # Auth: 优先 Header，fallback query param（EventSource 限制）
    user_id = None
    auth_token = None
    if authorization and authorization.startswith("Bearer "):
        auth_token = authorization.replace("Bearer ", "")
    elif token:
        auth_token = token

    if auth_token:
        payload = verify_token(auth_token)
        if payload:
            user_id = payload["sub"]

    if not user_id:
        raise HTTPException(status_code=401, detail="未提供有效的认证令牌")

    kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
    if not kw_list:
        raise HTTPException(status_code=400, detail="至少需要一个关键词")

    async def event_generator():
        t0 = time.time()
        all_results = []
        seen_urls = set()
        seen_titles = set()

        def make_event(event: str, data: dict) -> str:
            return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

        try:
            # Search phase — per keyword
            for kw in kw_list:
                yield make_event("search_start", {"keyword": kw, "total_keywords": len(kw_list)})

                # Serper + Bing 并行
                serper_task = search_serper(kw, MAX_RESULTS)
                bing_task = search_bing(kw, MAX_RESULTS)
                serper_r, bing_r = await asyncio.gather(serper_task, bing_task)
                combined = serper_r + bing_r

                if not combined:
                    yield make_event("search_status", {"keyword": kw, "message": "主搜索源无结果，使用 AI 搜索中..."})
                    combined = await search_deepseek(kw, MAX_RESULTS)

                # Dedup
                for item in combined:
                    url = item.get("url", "")
                    title_prefix = item.get("title", "")[:30]
                    if url and url in seen_urls:
                        continue
                    if title_prefix and title_prefix in seen_titles:
                        continue
                    seen_urls.add(url)
                    seen_titles.add(title_prefix)
                    all_results.append(item)

                # Send results for this keyword immediately
                yield make_event("search_done", {
                    "keyword": kw,
                    "found": len(combined),
                    "total_so_far": len(all_results),
                    "news": combined[:10],
                })

            # Cap results
            all_results = all_results[:MAX_RESULTS]

            # Scoring phase
            yield make_event("scoring_start", {"total": len(all_results)})
            scored = score_results(all_results, kw_list)

            duration = round(time.time() - t0, 1)

            # 保存搜索历史（SSE 路径）
            history_id = None
            try:
                response_json = json.dumps({
                    "keywords": kw_list,
                    "total": len(scored),
                    "duration_seconds": duration,
                    "results": scored,
                }, ensure_ascii=False)
                history_id = save_search(user_id, kw_list, response_json)
            except Exception as e:
                print(f"[History] SSE save failed: {e}")

            yield make_event("complete", {
                "keywords": kw_list,
                "total": len(scored),
                "duration_seconds": duration,
                "results": scored,
                "history_id": history_id,
            })

        except Exception as e:
            yield make_event("error", {"message": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── 独立报告生成 Endpoint ─────────────────────────────────────
class ReportRequest(BaseModel):
    id: str
    title: str
    source: str
    snippet: str


class CombinedReportRequest(BaseModel):
    items: list[ReportRequest] = Field(..., min_length=1, max_length=5)


@app.post("/api/reports/generate")
async def generate_report(req: ReportRequest, user_id: str = Depends(get_current_user)):
    """为单条新闻生成深度分析报告（需认证）"""
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=503, detail="DeepSeek API 未配置")

    item = {
        "id": req.id,
        "title": req.title,
        "source": req.source,
        "snippet": req.snippet,
    }
    report = await generate_single_report(item)
    if report is None:
        raise HTTPException(status_code=500, detail="报告生成失败，请重试")
    return report


@app.post("/api/reports/generate-combined")
async def generate_combined_report_endpoint(req: CombinedReportRequest, user_id: str = Depends(get_current_user)):
    """为 Top N 条新闻生成一份综合深度分析报告（需认证）"""
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=503, detail="DeepSeek API 未配置")

    items = [
        {"id": it.id, "title": it.title, "source": it.source, "snippet": it.snippet}
        for it in req.items
    ]
    report = await generate_combined_report(items)
    if report is None:
        raise HTTPException(status_code=500, detail="综合报告生成失败，请重试")
    return report


# ── 前端静态文件托管（SPA 模式）───────────────────────────────
@app.get("/{full_path:path}")
async def serve_spa():
    """所有非 API 路由返回 index.html（React SPA）"""
    import os
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        from fastapi.responses import FileResponse
        return FileResponse(index_path)
    return {"error": "前端未构建，请先运行 npm run build"}

# 静态资源（JS/CSS/图片等）
if os.path.exists(os.path.join(os.path.dirname(__file__), "static")):
    app.mount("/assets", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static", "assets")), name="static")
