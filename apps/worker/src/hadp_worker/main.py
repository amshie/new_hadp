"""Worker entrypoint — labeled skeleton.

Connects to Redis and blocks on a job queue. It logs received jobs but does NOT process
clinical work yet (import normalization runs inline in the API for the Milestone 0.5
spike). This exists so the async seam is real and runnable, not faked: it will fail
visibly if Redis is unreachable, and it clearly announces that it is a skeleton.
"""

from __future__ import annotations

import logging
import os
import signal
import sys
from types import FrameType

import redis

JOB_QUEUE = "hadp:jobs"
logger = logging.getLogger("hadp_worker")

_running = True


def _stop(_signum: int, _frame: FrameType | None) -> None:
    global _running
    _running = False


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    redis_url = os.environ.get("REDIS_URL", "redis://127.0.0.1:56379/0")
    client = redis.Redis.from_url(redis_url)
    client.ping()  # fail visibly if Redis is unreachable
    logger.info("worker started (SKELETON: no clinical job processing yet) queue=%s", JOB_QUEUE)

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    while _running:
        item = client.blpop([JOB_QUEUE], timeout=5)
        if item is None:
            continue
        # A real implementation would dispatch idempotently with retries; for now, log only.
        logger.info("received job (not processed in skeleton): id=%s", "<redacted>")

    logger.info("worker stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
