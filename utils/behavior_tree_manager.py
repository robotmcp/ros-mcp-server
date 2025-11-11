"""
Behavior Tree Manager for ROS-MCP Server

Provides behavior tree parsing, validation, and execution using py_trees.
Connects BT leaf nodes to ROS Actions and Services via rosbridge WebSocket.
"""

import json
import sys
import time
import uuid
from typing import Any, Dict, List, Optional

import py_trees
from py_trees.behaviour import Behaviour
from py_trees.common import Status
from py_trees.composites import Selector, Sequence, Parallel


class ROSActionBehaviour(Behaviour):
    """
    Behavior tree leaf node that executes a ROS Action via rosbridge.
    
    Attributes:
        action_name: ROS action topic (e.g., '/navigate_to_pose')
        action_type: ROS action type (e.g., 'nav2_msgs/action/NavigateToPose')
        goal_args: Dictionary containing the action goal parameters
        ws_manager: WebSocketManager instance for rosbridge communication
        timeout: Maximum time to wait for action completion (seconds)
    """

    def __init__(
        self,
        name: str,
        action_name: str,
        action_type: str,
        goal_args: Dict[str, Any],
        ws_manager,
        timeout: float = 30.0,
    ):
        super().__init__(name=name)
        self.action_name = action_name
        self.action_type = action_type
        self.goal_args = goal_args
        self.ws_manager = ws_manager
        self.timeout = timeout
        self.goal_id = None
        self.start_time = None
        self.last_status = None
        self.feedback_data = []

    def setup(self, **kwargs):
        """Called once before first tick."""
        self.logger.debug(f"Setting up action behavior: {self.action_name}")
        return True

    def initialise(self):
        """Called when behavior is ticked for the first time or after being reset."""
        self.logger.info(f"Initializing action: {self.action_name}")
        
        # Generate unique goal ID
        self.goal_id = f"goal_{int(time.time()*1000)}_{uuid.uuid4().hex[:8]}"
        self.start_time = time.time()
        self.last_status = None
        self.feedback_data = []
        
        # Send action goal via rosbridge
        message = {
            "op": "send_action_goal",
            "action": self.action_name,
            "action_type": self.action_type,
            "args": self.goal_args,
            "feedback": True,
        }
        
        with self.ws_manager:
            error = self.ws_manager.send(message)
            if error:
                self.logger.error(f"Failed to send action goal: {error}")
                self.feedback_message = f"Send error: {error}"

    def update(self) -> Status:
        """
        Called each tick to check action status.
        
        Returns:
            Status.RUNNING: Action still executing
            Status.SUCCESS: Action completed successfully
            Status.FAILURE: Action failed or timed out
        """
        # Check timeout
        elapsed = time.time() - self.start_time
        if elapsed > self.timeout:
            self.logger.warning(f"Action timeout after {elapsed:.1f}s")
            self.feedback_message = f"Timeout after {elapsed:.1f}s"
            return Status.FAILURE
        
        # Poll for action feedback/result
        with self.ws_manager:
            try:
                # Set short timeout for polling
                self.ws_manager.ws.settimeout(0.1)
                response_raw = self.ws_manager.receive(timeout=0.1)
                
                if response_raw:
                    from utils.websocket_manager import parse_json
                    response = parse_json(response_raw)
                    
                    if response and isinstance(response, dict):
                        op = response.get("op")
                        
                        # Handle action feedback
                        if op == "action_feedback":
                            feedback = response.get("values", {}).get("feedback", {})
                            self.feedback_data.append(feedback)
                            self.logger.info(f"Action feedback: {feedback}")
                            return Status.RUNNING
                        
                        # Handle action result
                        elif op == "action_result":
                            status_code = response.get("values", {}).get("status", 0)
                            result = response.get("values", {}).get("result", {})
                            
                            # Status codes: 4=SUCCEEDED, 5=CANCELED, 6=ABORTED
                            if status_code == 4:
                                self.logger.info(f"Action succeeded: {result}")
                                self.feedback_message = f"Success: {result}"
                                return Status.SUCCESS
                            elif status_code in [5, 6]:
                                self.logger.error(f"Action failed with status {status_code}: {result}")
                                self.feedback_message = f"Failed (status {status_code}): {result}"
                                return Status.FAILURE
                            else:
                                # Still executing
                                self.last_status = status_code
                                return Status.RUNNING
                
            except Exception as e:
                # Timeout or receive error - this is normal when polling
                pass
        
        # Still running
        return Status.RUNNING

    def terminate(self, new_status: Status):
        """Called when behavior is interrupted or completes."""
        self.logger.debug(f"Terminating with status: {new_status}")
        
        # If interrupted, cancel the action
        if new_status == Status.INVALID:
            self._cancel_action()

    def _cancel_action(self):
        """Send action cancel request."""
        if self.goal_id:
            message = {
                "op": "cancel_action_goal",
                "action": self.action_name,
                "action_type": self.action_type,
            }
            with self.ws_manager:
                self.ws_manager.send(message)
                self.logger.info(f"Cancelled action: {self.action_name}")


