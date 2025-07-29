"""
Gunicorn 配置文件
確保應用在 Gunicorn 環境下正確初始化
"""

import multiprocessing
import os

# 服務器配置
bind = "0.0.0.0:8080"
workers = 1  # 使用單一工作進程避免隊列共享問題
worker_class = "sync"
worker_connections = 1000
timeout = 300
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True  # 預加載應用

# 日誌配置
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 進程配置
daemon = False
pidfile = None
tmp_upload_dir = None

def when_ready(server):
    """當服務器準備好時的回調"""
    print("🚀 Gunicorn 服務器已準備就緒")

def worker_init(worker):
    """工作進程初始化時的回調"""
    print(f"🔧 工作進程 {worker.pid} 已初始化")

def on_starting(server):
    """服務器啟動時的回調"""
    print("🔄 Gunicorn 服務器正在啟動...")

def on_reload(server):
    """服務器重載時的回調"""
    print("🔄 Gunicorn 服務器正在重載...")

def post_fork(server, worker):
    """工作進程 fork 後的回調"""
    print(f"👶 工作進程 {worker.pid} 已 fork")
    
def pre_fork(server, worker):
    """工作進程 fork 前的回調"""
    print(f"🔄 準備 fork 工作進程...")

def worker_abort(worker):
    """工作進程異常終止時的回調"""
    print(f"💥 工作進程 {worker.pid} 異常終止")