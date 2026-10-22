# Rover overview

## What the rover does
The rover builds a map of an unknown indoor space while it drives (SLAM), and then drives itself to any goal clicked on that map (Nav2). It uses one 2D LiDAR as its main sensor. There are no wheel encoders. Motion is tracked by comparing LiDAR scans (laser odometry with rf2o). Everything (LiDAR driver, motor control, SLAM and Nav2) runs on the Raspberry Pi 5. The laptop only shows the map in RViz.

## What we demonstrated
- Manual driving with the keyboard.
- Real-time mapping with SLAM Toolbox while driving.
- Autonomous navigation to goals on the live map, and on a saved map.
- All of these both in the Gazebo simulation and on the real rover.

## Where it could be used
Mapping a building after a disaster (fire, gas leak, partial collapse) before people go in, and showing rescuers a safe route. This links to SDG 11 (safer cities and communities). A second use is mapping warehouse or factory floors and reaching inspection points (SDG 9). For real rubble it would need bigger wheels, a 3D sensor and an IMU. The mapping and navigation software would stay the same.

## Team and guide
Team 6: Abdul Rahman Khan, M. Yashwanth and Pranav Pujari, Department of AI and ML, Global Academy of Technology, Bengaluru. Guide: Prof. Vijaya Dalawai, Assistant Professor, Dept of AIML. Project title: Autonomous Mobile Rover with Real-Time Mapping and Navigation.

## Main parts
- Computer: Raspberry Pi 5, 4 GB, running Ubuntu Server 24.04 and ROS 2 Jazzy.
- LiDAR: Slamtec RPLiDAR A1M8, 360 degree 2D laser scanner, connected over USB with our own custom-made cable to its adapter board, about 6.85 scans per second on our rover.
- Motor driver: TB6612FNG dual H-bridge. One board drives all 4 motors and stays cool.
- Motors: 4 x 12 V BO gear motors, 200 RPM.
- Power: 3S LiPo battery, 2200 mAh (11.1 V nominal, 12.6 V full), and an XY-3606 5 V converter for the Pi.
- IMU: MPU6050 on I2C. Wired, but switched off for now (see the problems notes).
- Noise capacitors: 0.1 uF ceramic (104) on each motor, 470 uF + 0.1 uF on the driver's motor supply, 1000 uF + 0.1 uF on the converter's 5 V output.

## Drive type
The rover is 4-wheel drive with skid steering. There are no steering wheels. It turns like a tank: the left and right sides run at different speeds. The left pair of motors is on driver channel A and the right pair on channel B. Front and rear motors on each side are wired together.

## Measurements
- Length 28 cm, width 24.5 cm. Nav2 uses a 30 x 26 cm rectangle as the rover's shape.
- Wheelbase (front axle to rear axle): 18 cm.
- Track (left tyre centre to right tyre centre): 22 cm.
- Wheel size: 11 cm.
- LiDAR: 8.5 cm in front of the rover centre, laser height 21.5 cm above the floor.
- The LiDAR is mounted facing backwards (rotated 180 degrees). The robot model file tells the software this.

## Software pipeline
1. LiDAR driver publishes scans on the /scan topic.
2. A scan gate holds scans until the robot model is loaded, then passes them to the laser odometry.
3. Laser odometry (rf2o) compares each scan with the previous one to estimate how far the rover moved and turned.
4. SLAM Toolbox builds the map (5 cm squares, updated every 2 seconds) and corrects the rover position.
5. Nav2 plans a path on the map and follows it with the Regulated Pure Pursuit controller.
6. The motor node turns Nav2 speed commands into PWM power for the left and right sides.
7. A LiDAR guard script (version 3) watches the scans. If they stop, it resets the LiDAR's USB and restarts the LiDAR program.

## Nav2 settings
- Top speed 0.40 m/s for straight driving. Nav2 slows down on curves and near obstacles.
- Turning speed about 0.6 rad/s.
- Rover shape: a 30 x 26 cm rectangle (earlier a 40 cm circle).
- Obstacles are marked only up to 2.5 m away, because far LiDAR points are the noisiest.
- Safety zone (inflation) around obstacles: 0.30 m.
- A goal counts as reached when the heading is within about 20 degrees (0.35 rad).

## Motor node settings
- Minimum duty 10%, maximum duty 80%.
- Turning on the spot: a short kick at 42% power, then at least 38% sustain power (plus 0.08 per 1 rad/s asked), with a re-kick every 1.5 s so slow turns do not stall.
- Turning while driving: curve gain 6.0 (raised from 2.0, which was too weak for skid steer).
- Gentle slew ramps for speed changes.
- Safety timeout 0.5 s: motors stop if no command arrives.

## Limits
- Indoor only. Strong sunlight confuses the A1M8, and laser odometry needs walls to compare against.
- The LiDAR sees one flat slice at 21.5 cm height. Obstacles lower than about 25 cm may not be seen.
- No wheel encoders and no IMU at present, so fast turns can smear the map.
- Do not lift the rover while SLAM is running. It spoils the map.
