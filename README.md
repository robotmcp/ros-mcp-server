# ROS MCP Server 🧠⇄🤖

![Static Badge](https://img.shields.io/badge/ROS-Available-green)
![Static Badge](https://img.shields.io/badge/ROS2-Available-green)
![Static Badge](https://img.shields.io/badge/License-Apache%202.0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![GitHub Repo stars](https://img.shields.io/github/stars/robotmcp/ros-mcp-server?style=social)
![GitHub last commit](https://img.shields.io/github/last-commit/robotmcp/ros-mcp-server)


<p align="center">
  <img src="https://github.com/robotmcp/ros-mcp-server/blob/main/docs/images/framework.png"/>
</p>

The **ROS MCP Server** creates a **two-way bridge** between large language models (LLMs) and robots running **ROS1 or ROS2**.  With no changes to existing robot source code, this enables:
- 🗣 **Commanding the robot in natural language** → instructions are translated into ROS/ROS2 commands.  
- 👀 **Give AI full visibility** → subscribe to topics, call services, read sensor data, and monitor robot state in real time.  


### ✅ Key Benefits  

- **No robot code changes** → only requires adding the `rosbridge` node.  
- **True two-way communication** → LLMs can both *control* robots and *observe* everything happening in ROS (sensors, topics, parameters).  
- **ROS1 & ROS2 support** → works with both versions out of the box.  
- **MCP-compatible** → integrates with any MCP-enabled LLM (Claude Desktop, Gemini, ChatGPT, and beyond).   

## 🎥 Examples in Action  

**Controlling the MOCA mobile manipulator in NVIDIA Isaac Sim**  
Commands are entered into Claude Desktop, which uses the MCP server to directly drive the simulated robot.  

<p align="center">
  <img src="https://github.com/robotmcp/ros-mcp-server/blob/main/docs/images/result.gif" />
</p>  

More examples and tutorial videos are available in the [examples index](examples/examples-index.md).  

---

## ⚙️ Features  

- **List topics, services, and message types** → explore everything available in your robot’s ROS environment.  
- **View type definitions (incl. custom)** → understand the structure of any message.  
- **Publish/subscribe to topics** → send commands or stream robot data in real time.  
- **Call services (incl. custom)** → trigger robot functions directly.  
- **Get/set parameters** → read or adjust robot settings on the fly.  
- 🔜 **Action support** → upcoming support for ROS Actions.  
- 🔜 **Permission controls** → manage access for safer deployments.  

---

## 🛠 Getting Started  

The MCP server is version-agnostic (ROS1 or ROS2) and works with any MCP-compatible LLM.  

<p align="center">
  <img src="https://github.com/robotmcp/ros-mcp-server/blob/main/docs/images/MCP_topology.png"/>
</p>  

### Installation  

Follow the [installation guide](docs/installation.md) for step-by-step instructions:  
1. Clone the repository  
2. Install `uv` and `rosbridge`  
3. Install Claude Desktop (or any MCP-enabled client)  
4. Configure your client to connect to the ROS MCP Server  
5. Start `rosbridge` on the target robot  

---

## 📚 More Examples & Tutorials  

Browse our [examples](examples/examples-index.md) to see the server in action.  
We welcome community PRs with new examples and integrations!  

---

## 🤝 Contributing  

We love contributions of all kinds:  
- Bug fixes and documentation updates  
- New features (e.g., Action support, permissions)  
- Additional examples and tutorials  

Check out the [contributing guidelines](docs/contributing.md) and see issues tagged **good first issue** to get started.  

---

## 📜 License  

This project is licensed under the [Apache License 2.0](LICENSE).  