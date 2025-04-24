#!/usr/bin/env python3
"""
Main entry point for the Chemical Process Design Agent
This application uses an OpenAI-powered agent to design chemical processes
based on raw materials and product specifications, then simulates them using DWSIM.
"""

import argparse
import os
import yaml
import logging
from src.agent.process_designer import ProcessDesignerAgent
from src.utils.data_handler import DataHandler
from src.utils.logger import setup_logger

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Chemical Process Design Agent using OpenAI and DWSIM"
    )
    parser.add_argument(
        "--raw-materials",
        type=str,
        required=True,
        help="Path to JSON file containing raw materials"
    )
    parser.add_argument(
        "--product-specs",
        type=str,
        required=True,
        help="Path to JSON file containing product specifications"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Directory to save simulation results (default: output)"
    )
    parser.add_argument(
        "--property-package",
        type=str,
        help="DWSIM property package to use (overrides config file)"
    )
    parser.add_argument(
        "--max-iterations", 
        type=int,
        help="Maximum number of design iterations to run (overrides config file)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser.parse_args()

def main():
    """Main execution function."""
    args = parse_arguments()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = setup_logger(log_level)
    logger.info("Starting Chemical Process Design Agent")
    
    # Create output directory if it doesn't exist
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        logger.info(f"Created output directory: {args.output_dir}")
    
    # Load configuration
    try:
        with open(args.config, 'r') as config_file:
            config = yaml.safe_load(config_file)
            logger.info(f"Loaded configuration from {args.config}")
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return
    
    # Override config with command line arguments if provided
    if args.property_package:
        config['dwsim']['property_package'] = args.property_package
        logger.info(f"Using property package from command line: {args.property_package}")
    
    if args.max_iterations:
        config['agent']['max_iterations'] = args.max_iterations
        logger.info(f"Using max iterations from command line: {args.max_iterations}")
    
    # Load input data
    data_handler = DataHandler()
    try:
        raw_materials = data_handler.load_raw_materials(args.raw_materials)
        product_specs = data_handler.load_product_specs(args.product_specs)
    except Exception as e:
        logger.error(f"Error loading input data: {e}")
        return
    
    logger.info(f"Loaded {len(raw_materials)} raw materials and {len(product_specs)} product specifications")
    
    # Initialize and run the agent
    try:
        agent = ProcessDesignerAgent(
            config=config,
            raw_materials=raw_materials,
            product_specs=product_specs,
            output_dir=args.output_dir
        )
        
        success = agent.run()
        
        if success:
            logger.info("Process design completed successfully!")
            logger.info(f"Final results saved to {args.output_dir}")
        else:
            logger.warning("Process design did not fully meet specifications within the iteration limit")
            logger.info(f"Best attempt results saved to {args.output_dir}")
            
    except Exception as e:
        logger.error(f"Error during process design: {e}")
        return

if __name__ == "__main__":
    main()