"""
Results Analyzer module for processing DWSIM simulation outputs.
"""

import xml.etree.ElementTree as ET
from typing import Dict, Any

class ResultsAnalyzer:
    """
    Analyzes simulation results from DWSIM output files.
    """
    
    def __init__(self):
        """Initialize the ResultsAnalyzer."""
        pass
    
    def analyze_simulation_results(self, output_file: str) -> Dict[str, Any]:
        """
        Parse DWSIM simulation output and extract key results.
        
        Args:
            output_file: Path to the DWSIM simulation output file (XML)
            
        Returns:
            Dict containing analyzed results
        """
        tree = ET.parse(output_file)
        root = tree.getroot()
        results = {}

        # Extract product stream compositions
        product_comps = {}
        for stream in root.findall(".//Stream[@Type='Product']"):
            stream_id = stream.get("ID")
            comp_elem = stream.find("Composition")
            if comp_elem is not None:
                product_comps[stream_id] = {
                    c.get("Name"): float(c.get("MoleFraction", 0.0))
                    for c in comp_elem.findall("Compound")
                }
        results["product_compositions"] = product_comps

        # Extract energy consumption (example for heat exchangers)
        energy_use = 0.0
        for unit in root.findall(".//UnitOperation[@Type='HeatExchanger']"):
            heat_duty = float(unit.find("HeatDuty").text or 0.0)
            energy_use += abs(heat_duty)
        results["total_energy_use"] = energy_use

        return results

    def compare_to_targets(self, results: Dict[str, Any], targets: Dict[str, Any]) -> bool:
        """
        Compare simulation results to target values.
        
        Args:
            results: Analyzed simulation results
            targets: Target values from process design
            
        Returns:
            bool: True if targets are met, False otherwise
        """
        for stream_id, target_comp in targets.get("product_compositions", {}).items():
            actual_comp = results["product_compositions"].get(stream_id, {})
            for comp_name, target_value in target_comp.items():
                actual_value = actual_comp.get(comp_name, 0.0)
                if abs(actual_value - target_value) > 0.01:  # 1% tolerance
                    return False
        return Truex