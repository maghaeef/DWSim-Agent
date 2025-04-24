# Chemical Process Design Agent

An intelligent agent that designs chemical processes based on raw materials and product specifications, and simulates them using DWSIM.

## Features

- Uses OpenAI's API to create an intelligent agent for chemical process design
- Automatically converts conceptual designs into DWSIM simulations
- Iteratively improves process designs based on simulation results
- Supports various thermodynamic property packages (PR, SRK, NRTL, UNIQUAC, GERG-2008, PC-SAFT, etc.)
- Tracks simulation history for each iteration
- Validates designs against mass and energy balance constraints
- Works on Linux (Ubuntu) using DWSIM's Linux compatibility

## Prerequisites

- Python 3.8 or higher
- DWSIM installed on your system
- An OpenAI API key with access to appropriate models (GPT-4 or later recommended)
- For Linux (Ubuntu): Mono runtime environment for DWSIM

### Installing DWSIM on Ubuntu Linux

1. Install the Mono runtime environment:
```bash
sudo apt-get update
sudo apt-get install mono-complete
```

2. Download the latest version of DWSIM for Linux from https://dwsim.org/download/
3. Extract the archive to a location of your choice
4. Add the DWSIM installation directory to your PATH or specify its location in the configuration file

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/chemical-process-design-agent.git
cd chemical-process-design-agent
```

2. Install the required Python packages:
```bash
pip install -r requirements.txt
```

3. Copy the example configuration file and update it with your settings:
```bash
cp config.example.yaml config.yaml
```

4. Set your OpenAI API key:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

## Usage

Run the agent with your raw materials and product specifications:

```bash
python main.py --raw-materials sample_inputs/raw_materials.json --product-specs sample_inputs/product_specs.json --output-dir results
```

### Command Line Arguments

- `--raw-materials`: Path to JSON file containing raw materials (required)
- `--product-specs`: Path to JSON file containing product specifications (required)
- `--config`: Path to configuration file (default: config.yaml)
- `--output-dir`: Directory to save simulation results (default: output)
- `--property-package`: DWSIM property package to use (overrides config file)
- `--max-iterations`: Maximum number of design iterations to run (overrides config file)
- `--verbose`: Enable verbose logging

### Input File Format

#### Raw Materials JSON Format:
```json
{
  "materials": [
    {
      "name": "Methane",
      "formula": "CH4",
      "amount": 100,
      "unit": "kmol/h",
      "state": "gas",
      "temperature": 25,
      "pressure": 101.325,
      "composition": 0.99
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
      "name": "Methanol",
      "formula": "CH3OH",
      "min_purity": 0.95,
      "min_yield": 0.85,
      "target_production_rate": 50,
      "unit": "kmol/h",
      "temperature_range": {
        "min": 20,
        "max": 30,
        "unit": "C"
      },
      "pressure_range": {
        "min": 101.0,
        "max": 105.0,
        "unit": "kPa"
      }
    },
    ...
  ]
}
```

## Configuration

The `config.yaml` file contains settings for the agent, DWSIM integration, and simulation parameters. Key settings include:

- `agent.model`: The OpenAI model to use (e.g., "gpt-4")
- `agent.max_iterations`: Maximum number of design iterations to try
- `dwsim.install_path`: Path to your DWSIM installation
- `dwsim.property_package`: Default thermodynamic property package to use
- `dwsim.calculation_mode`: DWSIM calculation mode (e.g., "Sequential" or "Equation-Oriented")

## Output

The agent saves the following for each iteration:
- Process flow diagram design (as a description and diagram)
- DWSIM simulation file
- Simulation results summary
- Evaluation against product specifications and constraints
- Final report summarizing the best design and its performance

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- DWSIM - The open source chemical process simulator
- OpenAI - For providing the AI models used by the agent