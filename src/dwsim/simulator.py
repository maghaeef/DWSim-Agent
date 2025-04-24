"""
DWSIM Simulator interface module.
Handles interactions with the DWSIM process simulator.
"""

import os
import sys
import json
import logging
import subprocess
import time
from typing import Dict, Any, List, Optional, Tuple
import platform

from src.utils.logger import get_logger

class DWSIMSimulator:
    """
    Interface to the DWSIM process simulator.
    """
    
    def __init__(
        self,
        dwsim_path: str,
        property_package: str = "NRTL",
        calculation_mode: str = "Sequential",
        timeout: int = 300
    ):
        """
        Initialize the DWSIM simulator interface.
        
        Args:
            dwsim_path: Path to the DWSIM installation
            property_package: Thermodynamic property package to use
            calculation_mode: DWSIM calculation mode (Sequential or Equation-Oriented)
            timeout: Maximum simulation runtime in seconds
        """
        self.logger = get_logger(__name__)
        self.dwsim_path = dwsim_path
        self.property_package = property_package
        self.calculation_mode = calculation_mode
        self.timeout = timeout
        
        # Check if running on Linux and set up mono if needed
        self.is_linux = platform.system() == "Linux"
        
        # Validate DWSIM installation
        self._validate_dwsim_installation()
    
    def _validate_dwsim_installation(self) -> None:
        """
        Validate that the DWSIM installation is accessible.
        
        Raises:
            FileNotFoundError: If DWSIM is not found
        """
        if self.is_linux:
            # Check for DWSIM on Linux
            if not os.path.exists(self.dwsim_path):
                self.logger.error(f"DWSIM installation not found at: {self.dwsim_path}")
                raise FileNotFoundError(f"DWSIM installation not found at: {self.dwsim_path}")
            
            # Check for mono installation
            try:
                process = subprocess.run(["mono", "--version"], 
                                        stdout=subprocess.PIPE, 
                                        stderr=subprocess.PIPE,
                                        check=False)
                if process.returncode != 0:
                    self.logger.error("Mono runtime not found. Please install mono-complete.")
                    raise RuntimeError("Mono runtime not found. Please install mono-complete.")
                else:
                    mono_version = process.stdout.decode('utf-8').split('\n')[0]
                    self.logger.info(f"Found Mono runtime: {mono_version}")
            except FileNotFoundError:
                self.logger.error("Mono runtime not found. Please install mono-complete.")
                raise RuntimeError("Mono runtime not found. Please install mono-complete.")
        else:
            # Check for DWSIM on Windows
            dwsim_exe = os.path.join(self.dwsim_path, "DWSIM.exe")
            if not os.path.exists(dwsim_exe):
                self.logger.error(f"DWSIM executable not found at: {dwsim_exe}")
                raise FileNotFoundError(f"DWSIM executable not found at: {dwsim_exe}")
        
        self.logger.info(f"DWSIM installation validated at: {self.dwsim_path}")
    
    def _get_dwsim_automation_script(self, model_path: str, results_path: str) -> str:
        """
        Generate a Python script for automating DWSIM through its API.
        
        Args:
            model_path: Path to the DWSIM model file
            results_path: Path to save simulation results
            
        Returns:
            str: Python script for DWSIM automation
        """
        # Script to run the simulation and extract results
        return f"""#!/usr/bin/env python3
import os
import sys
import json
import traceback
try:
    # Set up paths
    model_path = "{model_path.replace('\\', '\\\\')}"
    results_path = "{results_path.replace('\\', '\\\\')}"
    
    # Load DWSIM API using clr/pythonnet
    import clr
    import System
    
    # Add DWSIM references
    sys.path.append("{self.dwsim_path.replace('\\', '\\\\')}")
    clr.AddReference("DWSIM")
    clr.AddReference("DWSIM.Interfaces")
    clr.AddReference("DWSIM.Thermodynamics")
    clr.AddReference("DWSIM.UnitOperations")
    
    # Import DWSIM namespaces
    from DWSIM.Interfaces import IFlowsheet
    from DWSIM.Thermodynamics import Streams
    from DWSIM.UnitOperations.UnitOperations import *
    from DWSIM.Thermodynamics.PropertyPackages import PropertyPackage
    from DWSIM.Thermodynamics.Streams.MaterialStream import MaterialStream
    
    # Load simulation
    print("Loading simulation from:", model_path)
    sim = IFlowsheet.CreateNew()
    sim.LoadFromFile(model_path)
    
    # Set calculation mode
    sim.CalculationMode = "{self.calculation_mode}"
    
    # Run simulation
    print("Running simulation...")
    sim.RunAsyncException += lambda sender, e: print(f"Simulation error: {{e.Exception.Message}}")
    success = sim.RunAllCalculators()
    
    if not success:
        print("Simulation failed to converge.")
        results = {{"status": "error", "message": "Simulation failed to converge."}}
    else:
        print("Simulation completed successfully.")
        
        # Extract results
        results = {{
            "status": "success",
            "streams": {{}},
            "unit_operations": {{}},
            "mass_balance": {{}},
            "energy_balance": {{}}
        }}
        
        # Process streams
        for stream_id, stream in sim.MaterialStreams.Items():
            ms = stream.Item2
            stream_data = {{
                "name": ms.GraphicObject.Tag,
                "from": ms.GraphicObject.InputConnectors[0].ConnectedObject.Tag if ms.GraphicObject.InputConnectors[0].IsAttached else "none",
                "to": ms.GraphicObject.OutputConnectors[0].ConnectedObject.Tag if ms.GraphicObject.OutputConnectors[0].IsAttached else "none",
                "temperature": float(ms.Temperature),
                "temperature_unit": "K",
                "pressure": float(ms.Pressure),
                "pressure_unit": "Pa",
                "total_flow": float(ms.MassFlow),
                "flow_unit": "kg/h",
                "phase": str(ms.Phase.ToString()),
                "components": {{}}
            }}
            
            # Add component data
            for i in range(ms.Components.Count):
                comp = ms.Components[i]
                stream_data["components"][comp.Name] = {{
                    "formula": comp.Formula,
                    "mole_fraction": float(comp.MoleFraction),
                    "mass_fraction": float(comp.MassFraction),
                    "mole_flow": float(comp.MolarFlow),
                    "mass_flow": float(comp.MassFlow)
                }}
            
            results["streams"][ms.GraphicObject.Tag] = stream_data
        
        # Process unit operations
        for unit_id, unit in sim.UnitOperations.Items():
            unit_obj = unit.Item2
            unit_data = {{
                "name": unit_obj.GraphicObject.Tag,
                "type": unit_obj.GetType().Name,
                "inputs": [],
                "outputs": [],
                "parameters": {{}}
            }}
            
            # Get input and output connections
            for connector in unit_obj.GraphicObject.InputConnectors:
                if connector.IsAttached:
                    unit_data["inputs"].append(connector.ConnectedObject.Tag)
            
            for connector in unit_obj.GraphicObject.OutputConnectors:
                if connector.IsAttached:
                    unit_data["outputs"].append(connector.ConnectedObject.Tag)
            
            # Extract unit-specific parameters
            # This would need to be expanded based on unit type
            if hasattr(unit_obj, "DeltaP"):
                unit_data["parameters"]["pressure_drop"] = float(unit_obj.DeltaP)
            if hasattr(unit_obj, "DeltaT"):
                unit_data["parameters"]["temperature_change"] = float(unit_obj.DeltaT)
            if hasattr(unit_obj, "HeatingDemand"):
                unit_data["parameters"]["heating_demand"] = float(unit_obj.HeatingDemand)
            if hasattr(unit_obj, "CoolingDemand"):
                unit_data["parameters"]["cooling_demand"] = float(unit_obj.CoolingDemand)
            if hasattr(unit_obj, "Efficiency"):
                unit_data["parameters"]["efficiency"] = float(unit_obj.Efficiency)
            
            results["unit_operations"][unit_obj.GraphicObject.Tag] = unit_data
        
        # Calculate mass balance
        total_input_mass = 0.0
        total_output_mass = 0.0
        
        for stream_id, stream_data in results["streams"].items():
            if stream_data["from"] == "none":  # Input stream
                total_input_mass += stream_data["total_flow"]
            elif stream_data["to"] == "none":  # Output stream
                total_output_mass += stream_data["total_flow"]
        
        mass_balance_error = 100.0
        if total_input_mass > 0:
            mass_balance_error = abs(total_input_mass - total_output_mass) / total_input_mass * 100.0
        
        results["mass_balance"] = {{
            "total_input_mass": float(total_input_mass),
            "total_output_mass": float(total_output_mass),
            "error_percent": float(mass_balance_error)
        }}
        
        # Energy balance would require more detailed calculations
        # Simplified version:
        total_energy_in = 0.0
        total_energy_out = 0.0
        
        # Sum up heating and cooling demands
        for unit_id, unit_data in results["unit_operations"].items():
            if "heating_demand" in unit_data["parameters"]:
                total_energy_in += unit_data["parameters"]["heating_demand"]
            if "cooling_demand" in unit_data["parameters"]:
                total_energy_out += unit_data["parameters"]["cooling_demand"]
        
        results["energy_balance"] = {{
            "total_energy_in": float(total_energy_in),
            "total_energy_out": float(total_energy_out)
        }}
    
    # Save results
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to: {{results_path}}")
    
except Exception as e:
    # Handle any unexpected errors
    error_info = {{
        "status": "error",
        "message": str(e),
        "traceback": traceback.format_exc()
    }}
    
    try:
        with open(results_path, 'w') as f:
            json.dump(error_info, f, indent=2)
    except:
        print("Failed to write error information to results file")
        print(traceback.format_exc())
"""
    
    def run_simulation(self, model_path: str) -> Dict[str, Any]:
        """
        Run a DWSIM simulation using the provided model.
        
        Args:
            model_path: Path to the DWSIM model file
            
        Returns:
            Dict: Simulation results
            
        Raises:
            RuntimeError: If the simulation fails
        """
        self.logger.info(f"Running DWSIM simulation with model: {model_path}")
        
        # Create temporary directory for results if it doesn't exist
        results_dir = os.path.join(os.path.dirname(model_path), "results")
        os.makedirs(results_dir, exist_ok=True)
        
        # Define path for simulation results
        results_path = os.path.join(results_dir, "simulation_results.json")
        
        # Create automation script
        script_content = self._get_dwsim_automation_script(model_path, results_path)
        script_path = os.path.join(os.path.dirname(model_path), "run_simulation.py")
        
        with open(script_path, "w") as f:
            f.write(script_content)
        
        # Make the script executable
        os.chmod(script_path, 0o755)
        
        # Run the simulation script
        self.logger.info("Starting DWSIM simulation...")
        start_time = time.time()
        
        try:
            if self.is_linux:
                # Run with mono on Linux
                cmd = ["mono", "--debug", os.path.join(self.dwsim_path, "DWSIM.exe"), 
                      "-console", "-script", script_path]
            else:
                # Run directly on Windows
                cmd = [os.path.join(self.dwsim_path, "DWSIM.exe"), 
                      "-console", "-script", script_path]
            
            self.logger.debug(f"Running command: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for the process to complete or timeout
            try:
                stdout, stderr = process.communicate(timeout=self.timeout)
                
                self.logger.debug(f"DWSIM stdout: {stdout}")
                if stderr:
                    self.logger.warning(f"DWSIM stderr: {stderr}")
                
                if process.returncode != 0:
                    self.logger.error(f"DWSIM process exited with code {process.returncode}")
                    raise RuntimeError(f"DWSIM simulation failed with exit code {process.returncode}")
                
            except subprocess.TimeoutExpired:
                process.kill()
                self.logger.error(f"DWSIM simulation timed out after {self.timeout} seconds")
                raise RuntimeError(f"DWSIM simulation timed out after {self.timeout} seconds")
            
        except Exception as e:
            self.logger.error(f"Error running DWSIM simulation: {e}")
            raise
        
        # Read simulation results
        if os.path.exists(results_path):
            with open(results_path, "r") as f:
                results = json.load(f)
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"Simulation completed in {elapsed_time:.2f} seconds")
            
            if results.get("status") == "error":
                self.logger.error(f"Simulation error: {results.get('message')}")
                raise RuntimeError(f"DWSIM simulation error: {results.get('message')}")
            
            return results
        else:
            self.logger.error("Simulation results file not found")
            raise RuntimeError("Simulation results file not found")