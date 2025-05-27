FROM python:3.11-slim

# Cài OS dependencies
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Tạo thư mục và copy requirements trước
WORKDIR /app
COPY requirements.txt .

# Cài pip và requirements
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Sau đó mới copy toàn bộ project (code)
COPY . .

# ENV và CMD như cũ
ENV PYTHONPATH=/app
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
