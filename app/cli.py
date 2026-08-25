"""Command-line entry points.

    flask --app wsgi:app seed-content
    flask --app wsgi:app create-owner you@example.com "Your Name"
"""

from __future__ import annotations

import secrets
import string

import click
from flask import current_app
from flask.cli import with_appcontext

from . import store

#: Generated passwords. Long enough that the throttle is the only defence
#: anyone needs, and unambiguous — no l/I/O/0 to mis-transcribe over a phone.
_ALPHABET = "".join(c for c in string.ascii_letters + string.digits if c not in "lIO0")


def register(app) -> None:
    app.cli.add_command(seed_content)
    app.cli.add_command(create_owner)
    app.cli.add_command(reset_password)


@click.command("seed-content")
@click.option("--force", is_flag=True,
              help="Overwrite rows that already exist, discarding edits.")
@with_appcontext
def seed_content(force: bool) -> None:
    """Fill the content store from the copy shipped in app/content.py."""
    database = current_app.extensions["kmq_db"]
    if not database.enabled:
        raise click.ClickException("No DATABASE_URL: nothing to seed.")

    if force:
        click.confirm(
            "--force overwrites stored content with the shipped copy, "
            "discarding every edit made in the admin. Continue?",
            abort=True,
        )

    counts = store.seed(database, force=force)
    click.echo(f"copy strings: {counts['copy']}")
    click.echo(f"content entries: {counts['entries']}")
    click.echo(f"branch columns filled: {counts['branches']}")

    with database.cursor() as conn:
        store.bump_version(conn)
        conn.commit()
    click.echo("content_version bumped.")


@click.command("create-owner")
@click.argument("email")
@click.argument("display_name")
@with_appcontext
def create_owner(email: str, display_name: str) -> None:
    """Create the first owner account and print its password once."""
    from .auth import create_user

    database = current_app.extensions["kmq_db"]
    if not database.enabled:
        raise click.ClickException("No DATABASE_URL: cannot create an account.")

    password = "".join(secrets.choice(_ALPHABET) for _ in range(20))
    try:
        create_user(database, email=email, display_name=display_name,
                    password=password, role="owner")
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo("")
    click.echo("  Owner account created.")
    click.echo(f"  email:    {email}")
    click.echo(f"  password: {password}")
    click.echo("")
    click.echo("  This password is shown once and is not stored anywhere.")
    click.echo("  You must change it at first sign-in before anything else.")
    click.echo("")


@click.command("reset-password")
@click.argument("email")
@with_appcontext
def reset_password(email: str) -> None:
    """Issue a new one-time password and force a change at next sign-in."""
    from .auth import set_password

    database = current_app.extensions["kmq_db"]
    if not database.enabled:
        raise click.ClickException("No DATABASE_URL.")

    password = "".join(secrets.choice(_ALPHABET) for _ in range(20))
    if not set_password(database, email=email, password=password,
                        must_change=True, revoke_sessions=True):
        raise click.ClickException(f"No account for {email}.")

    click.echo("")
    click.echo(f"  password: {password}")
    click.echo("  Existing sessions for this account are now signed out.")
    click.echo("")
