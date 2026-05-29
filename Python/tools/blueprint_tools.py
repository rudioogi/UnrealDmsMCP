"""
Blueprint tools: create, configure, inspect, and edit Blueprint visual graphs.
Graph-node operations route through the C++ plugin (flopperam bridge).
All other operations use the unreal Python module via execute_python.
"""

from __future__ import annotations
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP
import bridge

logger = logging.getLogger("unreal_dms.blueprint")


def register(mcp: FastMCP):

    # ─── Blueprint creation & configuration ───────────────────────────────────

    @mcp.tool()
    def create_blueprint(name: str, parent_class: str = "Actor") -> dict[str, Any]:
        """
        Create a new Blueprint class asset.
        parent_class: UClass name or short name (e.g. 'Actor', 'Pawn', 'Character').
        """
        return bridge.send_command("create_blueprint", {"name": name, "parent_class": parent_class})

    @mcp.tool()
    def add_component_to_blueprint(
        blueprint_name: str,
        component_type: str,
        component_name: str,
        location: list[float] = None,
        rotation: list[float] = None,
        scale: list[float] = None,
        component_properties: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """Add a component to a Blueprint's component hierarchy."""
        return bridge.send_command(
            "add_component_to_blueprint",
            {
                "blueprint_name": blueprint_name,
                "component_type": component_type,
                "component_name": component_name,
                "location": location or [],
                "rotation": rotation or [],
                "scale": scale or [],
                "component_properties": component_properties or {},
            },
        )

    @mcp.tool()
    def set_static_mesh_on_component(
        blueprint_name: str,
        component_name: str,
        static_mesh: str = "/Engine/BasicShapes/Cube.Cube",
    ) -> dict[str, Any]:
        """Assign a static mesh to a StaticMeshComponent inside a Blueprint."""
        return bridge.send_command(
            "set_static_mesh_properties",
            {
                "blueprint_name": blueprint_name,
                "component_name": component_name,
                "static_mesh": static_mesh,
            },
        )

    @mcp.tool()
    def set_physics_on_component(
        blueprint_name: str,
        component_name: str,
        simulate_physics: bool = True,
        gravity_enabled: bool = True,
        mass: float = 1.0,
        linear_damping: float = 0.01,
        angular_damping: float = 0.0,
    ) -> dict[str, Any]:
        """Set physics simulation properties on a Blueprint component."""
        return bridge.send_command(
            "set_physics_properties",
            {
                "blueprint_name": blueprint_name,
                "component_name": component_name,
                "simulate_physics": simulate_physics,
                "gravity_enabled": gravity_enabled,
                "mass": mass,
                "linear_damping": linear_damping,
                "angular_damping": angular_damping,
            },
        )

    @mcp.tool()
    def compile_blueprint(blueprint_name: str) -> dict[str, Any]:
        """Compile a Blueprint and report any errors."""
        return bridge.send_command("compile_blueprint", {"blueprint_name": blueprint_name})

    @mcp.tool()
    def set_blueprint_default_value(
        blueprint_path: str, variable_name: str, value: Any
    ) -> dict[str, Any]:
        """Set the default value of a Blueprint variable on the CDO."""
        script = f"""
import unreal, json
bp = unreal.load_asset({repr(blueprint_path)})
if bp is None:
    print(json.dumps({{"success": False, "error": "Blueprint not found"}}))
else:
    cdo = bp.generated_class.get_default_object()
    try:
        cdo.set_editor_property({repr(variable_name)}, {repr(value)})
        unreal.EditorAssetLibrary.save_asset({repr(blueprint_path)})
        print(json.dumps({{"success": True}}))
    except Exception as e:
        print(json.dumps({{"success": False, "error": str(e)}}))
"""
        return bridge.execute_python(script)

    # ─── Blueprint inspection ─────────────────────────────────────────────────

    @mcp.tool()
    def read_blueprint_content(
        blueprint_path: str,
        include_event_graph: bool = True,
        include_functions: bool = True,
        include_variables: bool = True,
        include_components: bool = True,
        include_interfaces: bool = True,
    ) -> dict[str, Any]:
        """Read the complete structure of a Blueprint (graphs, functions, variables, components)."""
        return bridge.send_command(
            "read_blueprint_content",
            {
                "blueprint_path": blueprint_path,
                "include_event_graph": include_event_graph,
                "include_functions": include_functions,
                "include_variables": include_variables,
                "include_components": include_components,
                "include_interfaces": include_interfaces,
            },
        )

    @mcp.tool()
    def analyze_blueprint_graph(
        blueprint_path: str,
        graph_name: str = "EventGraph",
        include_node_details: bool = True,
        include_pin_connections: bool = True,
        trace_execution_flow: bool = True,
    ) -> dict[str, Any]:
        """Analyse a specific graph (EventGraph or function graph) inside a Blueprint."""
        return bridge.send_command(
            "analyze_blueprint_graph",
            {
                "blueprint_path": blueprint_path,
                "graph_name": graph_name,
                "include_node_details": include_node_details,
                "include_pin_connections": include_pin_connections,
                "trace_execution_flow": trace_execution_flow,
            },
        )

    @mcp.tool()
    def get_blueprint_variable_details(
        blueprint_path: str, variable_name: str = None
    ) -> dict[str, Any]:
        """Get variable details from a Blueprint (type, default value, usage). Pass variable_name=None for all."""
        return bridge.send_command(
            "get_blueprint_variable_details",
            {"blueprint_path": blueprint_path, "variable_name": variable_name},
        )

    @mcp.tool()
    def get_blueprint_function_details(
        blueprint_path: str, function_name: str = None, include_graph: bool = True
    ) -> dict[str, Any]:
        """Get function details from a Blueprint (signature, graph). Pass function_name=None for all."""
        return bridge.send_command(
            "get_blueprint_function_details",
            {
                "blueprint_path": blueprint_path,
                "function_name": function_name,
                "include_graph": include_graph,
            },
        )

    # ─── Blueprint visual-graph node editing (C++ bridge) ────────────────────

    @mcp.tool()
    def add_blueprint_node(
        blueprint_path: str,
        graph_name: str,
        node_type: str,
        node_properties: dict[str, Any] = None,
        position_x: int = 0,
        position_y: int = 0,
    ) -> dict[str, Any]:
        """
        Add a node to a Blueprint graph.
        node_type: one of the 23 supported types (e.g. 'CallFunction', 'Branch', 'VariableGet',
                   'Print', 'SpawnActor', 'BeginPlay', 'Tick', etc.).
        Returns the new node's ID for use with connect_blueprint_nodes.
        """
        return bridge.send_command(
            "add_blueprint_node",
            {
                "blueprint_path": blueprint_path,
                "graph_name": graph_name,
                "node_type": node_type,
                "node_properties": node_properties or {},
                "position_x": position_x,
                "position_y": position_y,
            },
        )

    @mcp.tool()
    def connect_blueprint_nodes(
        blueprint_path: str,
        graph_name: str,
        source_node_id: str,
        source_pin: str,
        target_node_id: str,
        target_pin: str,
    ) -> dict[str, Any]:
        """Connect two pins between nodes in a Blueprint graph."""
        return bridge.send_command(
            "connect_nodes",
            {
                "blueprint_path": blueprint_path,
                "graph_name": graph_name,
                "source_node_id": source_node_id,
                "source_pin": source_pin,
                "target_node_id": target_node_id,
                "target_pin": target_pin,
            },
        )

    @mcp.tool()
    def disconnect_blueprint_nodes(
        blueprint_path: str,
        graph_name: str,
        source_node_id: str,
        source_pin: str,
        target_node_id: str,
        target_pin: str,
    ) -> dict[str, Any]:
        """Remove a connection between two pins in a Blueprint graph."""
        return bridge.send_command(
            "disconnect_nodes",
            {
                "blueprint_path": blueprint_path,
                "graph_name": graph_name,
                "source_node_id": source_node_id,
                "source_pin": source_pin,
                "target_node_id": target_node_id,
                "target_pin": target_pin,
            },
        )

    @mcp.tool()
    def create_blueprint_variable(
        blueprint_path: str,
        variable_name: str,
        variable_type: str = "bool",
        default_value: Any = None,
        is_exposed: bool = False,
    ) -> dict[str, Any]:
        """
        Add a variable to a Blueprint.
        variable_type: 'bool' | 'int' | 'float' | 'string' | 'vector' | 'rotator' | 'object'.
        """
        params: dict[str, Any] = {
            "blueprint_path": blueprint_path,
            "variable_name": variable_name,
            "variable_type": variable_type,
            "is_exposed": is_exposed,
        }
        if default_value is not None:
            params["default_value"] = default_value
        return bridge.send_command("create_variable", params)

    @mcp.tool()
    def add_event_node(
        blueprint_path: str,
        graph_name: str = "EventGraph",
        event_type: str = "BeginPlay",
        position_x: int = 0,
        position_y: int = 0,
    ) -> dict[str, Any]:
        """
        Add an event node (BeginPlay, Tick, custom event, etc.) to a Blueprint graph.
        event_type: 'BeginPlay' | 'Tick' | 'ActorBeginOverlap' | custom event name.
        """
        return bridge.send_command(
            "add_event_node",
            {
                "blueprint_path": blueprint_path,
                "graph_name": graph_name,
                "event_type": event_type,
                "position_x": position_x,
                "position_y": position_y,
            },
        )

    @mcp.tool()
    def delete_blueprint_node(
        blueprint_path: str, graph_name: str, node_id: str
    ) -> dict[str, Any]:
        """Delete a node from a Blueprint graph by its node ID."""
        return bridge.send_command(
            "delete_node",
            {
                "blueprint_path": blueprint_path,
                "graph_name": graph_name,
                "node_id": node_id,
            },
        )

    @mcp.tool()
    def create_blueprint_function(
        blueprint_path: str,
        function_name: str,
        inputs: list[dict[str, str]] = None,
        outputs: list[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """
        Create a new custom function in a Blueprint.
        inputs/outputs: list of {"name": "paramName", "type": "float"} dicts.
        """
        return bridge.send_command(
            "create_function",
            {
                "blueprint_path": blueprint_path,
                "function_name": function_name,
                "inputs": inputs or [],
                "outputs": outputs or [],
            },
        )
