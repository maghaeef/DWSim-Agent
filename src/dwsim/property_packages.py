"""
Property Package module for handling thermodynamic property packages in DWSIM models.
"""

from typing import Dict, Any
import xml.etree.ElementTree as ET

class PropertyPackageHandler:
    """
    Manages the selection and configuration of property packages for DWSIM simulations.
    """
    
    def __init__(self):
        """Initialize the PropertyPackageHandler."""
        self.supported_packages = ["NRTL", "UNIQUAC", "Peng-Robinson", "Soave-Redlich-Kwong"]

    def create_property_package(self, process_design: Dict[str, Any]) -> ET.Element:
        """
        Create a property package XML element based on the process design.
        
        Args:
            process_design: Process design dictionary
            
        Returns:
            ET.Element: Property package XML element
        """
        pp_elem = ET.Element("PropertyPackage")
        pp_name = process_design.get("property_package", "NRTL")
        
        if pp_name not in self.supported_packages:
            pp_name = "NRTL"  # Default fallback
        pp_elem.set("Name", pp_name)

        # Add interaction parameters if specified
        if "interaction_parameters" in process_design:
            ip_elem = ET.SubElement(pp_elem, "InteractionParameters")
            for param in process_design["interaction_parameters"]:
                param_elem = ET.SubElement(ip_elem, "Parameter")
                param_elem.set("Compound1", param["compound1"])
                param_elem.set("Compound2", param["compound2"])
                param_elem.set("Value", str(param["value"]))

        return pp_elem

    def validate_property_package(self, process_design: Dict[str, Any], compounds: list) -> bool:
        """
        Validate that the selected property package is suitable for the compounds.
        
        Args:
            process_design: Process design dictionary
            compounds: List of compound dictionaries
            
        Returns:
            bool: True if valid, False otherwise
        """
        pp_name = process_design.get("property_package", "NRTL")
        if pp_name not in self.supported_packages:
            return False
        # Additional validation logic could be added here (e.g., compound compatibility)
        return True