import os
import datetime as dt
from sqlalchemy.orm import Session
from shared.models import get_engine, Article, Keyword
from src.cooccurrence import rebuild_cooccurrences

DB_PATH = os.getenv("DB_PATH", "/data/db/sage.db")

SEED_ARTICLES = [
    {
        "paper_id": "arxiv-2017-03741",
        "title": "Attention Is All You Need",
        "arxiv_url": "https://arxiv.org/abs/1706.03762",
        "pdf_url": "https://arxiv.org/pdf/1706.03762",
        "date_submitted": "2017-06-12",
        "date_scraped": dt.date.today().isoformat(),
        "tags": ["cs.CL", "cs.LG"],
        "abstract": (
            "We propose a new simple network architecture, the Transformer, "
            "based solely on attention mechanisms, dispensing with recurrence "
            "and convolutions entirely."
        ),
    },
    {
        "paper_id": "arxiv-2018-04805",
        "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        "arxiv_url": "https://arxiv.org/abs/1810.04805",
        "pdf_url": "https://arxiv.org/pdf/1810.04805",
        "date_submitted": "2018-10-11",
        "date_scraped": dt.date.today().isoformat(),
        "tags": ["cs.CL"],
        "abstract": (
            "We introduce BERT, a new language representation model. "
            "BERT stands for Bidirectional Encoder Representations from Transformers. "
            "Unlike recent language representation models, BERT is designed to "
            "pre-train deep bidirectional representations from unlabeled text."
        ),
    },
    {
        "paper_id": "arxiv-2020-00001",
        "title": "Language Models are Few-Shot Learners",
        "arxiv_url": "https://arxiv.org/abs/2005.14165",
        "pdf_url": "https://arxiv.org/pdf/2005.14165",
        "date_submitted": "2020-05-28",
        "date_scraped": dt.date.today().isoformat(),
        "tags": ["cs.CL", "cs.AI"],
        "abstract": (
            "We demonstrate that scaling up language models greatly improves "
            "task-agnostic, few-shot performance, sometimes even reaching "
            "competitiveness with prior state-of-the-art fine-tuning approaches."
        ),
    },
    {
        "paper_id": "arxiv-2021-09461",
        "title": "An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale",
        "arxiv_url": "https://arxiv.org/abs/2010.11929",
        "pdf_url": "https://arxiv.org/pdf/2010.11929",
        "date_submitted": "2020-10-22",
        "date_scraped": dt.date.today().isoformat(),
        "tags": ["cs.CV", "cs.AI", "cs.LG"],
        "abstract": (
            "While the Transformer architecture has become the de-facto standard "
            "for natural language processing tasks, its applications to computer "
            "vision remain limited. We show that a pure transformer applied directly "
            "to sequences of image patches can perform very well on image classification."
        ),
    },
    {
        "paper_id": "arxiv-2022-00512",
        "title": "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models",
        "arxiv_url": "https://arxiv.org/abs/2201.11903",
        "pdf_url": "https://arxiv.org/pdf/2201.11903",
        "date_submitted": "2022-01-28",
        "date_scraped": dt.date.today().isoformat(),
        "tags": ["cs.CL", "cs.AI"],
        "abstract": (
            "We explore how generating a chain of thought — a series of intermediate "
            "reasoning steps — significantly improves the ability of large language "
            "models to perform complex reasoning."
        ),
    },
]

