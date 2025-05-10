FROM python:3.11-slim

# Cài đặt OS dependencies (nếu dùng asyncpg)
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Tạo thư mục và copy code vào
WORKDIR /app
COPY . .

# Cài dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Đảm bảo PYTHONPATH để dùng được lệnh kiểu: python -m api.migrate
ENV PYTHONPATH=/app

# Lệnh mặc định cho container app (FastAPI)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
