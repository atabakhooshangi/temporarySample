FROM 172.18.10.100:4040/python:3.11-slim-bullseye
# Set working directory
RUN echo "LC_ALL=fa_IR.UTF-8" | tee -a /etc/environment
RUN echo "fa_IR.UTF-8 UTF-8" | tee -a /etc/locale.gen
RUN echo "LANG=fa_IR.UTF-8" | tee -a /etc/locale.conf
RUN  locale-gen fa_IR.UTF-8

WORKDIR /app
# Copy requirements file
COPY requirements.txt . 

# Set pip configuration
COPY production.pip.conf /etc/pip.conf

# Update pip and install requirements
RUN pip install  pip==23.3.1 && \
    pip install -r requirements.txt

# Copy code and environment files
COPY . .
COPY config/.production.env src/core/.env

# Give execute permissions to start.sh
RUN chmod +x /app/start.sh
WORKDIR /app/src

# Expose port 80
EXPOSE 80

# Set environment variable
ENV PYTHONUNBUFFERED 1

# Start command
CMD ["bash", "/app/start.sh"]
