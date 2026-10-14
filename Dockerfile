FROM python:3.11-slim

WORKDIR /app

# 直接安装核心依赖，彻底避免文件路径找不到的问题
RUN pip install --no-cache-dir fastapi uvicorn requests python-dotenv pydantic python-multipart

# 复制仓库中的所有文件
COPY . .

ENV PORT=8080
EXPOSE 8080

# 自动寻找 app.py 的位置并启动服务
CMD ["sh", "-c", "if [ -f app.py ]; then uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}; elif [ -f backend/app.py ]; then uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8080}; elif [ -f reading-ai-tool/backend/app.py ]; then cd reading-ai-tool/backend && uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}; else APP_DIR=$(dirname $(find . -name 'app.py' | head -n 1)); cd $APP_DIR && uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}; fi"]
