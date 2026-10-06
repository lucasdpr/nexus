from app.rag.citations import finalize_answer
from app.rag.prompt import NOT_FOUND_ANSWER


def test_keeps_valid_citations_in_order_of_first_use() -> None:
    answer = finalize_answer("A garantia é de 24 meses [S2]. Conta da instalação [S1][S2].", 3)

    assert answer.answered
    assert answer.markers == [2, 1]
    assert answer.text == "A garantia é de 24 meses [S2]. Conta da instalação [S1][S2]."


def test_removes_citations_of_sources_that_do_not_exist() -> None:
    answer = finalize_answer("Prazo de 24 meses [S1] [S9].", 2)

    assert answer.markers == [1]
    assert answer.text == "Prazo de 24 meses [S1]."


def test_grouped_markers_are_split_and_validated() -> None:
    answer = finalize_answer("Vale para os dois modelos [S1, S4, S2].", 3)

    assert answer.markers == [1, 2]
    assert answer.text == "Vale para os dois modelos [S1][S2]."


def test_answer_without_any_valid_source_becomes_not_found() -> None:
    for raw in ("O prazo é de 99 meses.", "O prazo é de 99 meses [S7].", "   "):
        answer = finalize_answer(raw, 2)

        assert not answer.answered
        assert answer.text == NOT_FOUND_ANSWER
        assert answer.markers == []


def test_model_declining_to_answer_is_recorded_as_not_answered() -> None:
    answer = finalize_answer(f"{NOT_FOUND_ANSWER} [S1]", 2)

    assert not answer.answered
    assert answer.markers == []
