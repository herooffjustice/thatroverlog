# Problems and fixes

## LiDAR disconnects during turns (motor noise)
Symptom: during on-spot turns or sudden stops, the LiDAR USB connection dropped. In RViz the wheels turned white and the map stopped updating. Nav2 aborted goals with "Transform data too old", and the collision monitor stopped the rover.
Cause: electrical noise (EMI) from the motors. The kernel log (dmesg) showed "usb ... disabled by hub (EMI?)". It happened on both the blue USB 3.0 and black USB 2.0 ports. The 4-wheel skid-steer design pulls much more current in on-spot turns than the earlier 2-wheel design with a ball caster, because the wheels slide sideways.
Fixes, in the order we did them:
1. A LiDAR guard script that restarts the LiDAR automatically when scans stop. Version 3 finds the LiDAR by its stable USB ID, resets its USB straight away, and asks for a replug only if the USB does not come back.
2. Noise capacitors soldered at the sources: a 0.1 uF ceramic (code 104) across each of the 4 motors, 470 uF (25 V) + 0.1 uF across the TB6612 VM and GND pins, and 1000 uF + 0.1 uF across the converter's 5 V output to the Pi. After this, drops became much rarer.
3. Reconnected our custom-made LiDAR cable.
Result: 3 LiDAR dropouts in the first 10-minute test run, 0 in the final session.
Check command: sudo dmesg | grep -iE "EMI|disconnect"

## IMU freezes after the motors stop
Symptom: the MPU6050 IMU on I2C stops answering after the motors stop, and does not recover.
Test: standing still, 0% of readings failed. Driving straight at only 21% power for about 2 seconds, the IMU froze completely, and no software retry brought it back. Only cutting its power did.
Tried: slower I2C (50 kHz), retries and re-wake in the IMU program, a different timeout, gentle motor ramps, powering the Pi from a wall adapter, and the noise capacitors. The capacitors helped (before them it froze every time the motors stopped), but 2-19% of readings still fail while the motors run, and it can still freeze after they stop.
Why the IMU suffers more than the LiDAR: I2C is a slow, unprotected connection on two loose wires, so motor noise gets in easily, and the IMU chip locks up until its power is cut.
Status: paused. Navigation does not use it (USE_IMU = False). Next ideas, in order: a 0.1 uF + 10 uF capacitor right at the IMU board with short twisted wires kept away from the motor wires; powering the IMU from a GPIO pin so the program can switch it off and on when it freezes; or reading it on an ESP32 and sending the data to the Pi over USB.

## Map and rover missing in RViz
Symptom: RViz showed the LiDAR scans, but no map and no rover model. Map display showed a warning with width and height 0.
Cause: the launch file set FASTDDS_BUILTIN_TRANSPORTS=UDPv4. This forced large messages (the map and the robot description) through the WSL network layer, where they failed. Small messages like scans still worked.
Fix: removed that line from the launch file and rebuilt.

## Odometry ran backwards
Symptom: when the real rover drove forward, the rover in RViz moved backwards, and SLAM drew walls twice.
Cause: the LiDAR faces backwards. The laser odometry (rf2o) reads the LiDAR position only once, from the first scan. After moving everything onto the Pi, programs started faster, and the first scan sometimes arrived before the robot model was loaded. So the odometry assumed the LiDAR faced forward.
Fix: a scan gate. It holds scans back from the laser odometry until the LiDAR position is known, then waits 3 more seconds. SLAM and Nav2 still get scans directly.
How to check: the launch prints "Scans now go to the laser odometry." If it prints "base_footprint passed to lookupTransform ... does not exist", stop and start again.

## WiFi lag and packet loss
Symptom: about 1.2 s delay and 90% packet loss between the laptop and the Pi. Navigation froze when SLAM and Nav2 ran on the laptop.
Cause: WiFi power saving on the Pi. The WiFi chip sleeps between transmissions.
Fix: switch off power saving at every boot (iw dev wlan0 set power_save off, run from a boot job). Also moved SLAM and Nav2 onto the Pi, so the laptop only shows RViz.
Result: 171 of 171 pings arrived while driving, about 11 ms on average.

## Skid-steer turns stall
Symptom: slow on-spot turns stopped halfway.
Cause: a skid-steer rover needs high power to start turning, because the wheels must slide sideways. On-spot turns need about 32-35% power just to start.
Fix: in the motor node, a short kick at 42% power, then a sustain power of at least 38% with a re-kick every 1.5 s. Slew ramps keep speed changes gentle.

## Curves too weak while driving
Symptom: the rover did not follow the green path on curves. It drove almost straight, drifted off, stopped, spun on the spot and tried again. It looked stuck.
Cause: Nav2 asked for its strongest curve, but the left and right sides differed by only 8% power (curve gain 2.0). A 4-wheel skid-steer rover needs a much bigger difference to curve.
Fix: curve gain raised to 6.0. At Nav2's strongest curve the sides now differ by about 25%, and the rover follows the path.

## Too slow, and obstacle boundaries too thick
Symptom: the rover never went above 0.20 m/s, and the safety zones around walls were thick and messy, leaving little room in gaps.
Fix: Nav2 top speed 0.40 m/s for straight driving (turns stay slow). The rover's real shape, a 30 x 26 cm rectangle, instead of a 40 cm circle. Obstacles marked only up to 2.5 m away, because far points are the noisiest. Safety zone 0.30 m. In RViz, the global costmap display is switched off for a cleaner view.

## Wheels shown white in RViz
Symptom: the wheels in RViz were white with a RobotModel error.
Cause: the program that publishes wheel positions sometimes missed the model at start. The real rover has no wheel sensors anyway.
Fix: the wheels are fixed parts of the model on the real rover. They still turn in the simulation.

## Map drawn twice (star pattern)
Symptom: walls appear twice in a star-like pattern.
Cause: a LiDAR drop in the middle of a turn, or lifting the rover. Without encoders or an IMU, SLAM depends only on matching scans, and a large angle error is more than it can correct.
Fix: restart SLAM for a fresh map, keep the rover still at start, and drive gently.

## Nav2 hangs at start
Symptom: "failed to send response to /<node>/change_state (timeout)", or goals are ignored.
Fix: stop the navigation launch with Ctrl+C and start it again.

## RViz window does not appear (COPY MODE)
Symptom: on the WSL laptop, RViz or Gazebo shows only a taskbar icon or "COPY MODE", or freezes.
Fix: close it, run wsl --shutdown in PowerShell, wait 30 seconds, open Ubuntu again and test with xeyes.

## Laptop cannot see the Pi topics
Symptom: the laptop cannot see /scan from the Pi.
Cause: WSL lost network visibility after wsl --shutdown, or the Windows network profile for the hotspot was set to Public, which can block ROS discovery.
Fix: restart WSL, check ping, and set the network profile to Private.

## Hardware PWM failed with "Invalid argument"
Symptom: writing the PWM period on the Pi 5 failed.
Cause: wrong PWM channel numbers, and the pwm-2chan overlay was missing its clock setting.
Fix: use the right channels for the soldered pins (GPIO18 and GPIO19), and keep dtoverlay=pwm-2chan,clock=50000000 in config.txt.

## Left motor ran backwards
Cause: the left motor is mounted as a mirror image of the right.
Fix: LEFT_INVERTED = True in the motor code, which swaps the direction pins in software.

## Mechanical issues still open
- The front-left wheel was stiff and was refitted once.
- The left side is weaker than the right.
- In turns, the front wheels barely roll, and the rover pivots near the front axle.
