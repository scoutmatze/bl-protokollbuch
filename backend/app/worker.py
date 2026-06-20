"""RQ-Worker für die Ingestion-Pipeline (siehe docs/PIPELINE.md).

Phase 0: lauffähiger Worker-Prozess ohne Jobs. Die Pipeline-Tasks
(extract → segment → items → embeddings → match) folgen ab Phase 1.
"""
from redis import Redis
from rq import Queue, Worker

from .config import settings

QUEUE_NAME = "ingestion"


def main() -> None:
    redis = Redis.from_url(settings.redis_url)
    worker = Worker([Queue(QUEUE_NAME, connection=redis)], connection=redis)
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