class ROSServiceBehaviour(Behaviour):
    """
    Behavior tree leaf node that calls a ROS Service via rosbridge.
    
    Attributes:
        service_name: ROS service name (e.g., '/set_gripper')
        service_type: ROS service type (e.g., 'std_srvs/srv/SetBool')
        request_args: Dictionary containing service request parameters
        ws_manager: WebSocketManager instance for rosbridge communication
        timeout: Maximum time to wait for service response (seconds)
    """

    def __init__(
        self,
        name: str,
        service_name: str,
        service_type: str,
        request_args: Dict[str, Any],
        ws_manager,
        timeout: float = 5.0,
    ):
        super().__init__(name=name)
        self.service_name = service_name
        self.service_type = service_type
        self.request_args = request_args
        self.ws_manager = ws_manager
        self.timeout = timeout
        self.response = None

    def setup(self, **kwargs):
        """Called once before first tick."""
        self.logger.debug(f"Setting up service behavior: {self.service_name}")
        return True

    def initialise(self):
        """Called when behavior is ticked for the first time."""
        self.logger.info(f"Calling service: {self.service_name}")
        self.response = None

    def update(self) -> Status:
        """
        Call the service and return immediately with result.
        
        Returns:
            Status.SUCCESS: Service call succeeded
            Status.FAILURE: Service call failed
        """
        message = {
            "op": "call_service",
            "service": self.service_name,
            "type": self.service_type,
            "args": self.request_args,
        }
        
        with self.ws_manager:
            response = self.ws_manager.request(message, timeout=self.timeout)
            
            if "error" in response:
                self.logger.error(f"Service call failed: {response['error']}")
                self.feedback_message = f"Service error: {response['error']}"
                return Status.FAILURE
            
            self.response = response.get("values", {})
            self.logger.info(f"Service response: {self.response}")
            self.feedback_message = f"Service returned: {self.response}"
            return Status.SUCCESS

    def terminate(self, new_status: Status):
        """Called when behavior completes or is interrupted."""
        self.logger.debug(f"Service behavior terminated with: {new_status}")


