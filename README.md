# Chemical Process Design Agent

An OpenAI-powered agent that designs chemical processes using DWSIM simulations.

## Overview

This system leverages OpenAI's capabilities to design chemical processes that convert given raw materials into specified products. It uses DWSIM, an open-source chemical process simulator, to validate and refine these designs.

## Features

- Takes raw materials and product specifications as input
- Generates chemical process designs using OpenAI
- Simulates designs in DWSIM to verify feasibility
- Iteratively improves designs until specifications are met
- Supports various thermodynamic property packages
- Saves simulation outputs and design iterations for review

## Requirements

- Python 3.9+
- DWSIM (Linux/Ubuntu installation)
- OpenAI API key

## Installation

1. Clone this repository
2. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Install DWSIM following the instructions at [https://dwsim.org/](https://dwsim.org/)
4. Create a `.env` file in the project root with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

## Usage

Run the main script with your input files:

```bash
python main.py --raw-materials path/to/raw_materials.json --product-specs path/to/product_specs.json --property-package NRTL
```

### Input Format

#### Raw Materials JSON Format:
```json
{
  "materials": [
    {
      "name": "Ethanol",
      "formula": "C2H6O",
      "amount": 100,
      "unit": "kg",
      "temperature": 25,
      "pressure": 101.325
    },
    ...
  ]
}
```

#### Product Specifications JSON Format:
```json
{
  "products": [
    {
      "name": "Diethyl Ether",
      "formula": "C4H10O",
      "purity": 0.98,
      "minimum_yield": 0.85,
      "phase": "liquid",
      "temperature_range": {"min": 20, "max": 30},
      "pressure_range": {"min": 100, "max": 110}
    },
    ...
  ],
  "constraints": {
    "max_temperature": 200,
    "max_pressure": 1000,
    "energy_consumption": {"max": 5000, "unit": "kJ/kg"}
  }
}
```

## Output

The system will create a directory with:
- Final process design
- DWSIM simulation files
- Iteration history
- Performance metrics and analysis reports