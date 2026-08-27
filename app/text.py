"""Normalising the two kinds of user input this site accepts.

Both problems are the same problem: an Arabic-speaking visitor may type
digits in Arabic-Indic or Eastern Arabic-Indic form, and a plate or phone
number that reads identically to a human must match identically in Postgres.
Folding happens once, on the way in, and the folded form is what gets stored
and queried.
"""

from __future__ import annotations

import re

#: U+0660–0669 (Arabic-Indic) and U+06F0–06F9 (Eastern Arabic-Indic, used in
#: Persian and Urdu keyboards that Saudi users sometimes have installed).
_DIGITS = {ord("٠") + i: str(i) for i in range(10)}
_DIGITS.update({ord("۰") + i: str(i) for i in range(10)})

#: Arabic letters that appear on Saudi plates, mapped to the Latin letter the
#: plate carries on its other half. A plate is issued with both, so a visitor
#: may type either. Source: the Latin transliteration printed on the plate.
_PLATE_LETTERS = {
    "أ": "A", "ا": "A",   # أ / ا  -> A
    "ب": "B",                   # ب
    "ح": "J",                   # ح
    "د": "D",                   # د
    "ر": "R",                   # ر
    "س": "S",                   # س
    "ص": "X",                   # ص
    "ط": "T",                   # ط
    "ع": "E",                   # ع
    "ق": "G",                   # ق
    "ك": "K",                   # ك
    "ل": "L",                   # ل
    "م": "Z",                   # م
    "ن": "N",                   # ن
    "ه": "H",                   # ه
    "و": "U",                   # و
    "ي": "V",                   # ي
}

_NOT_ALNUM = re.compile(r"[^0-9A-Z]")


def fold_digits(value: str) -> str:
    """Arabic-Indic digits to ASCII."""
    return value.translate(_DIGITS)


def normalise_lookup(value: str) -> str:
    """Fold a plate or invoice number to its canonical comparison form.

    Case, spacing, punctuation and script all vary between how a plate is
    printed, how a customer types it, and how the back office entered it.
    Everything reduces to upper-case ASCII alphanumerics so that
    ``أ ب ج ١٢٣٤``, ``ABJ-1234`` and ``abj 1234`` are one key.
    """
    folded = fold_digits(value.strip().upper())
    folded = "".join(_PLATE_LETTERS.get(ch, ch) for ch in folded)
    return _NOT_ALNUM.sub("", folded)


#: Saudi mobile numbers are 9 digits beginning with 5, reached as +9665XXXXXXXX.
_SAUDI_MOBILE = re.compile(r"^(?:\+?966|00966|0)?(5\d{8})$")


def normalise_saudi_phone(value: str) -> str | None:
    """Return ``+9665XXXXXXXX``, or ``None`` if it is not a Saudi mobile.

    Accepts the four forms people actually type — ``0512345678``,
    ``512345678``, ``+966512345678``, ``00966512345678`` — in either digit
    script, with any spacing or dashes.
    """
    digits = _NOT_ALNUM.sub("", fold_digits(value.strip().upper()).replace("+", ""))
    # The leading + is stripped above; put the country code back in scope by
    # matching against the bare digit run.
    match = _SAUDI_MOBILE.match(digits)
    if not match:
        return None
    return "+966" + match.group(1)


def collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


#: An article body is plain text, not HTML: it is written in a textarea by
#: whoever is on the marketing team that month, and rendering their input as
#: markup would make every article an injection surface. Two conventions are
#: honoured, both of which survive being pasted out of a Word document —
#: a blank line starts a paragraph, and a line opening with ## is a
#: subheading.
_HEADING = "##"


def blocks(body: str) -> list[tuple[str, str]]:
    """Split an article body into ``("h" | "p", text)`` pairs."""
    if not body:
        return []
    out: list[tuple[str, str]] = []
    for chunk in re.split(r"\n\s*\n", body.replace("\r\n", "\n").strip()):
        chunk = chunk.strip()
        if not chunk:
            continue
        if chunk.startswith(_HEADING):
            out.append(("h", chunk.lstrip("#").strip()))
        else:
            out.append(("p", collapse_spaces(chunk.replace("\n", " "))))
    return out
