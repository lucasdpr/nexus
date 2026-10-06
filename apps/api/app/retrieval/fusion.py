from collections import defaultdict
from collections.abc import Hashable, Sequence


def reciprocal_rank_fusion[K: Hashable](rankings: Sequence[Sequence[K]], k: int) -> dict[K, float]:
    """Reciprocal Rank Fusion: combina listas ordenadas usando só a posição de cada item.

    Dispensa normalizar escalas incompatíveis (distância de cosseno e ranking de texto).
    Um item bem colocado nas duas buscas supera um que aparece no topo de só uma delas.
    """
    scores: defaultdict[K, float] = defaultdict(float)
    for ranking in rankings:
        for position, key in enumerate(ranking, start=1):
            scores[key] += 1 / (k + position)
    return dict(scores)
