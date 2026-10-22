# Simulation work

## Isaac Sim warehouse rover
We started in NVIDIA Isaac Sim 5.1, installed with pip in a Python virtual environment on the lab PC (RTX A2000 12 GB). The script warehouse_rover.py places a Nova Carter rover in the Simple Warehouse scene. It drives to 4 coloured waste objects using an Artificial Potential Field (APF) planner written in pure Python, with no ROS 2. The goal pulls the rover towards it, and obstacles push it away. At each object it plays a 3-second pickup animation (the object shrinks until it disappears). A second script, rover_simulation.py, builds procedural grassy uneven terrain.

## Two-layer simulation idea
The world can be detailed and realistic (RTX rendering, rich terrain). The robot model must behave like the real hardware, including servo backlash, encoder drift and sensor noise. This keeps simulation results honest.

## Gazebo digital twin of the real rover
For the real rover, we built a Gazebo Harmonic simulation with ROS 2 Jazzy, running in WSL2 (Ubuntu 24.04) on a laptop. It uses the same robot model file as the real rover (body, 4 wheels and LiDAR position from real measurements). The simulated hardware has skid-steer drive for 4 wheels and a LiDAR at about 7 scans per second, like the A1M8. One launch file (sim_slam_nav.launch.py) starts Gazebo, the rover, the ROS-Gazebo bridge, the scan gate, laser odometry, SLAM Toolbox, Nav2 and RViz in the right order. There are two worlds: a corridor with obstacles and an empty world. An option switches between laser odometry and Gazebo's wheel odometry, to compare the two. The simulation uses the same Nav2 settings file as the real rover.

## How the simulation was used
The same ROS 2 software mapped the Gazebo world and reached goals there. We used the simulation to check the software before moving it to the real rover, not to measure performance numbers. In simulation, all programs run on the laptop, so it does not prove the Pi can handle the load. That was checked separately on the real rover.

## Separate ROS channel
The simulation runs on ROS_DOMAIN_ID 7. Even if the real rover is switched on, the simulation can never send commands to it, and the maps never mix.

## What the simulation did not show
Five real problems never appeared in simulation: WiFi power-save lag, navigation freezing over WiFi, backwards odometry from the start-up timing on the Pi, motor noise dropping the LiDAR USB, and stalled skid-steer turns. This is the main sim-to-real lesson of the project.
