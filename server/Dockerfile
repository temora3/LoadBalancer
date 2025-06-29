FROM python:3.9-slim

WORKDIR /app

# Install Flask
RUN pip install flask

# Copy server code
COPY server.py .

# Expose port 5000
EXPOSE 5000

# Run the server
CMD ["python", "server.py"]