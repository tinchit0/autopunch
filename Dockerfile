FROM python:3.12.6-slim-bullseye

# System dependencies
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl

# Firefox
RUN apt-get update && apt-get install -y firefox-esr

# Install Geckodriver
RUN GECKODRIVER_VERSION=v0.35.0 && \
    wget -q "https://github.com/mozilla/geckodriver/releases/download/$GECKODRIVER_VERSION/geckodriver-$GECKODRIVER_VERSION-linux64.tar.gz" -O /tmp/geckodriver.tar.gz && \
    tar -xzf /tmp/geckodriver.tar.gz -C /usr/local/bin && \
    rm /tmp/geckodriver.tar.gz && \
    chmod +x /usr/local/bin/geckodriver

WORKDIR /app
ADD . /app
RUN pip install .

ENTRYPOINT ["autopunch"]
CMD ["punch"]
