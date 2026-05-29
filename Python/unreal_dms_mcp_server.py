"""
Unreal DMS MCP Server
Entry point — registers all tool modules and starts the FastMCP server.
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from mcp.server.fastmcp import FastMCP

import bridge

# Tool modules — each registers its @mcp.tool() decorators on import
from tools import (
    core_tools,
    blueprint_tools,
    mesh_material_tools,
    spline_vehicle_tools,
    metahuman_tools,
    animation_tools,
    capture_tools,
)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(name)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s",
    handlers=[logging.FileHandler("unreal_dms_mcp.log"), logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("unreal_dms")


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[dict]:
    logger.info("Unreal DMS MCP server starting — connection established lazily on first tool call")
    try:
        yield {}
    finally:
        bridge.reset_connection()
        logger.info("Unreal DMS MCP server shut down")


mcp = FastMCP("UnrealDMS", lifespan=lifespan)

# Register all tools from each module onto this mcp instance
core_tools.register(mcp)
blueprint_tools.register(mcp)
mesh_material_tools.register(mcp)
spline_vehicle_tools.register(mcp)
metahuman_tools.register(mcp)
animation_tools.register(mcp)
capture_tools.register(mcp)

if __name__ == "__main__":
    mcp.run()
