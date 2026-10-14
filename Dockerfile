FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# 复制所有代码
COPY . .

# 暴露端口并自适应启动服务
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8080}"]

