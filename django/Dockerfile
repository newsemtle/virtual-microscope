# Use an official Python runtime as a base image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Copy the project files to the container
COPY . .

# Install system dependencies
RUN apt update && apt install -y libpq-dev && rm -rf /var/lib/apt/lists/*

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port Daphne will run on
# (docker-compose can override this)
EXPOSE 8000

# Run Daphne
# (docker-compose can override this)
CMD ["daphne", "config.asgi:application", "-b", "0.0.0.0", "-p", "8000"]