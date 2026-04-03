"""
Gemini AI helper functions with smart model fallback.
Handles different model versions and free tier limitations.
"""
import logging
from typing import Optional, Any

try:
    import google.generativeai as genai
except ImportError:
    genai = None  # type: ignore


def get_text_model() -> Any:
    """
    Returns the best available Gemini text model.
    
    Uses the latest Gemini 2.5 models which are available for free tier.
    
    Returns:
        GenerativeModel: Configured Gemini model for text
        
    Raises:
        Exception: If no model is available
    """
    if genai is None:
        raise Exception("google.generativeai not installed")
    
    # Updated model list for 2025 - these are the CURRENT models
    text_models = [
        'gemini-2.5-flash',           # Best for free tier - fast and efficient
        'gemini-flash-latest',         # Alternative name for latest flash
        'gemini-2.0-flash',           # Fallback to 2.0 if 2.5 not available
        'gemini-pro-latest',          # Pro version (slower but more capable)
        'gemini-2.5-pro'              # Newest pro model
    ]
    
    for model_name in text_models:
        try:
            model = genai.GenerativeModel(model_name)  # type: ignore
            
            # Test the model with a simple prompt to verify it works
            test_response = model.generate_content("Hello")  # type: ignore
            
            # If we got here, the model works!
            logging.info(f"✅ Using Gemini text model: {model_name}")
            return model
            
        except Exception as e:
            logging.warning(f"⚠️ Model '{model_name}' failed: {str(e)[:100]}")
            continue
    
    raise Exception("No Gemini text models available")


def get_vision_model() -> Any:
    """
    Returns the best available Gemini vision model for image analysis.
    
    Uses the latest Gemini 2.5 models with vision capabilities.
    
    Returns:
        GenerativeModel: Configured Gemini model for vision
        
    Raises:
        Exception: If no vision model is available
    """
    if genai is None:
        raise Exception("google.generativeai not installed")
    
    # Updated model list for 2025 - vision-capable models
    vision_models = [
        'gemini-2.5-flash',           # Flash supports vision!
        'gemini-flash-latest',         # Latest flash with vision
        'gemini-2.0-flash',           # 2.0 also has vision
        'gemini-2.5-pro',             # Pro with vision
        'gemini-pro-latest'           # Latest pro
    ]
    
    for model_name in vision_models:
        try:
            model = genai.GenerativeModel(model_name)  # type: ignore
            logging.info(f"✅ Using Gemini vision model: {model_name}")
            return model
        except Exception as e:
            logging.warning(f"⚠️ Model '{model_name}' not available: {e}")
            continue
    
    raise Exception("No Gemini vision models available")


def configure_gemini(api_key: str) -> bool:
    """
    Configures the Gemini API with the provided key.
    
    Args:
        api_key: Gemini API key from .env or config
        
    Returns:
        bool: True if configuration successful, False otherwise
    """
    if genai is None:
        logging.error("google.generativeai not installed")
        return False
    
    try:
        if not api_key or api_key == "YOUR_API_KEY_HERE":
            logging.warning("Gemini API key not configured")
            return False
        
        genai.configure(api_key=api_key)  # type: ignore
        
        # Test the configuration by trying to get a model
        try:
            get_text_model()
            logging.info("✅ Gemini API configured successfully")
            return True
        except Exception as e:
            logging.error(f"❌ Gemini API test failed: {e}")
            return False
            
    except Exception as e:
        logging.error(f"❌ Failed to configure Gemini: {e}")
        return False


def generate_text_content(prompt: str, model: Optional[Any] = None) -> Optional[str]:
    """
    Generate text content with error handling.
    
    Args:
        prompt: The prompt to send to Gemini
        model: Optional pre-configured model. If None, gets a new one.
        
    Returns:
        str: Generated text, or None if failed
    """
    try:
        if model is None:
            model = get_text_model()
        
        # Type guard: at this point model cannot be None
        if model is None:
            return None
        
        response = model.generate_content(prompt)  # type: ignore
        return response.text  # type: ignore
        
    except Exception as e:
        logging.error(f"Text generation failed: {e}")
        return None


def generate_vision_content(prompt: str, image_data: dict, 
                           model: Optional[Any] = None) -> Optional[str]:
    """
    Generate content from image with error handling.
    
    Args:
        prompt: The prompt to send to Gemini
        image_data: Dict with 'mime_type' and 'data' keys
        model: Optional pre-configured model. If None, gets a new one.
        
    Returns:
        str: Generated text, or None if failed
    """
    try:
        if model is None:
            model = get_vision_model()
        
        # Type guard: at this point model cannot be None
        if model is None:
            return None
        
        response = model.generate_content([prompt, image_data])  # type: ignore
        return response.text  # type: ignore
        
    except Exception as e:
        logging.error(f"Vision generation failed: {e}")
        return None