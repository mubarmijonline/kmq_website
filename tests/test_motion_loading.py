"""Rendered-page contract for loading the motion runtime."""

import re

from app import create_app


def test_home_loads_gsap_before_the_application_bundle(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "motion-test-key")
    app = create_app({
        "ENV_NAME": "prod",
        "DATABASE_URL": None,
        "WHATSAPP_NUMBER": "",
    })
    html = app.test_client().get("/en/").get_data(as_text=True)
    scripts = re.findall(r'<script[^>]+src="([^"]+)"', html)

    assert scripts[-3:] == [
        "https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js",
        "https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/ScrollTrigger.min.js",
        next(src for src in scripts if re.fullmatch(r"/static/build/kmq\.[0-9a-f]{10}\.js", src)),
    ]

    tags = re.findall(r"<script\b[^>]*>", html)
    motion_tags = tags[-3:]
    assert all(" defer" in tag and " async" not in tag for tag in motion_tags)
    assert (
        'integrity="sha384-XmJ9SoHtVOHoQUcKvFAzVXwdkKo1Ie3bhmSoIAkcdsHGaIrVJIkmozyq0FJeb/Ly"'
        in motion_tags[0]
    )
    assert (
        'integrity="sha384-wl5TeDVvOWt30Pbf8aSo2ZrzsOjddu3avOBvHe+p+OhJt9gP6w9YXmDkN5DK2/dF"'
        in motion_tags[1]
    )
    assert all('crossorigin="anonymous"' in tag for tag in motion_tags[:2])
