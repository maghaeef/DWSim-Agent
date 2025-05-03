"""
Model Converter module for converting agent designs to DWSIM models.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
import xml.etree.ElementTree as ET
import uuid

from src.utils.logger import get_logger

class ModelConverter:
    """
    Converts process designs from the agent into DWSIM model files.
    """
    
    def __init__(self):
        """Initialize the ModelConverter."""
        self.logger = get_logger(__name__)
    
    def convert_design_to_dwsim(self, process_design: Dict[str, Any]) -> ET.Element:
        """
        Convert a process design from the agent into a DWSIM model.
        
        Args:
            process_design: Process design dictionary
            
        Returns:
            ET.Element: XML representation of the DWSIM model
        """
        self.logger.info(f"Converting process design to DWSIM model")
        
        # Create the root element
        dwsim_file = ET.Element("DWSIM")
        dwsim_file.set("Version", "5.0")  # Use appropriate version
        
        # Add simulation info
        sim_info = ET.SubElement(dwsim_file, "SimulationInfo")
        ET.SubElement(sim_info, "Name").text = process_design.get("process_name", "Agent Generated Process")
        ET.SubElement(sim_info, "Description").text = process_design.get("description", "")
        ET.SubElement(sim_info, "ID").text = str(uuid.uuid4())
        
        # Add property package info
        property_pkg = ET.SubElement(dwsim_file, "PropertyPackages")
        pp = ET.SubElement(property_pkg, "PropertyPackage")
        ET.SubElement(pp, "Name").text = process_design.get("property_package", "NRTL")
        
        # Add compounds based on raw materials and products
        compounds = self._extract_compounds(process_design)
        compounds_element = ET.SubElement(dwsim_file, "Compounds")
        for compound in compounds:
            comp_elem = ET.SubElement(compounds_element, "Compound")
            ET.SubElement(comp_elem, "Name").text = compound["name"]
            ET.SubElement(comp_elem, "Formula").text = compound["formula"]
            ET.SubElement(comp_elem, "ID").text = str(uuid.uuid4())
        
        # Add unit operations
        unit_ops = ET.SubElement(dwsim_file, "UnitOperations")
        unit_mapping = {}  # Map unit IDs to their XML elements
        
        for unit in process_design.get("unit_operations", []):
            unit_elem = self._create_unit_operation(unit)
            unit_ops.append(unit_elem)
            unit_mapping[unit["id"]] = unit_elem
        
        # Add streams
        streams = ET.SubElement(dwsim_file, "Streams")
        stream_mapping = {}  # Map stream IDs to their XML elements
        
        for stream in process_design.get("streams", []):
            stream_elem = self._create_stream(stream)
            streams.append(stream_elem)
            stream_mapping[stream["id"]] = stream_elem
        
        # Connect streams to unit operations
        self._connect_streams_to_units(streams, unit_mapping, stream_mapping, process_design)
        
        self.logger.info("DWSIM model conversion completed")
        return dwsim_file
    
    def _extract_compounds(self, process_design: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Extract all unique compounds from the process design.
        
        Args:
            process_design: Process design dictionary
            
        Returns:
            List of compounds with name and formula
        """
        compounds = {}
        for stream in process_design.get("streams", []):
            for compound in stream.get("compounds", []):
                name = compound["name"]
                if name not in compounds:
                    compounds[name] = {"name": name, "formula": compound.get("formula", name)}
        return list(compounds.values())

    def _create_unit_operation(self, unit: Dict[str, Any]) -> ET.Element:
        """
        Create a unit operation XML element based on the agent's unit specification.
        
        Args:
            unit: Unit operation dictionary
            
        Returns:
            ET.Element: Unit operation XML element
        """
        unit_type = unit.get("type", "").lower()
        unit_elem = ET.Element("UnitOperation")
        unit_elem.set("ID", str(unit["id"]))

        # Map agent unit types to DWSIM unit operation types
        unit_mapping = {
            "reactor": "CSTR",
            "distillation_column": "DistillationColumn",
            "heat_exchanger": "HeatExchanger",
            "pump": "Pump"
        }
        dwsim_type = unit_mapping.get(unit_type, "CustomUnit")
        unit_elem.set("Type", dwsim_type)

        # Add parameters based on unit type
        if unit_type == "reactor":
            ET.SubElement(unit_elem, "ReactionID").text = unit.get("reaction_id", "")
            ET.SubElement(unit_elem, "Volume").text = str(unit.get("volume", 0.0))
        elif unit_type == "distillation_column":
            ET.SubElement(unit_elem, "NumberOfTrays").text = str(unit.get("num_trays", 10))
            ET.SubElement(unit_elem, "RefluxRatio").text = str(unit.get("reflux_ratio", 1.5))
        elif unit_type == "heat_exchanger":
            ET.SubElement(unit_elem, "HeatDuty").text = str(unit.get("heat_duty", 0.0))

        return unit_elem

    def _create_stream(self, stream: Dict[str, Any]) -> ET.Element:
        """
        Create a stream XML element based on the agent's stream specification.
        
        Args:
            stream: Stream dictionary
            
        Returns:
            ET.Element: Stream XML element
        """
        stream_elem = ET.Element("Stream")
        stream_elem.set("ID", str(stream["id"]))
        
        ET.SubElement(stream_elem, "Temperature").text = str(stream.get("temperature", 298.15))  # K
        ET.SubElement(stream_elem, "Pressure").text = str(stream.get("pressure", 101325))      # Pa
        ET.SubElement(stream_elem, "MassFlow").text = str(stream.get("mass_flow", 1.0))       # kg/s

        # Add composition
        comp_elem = ET.SubElement(stream_elem, "Composition")
        for compound in stream.get("compounds", []):
            c_elem = ET.SubElement(comp_elem, "Compound")
            c_elem.set("Name", compound["name"])
            c_elem.set("MoleFraction", str(compound.get("mole_fraction", 0.0)))

        return stream_elem

    def _connect_streams_to_units(self, streams: ET.Element, unit_mapping: Dict[str, ET.Element], 
                                stream_mapping: Dict[str, ET.Element], process_design: Dict[str, Any]):
        """
        Connect streams to unit operations by specifying inlets and outlets.
        
        Args:
            streams: Streams XML element
            unit_mapping: Mapping of unit IDs to XML elements
            stream_mapping: Mapping of stream IDs to XML elements
            process_design: Process design dictionary
        """
        for conn in process_design.get("connections", []):
            from_id = conn.get("from")
            to_id = conn.get("to")
            stream_id = conn.get("stream_id")

            if from_id and stream_id and from_id in unit_mapping:
                unit_elem = unit_mapping[from_id]
                outlet = ET.SubElement(unit_elem, "Outlet")
                outlet.set("StreamID", str(stream_id))

            if to_id and stream_id and to_id in unit_mapping:
                unit_elem = unit_mapping[to_id]
                inlet = ET.SubElement(unit_elem, "Inlet")
                inlet.set("StreamID", str(stream_id))