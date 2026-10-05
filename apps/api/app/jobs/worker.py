import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Mapping
from contextlib import suppress
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.jobs import queue

logger = logging.getLogger(__name__)

Payload = dict[str, Any]


@dataclass(frozen=True, slots=True)
class JobHandler:
    run: Callable[[Payload], Awaitable[None]]
    # Chamado quando as tentativas se esgotam, para refletir a falha no domínio.
    on_give_up: Callable[[Payload], Awaitable[None]] | None = None


class Worker:
    STALE_CHECK_SECONDS = 60

    def __init__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
        handlers: Mapping[str, JobHandler],
        settings: Settings,
    ) -> None:
        self._sessionmaker = sessionmaker
        self._handlers = handlers
        self._settings = settings
        self._last_stale_check = 0.0

    async def run_once(self) -> bool:
        """Processa um job, se houver. Devolve False quando a fila está vazia."""
        async with self._sessionmaker() as db:
            await self._requeue_stale_jobs(db)
            job = await queue.claim_next(db)
        if job is None:
            return False

        handler = self._handlers.get(job.kind)
        log = {"job_id": str(job.id), "kind": job.kind, "attempt": job.attempts}
        try:
            if handler is None:
                raise LookupError(f"Nenhum handler para jobs do tipo {job.kind!r}.")
            started = time.perf_counter()
            await handler.run(job.payload)
        except Exception as exc:
            logger.exception("Job falhou", extra=log)
            async with self._sessionmaker() as db:
                retry = await queue.fail(
                    db, job, f"{type(exc).__name__}: {exc}", self._settings.job_retry_base_seconds
                )
            if not retry and handler is not None and handler.on_give_up is not None:
                await handler.on_give_up(job.payload)
        else:
            async with self._sessionmaker() as db:
                await queue.complete(db, job.id)
            logger.info(
                "Job concluído",
                extra=log | {"duration_ms": round((time.perf_counter() - started) * 1000)},
            )
        return True

    async def run_until_empty(self) -> int:
        processed = 0
        while await self.run_once():
            processed += 1
        return processed

    async def run_forever(self, stop: asyncio.Event) -> None:
        logger.info("Worker iniciado")
        while not stop.is_set():
            try:
                processed = await self.run_once()
            except Exception:
                # Banco indisponível, por exemplo: espera e tenta de novo.
                logger.exception("Falha no laço do worker")
                processed = False
            if not processed:
                with suppress(TimeoutError):
                    await asyncio.wait_for(stop.wait(), timeout=self._settings.worker_poll_seconds)
        logger.info("Worker encerrado")

    async def _requeue_stale_jobs(self, db: AsyncSession) -> None:
        now = time.monotonic()
        if now - self._last_stale_check < self.STALE_CHECK_SECONDS:
            return
        self._last_stale_check = now
        stale_after = timedelta(minutes=self._settings.job_stale_minutes)
        if requeued := await queue.requeue_stale(db, stale_after):
            logger.warning("Jobs presos devolvidos à fila", extra={"count": requeued})
