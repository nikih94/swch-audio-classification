# FROM arm64v8/python:3.10-bookworm
FROM python:3.10-slim-bookworm

# Set the working directory inside the container.
WORKDIR /app

RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install dependencies.
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy code and metadata into /app.
COPY src/ ./src/
COPY metadata/ ./metadata/
COPY resources/ ./resources/

# Expose the port the Waitress server is listening on.
EXPOSE 42002

# Start the application
CMD ["python", "src/main.py"]
