"""
Data Handler module for loading, saving, and processing input/output data.
"""

import json
import os
import logging
import jsonschema
from typing import Dict, Any, List, Optional
from src.utils.logger import get_logger

class DataHandler:
    """
    Handles input and output data operations for the Chemical Process Design Agent.
    """
    
    def __init__(self):
        """Initialize the DataHandler."""
        self.logger = get_logger(__name__)
    
    def load_raw_materials(self, file_path: str) -> Dict[str, Any]:
        """
        Load raw materials data from a JSON file.
        
        Args:
            file_path: Path to the raw materials JSON file
            
        Returns:
            Dictionary containing the raw materials data
        
        Raises:
            FileNotFoundError: If the file does not exist
            json.JSONDecodeError: If the file is not valid JSON
        """
        self.logger.info(f"Loading raw materials from {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Validate the data structure
            self._validate_raw_materials(data)
            return data
            
        except FileNotFoundError:
            self.logger.error(f"Raw materials file not found: {file_path}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in raw materials file: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading raw materials: {e}")
            raise
    
    def load_product_specs(self, file_path: str) -> Dict[str, Any]:
        """
        Load product specifications from a JSON file.
        
        Args:
            file_path: Path to the product specifications JSON file
            
        Returns:
            Dictionary containing the product specifications
        
        Raises:
            FileNotFoundError: If the file does not exist
            json.JSONDecodeError: If the file is not valid JSON
        """
        self.logger.info(f"Loading product specifications from {file_path}")
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Validate the data structure
            self._validate_product_specs(data)
            return data
            
        except FileNotFoundError:
            self.logger.error(f"Product specifications file not found: {file_path}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in product specifications file: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading product specifications: {e}")
            raise
    
    def save_simulation_results(self, results: Dict[str, Any], file_path: str) -> None:
        """
        Save simulation results to a JSON file.
        
        Args:
            results: Simulation results dictionary
            file_path: Path to save the results
        """
        self.logger.info(f"Saving simulation results to {file_path}")
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w') as f:
                json.dump(results, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving simulation results: {e}")
            raise
    
    def _validate_raw_materials(self, data: Dict[str, Any]) -> None:
        """
        Validate the raw materials data structure.
        
        Args:
            data: Raw materials data dictionary
            
        Raises:
            ValueError: If the data does not match the expected structure
        """
        # Basic structure validation
        if not isinstance(data, dict):
            raise ValueError("Raw materials data must be a dictionary")
        
        if "materials" not in data:
            raise ValueError("Raw materials data must contain a 'materials' key")
        
        if not isinstance(data["materials"], list):
            raise ValueError("The 'materials' key must contain a list")
        
        # Validate each material
        for i, material in enumerate(data["materials"]):
            if not isinstance(material, dict):
                raise ValueError(f"Material {i} must be a dictionary")
            
            required_keys = ["name", "formula", "amount", "unit", "state"]
            for key in required_keys:
                if key not in material:
                    raise ValueError(f"Material {i} ({material.get('name', 'unnamed')}) is missing required key '{key}'")
    
    def _validate_product_specs(self, data: Dict[str, Any]) -> None:
        """
        Validate the product specifications data structure.
        
        Args:
            data: Product specifications data dictionary
            
        Raises:
            ValueError: If the data does not match the expected structure
        """
        # Basic structure validation
        if not isinstance(data, dict):
            raise ValueError("Product specifications data must be a dictionary")
        
        if "products" not in data:
            raise ValueError("Product specifications data must contain a 'products' key")
        
        if not isinstance(data["products"], list):
            raise ValueError("The 'products' key must contain a list")
        
        # Validate each product
        for i, product in enumerate(data["products"]):
            if not isinstance(product, dict):
                raise ValueError(f"Product {i} must be a dictionary")
            
            required_keys = ["name", "formula", "min_purity", "min_yield", "target_production_rate", "unit"]
            for key in required_keys:
                if key not in product:
                    raise ValueError(f"Product {i} ({product.get('name', 'unnamed')}) is missing required key '{key}'")
    
    def convert_units(self, value: float, from_unit: str, to_unit: str) -> float:
        """
        Convert a value from one unit to another.
        
        Args:
            value: The value to convert
            from_unit: The source unit
            to_unit: The target unit
            
        Returns:
            The converted value
        
        Raises:
            ValueError: If the unit conversion is not supported
        """
        # Temperature conversions
        if from_unit == "C" and to_unit == "K":
            return value + 273.15
        elif from_unit == "K" and to_unit == "C":
            return value - 273.15
        elif from_unit == "F" and to_unit == "K":
            return (value + 459.67) * 5/9
        elif from_unit == "K" and to_unit == "F":
            return value * 9/5 - 459.67
        elif from_unit == "F" and to_unit == "C":
            return (value - 32) * 5/9
        elif from_unit == "C" and to_unit == "F":
            return value * 9/5 + 32
        
        # Pressure conversions
        elif from_unit == "kPa" and to_unit == "bar":
            return value / 100
        elif from_unit == "bar" and to_unit == "kPa":
            return value * 100
        elif from_unit == "psi" and to_unit == "kPa":
            return value * 6.89476
        elif from_unit == "kPa" and to_unit == "psi":
            return value / 6.89476
        elif from_unit == "bar" and to_unit == "psi":
            return value * 14.5038
        elif from_unit == "psi" and to_unit == "bar":
            return value / 14.5038
        
        # Flow rate conversions (rough approximations, depends on substance)
        elif from_unit == "kmol/h" and to_unit == "kg/h":
            # Need molecular weight for true conversion, using rough value
            self.logger.warning("Converting kmol/h to kg/h without specific molecular weight")
            return value * 20  # Rough approximation, should be replaced with actual calculation
        elif from_unit == "kg/h" and to_unit == "kmol/h":
            self.logger.warning("Converting kg/h to kmol/h without specific molecular weight")
            return value / 20  # Rough approximation
        
        # Same units
        elif from_unit == to_unit:
            return value
        
        else:
            raise ValueError(f"Unsupported unit conversion: {from_unit} to {to_unit}")