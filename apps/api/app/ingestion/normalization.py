import re
import unicodedata

SOFT_HYPHEN = chr(0xAD)

# Caracteres de controle, exceto tabulação e quebras de linha.
_CONTROL_CODES = [*range(0x09), 0x0B, 0x0C, *range(0x0E, 0x20), 0x7F]
_CONTROL = re.compile("[" + re.escape("".join(map(chr, _CONTROL_CODES))) + "]")
# Palavra quebrada em fim de linha pelo PDF ("manu-\ntenção"). Junta também compostos que
# caíram exatamente na quebra ("bem-\nestar" vira "bemestar"): troca aceita pela
# frequência muito maior do primeiro caso.
_HYPHENATED = re.compile(r"(\w)-\n(\w)")
_SPACES = re.compile(r"[ \t]+")
_BLANK_LINES = re.compile(r"\n{3,}")


def normalize_text(text: str) -> str:
    # NFKC também converte espaços especiais (não separável, fino...) em espaço comum.
    text = unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL.sub("", text.replace(SOFT_HYPHEN, ""))
    text = _HYPHENATED.sub(r"\1\2", text)
    text = _SPACES.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return _BLANK_LINES.sub("\n\n", text).strip()
