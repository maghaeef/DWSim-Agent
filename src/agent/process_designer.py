"""
Process Designer Agent module

This module contains the main agent class that designs chemical processes
using OpenAI's API and iteratively improves them based on simulation results.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from src.agent.model_manager import OpenAIModelManager
from src.dwsim.simulator import DWSIMSimulator
from src.dwsim.model_converter import ModelConverter
from src.evaluation.constraint_checker import ConstraintChecker
from src.evaluation.results_analyzer import ResultsAnalyzer
from src.utils.logger import get_logger

class ProcessDesignerAgent:
    """
    Agent that designs chemical processes using OpenAI's models and simulates them with DWSIM.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        raw_materials: Dict[str, Any],
        product_specs: Dict[str, Any],
        output_dir: str
    ):
        """
        Initialize the ProcessDesignerAgent.
        
        Args:
            config: Configuration dictionary
            raw_materials: Dictionary containing raw materials data
            product_specs: Dictionary containing product specifications
            output_dir: Directory to save outputs
        """
        self.logger = get_logger(__name__)
        self.config = config
        self.raw_materials = raw_materials
        self.product_specs = product_specs
        self.output_dir = output_dir
        
        # Create iteration-specific directories
        self.base_output_dir = output_dir
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = os.path.join(output_dir, f"run_{timestamp}")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize components
        self.model_manager = OpenAIModelManager(
            model=config["agent"]["model"],
            api_key=config["openai"]["api_key"],
            organization=config["openai"].get("organization", ""),
            temperature=config["agent"]["temperature"],
            system_message=config["agent"]["system_message"]
        )
        
        self.simulator = DWSIMSimulator(
            dwsim_path=config["dwsim"]["install_path"],
            property_package=config["dwsim"]["property_package"],
            calculation_mode=config["dwsim"]["calculation_mode"],
            timeout=config["dwsim"]["timeout"]
        )
        
        self.model_converter = ModelConverter()
        
        self.constraint_checker = ConstraintChecker(
            mass_balance_tolerance=config["evaluation"]["mass_balance_tolerance"],
            energy_balance_tolerance=config["evaluation"]["energy_balance_tolerance"]
        )
        
        self.results_analyzer = ResultsAnalyzer(
            product_specs=product_specs,
            purity_tolerance=config["evaluation"]["purity_tolerance"],
            yield_tolerance=config["evaluation"]["yield_tolerance"]
        )
        
        # Track iterations and best design
        self.current_iteration = 0
        self.max_iterations = config["agent"]["max_iterations"]
        self.best_design = None
        self.best_score = -float('inf')
        self.history = []
        
        # Save initial input data
        self._save_input_data()
        
    def _save_input_data(self):
        """Save the input data used for this run."""
        with open(os.path.join(self.output_dir, "raw_materials.json"), "w") as f:
            json.dump(self.raw_materials, f, indent=2)
            
        with open(os.path.join(self.output_dir, "product_specs.json"), "w") as f:
            json.dump(self.product_specs, f, indent=2)
            
        with open(os.path.join(self.output_dir, "config.json"), "w") as f:
            # Convert the config to a JSON-serializable format
            serializable_config = {k: v for k, v in self.config.items() if k != "agent" or k != "system_message"}
            if "agent" in serializable_config:
                serializable_config["agent"] = {k: v for k, v in serializable_config["agent"].items() 
                                              if k != "system_message"}
            json.dump(serializable_config, f, indent=2)
    
    def run(self) -> bool:
        """
        Run the process design agent through the full design-simulation-feedback loop.
        
        Returns:
            bool: True if a successful design was found, False otherwise
        """
        self.logger.info("Starting process design cycle")
        
        # Main iteration loop
        while self.current_iteration < self.max_iterations:
            self.current_iteration += 1
            self.logger.info(f"Beginning iteration {self.current_iteration}/{self.max_iterations}")
            
            # Create iteration directory
            iteration_dir = os.path.join(self.output_dir, f"iteration_{self.current_iteration}")
            os.makedirs(iteration_dir, exist_ok=True)
            
            # Get process design from OpenAI agent
            process_design = self._generate_process_design()
            
            # Save the process design
            design_path = os.path.join(iteration_dir, "process_design.json")
            with open(design_path, "w") as f:
                json.dump(process_design, f, indent=2)
            
            # Convert design to DWSIM model
            try:
                dwsim_model = self.model_converter.convert_design_to_dwsim(process_design)
                model_path = os.path.join(iteration_dir, "dwsim_model.dwxml")
                self.model_converter.save_model(dwsim_model, model_path)
                self.logger.info(f"Saved DWSIM model to {model_path}")
            except Exception as e:
                self.logger.error(f"Error converting design to DWSIM model: {e}")
                feedback = {
                    "status": "error",
                    "message": f"Failed to convert design to DWSIM model: {str(e)}",
                    "suggestions": ["Ensure all units and connections are properly specified",
                                  "Check for invalid operation parameters"]
                }
                self._record_iteration_results(iteration_dir, process_design, None, feedback)
                continue
            
            # Run simulation
            try:
                simulation_results = self.simulator.run_simulation(model_path)
                results_path = os.path.join(iteration_dir, "simulation_results.json")
                with open(results_path, "w") as f:
                    json.dump(simulation_results, f, indent=2)
                self.logger.info(f"Saved simulation results to {results_path}")
            except Exception as e:
                self.logger.error(f"Error running simulation: {e}")
                feedback = {
                    "status": "error",
                    "message": f"Simulation failed: {str(e)}",
                    "suggestions": ["Check for invalid input parameters",
                                  "Ensure thermodynamic property package is appropriate for components"]
                }
                self._record_iteration_results(iteration_dir, process_design, None, feedback)
                continue
            
            # Evaluate results
            constraint_results = self.constraint_checker.check_constraints(simulation_results)
            product_evaluation = self.results_analyzer.analyze_results(simulation_results)
            
            # Combine evaluation results
            evaluation = {
                "constraint_check": constraint_results,
                "product_evaluation": product_evaluation
            }
            
            evaluation_path = os.path.join(iteration_dir, "evaluation.json")
            with open(evaluation_path, "w") as f:
                json.dump(evaluation, f, indent=2)
            self.logger.info(f"Saved evaluation to {evaluation_path}")
            
            # Generate feedback
            feedback = self._generate_feedback(constraint_results, product_evaluation)
            
            # Check if this is the best design so far
            current_score = self._calculate_design_score(constraint_results, product_evaluation)
            if current_score > self.best_score:
                self.best_score = current_score
                self.best_design = {
                    "iteration": self.current_iteration,
                    "process_design": process_design,
                    "simulation_results": simulation_results,
                    "evaluation": evaluation,
                    "score": current_score
                }
                self.logger.info(f"New best design found at iteration {self.current_iteration} with score {current_score:.4f}")
            
            # Record this iteration
            self._record_iteration_results(iteration_dir, process_design, simulation_results, feedback)
            
            # Check if design meets all requirements
            if feedback["status"] == "success":
                self.logger.info("Process design meets all requirements!")
                self._generate_final_report()
                return True
        
        # If we've reached here, we've hit the maximum iterations without finding a perfect solution
        self.logger.info(f"Reached maximum iterations ({self.max_iterations}) without finding a perfect solution")
        self.logger.info(f"Best design found at iteration {self.best_design['iteration']} with score {self.best_score:.4f}")
        self._generate_final_report()
        return False
    
    def _generate_process_design(self) -> Dict[str, Any]:
        """
        Generate a process design using the OpenAI agent.
        
        Returns:
            Dict: A dictionary containing the process design
        """
        # Format the context for the AI
        context = self._format_design_context()
        
        # Get additional context from previous iterations if available
        if self.current_iteration > 1:
            feedback_context = self._format_feedback_context()
            context += "\n\n" + feedback_context
        
        # Generate the process design
        self.logger.info("Requesting process design from OpenAI model")
        response = self.model_manager.generate_process_design(context)
        
        # Parse the response into a structured format
        try:
            # The model should return a JSON structure, but let's handle parsing errors
            if isinstance(response, dict):
                process_design = response
            else:
                # Try to extract JSON from the response
                import re
                json_match = re.search(r'```json\n([\s\S]*?)\n```', response)
                if json_match:
                    process_design = json.loads(json_match.group(1))
                else:
                    self.logger.warning("Could not extract JSON from model response, treating entire response as design description")
                    process_design = {"design_description": response}
        except Exception as e:
            self.logger.error(f"Error parsing process design response: {e}")
            process_design = {"design_description": response}
        
        # Save the raw response if configured to do so
        if self.config["agent"].get("save_agent_responses", False):
            response_dir = os.path.join(self.output_dir, f"iteration_{self.current_iteration}")
            os.makedirs(response_dir, exist_ok=True)
            with open(os.path.join(response_dir, "raw_response.txt"), "w") as f:
                f.write(str(response))
        
        return process_design
    
    def _format_design_context(self) -> str:
        """
        Format the context information for the agent to generate a process design.
        
        Returns:
            str: Formatted context string
        """
        context = f"""
# Chemical Process Design Task

## Raw Materials
{json.dumps(self.raw_materials, indent=2)}

## Product Specifications
{json.dumps(self.product_specs, indent=2)}

## Process Design Requirements
1. Design a complete chemical process that converts the given raw materials into the specified products.
2. The process should satisfy all product specifications including purity, yield, and production rate.
3. The process must satisfy mass and energy balance constraints.
4. All unit operations must be fully specified with appropriate parameters.
5. Include material and energy streams between unit operations.
6. Specify operating conditions (temperature, pressure) for each unit.
7. Use {self.config['dwsim']['property_package']} as the thermodynamic property package for this design.

## Iteration Information
This is iteration {self.current_iteration} of a maximum {self.max_iterations} iterations.

## Output Format
Please provide your process design in JSON format with the following structure:
```json
{{
  "process_name": "Name of the process",
  "description": "Brief description of the process",
  "property_package": "{self.config['dwsim']['property_package']}",
  "unit_operations": [
    {{
      "id": "unit-1",
      "name": "Descriptive name",
      "type": "reactor/distillation/heat-exchanger/etc.",
      "specifications": {{
        // Unit-specific parameters
      }},
      "operating_conditions": {{
        "temperature": value,
        "temperature_unit": "C/K/F",
        "pressure": value,
        "pressure_unit": "kPa/bar/psi",
        "additional_parameters": {{}}
      }}
    }}
  ],
  "streams": [
    {{
      "id": "stream-1",
      "name": "Descriptive name",
      "type": "feed/intermediate/product/utility",
      "source": "unit-id or 'feed'",
      "destination": "unit-id or 'product'",
      "specifications": {{
        "phase": "liquid/gas/mixed",
        "temperature": value,
        "temperature_unit": "C/K/F",
        "pressure": value,
        "pressure_unit": "kPa/bar/psi",
        "flow_rate": value,
        "flow_rate_unit": "kmol/h or kg/h",
        "composition": [
          {{
            "component": "component name or formula",
            "fraction": value,
            "fraction_type": "mole/mass"
          }}
        ]
      }}
    }}
  ],
  "rationale": "Explanation of design choices and expected performance"
}}
```

Please provide your detailed process design now.
"""
        return context
    
    def _format_feedback_context(self) -> str:
        """
        Format feedback from previous iterations to help guide the current design.
        
        Returns:
            str: Formatted feedback context
        """
        # Get the most recent iteration's feedback
        last_iteration = self.current_iteration - 1
        last_dir = os.path.join(self.output_dir, f"iteration_{last_iteration}")
        
        feedback_file = os.path.join(last_dir, "feedback.json")
        if not os.path.exists(feedback_file):
            return "No feedback available from previous iterations."
        
        try:
            with open(feedback_file, "r") as f:
                feedback = json.load(f)
            
            context = f"""
## Feedback from Previous Iteration (Iteration {last_iteration})

### Status: {feedback['status']}

### Issues Found:
{feedback.get('message', 'No specific issues found.')}

### Specific Feedback:
"""
            
            # Add constraint issues if any
            if 'constraint_issues' in feedback and feedback['constraint_issues']:
                context += "\n#### Constraint Issues:\n"
                for issue in feedback['constraint_issues']:
                    context += f"- {issue}\n"
            
            # Add product specification issues if any
            if 'product_issues' in feedback and feedback['product_issues']:
                context += "\n#### Product Specification Issues:\n"
                for issue in feedback['product_issues']:
                    context += f"- {issue}\n"
            
            # Add suggestions if any
            if 'suggestions' in feedback and feedback['suggestions']:
                context += "\n### Improvement Suggestions:\n"
                for suggestion in feedback['suggestions']:
                    context += f"- {suggestion}\n"
            
            return context
            
        except Exception as e:
            self.logger.warning(f"Error reading feedback from previous iteration: {e}")
            return "Error retrieving feedback from previous iterations."
    
    def _generate_feedback(self, constraint_results: Dict[str, Any], product_evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate feedback based on simulation results and evaluation.
        
        Args:
            constraint_results: Results from the constraint checker
            product_evaluation: Results from the product evaluation
            
        Returns:
            Dict: Feedback for the current iteration
        """
        feedback = {
            "status": "unknown",
            "message": "",
            "constraint_issues": [],
            "product_issues": [],
            "suggestions": []
        }
        
        # Check if there were any constraint violations
        mass_balance_satisfied = constraint_results.get("mass_balance_satisfied", False)
        energy_balance_satisfied = constraint_results.get("energy_balance_satisfied", False)
        
        if not mass_balance_satisfied:
            feedback["constraint_issues"].append(f"Mass balance error: {constraint_results.get('mass_balance_error', 'unknown')}%")
            feedback["suggestions"].append("Adjust flow rates or component splits to ensure mass conservation")
        
        if not energy_balance_satisfied:
            feedback["constraint_issues"].append(f"Energy balance error: {constraint_results.get('energy_balance_error', 'unknown')}%")
            feedback["suggestions"].append("Review heat duties and enthalpy calculations for energy conservation")
        
        # Check product specifications
        all_products_meet_specs = product_evaluation.get("all_specifications_met", False)
        product_issues = product_evaluation.get("issues", {})
        
        for product_name, issues in product_issues.items():
            for issue_type, details in issues.items():
                issue_msg = f"{product_name}: {issue_type} - {details}"
                feedback["product_issues"].append(issue_msg)
                
                # Generate suggestions based on issue type
                if issue_type == "purity":
                    feedback["suggestions"].append(f"Improve separation for {product_name} to increase purity")
                elif issue_type == "yield":
                    feedback["suggestions"].append(f"Adjust reaction conditions or improve recovery for {product_name}")
                elif issue_type == "production_rate":
                    feedback["suggestions"].append(f"Increase feed rate or improve conversion for {product_name}")
                elif issue_type == "temperature":
                    feedback["suggestions"].append(f"Adjust cooling/heating for {product_name} stream")
                elif issue_type == "pressure":
                    feedback["suggestions"].append(f"Adjust pressure control for {product_name} stream")
        
        # Set overall status
        if mass_balance_satisfied and energy_balance_satisfied and all_products_meet_specs:
            feedback["status"] = "success"
            feedback["message"] = "Process design meets all requirements and constraints!"
        elif not (mass_balance_satisfied and energy_balance_satisfied):
            feedback["status"] = "constraint_violation"
            feedback["message"] = "Process design violates fundamental constraints"
        else:
            feedback["status"] = "product_specs_not_met"
            feedback["message"] = "Process design does not meet all product specifications"
        
        return feedback
    
    def _calculate_design_score(self, constraint_results: Dict[str, Any], product_evaluation: Dict[str, Any]) -> float:
        """
        Calculate a numerical score for the current design based on evaluation results.
        
        Args:
            constraint_results: Results from the constraint checker
            product_evaluation: Results from the product evaluation
            
        Returns:
            float: Score for the current design (higher is better)
        """
        score = 0.0
        
        # Base score of 100
        score = 100.0
        
        # Subtract for constraint violations
        if not constraint_results.get("mass_balance_satisfied", False):
            score -= min(50.0, abs(constraint_results.get("mass_balance_error", 0.0)) * 10)
            
        if not constraint_results.get("energy_balance_satisfied", False):
            score -= min(50.0, abs(constraint_results.get("energy_balance_error", 0.0)) * 5)
        
        # Subtract for product specification issues
        product_scores = product_evaluation.get("product_scores", {})
        for product_name, product_score in product_scores.items():
            # Normalize the product score to 0-100 scale
            normalized_score = product_score * 100
            
            # Calculate weighted average of all product scores
            num_products = len(product_scores)
            product_weight = 1.0 / num_products if num_products > 0 else 0
            
            # Adjust score based on how well products meet specifications
            score -= (100 - normalized_score) * product_weight
        
        return max(0.0, score)
    
    def _record_iteration_results(
        self, 
        iteration_dir: str, 
        process_design: Dict[str, Any],
        simulation_results: Optional[Dict[str, Any]], 
        feedback: Dict[str, Any]
    ) -> None:
        """
        Record the results of the current iteration.
        
        Args:
            iteration_dir: Directory to save results
            process_design: Process design dictionary
            simulation_results: Simulation results (if available)
            feedback: Feedback dictionary
        """
        # Save feedback
        feedback_path = os.path.join(iteration_dir, "feedback.json")
        with open(feedback_path, "w") as f:
            json.dump(feedback, f, indent=2)
        
        # Add to history
        iteration_record = {
            "iteration": self.current_iteration,
            "timestamp": datetime.now().isoformat(),
            "process_design_path": os.path.join(iteration_dir, "process_design.json"),
            "feedback": feedback,
        }
        
        if simulation_results:
            iteration_record["simulation_results_path"] = os.path.join(iteration_dir, "simulation_results.json")
        
        self.history.append(iteration_record)
        
        # Save updated history
        history_path = os.path.join(self.output_dir, "iteration_history.json")
        with open(history_path, "w") as f:
            json.dump(self.history, f, indent=2)
    
    def _generate_final_report(self) -> None:
        """Generate a final report summarizing the design process and results."""
        if not self.best_design:
            self.logger.warning("No successful design found, cannot generate final report")
            return
        
        report = {
            "summary": {
                "total_iterations": self.current_iteration,
                "best_iteration": self.best_design["iteration"],
                "best_score": self.best_score,
                "success": self.best_design["evaluation"]["product_evaluation"].get("all_specifications_met", False) and 
                          self.best_design["evaluation"]["constraint_check"].get("mass_balance_satisfied", False) and
                          self.best_design["evaluation"]["constraint_check"].get("energy_balance_satisfied", False)
            },
            "best_design": {
                "process_name": self.best_design["process_design"].get("process_name", "Unknown"),
                "description": self.best_design["process_design"].get("description", "No description available"),
                "property_package": self.best_design["process_design"].get("property_package", "Unknown")
            },
            "product_results": {}
        }
        
        # Add product-specific results
        product_evaluation = self.best_design["evaluation"]["product_evaluation"]
        products = product_evaluation.get("products", {})
        
        for product_name, product_data in products.items():
            report["product_results"][product_name] = {
                "target_production_rate": product_data.get("target_production_rate", "Unknown"),
                "actual_production_rate": product_data.get("actual_production_rate", "Unknown"),
                "target_purity": product_data.get("target_purity", "Unknown"),
                "actual_purity": product_data.get("actual_purity", "Unknown"),
                "target_yield": product_data.get("target_yield", "Unknown"),
                "actual_yield": product_data.get("actual_yield", "Unknown"),
                "specifications_met": product_data.get("specifications_met", False)
            }
        
        # Add performance metrics
        report["performance_metrics"] = {
            "mass_balance_error": self.best_design["evaluation"]["constraint_check"].get("mass_balance_error", "Unknown"),
            "energy_balance_error": self.best_design["evaluation"]["constraint_check"].get("energy_balance_error", "Unknown"),
        }
        
        # Save the report
        report_path = os.path.join(self.output_dir, "final_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Final report saved to {report_path}")
        
        # If configured to generate plots, create performance visualization
        if self.config["simulation"].get("generate_plots", False):
            self._generate_performance_plots()
    
    def _generate_performance_plots(self) -> None:
        """Generate performance plots for the design process."""
        try:
            import matplotlib.pyplot as plt
            import numpy as np
            
            # Extract iteration data
            iterations = []
            scores = []
            mass_balance_errors = []
            energy_balance_errors = []
            
            for i, record in enumerate(self.history, start=1):
                iterations.append(i)
                
                # Try to load the evaluation file
                eval_path = os.path.join(self.output_dir, f"iteration_{i}", "evaluation.json")
                if os.path.exists(eval_path):
                    with open(eval_path, "r") as f:
                        evaluation = json.load(f)
                        
                    # Extract scores (calculate if not present)
                    score = self._calculate_design_score(
                        evaluation["constraint_check"], 
                        evaluation["product_evaluation"]
                    ) if "constraint_check" in evaluation and "product_evaluation" in evaluation else 0
                    scores.append(score)
                    
                    # Extract mass balance errors
                    mass_error = evaluation.get("constraint_check", {}).get("mass_balance_error", None)
                    mass_balance_errors.append(mass_error if mass_error is not None else np.nan)
                    
                    # Extract energy balance errors
                    energy_error = evaluation.get("constraint_check", {}).get("energy_balance_error", None)
                    energy_balance_errors.append(energy_error if energy_error is not None else np.nan)
                else:
                    scores.append(0)
                    mass_balance_errors.append(np.nan)
                    energy_balance_errors.append(np.nan)
            
            # Create figures directory
            figures_dir = os.path.join(self.output_dir, "figures")
            os.makedirs(figures_dir, exist_ok=True)
            
            # Plot design scores
            plt.figure(figsize=(10, 6))
            plt.plot(iterations, scores, 'o-', color='blue')
            plt.xlabel('Iteration')
            plt.ylabel('Design Score')
            plt.title('Design Score by Iteration')
            plt.grid(True)
            plt.savefig(os.path.join(figures_dir, 'design_scores.png'))
            plt.close()
            
            # Plot mass balance errors
            plt.figure(figsize=(10, 6))
            plt.plot(iterations, mass_balance_errors, 'o-', color='red')
            plt.xlabel('Iteration')
            plt.ylabel('Mass Balance Error (%)')
            plt.title('Mass Balance Error by Iteration')
            plt.grid(True)
            plt.savefig(os.path.join(figures_dir, 'mass_balance_errors.png'))
            plt.close()
            
            # Plot energy balance errors
            plt.figure(figsize=(10, 6))
            plt.plot(iterations, energy_balance_errors, 'o-', color='green')
            plt.xlabel('Iteration')
            plt.ylabel('Energy Balance Error (%)')
            plt.title('Energy Balance Error by Iteration')
            plt.grid(True)
            plt.savefig(os.path.join(figures_dir, 'energy_balance_errors.png'))
            plt.close()
            
            self.logger.info(f"Performance plots saved to {figures_dir}")
            
        except Exception as e:
            self.logger.error(f"Error generating performance plots: {e}")