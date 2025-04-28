# Chọn base image từ Python
FROM python:3.11-slim

# Cài đặt dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code của bạn vào trong container
COPY . /app

# Cài đặt uvicorn nếu chưa có
RUN pip install uvicorn

# Cấu hình command để chạy app FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]