FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the requirements and install them
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy the rest of the application code
COPY . .

# Install the wqb library
RUN pip install .

# Set the default command to keep the container running for interactive use
CMD ["tail", "-f", "/dev/null"]
