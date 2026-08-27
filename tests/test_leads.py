"""The enquiry inbox, from the visitor's submission to the badge going down.

Every test writes a real lead through the public contact form and reads it
back through the admin, because a lead the admin cannot see is the whole
failure this inbox exists to prevent. Leads are deleted by the phone numbers
these tests use, which no real enquiry can hold.
"""

from __future__ import annotations

import pytest
from conftest import csrf, needs_db  # noqa: F401 - fixtures come from conftest

from app import leads

#: Every lead these tests write, one short of a full number: E.164 for a Saudi
#: mobile is +9665 and eight digits, and each test supplies the last three.
#: The cleanup deletes by this prefix, so it can never touch a real enquiry.
TEST_PHONE_PREFIX = "+966500000"


@pytest.fixture()
def inbox(admin_app):
    """The app with the test leads cleared before and after."""
    _clear_leads(admin_app)
    yield admin_app
    _clear_leads(admin_app)


def _clear_leads(app) -> None:
    with app.extensions["kmq_db"].cursor() as conn:
        conn.execute("DELETE FROM lead WHERE phone LIKE %s",
                     (f"{TEST_PHONE_PREFIX}%",))
        conn.commit()


def submit(app, *, name="Test Visitor", tail="001", notes="") -> None:
    """Send one enquiry the way a visitor does, through the form."""
    client = app.test_client()
    response = client.post("/ar/contact-us", data={
        "full_name": name,
        "phone": f"{TEST_PHONE_PREFIX}{tail}",
        "service": "ppf-gloss",
        "car_model": "Porsche 911",
        "branch": "al-rimal",
        "timing": "this-week",
        "notes": notes,
    })
    # The form answers 200 either way; only the confirmation proves it stored.
    assert response.status_code == 200, response.data[:400]
    from app import content as C
    assert C.AR["contact_ok_title"] in response.data.decode(), \
        "the form was rejected rather than stored"


@needs_db
def test_a_submitted_form_is_waiting_in_the_inbox(inbox, owner):
    submit(inbox, name="Waiting Visitor")

    assert leads.waiting_count(inbox.extensions["kmq_db"]) == 1

    html = owner.get("/admin/leads").data.decode()
    assert "Waiting Visitor" in html
    assert "Porsche 911" in html
    assert "Al Rimal Branch" in html
    assert "waiting" in html


@needs_db
def test_the_sidebar_counts_what_is_waiting(inbox, owner):
    assert 'class="adm__count"' not in owner.get("/admin/").data.decode()

    submit(inbox, tail="002")
    submit(inbox, tail="003")

    html = owner.get("/admin/").data.decode()
    assert 'class="adm__count"' in html
    assert "2 waiting" in html


@needs_db
def test_marking_handled_clears_it_from_the_queue(inbox, owner):
    submit(inbox, name="Handled Visitor")
    database = inbox.extensions["kmq_db"]
    lead_id = leads.recent(database)[0]["id"]

    response = owner.post(f"/admin/leads/{lead_id}/handled", data={
        "csrf_token": csrf(owner, "/admin/leads"),
        "handled": "1",
    })
    assert response.status_code == 302

    assert leads.waiting_count(database) == 0
    assert leads.get(database, lead_id)["waiting"] is False
    # Gone from the default view, still there when everything is asked for.
    assert "Handled Visitor" not in owner.get("/admin/leads").data.decode()
    assert "Handled Visitor" in owner.get("/admin/leads?show=all").data.decode()


@needs_db
def test_a_handled_enquiry_can_be_put_back(inbox, owner):
    submit(inbox, name="Reopened Visitor")
    database = inbox.extensions["kmq_db"]
    lead_id = leads.recent(database)[0]["id"]
    leads.set_handled(database, lead_id, handled=True, actor=None)

    response = owner.post(f"/admin/leads/{lead_id}/handled", data={
        "csrf_token": csrf(owner, "/admin/leads?show=all"),
        "handled": "0",
    })
    assert response.status_code == 302
    assert leads.waiting_count(database) == 1


@needs_db
def test_handling_a_lead_is_recorded_in_the_audit_trail(inbox, owner):
    submit(inbox, tail="004")
    database = inbox.extensions["kmq_db"]
    lead_id = leads.recent(database)[0]["id"]

    owner.post(f"/admin/leads/{lead_id}/handled", data={
        "csrf_token": csrf(owner, "/admin/leads"),
        "handled": "1",
    })

    from app import audit
    rows = audit.recent(database, entity="lead")
    assert rows and rows[0]["entity_id"] == str(lead_id)


@needs_db
def test_an_unknown_lead_is_404(inbox, owner):
    response = owner.post("/admin/leads/999999999/handled", data={
        "csrf_token": csrf(owner, "/admin/leads"),
        "handled": "1",
    })
    assert response.status_code == 404


@needs_db
def test_the_inbox_needs_a_session(inbox):
    response = inbox.test_client().get("/admin/leads")
    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]


@needs_db
def test_codes_are_shown_as_words_and_the_phone_as_a_link(inbox, owner):
    submit(inbox, tail="005", notes="يرجى التواصل مساءً")
    row = leads.recent(inbox.extensions["kmq_db"])[0]

    assert row["service_label"] == "PPF Gloss"
    assert row["timing_label"] == "This week"
    assert row["wa_url"] == "https://wa.me/966500000005"

    html = owner.get("/admin/leads").data.decode()
    assert "PPF Gloss" in html
    assert "https://wa.me/966500000005" in html
    # An Arabic note inside an English interface has to say so.
    assert 'dir="rtl"' in html
