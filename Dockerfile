FROM sitespeedio/sitespeed.io:35.3.0

USER root

ENV WEBPERF_RUNNER=docker

ENV PUPPETEER_SKIP_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome

ENV PATH="/usr/local/bin:${PATH}"

# https://codereview.stackexchange.com/a/286565
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

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
RUN groupadd --system sitespeedio && \
    useradd --system --create-home --gid sitespeedio sitespeedio && \
    mkdir --parents /usr/src/runner
RUN chown --recursive sitespeedio:sitespeedio /usr/src/runner

WORKDIR /usr/src/runner

RUN echo 'ALL ALL=NOPASSWD: /usr/sbin/tc, /usr/sbin/route, /usr/sbin/ip' > /etc/sudoers.d/tc

RUN npm install -g node-gyp puppeteer

# If own settings.json exists it will overwrite the default
COPY . /usr/src/runner

RUN chown --recursive sitespeedio:sitespeedio /usr/src/runner

# Run everything after as non-privileged user.
USER sitespeedio

RUN npm install --omit=dev

RUN python3.12 -m pip install -r requirements.txt --break-system-packages && \
    python3.12 -m pip install --upgrade pip --break-system-packages && \
    python3.12 -m pip install --upgrade setuptools --break-system-packages && \
    python3.12 -m pip install pyssim Pillow image --break-system-packages

RUN python3.12 default.py --setting tests.lighthouse.disable-sandbox=true --setting tests.sitespeed.xvfb=true --save-setting settings.json

ENTRYPOINT []

CMD ["python3.12", "default.py -h"]
