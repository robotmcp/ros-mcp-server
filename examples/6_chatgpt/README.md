# ChatGPT Desktop with ROS-MCP-Server

## Prerequisites

### Prepare host machine (MCP Server)

* Installation of ChatGPT Desktop. \[chatgpt.com/download] or Microsoft Store.
* Installation of WSL (Linux).

### Prepare target robot (ROS)

* Installation of Ubuntu or WSL (Windows Subsystem for Linux).
* Installation of ROS or ROS2. Test if ROS is installed by running Turtlesim. If you are not sure, follow, this toturial \[https://wiki.ros.org/ROS/Tutorials]

# Tutorial

## 1.1 Installation on Host Machine

### Install dependencies

* Install [`uv`](https://github.com/astral-sh/uv) using one of the following methods:

    <details>
	<summary><strong>Option A: PowerShell (Windows)</strong></summary>

	```bash
	winget install --id=astral-sh.uv -e
	```
	or
	```bash
	pip install uv
	```
	
	</details>

 	<details>
	<summary><strong>Option B: WSL (Linux) </strong></summary>

	```bash
	curl -LsSf https://astral.sh/uv/install.sh | sh
	```
	or
	```bash
	pip install uv
	```
	or
	```bash
	sudo snap install --classic astral-uv
	```
	</details>

* Install [`ngrok`](https://dashboard.ngrok.com/get-started/setup/linux) using one of the following methods:
	
	<details>
 	<summary><strong>Option A: PowerShell (Windows)</strong></summary>
	
	Install from Microsoft Store or from [here](https://dashboard.ngrok.com/get-started/setup/windows)
    </details>

	<details>
	<summary><strong>Option B: WSL (Linux)</strong></summary>
	
	Using Apt:
	
	```bash
	curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc \\
	  | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null \\
	  \&\& echo "deb https://ngrok-agent.s3.amazonaws.com bookworm main" \\
	  | sudo tee /etc/apt/sources.list.d/ngrok.list \\
	  \&\& sudo apt update \\
	  \&\& sudo apt install ngrok
	```
	or snap:
	```bash
	sudo snap install ngrok
	```
	</details>

* Login or create your account at [`ngrok`](https://dashboard.ngrok.com/login)
* Navigate to [`Your Authtoken`](https://dashboard.ngrok.com/get-started/your-authtoken)
* Copy your `Authtoken` to clipboard `<YOUR_AUTHTOKEN>`
* Activate `ngrok` with the following command, replacing `<YOUR_AUTHTOKEN>`:

```bash
ngrok config add-authtoken <YOUR_AUTHTOKEN>
```
* Obtain a static domain in `ngrok` by navigating to [Domains](https://dashboard.ngrok.com/domains)
* It should look be something like: `abc123-xyz789.ngrok-free.app`
* Save the ROS-MCP url domain, replacing it with yours.

	<details>
	<summary><strong>Option A: PowerShell (Windows)</strong></summary>

	```bash
	$env:MCP_DOMAIN=abc123-xyz789.ngrok-free.app
	```
	</details>

	<details>
	<summary><strong>Option B: WSL (Linux)</strong></summary>

	```bash
	export MCP_DOMAIN=abc123-xyz789.ngrok-free.app
	```
	</details>

* In WSL (Linux), consider adding all your `MCP` variable to `.bashrc`

```bash
export MCP_HOST=127.0.0.1
export MCP_PORT=9000
export MCP_DOMAIN=abc123-xyz789.ngrok-free.app
```

### Install ROS-MCP Server

*  On your Host Machine, clone the repository and navigate to the ROS-MCP Server folder.

```bash
git clone https://github.com/robotmcp/ros-mcp-server.git
cd ros-mcp-server
```


## 1.2 Run ROS-MCP Server



* Run the ROS-MCP using one of the following:
		
	<details>
	<summary><strong>Option A: PowerShell (Windows)</strong></summary>

	In PowerShell, set the tranport protocol:
	
	```bash
	$env:MCP_TRANSPORT="streamable-http" 
	```
	
	If you installed `uv` used the following:
	```bash

	uv run server.py
	```
	
	Otherwise you have to install all the dependencies manually and run:

	```bash
	python server.py
	```
	
	</details>

	<details>
	<summary><strong>Option B: WSL (Linux)</strong></summary>

	Open WSL

	Run the following:
	```bash
	export MCP_TRANSPORT="streamable-http"
	uv run server.py
	```

	or

	```bash
	cd scripts
	launch_mcp_server.sh
	```
	</details>

* By default, the server should start at `127.0.0.1:9000`, you can set `MCP_HOST` and `MCP_PORT` variables as needed



## 1.3 Tunnel ROS-MCP Server 

* On your host machine, launch `ngrok` with one of the following:

  	<details>
	<summary><strong>Option A: PowerShell (Windows)</strong></summary>

	In PowerShell, set the local port to tunnel:
	
	```bash
	$env:MCP_PORT=9000
	$env:MCP_DOMAIN=<YOUR_DOMAIN>
	```
	Run `ngrok` to tunnel your ROS-MCP server.
	
	```bash
	ngrok http --url=$env:MCP_DOMAIN $env:MCP_PORT
	```
	</details>

	<details>
	<summary><strong>Option B: WSL (Linux)</strong></summary>

	In WSL, set the local port to tunnel:
	```bash
	export MCP_PORT=9000
    export MCP_DOMAIN=<YOUR_DOMAIN>
	```
 	Run `ngrok` to tunnel your ROS-MCP server.
	```bash
	ngrok http --url=${MCP_DOMAIN} ${MCP_PORT}
	```
	Or you can also launch:
	```bash
	launch_mcp_tunnel_.sh
	```
 	</details>

* Once you launch `ngrok`, verify your public url domain, it should be the same as `MCP_DOMAIN`.

	```bash
	https://abc123xyz.ngrok-free.app -> http://localhost:9000
	```


## 1.4 Connect ROS-MCP to ChatGPT

* Open ChatGPT Desktop
* Navigate to Settings (Bottom Left)
* Open Connectors
* Create and fill the following:

	- Name: *ROS-MCP Server*
	- Description: *An MCP Server to connect with ROS/ROS2*
	- MCP Server URL: `https://abc123-xyz789.ngrok-free.app/mcp` (don't forget to replace with your domain and add the `\mcp`)
	- Authention: *No authentication*
	- I trust this application

* In ChatGPT, start a new Chat, navigate to `+` > `Developer Mode` > `Add sources` > Activate `ROS-MCP Server`

## 1.5 Run ROS on Target Machine

In WSL, launch `rosbridge` and `turtlesim`

```bash
source /opt/ros/jazzy/setup.bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml & ros2 run turtlesim turtlesim_node
```

or

```bash
launch_ros.sh
```

## Test Host Machine
* Windows 11
* WSL with Ubuntu 22.04
 
## Test Target Machine
* WSL with Ubuntu 22.04
* ROS 2 Jazzy
