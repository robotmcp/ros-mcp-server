# Go2 ROS 2 Control Workspace

Complete ROS 2 workspace for controlling the Unitree Go2 quadruped robot via custom services.

## Workspace Structure

```
go2_ws/
├── src/
│   ├── go2_interfaces/          # Custom service definitions
│   │   ├── CMakeLists.txt
│   │   ├── package.xml
│   │   └── srv/
│   │       ├── Trigger.srv      # Simple trigger (no input)
│   │       ├── SetBool.srv      # Enable/disable features
│   │       ├── Move.srv         # Movement with velocity + distance
│   │       ├── SetFloat.srv     # Float parameter setting
│   │       └── SetInt.srv       # Integer parameter setting
│   │
│   └── go2_control/             # Main control package
│       ├── package.xml
│       ├── setup.py
│       ├── setup.cfg
│       ├── resource/
│       │   └── go2_control
│       └── go2_control/
│           ├── __init__.py
│           ├── go2_backend.py       # SDK communication (separate process)
│           └── go2_service_node.py  # ROS 2 services
```

## Build Instructions

```bash
cd ~/go2_ws
colcon build --symlink-install
source install/setup.bash
```

## Running

```bash
source ~/go2_ws/install/setup.bash
ros2 run go2_control go2_services
```

---

## Complete Service Reference

### Service Types

| Type | Description | Request Fields |
|------|-------------|----------------|
| `Trigger` | Simple actions | (none) |
| `SetBool` | Toggle features | `enable: bool` |
| `Move` | Movement control | `vx, vy, vyaw, distance` |
| `SetFloat` | Float parameters | `value: float64` |
| `SetInt` | Integer parameters | `value: int32` |

---

### POSTURE SERVICES (Trigger)

| Service | Description |
|---------|-------------|
| `/go2/damp` | **Emergency stop** - Enter damping state (highest priority) |
| `/go2/balance` | Enter balance stand mode (maintains posture on uneven terrain) |
| `/go2/stop` | Stop current action, restore parameters to defaults |
| `/go2/stand_up` | Stand up to high stance (0.33m default height) |
| `/go2/stand_down` | Lie down to low stance |
| `/go2/recovery` | Recovery stand - use after robot falls or is in unknown state |
| `/go2/sit` | Sit down (special sitting posture) |
| `/go2/rise_sit` | Stand up from sitting position |

```bash
# Examples
ros2 service call /go2/stand_up go2_interfaces/srv/Trigger
ros2 service call /go2/sit go2_interfaces/srv/Trigger
ros2 service call /go2/recovery go2_interfaces/srv/Trigger
```

---

### MOVEMENT SERVICE (Move)

**Service:** `/go2/move`

**Request Fields:**
- `vx` (float64): Forward velocity in m/s (range: -2.5 to 3.8)
- `vy` (float64): Lateral velocity in m/s (range: -1.0 to 1.0)
- `vyaw` (float64): Angular velocity in rad/s (range: -4.0 to 4.0)
- `distance` (float64): Distance in meters OR angle in radians

**Response Fields:**
- `success` (bool): Command accepted
- `message` (string): Execution details
- `estimated_time` (float64): Estimated completion time in seconds
- `iterations` (int32): Number of control iterations

**Note:** The robot automatically enters walking mode when needed. No need to call a separate "free_walk" service.

```bash
# Move forward 1 meter at 0.3 m/s
ros2 service call /go2/move go2_interfaces/srv/Move "{vx: 0.3, vy: 0.0, vyaw: 0.0, distance: 1.0}"

# Move backward 0.5 meters
ros2 service call /go2/move go2_interfaces/srv/Move "{vx: -0.3, vy: 0.0, vyaw: 0.0, distance: 0.5}"

# Strafe left 1 meter
ros2 service call /go2/move go2_interfaces/srv/Move "{vx: 0.0, vy: 0.2, vyaw: 0.0, distance: 1.0}"

# Strafe right 0.5 meters
ros2 service call /go2/move go2_interfaces/srv/Move "{vx: 0.0, vy: -0.2, vyaw: 0.0, distance: 0.5}"

# Turn left 90 degrees (π/2 ≈ 1.57 radians)
ros2 service call /go2/move go2_interfaces/srv/Move "{vx: 0.0, vy: 0.0, vyaw: 0.5, distance: 1.57}"

# Turn right 180 degrees (π ≈ 3.14 radians)
ros2 service call /go2/move go2_interfaces/srv/Move "{vx: 0.0, vy: 0.0, vyaw: -0.5, distance: 3.14}"

# Diagonal movement (forward-left)
ros2 service call /go2/move go2_interfaces/srv/Move "{vx: 0.2, vy: 0.2, vyaw: 0.0, distance: 1.0}"
```

---

### BODY CONFIGURATION SERVICES

#### `/go2/body_height` (SetFloat)
Set body height relative to default (0.33m).
- Range: -0.18 to 0.03 meters
- Example: `-0.1` sets height to 0.23m

```bash
ros2 service call /go2/body_height go2_interfaces/srv/SetFloat "{value: -0.1}"
```

#### `/go2/foot_raise_height` (SetFloat)
Set foot raise height relative to default (0.09m).
- Range: -0.06 to 0.03 meters

