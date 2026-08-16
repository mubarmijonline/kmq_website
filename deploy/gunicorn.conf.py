"""Gunicorn settings for kmq.

nginx owns the public port (4023) and 443 and proxies here. A port can
only be bound once, so gunicorn listens on 4024, on loopback only —
it must never be reachable from outside without nginx in front of it.

gthread rather than sync workers: these requests are I/O-bound, and threads keep
a slow upload from occupying a whole worker for its duration.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

bind = "127.0.0.1:4024"

workers = 2
worker_class = "gthread"
threads = 4

# Generous, because a large upload has to finish streaming to disk.
timeout = 180
graceful_timeout = 30
keepalive = 5

# See the note in the systemd unit: the default control-socket path is not
# writable under this unit's sandboxing.
control_socket = os.environ.get("GUNICORN_CTL", str(BASE_DIR / "logs" / "gunicorn.ctl"))
control_socket_mode = 0o660

chdir = str(BASE_DIR)
pythonpath = str(BASE_DIR)

accesslog = str(BASE_DIR / "logs" / "access.log")
errorlog = str(BASE_DIR / "logs" / "error.log")
loglevel = "info"
# %({X-Forwarded-For}i)s is the client as seen past nginx and the CDN.
access_log_format = '%({X-Forwarded-For}i)s %(t)s "%(r)s" %(s)s %(b)s %(M)sms "%(f)s"'

proc_name = "kmq"
# Trust X-Forwarded-* only from the local nginx.
forwarded_allow_ips = "127.0.0.1"

preload_app = False
max_requests = 2000
max_requests_jitter = 200
