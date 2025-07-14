# 使用一个官方的、精简的 Python 镜像作为基础
FROM python:3.11-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 新增：安装系统级的构建依赖
# 这对于编译某些Python包的C扩展是必需的
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential python3-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 安装项目依赖
# 首先复制 pyproject.toml，如果它没有变化，Docker 会利用缓存，加快构建速度
COPY pyproject.toml ./
# 安装项目本身及其所有依赖
RUN pip install .

# 复制所有项目代码到工作目录
COPY . .

