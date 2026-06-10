import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from shared.models import get_engine, Article, Keyword, KeywordCooccurrence

DB_PATH = os.getenv("DB_PATH", "/data/db/sage.db")
engine = get_engine(DB_PATH)

app = FastAPI(title="SAGE API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/keywords")
def search_keywords(q: str = ""):
    with Session(engine) as session:
        query = session.query(Keyword)
        if q:
            query = query.filter(Keyword.keyword.ilike(f"%{q}%"))
        results = query.order_by(Keyword.count.desc()).limit(20).all()
        return [{"keyword": k.keyword, "count": k.count} for k in results]


@app.get("/api/keywords/{keyword}")
def get_keyword(keyword: str):
    with Session(engine) as session:
        kw = session.get(Keyword, keyword)
        if not kw:
            raise HTTPException(status_code=404, detail="Keyword not found")

        articles = []
        for paper_id in kw.paper_references or []:
            art = session.get(Article, paper_id)
            if art:
                articles.append(
                    {
                        "paper_id": art.paper_id,
                        "title": art.title,
                        "arxiv_url": art.arxiv_url,
                        "pdf_url": art.pdf_url,
                        "date_submitted": art.date_submitted,
                        "tags": art.tags,
                        "abstract": art.abstract,
                    }
                )

        return {
            "keyword": kw.keyword,
            "definition_simple": kw.definition_simple,
            "definition_technical": kw.definition_technical,
            "count": kw.count,
            "articles": articles,
        }


@app.get("/api/keywords/{keyword}/related")
def get_related_keywords(keyword: str):
    with Session(engine) as session:
        rows = (
            session.query(KeywordCooccurrence)
            .filter(KeywordCooccurrence.keyword_a == keyword)
            .order_by(KeywordCooccurrence.score.desc())
            .limit(10)
            .all()
        )
        return [{"keyword": r.keyword_b} for r in rows]
