# Calibration and results

## Straight-line speed
- 55% power: 160 cm in 2 s, about 0.80 m/s.
- A 0.2 m/s speed command gave 60 cm in 3 s, which matches the command.

## Turning on the spot
- 30% power: barely turns.
- 35% power: about 0.4 rad/s.
- 38-40% power: about 0.5 rad/s.
- 65% power: about 2.4 rad/s.
On-spot turns need about 32-35% power to start.

## First full test run (before the final fixes)
- 16 of 20 goals reached in one 10-minute run. 27 goals were sent in total. 7 were sent while the LiDAR was disconnected, so they could not start and are not counted.
- 4 misses: 3 goals stopped because the LiDAR dropped during the trip (the rover stopped itself, as designed), and 1 got stuck in a tight turn. Both causes were fixed after this run.
- Total autonomous travel 34+ m, added over the 16 reached goals as straight-line distances from start to goal. The real driven path is longer. Longest single trip 5.4 m, and three trips were over 5 m.
- Average speed on the long trips about 0.13-0.18 m/s (for example 5.4 m in about 30 s).
- The goal counts come from the Nav2 log on the Pi ("Goal succeeded", "Transform data too old", "Failed to make progress").
- This was the initial result. The misses showed exactly what to fix: the LiDAR drops (motor noise) and the stalled tight turn (weak turning power).

## Final run (after all the fixes)
- 20 of 20 goals reached, with no LiDAR drops.
- By the final run, all the fixes in our workflow were in place: noise capacitors on the motors, driver and converter; our custom-made LiDAR cable reconnected; the LiDAR guard v3; a stronger curve setting (6.0); the scan gate; and the faster Nav2 settings (0.40 m/s, rectangle footprint).
- The Pi's kernel log showed only one USB reset in the final session, and that was our own test of the guard.
- The rover was also demonstrated live at the Open Day: manual control, real-time mapping, and navigation on live and saved maps.

## LiDAR dropouts
3 dropouts caused by motor noise in the first 10-minute test run. 0 in the final run. Measured from the LiDAR guard log and the Pi kernel log.

## WiFi
Before the fix: 9 of 10 pings lost, and the one that arrived took 1190 ms. After switching off WiFi power saving: 171 of 171 pings arrived while driving, 11 ms on average.

## Pi 5 load
While running SLAM and Nav2: 48-52 C, never throttled (throttled=0x0), load average about 1-2 out of 4 cores. LiDAR end-to-end rate about 6.85 Hz.

## Known limits of these results
- Each result (16 of 20 first, 20 of 20 final) comes from a single run, not from many repeated runs.
- Goal accuracy uses the rover's own SLAM position. It was not checked with a tape measure.
- The Gazebo simulation was used to check the software, not to measure performance numbers.
