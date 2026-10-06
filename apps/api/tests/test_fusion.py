from app.retrieval.fusion import reciprocal_rank_fusion


def test_item_found_by_both_searches_beats_the_top_of_a_single_one() -> None:
    scores = reciprocal_rank_fusion([["a", "b", "c"], ["c", "d"]], k=60)

    assert max(scores, key=scores.__getitem__) == "c"
    assert scores["a"] > scores["b"] == scores["d"]


def test_empty_rankings_produce_no_scores() -> None:
    assert reciprocal_rank_fusion([[], []], k=60) == {}
