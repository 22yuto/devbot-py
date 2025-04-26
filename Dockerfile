FROM python:3

ARG USERNAME=user
ARG GROUPNAME=user
ARG UID=1000
ARG GID=1000
RUN groupadd -g $GID $GROUPNAME && \
    useradd -m -s /bin/bash -u $UID -g $GID $USERNAME

# システムのロケールと環境設定
RUN apt-get update && apt-get install -y \
    vim \
    less \
    locales \
    && localedef -f UTF-8 -i ja_JP ja_JP.UTF-8 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV LANG ja_JP.UTF-8
ENV LANGUAGE ja_JP:ja
ENV LC_ALL ja_JP.UTF-8
ENV TZ JST-9
ENV TERM xterm

WORKDIR /home/$USERNAME/

# Pythonパッケージのインストール
COPY requirements.txt ./
RUN pip install --upgrade pip setuptools && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install openai==1.25.1 python-dotenv jupyterlab

# ローカルのソースコードをコピー
COPY . .

# ユーザー切り替え
USER $USERNAME
