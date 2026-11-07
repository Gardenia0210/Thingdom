"""Gunicorn config."""
import multiprocessing
import os

bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")

workers = 1
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "sync")
worker_connections = int(os.getenv("GUNICORN_WORKER_CONNECTIONS", "1000"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))

accesslog = os.getenv("GUNICORN_ACCESS_LOG", "-")
errorlog = os.getenv("GUNICORN_ERROR_LOG", "-")
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

proc_name = "kids_language_2"

preload_app = False
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "50"))

limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))

def on_starting(server):
    """On starting."""
    server.log.info("Gunicorn 服务器正在启动...")

def on_reload(server):
    """On reload."""
    server.log.info("Gunicorn 服务器正在重载...")

def when_ready(server):  
    """When ready."""
    server.log.info(f"Gunicorn 服务器已就绪，监听 {server.address}")

def on_exit(server):
    """On exit."""
    server.log.info("Gunicorn 服务器正在退出...")

def post_fork(server, worker):
    """Post fork."""

    server.log.info(f"Worker {worker.pid} 已启动，等待 Django 应用初始化...")

