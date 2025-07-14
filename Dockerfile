FROM python:3.11-slim

# 设置环境变量
# PYTHONDONTWRITEBYTECODE: 防止 Python 写入 .pyc 文件
# PYTHONUNBUFFERED: 确保 Python 输出是无缓冲的，便于在 Docker 日志中实时查看
# PYTHONPATH: 将/app目录添加到PYTHONPATH，这样Python就可以找到wqb模块
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /app

# 设置工作目录
WORKDIR /app

# 复制 pyproject.toml 文件
COPY pyproject.toml ./

# 从 pyproject.toml 中提取并安装依赖
# 这个方法可以避免 setuptools 在构建时因动态版本号而找不到本地模块的问题
RUN pip install toml && \
    python -c "import toml; config = toml.load('pyproject.toml'); deps = config['project']['dependencies']; [print(d) for d in deps]" > requirements.txt && \
    pip install -r requirements.txt

# 复制所有项目代码
COPY . .

# 这个基础镜像不设置默认的CMD，使其更灵活
# 启动命令将在 docker-compose.yml 或 docker run 命令中指定

