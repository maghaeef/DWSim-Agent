"""
Model Manager module for handling interactions with OpenAI models.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union

from openai import OpenAI
from src.utils.logger import get_logger

class OpenAIModelManager:
    """
    Manages interactions with OpenAI models for process design tasks.
    """
    
    def __init__(
        self,
        model: str,
        api_key: str,
        organization: str = "",
        temperature: float = 0.2,
        system_message: str = ""
    ):
        """
        Initialize the OpenAI model manager.
        
        Args:
            model: The OpenAI model to use (e.g., "gpt-4o")
            api_key: OpenAI API key
            organization: OpenAI organization ID (optional)
            temperature: Model temperature (0.0 to 1.0)
            system_message: System message to guide the model's responses
        """
        self.logger = get_logger(__name__)
        self.model = model
        self.temperature = temperature
        self.system_message = system_message
        
        # Initialize OpenAI client
        client_kwargs = {"api_key": api_key}
        if organization:
            client_kwargs["organization"] = organization
            
        try:
            self.client = OpenAI(**client_kwargs)
            self.logger.info(f"Initialized OpenAI client with model {model}")
        except Exception as e:
            self.logger.error(f"Error initializing OpenAI client: {e}")
            raise
    
    def generate_process_design(self, context: str) -> Dict[str, Any]:
        """
        Generate a process design based on the provided context.
        
        Args:
            context: String containing raw materials, product specifications, and requirements
            
        Returns:
            Dict: Process design as a structured dictionary
        """
        self.logger.info(f"Generating process design using {self.model}")
        
        try:
            messages = [
                {"role": "system", "content": self.system_message},
                {"role": "user", "content": context}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                response_format={"type": "json_object"},
                max_tokens=4000
            )
            
            # Extract and parse the response
            result = response.choices[0].message.content
            
            try:
                # Try to parse as JSON
                process_design = json.loads(result)
                return process_design
            except json.JSONDecodeError:
                self.logger.warning("Failed to parse model response as JSON, returning raw response")
                return {"design_description": result}
                
        except Exception as e:
            self.logger.error(f"Error generating process design: {e}")
            return {"error": str(e)}
    
    def analyze_simulation_results(
        self, 
        simulation_results: Dict[str, Any],
        design: Dict[str, Any],
        product_specs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze simulation results and provide feedback for improvement.
        
        Args:
            simulation_results: Dictionary containing simulation results
            design: The current process design
            product_specs: Product specifications
            
        Returns:
            Dict: Analysis and recommendations
        """
        self.logger.info("Analyzing simulation results using OpenAI model")
        
        # Format the context for analysis
        context = f"""
# Chemical Process Simulation Analysis

## Current Process Design
{json.dumps(design, indent=2)}

## Simulation Results
{json.dumps(simulation_results, indent=2)}

## Product Specifications
{json.dumps(product_specs, indent=2)}

Please analyze the simulation results and provide:
1. An assessment of how well the process meets product specifications
2. Identification of any constraint violations or inefficiencies
3. Specific recommendations for improving the process design
4. A priority ranking of the issues that need to be addressed

Format your response as a JSON with the following structure:
```json
{{
  "assessment": "Overall assessment of the process performance",
  "issues": [
    {{
      "description": "Issue description",
      "severity": "high/medium/low",
      "related_to": "unit-id or stream-id or general"
    }}
  ],
  "recommendations": [
    {{
      "description": "Recommendation description",
      "target": "unit-id or stream-id or general",
      "expected_impact": "Description of expected improvement"
    }}
  ],
  "priority_actions": ["First action", "Second action", ...]
}}
```
"""
        
        try:
            messages = [
                {"role": "system", "content": self.system_message},
                {"role": "user", "content": context}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                response_format={"type": "json_object"},
                max_tokens=2000
            )
            
            # Extract and parse the response
            result = response.choices[0].message.content
            
            try:
                # Try to parse as JSON
                analysis = json.loads(result)
                return analysis
            except json.JSONDecodeError:
                self.logger.warning("Failed to parse analysis response as JSON, returning raw response")
                return {"assessment": result}
                
        except Exception as e:
            self.logger.error(f"Error analyzing simulation results: {e}")
            return {"error": str(e)}
    
    def suggest_design_improvements(
        self,
        current_design: Dict[str, Any],
        feedback: Dict[str, Any],
        iteration: int,
        max_iterations: int
    ) -> Dict[str, Any]:
        """
        Suggest specific improvements to the process design based on feedback.
        
        Args:
            current_design: The current process design
            feedback: Feedback from the previous iteration
            iteration: Current iteration number
            max_iterations: Maximum number of iterations
            
        Returns:
            Dict: Suggested improvements
        """
        self.logger.info(f"Suggesting design improvements for iteration {iteration}/{max_iterations}")
        
        # Format the context for improvement suggestions
        context = f"""
# Process Design Improvement (Iteration {iteration}/{max_iterations})

## Current Process Design
{json.dumps(current_design, indent=2)}

## Feedback from Previous Simulation
{json.dumps(feedback, indent=2)}

Based on the feedback from the previous simulation, please suggest specific improvements to the process design.
Focus on addressing the most critical issues first.

Your response should include:
1. A summary of the key issues that need to be addressed
2. Specific changes to unit operations (parameters, configurations)
3. Specific changes to process streams (flow rates, compositions)
4. Rationale for each suggested change

Format your response as a JSON with the following structure:
```json
{{
  "summary": "Summary of key issues and approach to improvements",
  "unit_operation_changes": [
    {{
      "unit_id": "unit-id",
      "parameter": "parameter name",
      "current_value": current value,
      "suggested_value": suggested value,
      "rationale": "Reason for the change"
    }}
  ],
  "stream_changes": [
    {{
      "stream_id": "stream-id",
      "parameter": "parameter name",
      "current_value": current value,
      "suggested_value": suggested value,
      "rationale": "Reason for the change"
    }}
  ],
  "structural_changes": [
    {{
      "type": "add/remove/modify",
      "description": "Description of the structural change",
      "rationale": "Reason for the change"
    }}
  ]
}}
```
"""
        
        try:
            messages = [
                {"role": "system", "content": self.system_message},
                {"role": "user", "content": context}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                response_format={"type": "json_object"},
                max_tokens=2000
            )
            
            # Extract and parse the response
            result = response.choices[0].message.content
            
            try:
                # Try to parse as JSON
                improvements = json.loads(result)
                return improvements
            except json.JSONDecodeError:
                self.logger.warning("Failed to parse improvements response as JSON, returning raw response")
                return {"summary": result}
                
        except Exception as e:
            self.logger.error(f"Error suggesting design improvements: {e}")
            return {"error": str(e)}