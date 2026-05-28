# gunicorn_conf.py
import multiprocessing

# 1. Worker Count: (2 x cores) + 1 is the standard rule
workers = multiprocessing.cpu_count() * 2 + 1

# 2. Worker Class: Use 'uvicorn' for FastAPI/Starlette, 'gevent' for Flask/Django
worker_class = 'uvicorn.workers.UvicornWorker'

# 3. Prevent Memory Leaks: Restart workers after 1000 requests
max_requests = 1000
max_requests_jitter = 50  # Prevents all workers from restarting at the same time

# 4. Timeouts: Increase if you have slow API calls (default is 30)
timeout = 60

# 5. Keep-Alive: Helps with performance behind a Load Balancer (Nginx/AWS)
keepalive = 5
