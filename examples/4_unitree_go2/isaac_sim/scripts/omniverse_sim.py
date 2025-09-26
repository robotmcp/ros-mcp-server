# Copyright (c) 2024, RoboVerse community
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


from __future__ import annotations

import argparse
import os
import threading

import carb
import cli_args
import custom_rl_env
import gymnasium as gym
import isaaclab.sim as sim_utils
import omni
import omni.appwindow
import rclpy
import torch
from agent_cfg import unitree_g1_agent_cfg, unitree_go2_agent_cfg
from custom_rl_env import G1RoughEnvCfg, UnitreeGo2CustomEnvCfg
from geometry_msgs.msg import Twist
from isaaclab.app import AppLauncher
from isaaclab_rl.rsl_rl import (
    RslRlOnPolicyRunnerCfg,
    RslRlVecEnvWrapper,
)
from isaaclab_tasks.utils import get_checkpoint_path
from isaacsim.storage.native import get_assets_root_path
from omnigraph import create_front_cam_omnigraph
from ros2 import RobotBaseNode, add_camera, add_rtx_lidar, pub_robo_data_ros2
from rsl_rl.runners import OnPolicyRunner

# add argparse arguments
parser = argparse.ArgumentParser(description="Train an RL agent with RSL-RL.")
# parser.add_argument("--device", type=str, default="cpu", help="Use CPU pipeline.")
parser.add_argument(
    "--disable_fabric",
    action="store_true",
    default=False,
    help="Disable fabric and use USD I/O operations.",
)
parser.add_argument("--num_envs", type=int, default=1, help="Number of environments to simulate.")
parser.add_argument(
    "--task",
    type=str,
    default="Isaac-Velocity-Rough-Unitree-Go2-v0",
    help="Name of the task.",
)
parser.add_argument("--seed", type=int, default=None, help="Seed used for the environment")
parser.add_argument("--custom_env", type=str, default="", help="Setup the environment")
parser.add_argument("--robot", type=str, default="go2", help="Setup the robot")
parser.add_argument("--robot_amount", type=int, default=1, help="Setup the robot amount")


# append RSL-RL cli arguments
cli_args.add_rsl_rl_args(parser)


# append AppLauncher cli args
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()


# launch omniverse app
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app


ext_manager = omni.kit.app.get_app().get_extension_manager()
ext_manager.set_extension_enabled_immediate("isaacsim.ros2.bridge", True)

# FOR VR SUPPORT
# ext_manager.set_extension_enabled_immediate("omni.kit.xr.core", True)
# ext_manager.set_extension_enabled_immediate("omni.kit.xr.system.steamvr", True)
# ext_manager.set_extension_enabled_immediate("omni.kit.xr.system.simulatedxr", True)
# ext_manager.set_extension_enabled_immediate("omni.kit.xr.system.openxr", True)
# ext_manager.set_extension_enabled_immediate("omni.kit.xr.telemetry", True)
# ext_manager.set_extension_enabled_immediate("omni.kit.xr.profile.vr", True)


def sub_keyboard_event(event, *args, **kwargs) -> bool:
    if len(custom_rl_env.base_command) > 0:
        if event.type == carb.input.KeyboardEventType.KEY_PRESS:
            if event.input.name == "W":
                custom_rl_env.base_command["0"] = [1, 0, 0]
            if event.input.name == "S":
                custom_rl_env.base_command["0"] = [-1, 0, 0]
            if event.input.name == "A":
                custom_rl_env.base_command["0"] = [0, 1, 0]
            if event.input.name == "D":
                custom_rl_env.base_command["0"] = [0, -1, 0]
            if event.input.name == "Q":
                custom_rl_env.base_command["0"] = [0, 0, 1]
            if event.input.name == "E":
                custom_rl_env.base_command["0"] = [0, 0, -1]

            if len(custom_rl_env.base_command) > 1:
                if event.input.name == "I":
                    custom_rl_env.base_command["1"] = [1, 0, 0]
                if event.input.name == "K":
                    custom_rl_env.base_command["1"] = [-1, 0, 0]
                if event.input.name == "J":
                    custom_rl_env.base_command["1"] = [0, 1, 0]
                if event.input.name == "L":
                    custom_rl_env.base_command["1"] = [0, -1, 0]
                if event.input.name == "U":
                    custom_rl_env.base_command["1"] = [0, 0, 1]
                if event.input.name == "O":
                    custom_rl_env.base_command["1"] = [0, 0, -1]
        elif event.type == carb.input.KeyboardEventType.KEY_RELEASE:
            for i in range(len(custom_rl_env.base_command)):
                custom_rl_env.base_command[str(i)] = [0, 0, 0]
    return True


