# Contributing to ROS-MCP-Server

---

## 📌 Ways to Contribute

- **Report issues**: Bug reports, documentation gaps, or feature requests.  
- **Improve documentation**: Clarify installation steps, add tutorials, or share demos.  
- **Submit code**: Bug fixes, new features, refactors, or tests.  
- **Share use cases**: Show how you use ROS-MCP with your robot.  
- **Community support**: Answer GitHub Discussions or ROS Discourse questions.  

---

## 🔀 How to Pull-request

1. **Fork the repository:** Click the "Fork" button in the top right corner of the GitHub page.

2. **Create a new branch:** Create a separate branch for your changes to keep them isolated from the main project.

   ```bash
   git checkout -b "your_branch_name"
   ```

3. **Make your changes:** Edit files with your additions or corrections. Please follow the existing format and style guidelines. When adding a new function, make sure to include:

    * The function name and format.
    * A brief description of the function's functionality.
    * Any parameters the function takes.
    * The return type of the function.

4. **Commit your changes:** Commit your changes with a clear and concise message explaining what you've done.

   ```bash
   git commit -m "your_commit_message"
   ```

5. **Push your branch:** Push your branch to your forked repository.

   ```bash
   git push origin "your_branch_name"
   ```

6. **Create a pull request:** Navigate to the original repository and click the "New pull request" button. Select your fork and the branch you pushed. **Important:** Target the `develop` branch (not `main`) for your pull request. Provide a clear title and description of your changes.

7. **Review and merge:** Your pull request will be reviewed by the maintainers. They may suggest changes or ask for clarification. Once approved, your changes will be merged into the main repository.

Thank you for contributing!

---

## Style & CI
We use **Ruff** for both linting and formatting. CI requires:
- `ruff format --check .`
- `ruff check .`

**Local setup**
- Option A (recommended): `pre-commit install` (auto-fixes on commit)
- Option B (manual): `ruff format . && ruff check --fix .`

**Using Black locally?**
- That's fine. Please align with:
  - `line-length = 100`, target `py310`
  - Avoid `--preview`, `--skip-string-normalization`, `--skip-magic-trailing-comma`
- CI uses Ruff as the final arbiter; run `ruff format .` before pushing.

---

## Optional: Using Devcontainer

The devcontainer provides a stable testing platform with ROS2 humble pre-installed as well as an environment to test the MCP server in http transport. (stdio transport is not compatible with the devcontainer)

1. Install [VSCode](https://code.visualstudio.com/) and the **Remote - Containers** extension.  
2. Open the `ros-mcp-server` repository in VSCode.  
3. When prompted, **reopen in container**.  
   - The container includes ROS2 Humble, Python 3.10+, `ruff`, `pre-commit`, `uv`, and `git`.  
   - The repository is mounted at `/root/workspace`.  
   - **Note for GUI apps** (`turtlesim`, `rviz`, `Gazebo`): 
     Ensure the container can access your host X server by running the following command once on the host:

     <details>
     <summary> Ubuntu host </summary>

     ```bash
     sudo apt install x11-xserver-utils   # if xhost is not installed
     xhost +local:root                    # allow container user access
     ```
     </details>

     <details>
     <summary> Windows WSL2 host </summary>

     ```bash
     export DISPLAY=$(grep nameserver /etc/resolv.conf | awk '{print $2}'):0
     export QT_X11_NO_MITSHM=1
     xhost +local:root
     ```
     </details>

     <details>
     <summary> macOS host </summary>

     Install [XQuartz](https://www.xquartz.org/) and enable **"Allow connections from network clients"** in XQuartz → Settings → Security. Log out and back in (or restart XQuartz) for the setting to take effect.

     ```bash
     xhost +   # allow connections (run on macOS host, not inside the container)
     ```

     Inside the devcontainer terminal, override the display variable:
     ```bash
     export DISPLAY=host.docker.internal:0   # Docker's built-in DNS to reach host XQuartz
     ```

     **Note:** The `postStartCommand` (`xhost +local:vscode || true`) runs inside the container and only works on Linux hosts with a shared X11 socket. On macOS, you must run `xhost` on the host side as shown above.
     </details>

     <details>
     <summary> NVIDIA GPU passthrough (Linux only) </summary>

     If you have an NVIDIA GPU and the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) installed, you can enable GPU passthrough by adding `"--gpus=all"` to `runArgs` in `.devcontainer/devcontainer.json`:

     ```json
     "runArgs": [
         "--gpus=all",
         ...
     ]
     ```

     This flag is not included by default because it prevents the container from starting on macOS and Windows, where the NVIDIA Container Toolkit is not available.
     </details>

4. You can now control the Turtlesim robot following the [Rosbridge setup](install/rosbridge.md) and [Connect to your robot](install/connect.md) guides.
5. Initialize pre-commit hooks (optional but recommended):
   ```bash
   pre-commit install
   pre-commit run --all-files
   ```
6. Check Python code formatting with `ruff`
   ```bash
   ruff check .
   ruff format --check .
   ```
  <details>
  <summary>SSH Agent Setup for Git (click to expand)</summary>

  This should be run on the host side prior to building the devcontainer.
  ```bash
  # Start the SSH agent
  eval "$(ssh-agent -s)"

  # List keys currently loaded
  ssh-add -l
  ```

  If it says “The agent has no identities”, you must load your key, for example:
  ```bash
  ssh-add ~/.ssh/id_ed25519
  ssh-add -l   # confirm fingerprint shows up
  ```
  </details>
  
   **Note:** This setup has been tested and verified on Ubuntu and macOS (Apple Silicon).


## License

This project is licensed under the **Apache License 2.0**. By contributing to this project, you agree that your contributions will be licensed under the same license.

**Key points for contributors:**
- Your contributions will be licensed under Apache 2.0
- You retain copyright to your contributions
- You grant the project a perpetual, worldwide, non-exclusive license to use your contributions
- No additional legal agreements required for standard contributions

For the full license text, see [LICENSE](../LICENSE) in the project root.
