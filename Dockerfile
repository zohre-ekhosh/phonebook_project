# Dockerfile for Phonebook Management System
FROM python:3.11-slim

WORKDIR /app

# Copy project files
COPY requirements.txt .
COPY main.py .
COPY database.py .
COPY assets/ ./assets/

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p contact_photos phonebook_data

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8550

# Run the application
CMD ["python", "main.py"]