def move_copter(copter):
    # TODO tmp solution for test
    if custom_rl_env.base_command["0"] == [0, 0, 0]:
        copter_move_cmd = torch.tensor([[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]], device="cuda:0")

    if custom_rl_env.base_command["0"] == [1, 0, 0]:
        copter_move_cmd = torch.tensor([[1.0, 0.0, 0.0, 0.0, 0.0, 0.0]], device="cuda:0")

    if custom_rl_env.base_command["0"] == [-1, 0, 0]:
        copter_move_cmd = torch.tensor([[-1.0, 0.0, 0.0, 0.0, 0.0, 0.0]], device="cuda:0")

    if custom_rl_env.base_command["0"] == [0, 1, 0]:
        copter_move_cmd = torch.tensor([[0.0, 1.0, 0.0, 0.0, 0.0, 0.0]], device="cuda:0")

    if custom_rl_env.base_command["0"] == [0, -1, 0]:
        copter_move_cmd = torch.tensor([[0.0, -1.0, 0.0, 0.0, 0.0, 0.0]], device="cuda:0")

    if custom_rl_env.base_command["0"] == [0, 0, 1]:
        copter_move_cmd = torch.tensor([[0.0, 0.0, 1.0, 0.0, 0.0, 0.0]], device="cuda:0")

    if custom_rl_env.base_command["0"] == [0, 0, -1]:
        copter_move_cmd = torch.tensor([[0.0, 0.0, -1.0, 0.0, 0.0, 0.0]], device="cuda:0")

    copter.write_root_velocity_to_sim(copter_move_cmd)
    copter.write_data_to_sim()


def setup_custom_env():
    try:
        if args_cli.custom_env == "warehouse":
            cfg_scene = sim_utils.UsdFileCfg(usd_path="./envs/warehouse.usd")
            cfg_scene.func("/World/warehouse", cfg_scene, translation=(0.0, 0.0, 0.0))

        if args_cli.custom_env == "office":
            cfg_scene = sim_utils.UsdFileCfg(usd_path="./envs/office.usd")
            cfg_scene.func("/World/office", cfg_scene, translation=(0.0, 0.0, 0.0))

        if args_cli.custom_env == "small_warehouse":
            assets_root_path = get_assets_root_path()
            cfg_scene = sim_utils.UsdFileCfg(
                usd_path=assets_root_path
                + "/Isaac/Environments/Digital_Twin_Warehouse/small_warehouse_digital_twin.usd"
            )
            cfg_scene.func("/World/small_warehouse", cfg_scene, translation=(2.5, -1.5, 0.0))

        if args_cli.custom_env == "hospital":
            cfg_scene = sim_utils.UsdFileCfg(usd_path="./envs/hospital.usd")
            cfg_scene.func("/World/hospital", cfg_scene, translation=(0.0, 0.0, 0.0))
    except Exception as e:
        print(
            f"Error loading custom environment. You should download custom envs folder from: https://drive.google.com/drive/folders/1vVGuO1KIX1K6mD6mBHDZGm9nk2vaRyj3?usp=sharing : {e}"
        )


def cmd_vel_cb(msg, num_robot):
    x = msg.linear.x
    y = msg.linear.y
    z = msg.angular.z
    custom_rl_env.base_command[str(num_robot)] = [x, y, z]


