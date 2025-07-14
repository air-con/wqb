# ---- STAGE 1: Builder ----
# 使用一个功能齐全的 Python 镜像作为构建环境
FROM python:3.11 as builder

# 设置工作目录
WORKDIR /app

# 仅复制构建依赖所需的文件
COPY pyproject.toml ./

# 创建一个虚拟环境来安装依赖，这是一个好习惯
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 安装依赖并将它们编译成 wheel 文件，存放在 /wheels 目录
# 这会处理您项目的所有依赖
RUN pip install --upgrade pip && \
    pip wheel . -w /wheels


# ---- STAGE 2: Final ----
# 使用精简的镜像作为最终的生产环境
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 创建一个非 root 用户来运行应用，这是一个安全最佳实践
RUN useradd --create-home appuser
USER appuser

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 从构建阶段复制预编译的 wheel 文件
COPY --from=builder /wheels /wheels

# 从本地的 wheel 文件安装所有依赖，无需编译，也无需访问网络
RUN /opt/venv/bin/pip install --no-index --find-links=/wheels /wheels/*.whl

# 复制所有项目代码
COPY --chown=appuser:appuser . .

# 将虚拟环境的路径加入到 PATH 中
ENV PATH="/opt/venv/bin:$PATH"

# CMD/ENTRYPOINT 将在 docker-compose.yml 中定义