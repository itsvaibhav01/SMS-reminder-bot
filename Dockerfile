# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Install any needed packages specified in requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download and install spacy-transformers and the en_core_web_trf model
RUN python -m spacy download en_core_web_trf

# Set the working directory in the container to /app
WORKDIR /app

# Add the current directory contents into the container at /app
ADD . /app

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable
ENV NAME World

# Run app.py using gunicorn when the container launches
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:5000"]
