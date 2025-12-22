FROM sitespeedio/sitespeed.io:39.2.0

USER root

ENV WEBPERF_RUNNER=docker

ENV PUPPETEER_SKIP_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome

ENV PATH="/usr/local/bin:${PATH}"

# https://codereview.stackexchange.com/a/286565
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# phantomas should pick this up and use --no-sandbox
ENV LAMBDA_TASK_ROOT=/trick/phantomas

RUN apt-get update &&\
    apt-get install -y --no-install-recommends curl gcc g++ gnupg unixodbc-dev openssl git default-jre default-jdk && \
    apt-get install -y software-properties-common ca-certificates && \
    apt-get install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libssl-dev libreadline-dev libffi-dev wget libbz2-dev libsqlite3-dev && \
    update-ca-certificates && \
    rm -rf /var/lib/apt/lists/*

RUN apt -y autoremove

# Add user so we don't need --no-sandbox.
RUN groupadd --system sitespeedio && \
    useradd --system --create-home --gid sitespeedio sitespeedio && \
    mkdir --parents /usr/src/runner
RUN chown --recursive sitespeedio:sitespeedio /usr/src/runner

WORKDIR /usr/src/runner

RUN echo 'ALL ALL=NOPASSWD: /usr/sbin/tc, /usr/sbin/route, /usr/sbin/ip' > /etc/sudoers.d/tc

# https://github.com/puppeteer/puppeteer/issues/8148#issuecomment-1397528849
RUN Xvfb -ac :99 -screen 0 1280x1024x16 & export DISPLAY=:99

RUN npm install -g node-gyp puppeteer-core npm-check-updates

# If own settings.json exists it will overwrite the default
COPY . /usr/src/runner

# Use same parameters phantomas
COPY pa11y-docker-config.json /usr/src/runner/pa11y.json

RUN chown --recursive sitespeedio:sitespeedio /usr/src/runner

RUN python3 -m pip install -r requirements.txt --break-system-packages && \
    python3 -m pip install --upgrade pip --break-system-packages && \
    python3 -m pip install --upgrade setuptools --break-system-packages && \
    python3 -m pip install pyssim Pillow image --break-system-packages

# Run everything after as non-privileged user.
USER sitespeedio

RUN npm install --omit=dev

RUN python3 default.py --setting tests.sitespeed.xvfb=true --save-setting settings.json

ENTRYPOINT []

CMD ["python3", "default.py -h"]
