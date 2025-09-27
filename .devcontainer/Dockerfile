FROM osrf/ros:humble-desktop

# Install dev tools, ROS2 extras, git, Python and pip
RUN apt-get update && apt-get install -y \
    python3 \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-vcstool \
    python3-pip \
    git \
    build-essential \
    ros-humble-rosbridge-server \
    # GUI + X11/WSL2 compatibility
    x11-apps \
    libx11-xcb1 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
    libxcb-randr0 libxcb-render-util0 libxcb-xinerama0 \
    mesa-utils \
    libgl1-mesa-glx \
    libglu1-mesa \
    libxext6 \
    libxrender1 \
    libxrandr2 \
    libxi6 \
    && rm -rf /var/lib/apt/lists/*

# Ensure pip is accessible as `pip`
RUN ln -sf /usr/bin/pip3 /usr/bin/pip

# Initialize rosdep
RUN rosdep init || true && rosdep update

# Install Ruff, pre-commit, uv globally
RUN pip install --no-cache-dir ruff pre-commit uv

# Add non-root user for VSCode devcontainer
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Auto-source ROS2 for all users
RUN echo "source /opt/ros/humble/setup.bash" >> /etc/bash.bashrc

# Set locale
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Ensure Qt apps can run
ENV QT_X11_NO_MITSHM=1
ENV QT_QPA_PLATFORM=xcb
ENV LIBGL_ALWAYS_SOFTWARE=1
ENV QT_XCB_GL_INTEGRATION=none

# Create a workspace for the non-root user
RUN mkdir -p /home/$USERNAME/workspace \
    && chown -R $USERNAME:$USERNAME /home/$USERNAME/workspace

# Set workspace directory
WORKDIR /home/$USERNAME/workspace

# Switch to non-root user by default in devcontainer
USER $USERNAME

# Allow pre-commit to run even if no config exists
ENV PRE_COMMIT_ALLOW_NO_CONFIG=1

RUN git init . \
    && pre-commit install --allow-missing-config || true