"""Gunicorn configuration for Multi-User Study Viewer."""
import multiprocessing

# Server socket
bind = "127.0.0.1:5051"

# Worker processes
workers = min(multiprocessing.cpu_count(), 4)
worker_class = "sync"
timeout = 120
preload_app = True

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
