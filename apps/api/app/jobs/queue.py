from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.models import Job, JobStatus


def enqueue(db: AsyncSession, kind: str, payload: dict[str, Any], *, max_attempts: int) -> Job:
    """Adiciona o job à transação corrente: só entra na fila se a transação for confirmada."""
    job = Job(kind=kind, payload=payload, max_attempts=max_attempts)
    db.add(job)
    return job


async def claim_next(db: AsyncSession) -> Job | None:
    """Reserva o próximo job pronto. SKIP LOCKED permite vários workers sem disputa."""
    next_id = (
        select(Job.id)
        .where(Job.status == JobStatus.QUEUED, Job.run_after <= func.now())
        .order_by(Job.run_after, Job.id)
        .limit(1)
        .with_for_update(skip_locked=True)
        .scalar_subquery()
    )
    statement = (
        update(Job)
        .where(Job.id == next_id)
        .values(status=JobStatus.RUNNING, locked_at=func.now(), attempts=Job.attempts + 1)
        .returning(Job)
        .execution_options(synchronize_session=False)
    )
    job = (await db.scalars(statement)).one_or_none()
    await db.commit()
    return job


async def complete(db: AsyncSession, job_id: UUID) -> None:
    await db.execute(
        update(Job)
        .where(Job.id == job_id)
        .values(status=JobStatus.DONE, finished_at=func.now(), locked_at=None, last_error=None)
    )
    await db.commit()


async def fail(db: AsyncSession, job: Job, error: str, retry_base_seconds: float) -> bool:
    """Registra a falha. Devolve True se o job voltou para a fila (backoff exponencial)."""
    retry = job.attempts < job.max_attempts
    values: dict[str, Any] = {"last_error": error[:1000], "locked_at": None}
    if retry:
        delay = timedelta(seconds=retry_base_seconds * 2 ** (job.attempts - 1))
        values |= {"status": JobStatus.QUEUED, "run_after": datetime.now(UTC) + delay}
    else:
        values |= {"status": JobStatus.FAILED, "finished_at": func.now()}
    await db.execute(update(Job).where(Job.id == job.id).values(**values))
    await db.commit()
    return retry


async def requeue_stale(db: AsyncSession, stale_after: timedelta) -> int:
    """Devolve à fila jobs presos em RUNNING (worker que caiu no meio do trabalho)."""
    result = await db.execute(
        update(Job)
        .where(Job.status == JobStatus.RUNNING, Job.locked_at < datetime.now(UTC) - stale_after)
        .values(status=JobStatus.QUEUED, locked_at=None)
    )
    await db.commit()
    return int(result.rowcount)  # type: ignore[attr-defined]
