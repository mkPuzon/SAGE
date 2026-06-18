'''main.py

Central script for SAGE data pipeline functionality.

'''
import os
import sqlite3
import sys
import time
import datetime as dt

from sqlalchemy.orm import Session

from shared.models import get_engine, Article
from src.scraper import fetch_arxiv_papers
from src.pdf_reader import download_and_extract_text
from src.extractor import extract_keywords, extract_definitions
from src.seed import upsert_keyword
from src.cooccurrence import update_cooccurrences
from src.logger import RunLogger

DB_PATH = os.getenv("DB_PATH", "/data/db/sage.db")
BACKUP_DIR = os.getenv("BACKUP_DIR", "/data/backups")
LOG_DIR = os.getenv("LOG_DIR", "/data/logs")
CAPTURE_DEFINITIONS = os.getenv("CAPTURE_DEFINITIONS", "").lower() in ("1", "true", "yes")


def backup_db(today: str) -> None:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    dest = os.path.join(BACKUP_DIR, f"sage_{today}.db")
    src_conn = sqlite3.connect(DB_PATH)
    dst_conn = sqlite3.connect(dest)
    src_conn.backup(dst_conn)
    dst_conn.close()
    src_conn.close()
    print(f"  DB backed up → {dest}")

def clean_backups(today: str) -> None:
    num_backups = sum(1 for entry in os.scandir(BACKUP_DIR) if entry.is_file())
    print(f"{num_backups=}")
    if num_backups > 4:
        files = sorted(
            (e.path for e in os.scandir(BACKUP_DIR) if e.is_file() and e.name.startswith("sage_") and e.name.endswith(".db")),
        )
        oldest = files[0]
        os.remove(oldest)
        print(f"  Deleted old backup: {oldest}")

def process_paper(paper: dict, engine, logger: RunLogger) -> list[str] | None:
    paper_id = paper["paper_id"]

    with Session(engine) as s:
        if s.get(Article, paper_id):
            print(f"  [{paper_id}] already in DB — skipping")
            return None

    print(f"  [{paper_id}] {paper['title'][:70]}")

    print("    → extracting keywords from abstract")
    with logger.time_paper_step(paper_id, "extract_keywords"):
        keywords, kw_model, kw_usage = extract_keywords(paper["abstract"])
    logger.record_openai_usage("extract_keywords", paper_id, kw_model, kw_usage)
    print(f"    → keywords: {keywords}")

    print("    → downloading PDF")
    with logger.time_paper_step(paper_id, "download_pdf"):
        pdf_text = download_and_extract_text(paper["pdf_url"])
    print(f"    → extracted {len(pdf_text):,} chars from PDF")

    print("    → extracting definitions")
    with logger.time_paper_step(paper_id, "extract_definitions"):
        definitions_simple, definitions_technical, def_model, def_usage = extract_definitions(
            pdf_text, keywords, paper_id=paper_id, capture=CAPTURE_DEFINITIONS
        )
    logger.record_openai_usage("extract_definitions", paper_id, def_model, def_usage)

    with logger.time_paper_step(paper_id, "db_upsert"):
        with Session(engine) as s:
            s.add(Article(**paper))
            for kw in keywords:
                upsert_keyword(
                    s,
                    {
                        "keyword": kw,
                        "definition_simple": definitions_simple.get(kw),
                        "definition_technical": definitions_technical.get(kw),
                        "paper_references": [paper_id],
                        "dates": [paper["date_submitted"]],
                    },
                )
            s.commit()

    print("    → saved to DB")
    return keywords


def reset_db() -> None:
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"  Deleted existing DB at {DB_PATH}")
    else:
        print(f"  No DB found at {DB_PATH} — nothing to delete")


def job():
    today = dt.datetime.today().strftime("%Y-%m-%d")
    run_id = dt.datetime.today().strftime("%Y-%m-%dT%H:%M:%S")
    num_papers = 5
    print(f"Running job to scrape {num_papers} papers for {today}...")

    if os.getenv("NEW_DB") == "1":
        print("---- 0. NEW_DB=1: resetting database ----")
        reset_db()

    logger = RunLogger(run_id)

    try:
        print("---- 1. Fetch metadata from arXiv ----")
        with logger.time_step("fetch_papers"):
            papers = fetch_arxiv_papers("cs.AI", num_papers)
        print(f"  Fetched {len(papers)} papers")

        engine = get_engine(DB_PATH)

        print("---- 2. Extract keywords, definitions & insert into DB ----")
        new_paper_keywords: list[list[str]] = []
        with logger.time_step("process_papers"):
            for i, paper in enumerate(papers):
                paper_id = paper.get("paper_id", "?")
                try:
                    t0 = time.perf_counter()
                    kws = process_paper(paper, engine, logger)
                    duration = round(time.perf_counter() - t0, 3)
                    if kws is not None:
                        new_paper_keywords.append(kws)
                        logger.record_paper(paper_id, paper["title"], "processed", kws, duration)
                    else:
                        logger.record_paper(paper_id, paper["title"], "skipped")
                except Exception as e:
                    print(f"  [{paper_id}] ERROR: {e}")
                    logger.record_paper(paper_id, paper.get("title", ""), "errored")
                if i < len(papers) - 1:
                    time.sleep(3)  # respect arXiv rate limit between papers

        print("---- 3. Backup DB ----")
        with logger.time_step("backup_db"):
            backup_db(today)

        print("---- 4. Update co-occurrence index ----")
        with logger.time_step("update_cooccurrences"):
            with Session(engine) as session:
                update_cooccurrences(session, new_paper_keywords)

        print("---- 5. Clean old backups ----")
        with logger.time_step("clean_backups"):
            clean_backups(today)

        print(f"Job complete for {today}.")

    finally:
        logger.write(LOG_DIR, today)


if __name__ == "__main__":
    import schedule

    try:
        job()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

    schedule.every().day.at("02:00").do(job)

    print("Scheduler started; waiting for 2:00am...")

    while True:
        schedule.run_pending()
        time.sleep(60)
