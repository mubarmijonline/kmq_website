"""Server-side validation for the lead form.

Client-side validation is a courtesy; this is the check that counts. Every
rule below runs regardless of what the browser did, and a failure returns the
visitor's own answers so they never retype a form.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import content as C
from .text import collapse_spaces, normalise_saudi_phone


@dataclass
class LeadForm:
    locale: str
    values: dict[str, str] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def error_for(self, name: str) -> str | None:
        key = self.errors.get(name)
        if key is None:
            return None
        return C.LEAD_ERRORS[self.locale][key]

    def value_for(self, name: str) -> str:
        return self.values.get(name, "")


def _choices(locale: str, source: str) -> set[str]:
    getter = {
        "service_options": C.service_options,
        "branch_options": C.branch_options,
        "timing_options": C.timing_options,
    }[source]
    return {value for value, _label in getter(locale)}


def validate_lead(raw: dict[str, str], locale: str) -> LeadForm:
    form = LeadForm(locale=locale)

    for spec in C.LEAD_FIELDS:
        name = spec["name"]
        value = collapse_spaces(raw.get(name, ""))
        form.values[name] = value

        if not value:
            if spec["required"]:
                form.errors[name] = "required"
            continue

        maxlength = spec.get("maxlength")
        if maxlength and len(value) > maxlength:
            form.errors[name] = "too_long"
            continue

        if spec["type"] == "select":
            if value not in _choices(locale, spec["options"]):
                form.errors[name] = "choice"
            continue

        if name == "phone":
            normalised = normalise_saudi_phone(value)
            if normalised is None:
                form.errors[name] = "phone"
            else:
                # Keep what they typed on screen, store the canonical form.
                form.values["phone_e164"] = normalised

    return form


def lead_payload(form: LeadForm, *, ip_hash: str, user_agent: str) -> dict[str, Any]:
    """Turn a validated form into the row the database expects."""
    return {
        "full_name": form.values["full_name"],
        "phone": form.values["phone_e164"],
        "service": form.values["service"],
        "car_model": form.values["car_model"],
        "branch_id": form.values["branch"],
        "timing": form.values["timing"],
        "notes": form.values.get("notes") or None,
        "locale": form.locale,
        "ip_hash": ip_hash,
        "user_agent": user_agent[:400],
    }
