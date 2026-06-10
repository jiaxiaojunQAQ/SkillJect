"""Example agent framework tool registration and schema generation."""
from typing import Callable, Any, get_type_hints
import inspect
import json

class AgentFramework:
    def __init__(self):
        self._tools = {}
    
    def register_tool(self, func: Callable) -> Callable:
        """Register a function as an agent tool via decorator."""
        hints = get_type_hints(func)
        sig = inspect.signature(func)
        
        schema = {
            "name": func.__name__,
            "description": func.__doc__ or "",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
        
        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue
            param_type = hints.get(param_name, Any)
            schema["parameters"]["properties"][param_name] = {
                "type": self._python_type_to_json(param_type)
            }
            if param.default == inspect.Parameter.empty:
                schema["parameters"]["required"].append(param_name)
        
        self._tools[func.__name__] = {"func": func, "schema": schema}
        return func
    
    def execute_tool(self, name: str, args: dict) -> str:
        if name not in self._tools:
            return f"Error: Tool '{name}' not found"
        try:
            result = self._tools[name]["func"](**args)
            return str(result)
        except Exception as e:
            return f"Error: {e}"
    
    def _python_type_to_json(self, t) -> str:
        mapping = {str: "string", int: "integer", float: "number", bool: "boolean"}
        return mapping.get(t, "string")