```bash
ros2 service call /go2/foot_raise_height go2_interfaces/srv/SetFloat "{value: 0.02}"
```

#### `/go2/speed_level` (SetInt)
Set speed range.
- `-1` = Slow
- `0` = Normal
- `1` = Fast

```bash
ros2 service call /go2/speed_level go2_interfaces/srv/SetInt "{value: 1}"
```

#### `/go2/switch_gait` (SetInt)
Switch gait mode.
- `0` = Idle
- `1` = Trot
- `2` = Trot running
- `3` = Forward climbing mode
- `4` = Reverse climbing mode

```bash
ros2 service call /go2/switch_gait go2_interfaces/srv/SetInt "{value: 1}"
```

---

### TOGGLE SERVICES (SetBool)

| Service | Description |
|---------|-------------|
| `/go2/switch_joystick` | Enable/disable native remote control response |
| `/go2/continuous_gait` | Enable/disable continuous gait (maintains walking even at zero velocity) |
| `/go2/handstand` | Enable/disable handstand mode |
| `/go2/walk_upright` | Enable/disable upright walking |
| `/go2/free_avoid` | Enable/disable obstacle avoidance |
| `/go2/free_bound` | Enable/disable bounding gait |
| `/go2/cross_step` | Enable/disable cross-step walking |
| `/go2/free_jump` | Enable/disable jumping capability |

```bash
# Enable obstacle avoidance
ros2 service call /go2/free_avoid go2_interfaces/srv/SetBool "{enable: true}"

# Disable remote control response
ros2 service call /go2/switch_joystick go2_interfaces/srv/SetBool "{enable: false}"

# Enable handstand
ros2 service call /go2/handstand go2_interfaces/srv/SetBool "{enable: true}"
```

---

### GESTURE / TRICK SERVICES (Trigger)

| Service | Description |
|---------|-------------|
| `/go2/hello` | Wave hello greeting |
| `/go2/stretch` | Stretch |
| `/go2/wallow` | Roll over |
| `/go2/pose_on` | Strike a pose |
| `/go2/pose_off` | Exit pose |
| `/go2/scrape` | New Year greeting gesture |
| `/go2/front_flip` | Front flip |
| `/go2/front_jump` | Jump forward |
| `/go2/front_pounce` | Pounce forward |
| `/go2/left_flip` | Left flip |
| `/go2/back_flip` | Back flip |
| `/go2/dance1` | Dance routine 1 |
| `/go2/dance2` | Dance routine 2 |

```bash
# Say hello
ros2 service call /go2/hello go2_interfaces/srv/Trigger

# Dance
ros2 service call /go2/dance1 go2_interfaces/srv/Trigger

# Front flip (caution!)
ros2 service call /go2/front_flip go2_interfaces/srv/Trigger

# Stretch
ros2 service call /go2/stretch go2_interfaces/srv/Trigger
```

---

## Distance Calculation

The Move service automatically calculates iterations:

```
iterations = ceil(distance / (velocity × 0.5s))
```

**Example:** Moving 2 meters at 0.3 m/s
- Distance per iteration: 0.3 × 0.5 = 0.15 meters
- Iterations needed: ceil(2.0 / 0.15) = 14
- Estimated time: 14 × 0.5 = 7.0 seconds

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        LLM / User                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ ROS 2 Service Calls
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Go2ServiceNode (ROS 2)                    │
│  - Exposes /go2/* services                                   │
│  - Validates inputs, calculates iterations                   │
│  - Sends commands via multiprocessing Queue                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ Multiprocessing Queue
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Backend Process (SDK)                      │
│  - Runs Unitree SDK (separate DDS domain)                   │
│  - Executes SportClient commands                             │
│  - Handles mode transitions and timing                       │
│  - Automatically enters walking mode for Move commands       │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ Unitree SDK
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Go2 Robot                               │
└─────────────────────────────────────────────────────────────┘
```

---

## LLM Integration Examples

### Common Commands for LLM

**"Stand up and walk forward 3 meters":**
```bash
ros2 service call /go2/stand_up go2_interfaces/srv/Trigger
ros2 service call /go2/move go2_interfaces/srv/Move "{vx: 0.3, vy: 0.0, vyaw: 0.0, distance: 3.0}"
```

**"Turn around" (180°):**
```bash
ros2 service call /go2/move go2_interfaces/srv/Move "{vx: 0.0, vy: 0.0, vyaw: 0.5, distance: 3.14}"
```

**"Say hello and do a dance":**
```bash
ros2 service call /go2/hello go2_interfaces/srv/Trigger
ros2 service call /go2/dance1 go2_interfaces/srv/Trigger
```

**"Sit down":**
```bash
ros2 service call /go2/sit go2_interfaces/srv/Trigger
```

---

## Troubleshooting

### "Service not found"
```bash
source ~/go2_ws/install/setup.bash
```

### "Module not found: go2_interfaces"
Rebuild and source:
```bash
cd ~/go2_ws
colcon build --packages-select go2_interfaces
source install/setup.bash
colcon build --packages-select go2_control
source install/setup.bash
```

### Clock skew warnings
```bash
sudo timedatectl set-ntp true
# or
sudo ntpdate ntp.ubuntu.com
```

These warnings don't affect functionality.
