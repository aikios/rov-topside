FROM ros:jazzy

ENV DEBIAN_FRONTEND=noninteractive

# Install ROS2 packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-jazzy-rmw-cyclonedds-cpp \
    ros-jazzy-mavros-msgs \
    ros-jazzy-image-transport \
    ros-jazzy-compressed-image-transport \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
RUN pip3 install --break-system-packages evdev websockets

# Set up workspace
WORKDIR /ros_ws
COPY src/ src/

# Build all topside packages (rov_joystick, rov_dashboard, rov_photogrammetry)
RUN . /opt/ros/jazzy/setup.sh && \
    colcon build --symlink-install

# DDS config — uses env var CYCLONEDDS_URI at runtime for flexibility
COPY cyclonedds_topside.xml /ros_ws/cyclonedds.xml

# Environment
ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
ENV CYCLONEDDS_URI=file:///ros_ws/cyclonedds.xml

# Web dashboard ports
EXPOSE 8080 9090

# Entrypoint
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