SEED_KEYWORDS = [
    {
        "keyword": "Transformer Architecture",
        "definition_simple": (
            "A neural network design that uses self-attention mechanisms to process "
            "sequential data in parallel, rather than step-by-step. It became the "
            "foundation for modern AI language models and is central to virtually "
            "every state-of-the-art AI system today."
        ),
        "definition_technical": (
            "A neural network design that uses self-attention mechanisms to process "
            "sequential data in parallel, rather than step-by-step. It became the "
            "foundation for modern AI language models and is central to virtually "
            "every state-of-the-art AI system today."
        ),
        "paper_references": ["arxiv-2017-03741", "arxiv-2018-04805", "arxiv-2021-09461"],
    },
    {
        "keyword": "Self-Attention",
        "definition_simple": (
            "A mechanism that allows a model to weigh the importance of different "
            "parts of its input when producing an output. It lets the model relate "
            "every word (or token) to every other word in a sequence, capturing "
            "long-range dependencies that older models struggled with."
        ),
        "definition_technical": (
            "A mechanism that allows a model to weigh the importance of different "
            "parts of its input when producing an output. It lets the model relate "
            "every word (or token) to every other word in a sequence, capturing "
            "long-range dependencies that older models struggled with."
        ),
        "paper_references": ["arxiv-2017-03741"],
    },
    {
        "keyword": "Pre-training",
        "definition_simple": (
            "The process of training a model on a large general dataset before "
            "fine-tuning it on a specific task. Pre-training allows models to learn "
            "broad knowledge from vast amounts of text, which can then be adapted "
            "cheaply to specialized applications."
        ),
        "definition_technical": (
            "The process of training a model on a large general dataset before "
            "fine-tuning it on a specific task. Pre-training allows models to learn "
            "broad knowledge from vast amounts of text, which can then be adapted "
            "cheaply to specialized applications."
        ),
        "paper_references": ["arxiv-2018-04805", "arxiv-2020-00001"],
    },
    {
        "keyword": "Large Language Model",
        "definition_simple": (
            "An AI model trained on massive amounts of text data with billions of "
            "parameters. These models learn statistical patterns in language and can "
            "generate, summarize, translate, and reason about text. GPT and BERT "
            "are prominent examples."
        ),
        "definition_technical": (
            "An AI model trained on massive amounts of text data with billions of "
            "parameters. These models learn statistical patterns in language and can "
            "generate, summarize, translate, and reason about text. GPT and BERT "
            "are prominent examples."
        ),
        "paper_references": ["arxiv-2020-00001", "arxiv-2022-00512"],
    },
    {
        "keyword": "Few-Shot Learning",
        "definition_simple": (
            "A model's ability to perform a new task given only a handful of "
            "examples, without additional training. Large language models can do "
            "this by learning patterns across many tasks during pre-training."
        ),
        "definition_technical": (
            "A model's ability to perform a new task given only a handful of "
            "examples, without additional training. Large language models can do "
            "this by learning patterns across many tasks during pre-training."
        ),
        "paper_references": ["arxiv-2020-00001"],
    },
    {
        "keyword": "Vision Transformer",
        "definition_simple": (
            "An adaptation of the Transformer architecture for image recognition "
            "tasks. Images are split into fixed-size patches, which are then treated "
            "like word tokens and fed into a standard Transformer encoder."
        ),
        "definition_technical": (
            "An adaptation of the Transformer architecture for image recognition "
            "tasks. Images are split into fixed-size patches, which are then treated "
            "like word tokens and fed into a standard Transformer encoder."
        ),
        "paper_references": ["arxiv-2021-09461"],
    },
    {
        "keyword": "Chain-of-Thought Prompting",
        "definition_simple": (
            "A prompting technique where the model is asked to show its reasoning "
            "step-by-step before giving a final answer. This significantly improves "
            "performance on complex reasoning tasks by encouraging intermediate "
            "logical steps."
        ),
        "definition_technical": (
            "A prompting technique where the model is asked to show its reasoning "
            "step-by-step before giving a final answer. This significantly improves "
            "performance on complex reasoning tasks by encouraging intermediate "
            "logical steps."
        ),
        "paper_references": ["arxiv-2022-00512"],
    },
    {
        "keyword": "Fine-tuning",
        "definition_simple": (
            "Continuing to train a pre-trained model on a smaller, task-specific "
            "dataset to adapt its general capabilities to a particular problem. "
            "Fine-tuning typically requires far less data and compute than training "
            "from scratch."
        ),
        "definition_technical": (
            "Continuing to train a pre-trained model on a smaller, task-specific "
            "dataset to adapt its general capabilities to a particular problem. "
            "Fine-tuning typically requires far less data and compute than training "
            "from scratch."
        ),
        "paper_references": ["arxiv-2018-04805", "arxiv-2020-00001"],
    },
]


def upsert_keyword(session: Session, kw_data: dict) -> None:
    existing = session.get(Keyword, kw_data["keyword"])
    if existing:
        existing.count += 1
        refs = set(existing.paper_references or [])
        refs.update(kw_data["paper_references"])
        existing.paper_references = list(refs)
        existing.dates = (existing.dates or []) + kw_data.get("dates", [])
    else:
        session.add(
            Keyword(
                keyword=kw_data["keyword"],
                definition_simple=kw_data.get("definition_simple"),
                definition_technical=kw_data.get("definition_technical"),
                count=1,
                paper_references=kw_data["paper_references"],
                dates=kw_data.get("dates", []),
            )
        )


def seed() -> None:
    engine = get_engine(DB_PATH)
    with Session(engine) as session:
        for art in SEED_ARTICLES:
            if not session.get(Article, art["paper_id"]):
                session.add(Article(**art))

        for kw in SEED_KEYWORDS:
            upsert_keyword(session, kw)

        session.commit()
        rebuild_cooccurrences(session)
    print("Seed complete.")
