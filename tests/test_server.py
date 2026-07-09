from bambu_print_prep_mcp.server import mcp


def test_mcp_server_is_named() -> None:
    assert mcp.name == "Bambu Print Prep MCP"
