# ============================================
# Gunicorn Configuration
# Optimized for Render Free Tier (512MB RAM)
# ============================================

import os

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

# Worker processes
workers = 2  # Keep low for 512MB RAM
worker_class = "sync"
threads = 2

# Timeout (high for cold starts)
timeout = 120
graceful_timeout = 30

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Preload app for faster worker spawning
preload_app = True

# Restart workers after handling N requests (prevent memory leaks)
max_requests = 500
max_requests_jitter = 50