class BehaviorTreeManager:
    """
    Manages behavior tree parsing, validation, and execution.
    
    Supports JSON format for behavior tree definitions:
    {
        "type": "sequence|selector|parallel",
        "name": "Root",
        "children": [
            {
                "type": "action",
                "name": "NavigateToPose",
                "action_name": "/navigate_to_pose",
                "action_type": "nav2_msgs/action/NavigateToPose",
                "goal": {...},
                "timeout": 30.0
            },
            {
                "type": "service",
                "name": "SetGripper",
                "service_name": "/set_gripper",
                "service_type": "std_srvs/srv/SetBool",
                "request": {...},
                "timeout": 5.0
            }
        ]
    }
    """

    def __init__(self, ws_manager):
        """
        Initialize the behavior tree manager.
        
        Args:
            ws_manager: WebSocketManager instance for rosbridge communication
        """
        self.ws_manager = ws_manager
        self.current_tree = None
        self.tree_root = None
        self.execution_status = "idle"
        self.status_log = []

    def validate_tree_definition(self, tree_def: str) -> Dict[str, Any]:
        """
        Validate a behavior tree definition.
        
        Args:
            tree_def: JSON string containing the tree definition
            
        Returns:
            Dict with 'valid' boolean and optional 'error' message
        """
        try:
            # Parse JSON
            tree_dict = json.loads(tree_def)
            
            # Validate structure
            if not isinstance(tree_dict, dict):
                return {"valid": False, "error": "Tree definition must be a JSON object"}
            
            if "type" not in tree_dict:
                return {"valid": False, "error": "Root node must have 'type' field"}
            
            if "name" not in tree_dict:
                return {"valid": False, "error": "Root node must have 'name' field"}
            
            # Recursively validate tree structure
            error = self._validate_node(tree_dict)
            if error:
                return {"valid": False, "error": error}
            
            return {"valid": True, "message": "Tree definition is valid"}
            
        except json.JSONDecodeError as e:
            return {"valid": False, "error": f"Invalid JSON: {str(e)}"}
        except Exception as e:
            return {"valid": False, "error": f"Validation error: {str(e)}"}

    def _validate_node(self, node: Dict[str, Any], path: str = "root") -> Optional[str]:
        """
        Recursively validate a node in the tree.
        
        Returns:
            Error message string if invalid, None if valid
        """
        node_type = node.get("type")
        
        # Validate composite nodes
        if node_type in ["sequence", "selector", "parallel"]:
            if "children" not in node or not isinstance(node["children"], list):
                return f"{path}: Composite node must have 'children' list"
            
            if len(node["children"]) == 0:
                return f"{path}: Composite node must have at least one child"
            
            # Validate each child
            for i, child in enumerate(node["children"]):
                error = self._validate_node(child, f"{path}.children[{i}]")
                if error:
                    return error
        
        # Validate action nodes
        elif node_type == "action":
            required = ["action_name", "action_type", "goal"]
            for field in required:
                if field not in node:
                    return f"{path}: Action node missing required field '{field}'"
        
        # Validate service nodes
        elif node_type == "service":
            required = ["service_name", "service_type", "request"]
            for field in required:
                if field not in node:
                    return f"{path}: Service node missing required field '{field}'"
        
        else:
            return f"{path}: Unknown node type '{node_type}'"
        
        return None

    def build_tree(self, tree_def: str) -> Dict[str, Any]:
        """
        Parse and build a behavior tree from JSON definition.
        
        Args:
            tree_def: JSON string containing the tree definition
            
        Returns:
            Dict with 'success' boolean and optional 'error' message or 'tree' object
        """
        try:
            # Validate first
            validation = self.validate_tree_definition(tree_def)
            if not validation["valid"]:
                return {"success": False, "error": validation["error"]}
            
            # Parse JSON
            tree_dict = json.loads(tree_def)
            
            # Build py_trees structure
            self.tree_root = self._build_node(tree_dict)
            
            # Create behavior tree
            self.current_tree = py_trees.trees.BehaviourTree(root=self.tree_root)
            
            # Setup the tree
            self.current_tree.setup(timeout=15)
            
            self.execution_status = "ready"
            self.status_log = []
            
            return {
                "success": True,
                "message": "Behavior tree built successfully",
                "tree_name": tree_dict.get("name", "unnamed"),
            }
            
        except Exception as e:
            return {"success": False, "error": f"Failed to build tree: {str(e)}"}

    def _build_node(self, node_def: Dict[str, Any]) -> Behaviour:
        """
        Recursively build a py_trees node from definition.
        
        Args:
            node_def: Dictionary containing node definition
            
        Returns:
            py_trees Behaviour instance
        """
        node_type = node_def["type"]
        name = node_def.get("name", "unnamed")
        
        # Build composite nodes
        if node_type == "sequence":
            children = [self._build_node(child) for child in node_def["children"]]
            return Sequence(name=name, memory=True, children=children)
        
        elif node_type == "selector":
            children = [self._build_node(child) for child in node_def["children"]]
            return Selector(name=name, memory=True, children=children)
        
        elif node_type == "parallel":
            children = [self._build_node(child) for child in node_def["children"]]
            policy = node_def.get("policy", "SuccessOnAll")
            
            if policy == "SuccessOnOne":
                sync_policy = Parallel.SuccessOnOne()
            else:
                sync_policy = Parallel.SuccessOnAll()
            
            return Parallel(name=name, policy=sync_policy, children=children)
        
        # Build action nodes
        elif node_type == "action":
            return ROSActionBehaviour(
                name=name,
                action_name=node_def["action_name"],
                action_type=node_def["action_type"],
                goal_args=node_def["goal"],
                ws_manager=self.ws_manager,
                timeout=node_def.get("timeout", 30.0),
            )
        
        # Build service nodes
        elif node_type == "service":
            return ROSServiceBehaviour(
                name=name,
                service_name=node_def["service_name"],
                service_type=node_def["service_type"],
                request_args=node_def["request"],
                ws_manager=self.ws_manager,
                timeout=node_def.get("timeout", 5.0),
            )
        
        else:
            raise ValueError(f"Unknown node type: {node_type}")

    def execute_tree(self, max_ticks: int = 100, tick_rate: float = 10.0) -> Dict[str, Any]:
        """
        Execute the currently loaded behavior tree.
        
        Args:
            max_ticks: Maximum number of ticks before stopping
            tick_rate: Ticks per second
            
        Returns:
            Dict with execution results and status
        """
        if not self.current_tree:
            return {"success": False, "error": "No tree loaded. Call build_tree first."}
        
        self.execution_status = "running"
        self.status_log = []
        
        tick_count = 0
        tick_period = 1.0 / tick_rate
        
        try:
            while tick_count < max_ticks:
                # Tick the tree
                self.current_tree.tick()
                tick_count += 1
                
                # Get current status
                status = self.tree_root.status
                status_str = status.name
                
                # Log status
                self.status_log.append({
                    "tick": tick_count,
                    "status": status_str,
                    "timestamp": time.time(),
                })
                
                print(f"[BT] Tick {tick_count}: {status_str}", file=sys.stderr)
                
                # Check if tree completed
                if status in [Status.SUCCESS, Status.FAILURE]:
                    self.execution_status = "completed"
                    return {
                        "success": True,
                        "final_status": status_str,
                        "ticks": tick_count,
                        "message": f"Tree completed with status: {status_str}",
                        "status_log": self.status_log,
                    }
                
                # Wait before next tick
                time.sleep(tick_period)
            
            # Max ticks reached
            self.execution_status = "timeout"
            return {
                "success": False,
                "error": f"Tree did not complete within {max_ticks} ticks",
                "final_status": self.tree_root.status.name,
                "ticks": tick_count,
                "status_log": self.status_log,
            }
            
        except Exception as e:
            self.execution_status = "error"
            return {
                "success": False,
                "error": f"Execution error: {str(e)}",
                "ticks": tick_count,
                "status_log": self.status_log,
            }

    def get_status(self) -> Dict[str, Any]:
        """
        Get current execution status.
        
        Returns:
            Dict with current status information
        """
        if not self.current_tree:
            return {
                "execution_status": "idle",
                "message": "No tree loaded",
            }
        
        return {
            "execution_status": self.execution_status,
            "tree_status": self.tree_root.status.name if self.tree_root else "unknown",
            "status_log_size": len(self.status_log),
            "latest_log": self.status_log[-1] if self.status_log else None,
        }

    def get_tree_visualization(self) -> str:
        """
        Get ASCII visualization of the current tree.
        
        Returns:
            String containing tree visualization
        """
        if not self.current_tree:
            return "No tree loaded"
        
        return py_trees.display.unicode_tree(self.tree_root, show_status=True)
