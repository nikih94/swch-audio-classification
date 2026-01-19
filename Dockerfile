FROM nikih94/audio_classification_base_image:latest

WORKDIR /app
COPY src ./src
CMD ["python", "src/main.py"]
