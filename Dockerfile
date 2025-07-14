# 使用一个功能更齐全的 Python 镜像，它基于 Debian "Bullseye"
# 这个镜像已经包含了大部分编译 C 扩展所需的工具
FROM python:3.11-bullseye

# 安装 Rust 编译器，这是 cryptography 等包的硬性要求
RUN apt-get update && \
    apt-get install -y --no-install-recommends rustc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制项目依赖定义文件
COPY pyproject.toml ./

# 安装所有依赖，包括项目本身
# 在这个功能齐全的环境中，这个命令将会成功
RUN pip install --upgrade pip && \
    pip install .

# 复制所有项目代码
COPY . .

# CMD/ENTRYPOINT 将在 docker-compose.yml 中定义