FROM python:3.13.3-slim

# Set working directory
WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git curl wget vim tmux unzip zip tree htop iputils-ping dnsutils netcat-openbsd connect-proxy ffmpeg locales locales-all zsh \
    nodejs npm \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set Chinese locale and timezone
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN echo "zh_CN.UTF-8 UTF-8" > /etc/locale.gen && locale-gen zh_CN.UTF-8 && update-locale LANG=zh_CN.UTF-8 LANGUAGE=zh_CN:zh LC_ALL=zh_CN.UTF-8
ENV LANG=zh_CN.UTF-8
ENV LANGUAGE=zh_CN:zh
ENV LC_ALL=zh_CN.UTF-8

# Optional: Set pip mirrors
RUN pip config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

# Upgrade pip
RUN python -m pip install --upgrade pip

# Install uv, pipx, debugpy
RUN pip install --no-cache-dir uv pipx debugpy && pipx ensurepath

# Install mcp-proxy
RUN pipx install mcp-proxy

# Install oh-my-zsh and powerlevel10k
RUN sh -c "$(wget -O- https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" || true
RUN git clone --depth=1 https://github.com/romkatv/powerlevel10k.git ${ZSH_CUSTOM:-/root/.oh-my-zsh/custom}/themes/powerlevel10k || true
RUN echo 'ZSH_THEME="powerlevel10k/powerlevel10k"' >> ~/.zshrc

# Install fonts
RUN apt-get update && apt-get install -y fonts-powerline && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt

# Install Python dependencies
RUN if [ -f requirements.txt ]; then uv pip install -r requirements.txt --system; fi

# Pre-create directories
RUN mkdir -p /workspace/pids /workspace/logs /root/.ssh

# Common aliases
RUN echo 'alias ls="ls --color=auto"' && \
    echo 'alias ll="ls -al"' >> ~/.zshrc && \
    echo 'alias grep="grep --color=auto"' >> ~/.zshrc && \
    echo 'alias tmux="tmux attach -t main || tmux new -s main"' >> ~/.zshrc && \
    echo 'alias cls="clear"' >> ~/.zshrc

# Add common aliases
RUN echo 'alias ls="ls --color=auto"' >> ~/.bashrc && \
    echo 'alias ll="ls -al"' >> ~/.bashrc && \
    echo 'alias grep="grep --color=auto"' >> ~/.bashrc && \
    echo 'alias tmux="tmux attach -t main || tmux new -s main"' >> ~/.bashrc && \
    echo 'alias cls="clear"' >> ~/.bashrc

# Default command for easy attach
CMD ["tail", "-f", "/dev/null"]