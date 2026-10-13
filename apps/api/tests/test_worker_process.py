import subprocess
import sys


def test_the_worker_module_can_map_every_table_on_its_own() -> None:
    """Num processo novo, só com o que `app.worker` importa, o mapeamento do banco fecha.

    Em produção o worker roda sozinho (`python -m app.worker`): se um modelo só for importado
    pela API, as chaves estrangeiras dele não resolvem e o worker quebra ao processar o primeiro
    documento, o que nenhum teste dentro do processo da API percebe.
    """
    code = (
        "import app.worker\n"
        "from sqlalchemy.orm import configure_mappers\n"
        "from app.core.models import Base\n"
        "configure_mappers()\n"
        "Base.metadata.sorted_tables\n"
    )
    result = subprocess.run(  # noqa: S603 (código fixo, sem entrada externa)
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )

    assert result.returncode == 0, result.stderr
