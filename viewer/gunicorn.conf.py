"""Gunicorn configuration for Study Viewer."""
import multiprocessing

# Server socket
bind = "127.0.0.1:5050"

# Worker processes
workers = min(multiprocessing.cpu_count(), 4)
worker_class = "sync"
timeout = 120
preload_app = True

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
