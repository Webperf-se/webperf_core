FROM sitespeedio/webbrowsers:chrome-124.0-firefox-125.0-edge-123.0

ENV WEBPERF_RUNNER docker

ENV PUPPETEER_SKIP_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome-stable

ENV PATH="/usr/local/bin:${PATH}"

# https://codereview.stackexchange.com/a/286565
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND noninteractive

# RUN ls /usr/bin/python*

RUN apt-get update &&\
    apt-get install -y --no-install-recommends curl gcc g++ gnupg unixodbc-dev openssl git default-jre default-jdk && \
    apt-get install -y software-properties-common ca-certificates && \
    apt-get install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libssl-dev libreadline-dev libffi-dev wget libbz2-dev libsqlite3-dev && \
    update-ca-certificates && \
    rm -rf /var/lib/apt/lists/*
    
# TODO: Check Python version used, there are no need to remove python if we have correct version

# List all python packages installed
RUN dpkg -l | grep python

RUN add-apt-repository ppa:deadsnakes/ppa

RUN apt install -y python3.12

RUN apt install -y curl

RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py

RUN python3.12 get-pip.py

# List all python packages installed
# RUN dpkg -l | grep python

# # Remove python packages
# RUN apt-get -y remove python.*
# RUN apt-get -y remove python3.*

# # Autoremove any dependencies left behind after the uninstall
# RUN apt-get -y autoremove

# Remove old pip3 (Python), as it is too old
# RUN apt-get purge --auto-remove python3-pip

# Remove old Python, as it was 3.10 and not 3.12 that we needed
# RUN apt remove -y --auto-remove python3

# List all python packages installed
# RUN dpkg -l | grep python

# RUN mkdir /python && cd /python && \
#     wget https://www.python.org/ftp/python/3.12.2/Python-3.12.2.tgz && \
#     tar -zxvf Python-3.12.2.tgz && \
#     cd Python-3.12.2 && \
#     ls -lhR && \
#     ./configure --enable-optimizations --prefix=/usr/local/ && \
#     make install && \
#     rm -rf /python

# List all python packages installed
RUN dpkg -l | grep python

# Add user so we don't need --no-sandbox.
RUN groupadd --system pptruser && \
    useradd --system --create-home --gid pptruser pptruser && \
    mkdir --parents /usr/src/app
RUN chown --recursive pptruser:pptruser /usr/src/app

WORKDIR /usr/src/app

RUN echo 'ALL ALL=NOPASSWD: /usr/sbin/tc, /usr/sbin/route, /usr/sbin/ip' > /etc/sudoers.d/tc

RUN npm install -g node-gyp puppeteer

RUN wget -q -O vnu.jar https://github.com/validator/validator/releases/download/latest/vnu.jar

# If own config.py exists it will overwrite the SAMPLE
COPY . /usr/src/app

RUN chown --recursive pptruser:pptruser /usr/src/app

# Run everything after as non-privileged user.
USER pptruser

RUN npm install

# RUN echo 'alias python=python3.12' >> ~/.bashrc && \
#     echo 'alias pip=pip3' >> ~/.bashrc

# RUN source ~/.bashrc

# RUN echo "alias python='python3.12'" >> ~/.profile
# RUN echo "alias pip=pip3'" >> ~/.profile

# RUN source ~/.profile

# RUN pip install -r requirements.txt --break-system-packages && \
#     python -m pip install --upgrade pip --break-system-packages && \
#     python -m pip install --upgrade setuptools --break-system-packages && \
#     python -m pip install pyssim Pillow image --break-system-packages

CMD ["python3.12", "--version"]
