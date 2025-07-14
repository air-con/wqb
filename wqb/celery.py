from celery import Celery

# 创建一个Celery应用实例
app = Celery('wqb')

# 从celeryconfig.py文件中加载配置
app.config_from_object('celeryconfig')

# 自动发现所有任务
# Celery会自动查找在task_imports中列出的模块里的任务
app.autodiscover_tasks()
