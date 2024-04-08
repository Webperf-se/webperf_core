FROM python:3.12.2-slim-bookworm

ARG TARGETPLATFORM=linux/amd64

ENV WEBPERF_RUNNER docker

ENV NODE_VERSION 20.4.0

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
    apt-get install -y --no-install-recommends firefox-esr tcpdump iproute2 ca-certificates curl dirmngr xz-utils libatomic1 sudo imagemagick libjpeg-dev xz-utils ffmpeg gnupg gnupg2 wget libjpeg-dev libfontconfig build-essential gconf-service lsb-release xdg-utils fonts-liberation xvfb default-jdk --no-install-recommends --no-install-suggests --fix-missing && \
    apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && rm -rf /var/lib/apt/lists/* /tmp/*

RUN echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list && \
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add - && \
    apt-get update && \
    apt-get install -y --no-install-recommends google-chrome-stable && \
    apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
    && rm -rf /var/lib/apt/lists/* /tmp/*

# https://github.com/nodejs/docker-node/blob/31bc0387d4a2eea9e9fee4d5b1f8dca0e0596dca/20/bookworm-slim/Dockerfile
RUN ARCH= && dpkgArch="$(dpkg --print-architecture)" \
    && case "${dpkgArch##*-}" in \
      amd64) ARCH='x64';; \
      ppc64el) ARCH='ppc64le';; \
      s390x) ARCH='s390x';; \
      arm64) ARCH='arm64';; \
      armhf) ARCH='armv7l';; \
      i386) ARCH='x86';; \
      *) echo "unsupported architecture"; exit 1 ;; \
    esac \
    && set -ex \
    && for key in \
      4ED778F539E3634C779C87C6D7062848A1AB005C \
      141F07595B7B3FFE74309A937405533BE57C7D57 \
      74F12602B6F1C4E913FAA37AD3A89613643B6201 \
      DD792F5973C6DE52C432CBDAC77ABFA00DDBF2B7 \
      61FC681DFB92A079F1685E77973F295594EC4689 \
      8FCCA13FEF1D0C2E91008E09770F7A9A5AE15600 \
      C4F0DFFF4E8C1A8236409D08E73BC641CC11F4C8 \
      890C08DB8579162FEE0DF9DB8BEAB4DFCF555EF4 \
      C82FA3AE1CBEDC6BE46B9360C43CEC45C17AB93C \
      108F52B48DB57BB0CC439B2997B01419BD92F80A \
    ; do \
      gpg --batch --keyserver hkps://keys.openpgp.org --recv-keys "$key" || \
      gpg --batch --keyserver keyserver.ubuntu.com --recv-keys "$key" ; \
    done \
    && curl -fsSLO --compressed "https://nodejs.org/dist/v$NODE_VERSION/node-v$NODE_VERSION-linux-$ARCH.tar.xz" \
    && curl -fsSLO --compressed "https://nodejs.org/dist/v$NODE_VERSION/SHASUMS256.txt.asc" \
    && gpg --batch --decrypt --output SHASUMS256.txt SHASUMS256.txt.asc \
    && grep " node-v$NODE_VERSION-linux-$ARCH.tar.xz\$" SHASUMS256.txt | sha256sum -c - \
    && tar -xJf "node-v$NODE_VERSION-linux-$ARCH.tar.xz" -C /usr/local --strip-components=1 --no-same-owner \
    && rm "node-v$NODE_VERSION-linux-$ARCH.tar.xz" SHASUMS256.txt.asc SHASUMS256.txt \
    && find /usr/local -type f -executable -exec ldd '{}' ';' \
      | awk '/=>/ { so = $(NF-1); if (index(so, "/usr/local/") == 1) { next }; gsub("^/(usr/)?", "", so); print so }' \
      | sort -u \
      | xargs -r dpkg-query --search \
      | cut -d: -f1 \
      | sort -u \
      | xargs -r apt-mark manual \
    && ln -s /usr/local/bin/node /usr/local/bin/nodejs \
    && node --version \
    && npm --version

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