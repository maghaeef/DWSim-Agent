"""
Constraint Checker module for validating process designs before DWSIM simulation.
"""

from typing import Dict, Any

class ConstraintChecker:
    """
    Checks constraints on the process design to ensure simulation readiness.
    """
    
    def __init__(self):
        """Initialize the ConstraintChecker."""
        pass
    
    def check_mass_balance(self, process_design: Dict[str, Any]) -> bool:
        """
        Verify that mass balance is satisfied across feeds and products.
        
        Args:
            process_design: Process design dictionary
            
        Returns:
            bool: True if mass balance holds, False otherwise
        """
        total_in = sum(stream.get("mass_flow", 0.0) for stream in process_design.get("feeds", []))
        total_out = sum(stream.get("mass_flow", 0.0) for stream in process_design.get("products", []))
        return abs(total_in - total_out) < 1e-6

    def check_stream_connections(self, process_design: Dict[str, Any]) -> bool:
        """
        Ensure all unit operations have required stream connections.
        
        Args:
            process_design: Process design dictionary
            
        Returns:
            bool: True if all connections are valid, False otherwise
        """
        units = {unit["id"]: unit for unit in process_design.get("unit_operations", [])}
        connections = process_design.get("connections", [])

        for unit_id, unit in units.items():
            unit_type = unit.get("type", "").lower()
            inlets = [c for c in connections if c.get("to") == unit_id]
            outlets = [c for c in connections if c.get("from") == unit_id]

            if unit_type in ["reactor", "distillation_column", "heat_exchanger"]:
                if not inlets or not outlets:
                    return False
            elif unit_type == "pump":
                if not inlets or len(outlets) != 1:
                    return False

        return True

    def check_parameters(self, process_design: Dict[str, Any]) -> bool:
        """
        Verify that unit operation parameters are valid.
        
        Args:
            process_design: Process design dictionary
            
        Returns:
            bool: True if parameters are valid, False otherwise
        """
        for unit in process_design.get("unit_operations", []):
            unit_type = unit.get("type", "").lower()
            if unit_type == "reactor" and unit.get("volume", 0.0) <= 0:
                return False
            elif unit_type == "distillation_column" and unit.get("num_trays", 0) <= 0:
                return False
        return True