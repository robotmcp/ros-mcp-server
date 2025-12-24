"""
Go2 Backend Module
==================
Handles direct communication with the Unitree Go2 robot via the SDK.

This module runs in a SEPARATE PROCESS from the ROS 2 node because:
1. Unitree SDK uses its own DDS implementation (CycloneDDS)
2. ROS 2 also uses DDS (FastDDS by default)
3. Running both in the same process causes conflicts

Architecture:
    [ROS 2 Node] --Queue--> [Backend Process] --SDK--> [Go2 Robot]
"""

import time
from multiprocessing import Queue

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.sport.sport_client import SportClient

# Time interval between Move() calls (robot requires this delay)
MOVE_INTERVAL = 0.5  # seconds


def backend_loop(cmd_queue: Queue):
    """
    Main backend loop - runs in separate process.
    
    Continuously reads commands from the queue and executes them
    on the robot via the Unitree SDK.
    
    Args:
        cmd_queue: Multiprocessing queue receiving command dictionaries
    """
    
    # ================================================================
    # SDK INITIALIZATION
    # ================================================================
    
    ChannelFactoryInitialize(0)
    
    sc = SportClient()
    sc.SetTimeout(10.0)
    sc.Init()
    
    # ================================================================
    # STATE TRACKING
    # ================================================================
    
    walking = False          # Is robot currently in walking mode?
    last_mode_time = 0.0     # Timestamp of last mode change
    
    def mode_guard():
        """
        Enforce minimum delay between mode-changing commands.
        The robot needs time to transition between modes.
        Minimum gap: 0.5 seconds
        """
        nonlocal last_mode_time
        elapsed = time.time() - last_mode_time
        if elapsed < 0.5:
            time.sleep(0.5 - elapsed)
        last_mode_time = time.time()
    
    print("=" * 60)
    print("[Go2 Backend] Initialized and ready for commands")
    print("=" * 60)
    
    # ================================================================
    # MAIN COMMAND LOOP
    # ================================================================
    
    while True:
        cmd = cmd_queue.get()
        
        if cmd is None:
            print("[Go2 Backend] Received shutdown signal")
            break
            
        ctype = cmd.get("type", "")
        
        try:
            # --------------------------------------------------------
            # POSTURE / STATE COMMANDS
            # --------------------------------------------------------
            
            if ctype == "damp":
                mode_guard()
                sc.Damp()
                walking = False
                print("[Backend] Executed: Damp (emergency stop)")
            
            elif ctype == "balance":
                mode_guard()
                sc.BalanceStand()
                walking = False
                print("[Backend] Executed: BalanceStand")
                
            elif ctype == "stop":
                mode_guard()
                sc.StopMove()
                walking = False
                print("[Backend] Executed: StopMove")
                
            elif ctype == "stand_up":
                mode_guard()
                sc.StandUp()
                walking = False
                print("[Backend] Executed: StandUp")
                
            elif ctype == "stand_down":
                mode_guard()
                sc.StandDown()
                walking = False
                print("[Backend] Executed: StandDown")
                
            elif ctype == "recovery":
                mode_guard()
                sc.RecoveryStand()
                walking = False
                print("[Backend] Executed: RecoveryStand")
                
            elif ctype == "sit":
                mode_guard()
                sc.Sit()
                walking = False
                print("[Backend] Executed: Sit")
                
            elif ctype == "rise_sit":
                mode_guard()
                sc.RiseSit()
                walking = False
                print("[Backend] Executed: RiseSit")
            
            # --------------------------------------------------------
            # MOVEMENT COMMAND
            # --------------------------------------------------------
            
            elif ctype == "move":
                vx = cmd.get("vx", 0.0)
                vy = cmd.get("vy", 0.0)
                wz = cmd.get("wz", 0.0)
                iterations = cmd.get("iterations", 1)
                
                # Internally enable walking mode if not already
                if not walking:
                    mode_guard()
                    sc.FreeWalk()
                    walking = True
                
                print(f"[Backend] Moving: vx={vx:.2f}, vy={vy:.2f}, wz={wz:.2f} for {iterations} iterations")
                
                for i in range(iterations):
                    sc.Move(vx, vy, wz)
                    time.sleep(MOVE_INTERVAL)
                
                # Stop after completing movement
                sc.Move(0.0, 0.0, 0.0)
                print("[Backend] Move complete")
            
            # --------------------------------------------------------
            # BODY CONFIGURATION COMMANDS
            # --------------------------------------------------------
            
            elif ctype == "euler":
                roll = cmd.get("roll", 0.0)
                pitch = cmd.get("pitch", 0.0)
                yaw = cmd.get("yaw", 0.0)
                mode_guard()
                sc.Euler(roll, pitch, yaw)
                print(f"[Backend] Executed: Euler(roll={roll}, pitch={pitch}, yaw={yaw})")
                
            elif ctype == "body_height":
                height = cmd.get("height", 0.0)
                mode_guard()
                sc.BodyHeight(height)
                print(f"[Backend] Executed: BodyHeight({height})")
                
            elif ctype == "foot_raise_height":
                height = cmd.get("height", 0.0)
                mode_guard()
                sc.FootRaiseHeight(height)
                print(f"[Backend] Executed: FootRaiseHeight({height})")
                
            elif ctype == "speed_level":
                level = cmd.get("level", 0)
                mode_guard()
                sc.SpeedLevel(level)
                print(f"[Backend] Executed: SpeedLevel({level})")
                
            elif ctype == "switch_gait":
                gait = cmd.get("gait", 0)
                mode_guard()
                sc.SwitchGait(gait)
                print(f"[Backend] Executed: SwitchGait({gait})")
            
            # --------------------------------------------------------
            # TOGGLE COMMANDS (enable/disable)
            # --------------------------------------------------------
            
            elif ctype == "switch_joystick":
                enable = cmd.get("enable", True)
                mode_guard()
                sc.SwitchJoystick(enable)
                print(f"[Backend] Executed: SwitchJoystick({enable})")
                
            elif ctype == "continuous_gait":
                enable = cmd.get("enable", False)
                mode_guard()
                sc.ContinuousGait(enable)
                print(f"[Backend] Executed: ContinuousGait({enable})")
                
            elif ctype == "handstand":
                enable = cmd.get("enable", False)
                mode_guard()
                sc.HandStand(enable)
                print(f"[Backend] Executed: HandStand({enable})")
                
            elif ctype == "walk_upright":
                enable = cmd.get("enable", False)
                mode_guard()
                sc.WalkUpright(enable)
                print(f"[Backend] Executed: WalkUpright({enable})")
                
            elif ctype == "free_avoid":
                enable = cmd.get("enable", False)
                mode_guard()
                sc.FreeAvoid(enable)
                print(f"[Backend] Executed: FreeAvoid({enable})")
                
            elif ctype == "free_bound":
                enable = cmd.get("enable", False)
                mode_guard()
                sc.FreeBound(enable)
                print(f"[Backend] Executed: FreeBound({enable})")
                
            elif ctype == "cross_step":
                enable = cmd.get("enable", False)
                mode_guard()
                sc.CrossStep(enable)
                print(f"[Backend] Executed: CrossStep({enable})")
                
            elif ctype == "free_jump":
                enable = cmd.get("enable", False)
                mode_guard()
                sc.FreeJump(enable)
                print(f"[Backend] Executed: FreeJump({enable})")
            
            # --------------------------------------------------------
            # GESTURE / TRICK COMMANDS (one-shot actions)
            # --------------------------------------------------------
            
            elif ctype == "hello":
                mode_guard()
                sc.Hello()
                print("[Backend] Executed: Hello (greeting)")
                
            elif ctype == "stretch":
                mode_guard()
                sc.Stretch()
                print("[Backend] Executed: Stretch")
                
            elif ctype == "wallow":
                mode_guard()
                sc.Wallow()
                print("[Backend] Executed: Wallow (rolling)")
                
            elif ctype == "pose":
                enable = cmd.get("enable", True)
                mode_guard()
                sc.Pose(enable)
                print(f"[Backend] Executed: Pose({enable})")
                
            elif ctype == "scrape":
                mode_guard()
                sc.Scrape()
                print("[Backend] Executed: Scrape (New Year greeting)")
                
            elif ctype == "front_flip":
                mode_guard()
                sc.FrontFlip()
                print("[Backend] Executed: FrontFlip")
                
            elif ctype == "front_jump":
                mode_guard()
                sc.FrontJump()
                print("[Backend] Executed: FrontJump")
                
            elif ctype == "front_pounce":
                mode_guard()
                sc.FrontPounce()
                print("[Backend] Executed: FrontPounce")
                
            elif ctype == "left_flip":
                mode_guard()
                sc.LeftFlip()
                print("[Backend] Executed: LeftFlip")
                
            elif ctype == "back_flip":
                mode_guard()
                sc.BackFlip()
                print("[Backend] Executed: BackFlip")
                
            elif ctype == "dance1":
                mode_guard()
                sc.Dance1()
                print("[Backend] Executed: Dance1")
                
            elif ctype == "dance2":
                mode_guard()
                sc.Dance2()
                print("[Backend] Executed: Dance2")
                
            else:
                print(f"[Backend] WARNING: Unknown command type: {ctype}")
                
        except Exception as e:
            print(f"[Backend] ERROR executing {ctype}: {e}")
    
    print("[Go2 Backend] Shutdown complete")
