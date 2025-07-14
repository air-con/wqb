# 依然使用 slim 镜像作为基础
FROM python:3.11-slim

# 在一步之内，安装所有可能的编译工具
# 这是为了确保任何包（包括需要 C 或 Rust 编译的）都能成功安装
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    cargo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY pyproject.toml ./

# 在这个准备充分的环境中，安装所有依赖
RUN pip install --upgrade pip && \
    pip install .

# 复制所有项目代码
COPY . .

# 容器的启动命令将在 docker-compose.yml 中定义