def add_cmd_sub(num_envs):
    node_test = rclpy.create_node("position_velocity_publisher")
    for i in range(num_envs):
        node_test.create_subscription(
            Twist, f"robot{i}/cmd_vel", lambda msg, i=i: cmd_vel_cb(msg, str(i)), 10
        )
    # Spin in a separate thread
    thread = threading.Thread(target=rclpy.spin, args=(node_test,), daemon=True)
    thread.start()


def specify_cmd_for_robots(numv_envs):
    for i in range(numv_envs):
        custom_rl_env.base_command[str(i)] = [0, 0, 0]


def run_sim():
    # acquire input interface
    _input = carb.input.acquire_input_interface()
    _appwindow = omni.appwindow.get_default_app_window()
    _keyboard = _appwindow.get_keyboard()
    _sub_keyboard = _input.subscribe_to_keyboard_events(_keyboard, sub_keyboard_event)

    """Play with RSL-RL agent."""
    # parse configuration

    env_cfg = UnitreeGo2CustomEnvCfg()

    if args_cli.robot == "g1":
        env_cfg = G1RoughEnvCfg()

    # TODO need to think about better copter integration.
    # copter_cfg = CRAZYFLIE_CFG
    # copter_cfg.spawn.func(
    #     "/World/Crazyflie/Robot_1", copter_cfg.spawn, translation=(1.5, 0.5, 2.42)
    # )

    # # create handles for the robots
    # copter = Articulation(copter_cfg.replace(prim_path="/World/Crazyflie/Robot.*"))

    # add N robots to env
    env_cfg.scene.num_envs = args_cli.robot_amount

    specify_cmd_for_robots(env_cfg.scene.num_envs)

    agent_cfg: RslRlOnPolicyRunnerCfg = unitree_go2_agent_cfg

    if args_cli.robot == "g1":
        agent_cfg: RslRlOnPolicyRunnerCfg = unitree_g1_agent_cfg

    # create isaac environment
    env = gym.make(args_cli.task, cfg=env_cfg)
    # wrap around environment for rsl-rl
    env = RslRlVecEnvWrapper(env)

    # specify directory for logging experiments
    log_root_path = os.path.join("logs", "rsl_rl", agent_cfg["experiment_name"])
    log_root_path = os.path.abspath(log_root_path)
    print(f"[INFO] Loading experiment from directory: {log_root_path}")

    resume_path = get_checkpoint_path(
        log_root_path, agent_cfg["load_run"], agent_cfg["load_checkpoint"]
    )

    # load previously trained model
    ppo_runner = OnPolicyRunner(env, agent_cfg, log_dir=None, device=agent_cfg["device"])
    ppo_runner.load(resume_path)
    print(f"[INFO]: Loading model checkpoint from: {resume_path}")

    # obtain the trained policy for inference
    policy = ppo_runner.get_inference_policy(device=env.unwrapped.device)

    # reset environment
    obs = env.get_observations()

    # initialize ROS2 node
    rclpy.init()
    base_node = RobotBaseNode(env_cfg.scene.num_envs)
    add_cmd_sub(env_cfg.scene.num_envs)

    UnitreeL1_annotator_lst = add_rtx_lidar(
        env_cfg.scene.num_envs, args_cli.robot, "UnitreeL1", False
    )
    ExtraLidar_annotator_lst = add_rtx_lidar(env_cfg.scene.num_envs, args_cli.robot, "Extra", False)
    annotator_lst = UnitreeL1_annotator_lst + ExtraLidar_annotator_lst
    add_camera(env_cfg.scene.num_envs, args_cli.robot)
    # add_copter_camera()

    # create ros2 camera stream omnigraph
    for i in range(env_cfg.scene.num_envs):
        create_front_cam_omnigraph(i)

    setup_custom_env()

    # simulate environment
    while simulation_app.is_running():
        # run everything in inference mode
        with torch.inference_mode():
            # agent stepping
            actions = policy(obs)
            # env stepping
            obs, _, _, _ = env.step(actions)
            pub_robo_data_ros2(
                args_cli.robot,
                env_cfg.scene.num_envs,
                base_node,
                env,
                annotator_lst,
            )
            # move_copter(copter)

    env.close()
