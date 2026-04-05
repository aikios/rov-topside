FROM ros:jazzy

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install ROS2 packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-jazzy-rmw-cyclonedds-cpp \
    ros-jazzy-mavros-msgs \
    ros-jazzy-image-transport \
    ros-jazzy-compressed-image-transport \
    python3-pip \
    python3-tk \
    python3-pil \
    python3-pil.imagetk \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
RUN pip3 install --break-system-packages evdev

# Set up workspace
WORKDIR /ros_ws
COPY src/ src/

# Build
RUN . /opt/ros/jazzy/setup.sh && \
    colcon build --packages-select rov_topside --symlink-install

# DDS config
COPY cyclonedds_topside.xml /ros_ws/cyclonedds.xml

# Environment
ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
ENV CYCLONEDDS_URI=file:///ros_ws/cyclonedds.xml

# Entrypoint
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
