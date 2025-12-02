import logging
import json
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

class DocumentValidatorAgent:
    """
    Agent responsible for validating documents using LLM (Groq)
    """
    
    def __init__(self, groq_api_key: str, mandatory_fields: List[str], validated_data_path: str, model: str = "llama-3.3-70b-versatile"):
        """
        Initialize Document Validator Agent
        
        Args:
            groq_api_key: Groq API key
            mandatory_fields: List of mandatory fields to check
            validated_data_path: Path to store validated JSON data
            model: Groq model to use
        """
        self.mandatory_fields = mandatory_fields
        self.validated_data_path = validated_data_path
        
        # Initialize Groq LLM
        self.llm = ChatGroq(
            api_key=groq_api_key,
            model_name=model,
            temperature=0,
            max_tokens=2000
        )
        
        # Create validated data directory
        Path(validated_data_path).mkdir(parents=True, exist_ok=True)
        logger.info(f"Document Validator Agent initialized - Model: {model}")
        logger.info(f"Mandatory fields: {', '.join(self.mandatory_fields)}")
    
    def _create_extraction_prompt(self, document_text: str, filename: str) -> str:
        """
        Create the system prompt for the LLM to extract data
        """
        fields_list = ', '.join(self.mandatory_fields)
        
        prompt = f"""You are an expert document data extraction agent. Extract the following mandatory fields from the document: {fields_list}

IMPORTANT RULES:
1. Return ONLY valid JSON, nothing else
2. Use exactly these field names: {', '.join(self.mandatory_fields)}
3. If a field is NOT found, set it to empty string ""
4. If a field IS found, extract the EXACT value from the document
5. Do NOT make up or invent data

Document: {filename}

Text to analyze:
{document_text}

Return JSON in this exact format:
{{
  "name": "extracted value or empty string",
  "address": "extracted value or empty string",
  "phone_number": "extracted value or empty string"
}}
"""
        return prompt
    
    def validate_and_extract(self, document_text: str, filename: str) -> Dict[str, Any]:
        """
        Main method to send document text to LLM for extraction and validation
        
        Args:
            document_text: Text extracted from the document
            filename: Original document filename
            
        Returns:
            Dictionary with validation results
        """
        logger.info(f"Validating document: {filename}")
        
        result = {
            'filename': filename,
            'extracted_data': {},
            'missing_fields': [],
            'all_fields_present': False,
            'error_type': None
        }
        
        if not document_text or len(document_text.strip()) < 10:
            result['error_type'] = 'cannot_read_document'
            result['missing_fields'] = self.mandatory_fields.copy()
            logger.error(f"Cannot process {filename}: Document text is empty or too short.")
            return result
        
        try:
            prompt = self._create_extraction_prompt(document_text, filename)
            
            logger.info(f"Sending document to LLM for extraction...")
            
            # Call LLM
            response = self.llm.invoke([HumanMessage(content=prompt)])
            response_text = response.content.strip()
            
            logger.info(f"LLM Response received: {response_text[:200]}...")
            
            # Clean response - remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()
            
            # Parse JSON
            extracted_data = json.loads(response_text)
            
            # Ensure all mandatory fields exist in extracted_data
            for field in self.mandatory_fields:
                if field not in extracted_data:
                    extracted_data[field] = ""
            
            result['extracted_data'] = extracted_data
            
            # Check for missing/empty fields
            missing_fields = []
            for field in self.mandatory_fields:
                value = extracted_data.get(field, "")
                if not value or str(value).strip() == "":
                    missing_fields.append(field)
            
            result['missing_fields'] = missing_fields
            result['all_fields_present'] = len(missing_fields) == 0
            
            logger.info(f"Extraction complete for {filename}")
            logger.info(f"  Extracted data: {extracted_data}")
            logger.info(f"  Missing fields: {missing_fields}")
            logger.info(f"  All fields present: {result['all_fields_present']}")
            
        except json.JSONDecodeError as e:
            result['error_type'] = 'llm_json_error'
            result['missing_fields'] = self.mandatory_fields.copy()
            logger.error(f"LLM did not return valid JSON for {filename}: {str(e)}")
            logger.error(f"LLM raw response: {response_text}")
            
        except Exception as e:
            result['error_type'] = 'llm_api_error'
            result['missing_fields'] = self.mandatory_fields.copy()
            logger.error(f"LLM API error during processing {filename}: {str(e)}")
        
        return result
    
    def save_validated_data(self, validation_result: Dict[str, Any]) -> str | None:
        """
        Save successfully validated data to a JSON file
        
        Args:
            validation_result: Result from document validator
            
        Returns:
            Path to the saved JSON file or None if not saved
        """
        if not validation_result.get('all_fields_present', False):
            logger.warning("Cannot save data - not all mandatory fields are present")
            return None
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_filename = Path(validation_result['filename']).stem
        json_filename = f"{timestamp}_{original_filename}.json"
        json_filepath = Path(self.validated_data_path) / json_filename
        
        # Prepare data to save
        save_data = {
            'timestamp': datetime.now().isoformat(),
            'source_document': validation_result['filename'],
            'extracted_data': validation_result['extracted_data'],
            'validation_status': 'complete',
            'all_fields_present': True
        }
        
        # Save to JSON file
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved validated data to: {json_filepath}")
        return str(json_filepath)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            'agent': 'DocumentValidatorAgent',
            'llm_provider': 'Groq',
            'model': self.llm.model_name,
            'mandatory_fields': self.mandatory_fields,
            'validated_data_path': self.validated_data_path
        }