# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container to /app
WORKDIR /app

# Copy the local directory contents into the container
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 7860 to access the app
EXPOSE 7860
ENV GRADIO_SERVER_NAME="0.0.0.0"

# Command to run the application
CMD ["python", "app.py"]
