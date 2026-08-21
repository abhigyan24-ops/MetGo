FROM python:3.11-slim

WORKDIR /app

# Copy requirements files
COPY kmrl-backend/requirements.txt ./kmrl-backend/requirements.txt
COPY LOCKWOOD/requirements.txt ./LOCKWOOD/requirements.txt

# Install Python packages
RUN pip install --no-cache-dir -r kmrl-backend/requirements.txt
RUN pip install --no-cache-dir -r LOCKWOOD/requirements.txt

# Copy source directories
COPY kmrl-backend ./kmrl-backend
COPY LOCKWOOD ./LOCKWOOD

# Set Python path to support sys.path and lockwood resolving
ENV PYTHONPATH=/app/LOCKWOOD

WORKDIR /app/kmrl-backend

EXPOSE 8000

# Default command for the Web API service
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
