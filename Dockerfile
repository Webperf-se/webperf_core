FROM sitespeedio/webbrowsers:chrome-124.0-firefox-125.0-edge-123.0

ENV WEBPERF_RUNNER docker

ENV PUPPETEER_SKIP_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome-stable

ENV PATH="/usr/local/bin:${PATH}"

# https://codereview.stackexchange.com/a/286565
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update &&\
    apt-get install -y --no-install-recommends curl gcc g++ gnupg unixodbc-dev openssl git default-jre default-jdk && \
    apt-get install -y software-properties-common ca-certificates && \
    apt-get install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libssl-dev libreadline-dev libffi-dev wget libbz2-dev libsqlite3-dev && \
    update-ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# NOTE: Python speed improvements from: https://tecadmin.net/how-to-install-python-3-12-on-ubuntu/
RUN add-apt-repository ppa:deadsnakes/ppa -y

RUN apt update

RUN apt install -y python3.12 python3.12-venv

RUN apt install -y python3-pip

RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 311

RUN update-alternatives --config python3

RUN apt install -y python3.12-distutils

RUN wget https://bootstrap.pypa.io/get-pip.py

RUN python3.12 get-pip.py

RUN apt -y autoremove

# Add user so we don't need --no-sandbox.
RUN groupadd --system pptruser && \
    useradd --system --create-home --gid pptruser pptruser && \
    mkdir --parents /usr/src/app
RUN chown --recursive pptruser:pptruser /usr/src/app

WORKDIR /usr/src/app

RUN echo 'ALL ALL=NOPASSWD: /usr/sbin/tc, /usr/sbin/route, /usr/sbin/ip' > /etc/sudoers.d/tc

RUN npm install -g node-gyp puppeteer

# If own settings.json exists it will overwrite the default
COPY . /usr/src/app

RUN chown --recursive pptruser:pptruser /usr/src/app

# Run everything after as non-privileged user.
USER pptruser

RUN npm install

RUN python3.12 -m pip install -r requirements.txt --break-system-packages && \
    python3.12 -m pip install --upgrade pip --break-system-packages && \
    python3.12 -m pip install --upgrade setuptools --break-system-packages && \
    python3.12 -m pip install pyssim Pillow image --break-system-packages


CMD ["python3.12", "default.py -h"]
