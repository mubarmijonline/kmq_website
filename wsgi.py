"""WSGI entry point. gunicorn loads ``wsgi:application``."""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from app import create_app  # noqa: E402  (after load_dotenv, by design)

application = create_app()

#: The house systemd template starts `gunicorn ... wsgi:app`. `application`
#: stays canonical — it is the WSGI convention — and this alias means a
#: re-rendered unit file keeps working rather than failing at boot on an
#: attribute name.
app = application

if __name__ == "__main__":
    application.run(port=5200, debug=True)
