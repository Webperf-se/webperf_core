FROM python:3.12.2-slim-bookworm

ARG TARGETPLATFORM=linux/amd64

ENV WEBPERF_RUNNER docker

ENV SITESPEED_IO_BROWSERTIME__DOCKER true
ENV SITESPEED_IO_BROWSERTIME__VIDEO false
ENV SITESPEED_IO_BROWSERTIME__BROWSER chrome
ENV SITESPEED_IO_BROWSERTIME__VISUAL_METRICS false
ENV SITESPEED_IO_BROWSERTIME__HEADLESS true

ENV PUPPETEER_SKIP_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome-stable

ENV PATH="/usr/local/bin:${PATH}"

RUN echo "deb http://deb.debian.org/debian/ stable main contrib non-free" >> /etc/apt/sources.list.d/debian.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends firefox-esr tcpdump iproute2 ca-certificates sudo imagemagick libjpeg-dev xz-utils ffmpeg gnupg gnupg2 wget libjpeg-dev libfontconfig build-essential gconf-service lsb-release xdg-utils fonts-liberation xvfb default-jdk nodejs npm --no-install-recommends --no-install-suggests --fix-missing && \
    apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && rm -rf /var/lib/apt/lists/* /tmp/*

RUN echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list && \
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add - && \
    apt-get update && \
    apt-get install -y --no-install-recommends google-chrome-stable && \
    apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && rm -rf /var/lib/apt/lists/* /tmp/*

# Add user so we don't need --no-sandbox.
RUN groupadd --system pptruser && \
  useradd --system --create-home --gid pptruser pptruser && \
  mkdir --parents /usr/src/app
RUN chown --recursive pptruser:pptruser /usr/src/app

WORKDIR /usr/src/app

RUN echo 'ALL ALL=NOPASSWD: /usr/sbin/tc, /usr/sbin/route, /usr/sbin/ip' > /etc/sudoers.d/tc

RUN npm install -g node-gyp
RUN npm install -g puppeteer

RUN wget -q -O vnu.jar https://github.com/validator/validator/releases/download/latest/vnu.jar

COPY . /usr/src/app
COPY Dockerfile-config.py /usr/src/app/config.py

RUN chown --recursive pptruser:pptruser /usr/src/app

# Run everything after as non-privileged user.
USER pptruser

RUN npm install pa11y
RUN npm install yellowlabtools
RUN npm install lighthouse
RUN npm install sitespeed.io

RUN pip install -r requirements.txt --break-system-packages
RUN python -m pip install --upgrade pip --break-system-packages
RUN python -m pip install --upgrade setuptools --break-system-packages
RUN python -m pip install pyssim Pillow image --break-system-packages