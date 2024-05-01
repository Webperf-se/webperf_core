FROM sitespeedio/webbrowsers:chrome-124.0-firefox-125.0-edge-123.0

ENV WEBPERF_RUNNER docker

ENV PUPPETEER_SKIP_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome-stable

ENV PATH="/usr/local/bin:${PATH}"

# https://codereview.stackexchange.com/a/286565
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND noninteractive

RUN ls /usr/bin/python*

RUN apt-get update &&\
    apt-get install -y --no-install-recommends curl gcc g++ gnupg unixodbc-dev openssl git default-jre default-jdk && \
    apt-get install -y software-properties-common ca-certificates && \
    apt-get install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libssl-dev libreadline-dev libffi-dev wget libbz2-dev libsqlite3-dev && \
    update-ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# TODO: Check Python version used, there are no need to remove python if we have correct version

# List all python packages installed
RUN dpkg -l | grep python

# Remove python packages
RUN apt-get -y remove python.*
RUN apt-get -y remove python3.*

# Autoremove any dependencies left behind after the uninstall
RUN apt-get autoremove

# Remove old pip3 (Python), as it is too old
# RUN apt-get purge --auto-remove python3-pip

# Remove old Python, as it was 3.10 and not 3.12 that we needed
# RUN apt remove -y --auto-remove python3

RUN ls /usr/bin/python*

RUN mkdir /python && cd /python && \
    wget https://www.python.org/ftp/python/3.12.2/Python-3.12.2.tgz && \
    tar -zxvf Python-3.12.2.tgz && \
    cd Python-3.12.2 && \
    ls -lhR && \
    ./configure --enable-optimizations && \
    make install && \
    rm -rf /python

RUN ls /usr/bin/python*

# Add user so we don't need --no-sandbox.
RUN groupadd --system pptruser && \
    useradd --system --create-home --gid pptruser pptruser && \
    mkdir --parents /usr/src/app
RUN chown --recursive pptruser:pptruser /usr/src/app

WORKDIR /usr/src/app

RUN echo 'ALL ALL=NOPASSWD: /usr/sbin/tc, /usr/sbin/route, /usr/sbin/ip' > /etc/sudoers.d/tc

RUN npm install -g node-gyp puppeteer

RUN wget -q -O vnu.jar https://github.com/validator/validator/releases/download/latest/vnu.jar

# First add the SAMPLE file as real config
COPY SAMPLE-config.py /usr/src/app/config.py

# If own config.py exists it will overwrite the SAMPLE
COPY . /usr/src/app

RUN chown --recursive pptruser:pptruser /usr/src/app

# Run everything after as non-privileged user.
USER pptruser

RUN npm install

RUN echo 'alias python=python3' >> ~/.bashrc && \
    echo 'alias pip=pip3' >> ~/.bashrc

RUN pip install -r requirements.txt --break-system-packages && \
    python -m pip install --upgrade pip --break-system-packages && \
    python -m pip install --upgrade setuptools --break-system-packages && \
    python -m pip install pyssim Pillow image --break-system-packages

CMD ["python", "--version"]
