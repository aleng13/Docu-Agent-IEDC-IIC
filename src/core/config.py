"""
Configuration management for DocuAgent.
Handles loading and validating the config.json file.
"""
import os
import json
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def load_config():
    """
    Loads settings from config.json in the project root.
    
    Environment Variables (from .env):
    - GEMINI_API_KEY: Optional override for Gemini API key
    - TEMPLATE_FOLDER_ID: Optional override for template folder
    - PARENT_FOLDER_ID: Optional override for parent folder
    
    Priority: .env variables > config.json values
    
    Why this works differently now:
    - Uses __file__ to find THIS file's location
    - Navigates UP to project root (../../ from src/core/)
    - Uses absolute path resolution to avoid issues
    
    Returns:
        dict: Configuration dictionary, or None if loading fails
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Navigate up: src/core/ -> src/ -> project_root/
        project_root = os.path.dirname(os.path.dirname(current_dir))
        
        # Build absolute path to config.json
        config_path = os.path.join(project_root, 'config.json')
        
        logging.info(f"Loading config from: {config_path}")
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Override with environment variables if present
        # This allows keeping sensitive data out of config.json
        if os.getenv('GEMINI_API_KEY'):
            config['gemini_api_key'] = os.getenv('GEMINI_API_KEY')
            logging.info("Using GEMINI_API_KEY from environment")
        
        if os.getenv('TEMPLATE_FOLDER_ID'):
            config['template_folder_id'] = os.getenv('TEMPLATE_FOLDER_ID')
            logging.info("Using TEMPLATE_FOLDER_ID from environment")
        
        if os.getenv('PARENT_FOLDER_ID'):
            config['parent_folder_id'] = os.getenv('PARENT_FOLDER_ID')
            logging.info("Using PARENT_FOLDER_ID from environment")
        
        return config
            
    except FileNotFoundError:
        logging.error("FATAL: config.json not found in project root.")
        return None
    except json.JSONDecodeError:
        logging.error("FATAL: config.json is not a valid JSON file.")
        return None
    except Exception as e:
        logging.error(f"Unexpected error loading config: {e}")
        return None


def get_project_root():
    """
    Returns the absolute path to the project root directory.
    Useful for resolving paths to credentials.json, token.pkl, etc.
    
    Returns:
        str: Absolute path to project root
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(current_dir))