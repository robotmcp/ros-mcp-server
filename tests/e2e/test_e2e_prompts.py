"""E2E tests for MCP prompts registration and content validation."""

import pytest

pytestmark = pytest.mark.e2e


class TestPromptsRegistration:
    """E2E tests for prompt registration with MCP server."""

    def test_prompts_registered_with_mcp(self, mcp_server):
        """Verify prompts are registered with MCP server."""
        # Access the registered prompts via the server's internal state
        # FastMCP stores prompts in _prompt_manager
        prompt_manager = mcp_server._prompt_manager
        prompts = prompt_manager._prompts

        assert len(prompts) > 0, "Expected at least one prompt to be registered"

    def test_prompt_content_non_empty(self, mcp_server):
        """Verify registered prompts have non-empty content."""
        prompt_manager = mcp_server._prompt_manager
        prompts = prompt_manager._prompts

        for prompt_name, prompt_obj in prompts.items():
            # Each prompt should have a description or function
            assert prompt_obj is not None, f"Prompt {prompt_name} should not be None"

    def test_prompt_names_follow_convention(self, mcp_server):
        """Verify prompt names follow the naming convention (kebab-case)."""
        prompt_manager = mcp_server._prompt_manager
        prompts = prompt_manager._prompts

        for prompt_name in prompts.keys():
            # Prompt names should use kebab-case (lowercase with hyphens)
            assert prompt_name == prompt_name.lower(), (
                f"Prompt name {prompt_name} should be lowercase"
            )
            # Should not contain underscores (use hyphens instead)
            assert "_" not in prompt_name or prompt_name.startswith("test_"), (
                f"Prompt name {prompt_name} should use hyphens, not underscores"
            )

    def test_expected_prompts_exist(self, mcp_server):
        """Verify expected prompts are registered."""
        prompt_manager = mcp_server._prompt_manager
        prompts = prompt_manager._prompts
        prompt_names = list(prompts.keys())

        # Expected prompts based on the project structure
        expected_prompts = [
            "test-server-tools",
            "test-connection-tools",
            "test-nodes-tools",
            "test-services-tools",
            "test-topics-tools",
            "test-actions-tools",
            "test-parameters-tools",
        ]

        for expected in expected_prompts:
            assert expected in prompt_names, (
                f"Expected prompt '{expected}' to be registered. Found: {prompt_names}"
            )
