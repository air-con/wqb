# 使用一个官方的、精简的 Python 镜像作为基础
FROM python:3.11-slim

# 设置环境变量，防止 Python 写入 .pyc 文件
ENV PYTHONDONTWRITEBYTECODE 1
# 确保 Python 输出是无缓冲的，便于在 Docker 日志中实时查看
ENV PYTHONUNBUFFERED 1

# 设置工作目录
WORKDIR /app

# 安装项目依赖
# 首先复制 pyproject.toml，如果它没有变化，Docker 会利用缓存，加快构建速度
COPY pyproject.toml ./
# 安装项目本身及其所有依赖
RUN pip install .

# 复制所有项目代码到工作目录
COPY . .

# CMD 不在这里设置，因为我们将为每个服务在 docker-compose.yml 中指定不同的启动命令