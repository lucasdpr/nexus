from app.ingestion.normalization import normalize_text


def test_joins_words_hyphenated_at_line_breaks() -> None:
    assert normalize_text("plano de manu-\ntenção") == "plano de manutenção"


def test_collapses_spaces_and_special_spaces() -> None:
    no_break_space = chr(0xA0)
    assert normalize_text(f"válvula{no_break_space}{no_break_space}de   alívio\t\tPSV") == (
        "válvula de alívio PSV"
    )


def test_removes_control_characters_and_soft_hyphens() -> None:
    assert normalize_text(f"tor{chr(0xAD)}que{chr(0x07)} de aperto") == "torque de aperto"


def test_keeps_paragraphs_but_collapses_extra_blank_lines() -> None:
    assert normalize_text("Seção 1\r\n\r\n\r\n\r\n  Seção 2  ") == "Seção 1\n\nSeção 2"
