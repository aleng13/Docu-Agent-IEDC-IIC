"""
Handles all interactions with the Google Gemini API for summary extraction.
Uses the centralized gemini_helper for model management.
"""
import logging
import json

# Use our centralized Gemini helper
from src.core.gemini_client import generate_text_content

log = logging.getLogger(__name__)


def extract_details_from_text(report_text: str, additional_data: str = "") -> str:
    """
    Uses Gemini to read raw text and extract structured event details.
    
    Args:
        report_text: The full text content of the event report
        additional_data: Additional context (coordinator details, feedback responses, counts)
    
    Returns:
        A JSON string with extracted event details
    """
    
    # Build the prompt based on the user's latest refined instructions
    prompt = f"""You are a precise documentation assistant for a college activity management system (IEDC).
Your job is to extract structured data for an Activity Summary Google Sheet.

Context
You are given:
- Event name
- Event report text (official report PDF/DOC)
- Optional Google Form responses (registration / feedback)
- Additional computed metadata (participant counts, feedback summaries)

Some fields may appear either in the report OR in the forms.

âš ï¸ VERY IMPORTANT RULES
1. Use ONLY the exact column names listed below (case & spelling sensitive)
2. Prefer form data if available; if missing, fallback to report content
3. Do NOT guess or hallucinate
4. If a value cannot be confidently extracted, return an empty string ""
5. Output ONLY valid JSON
6. No explanations, no markdown, no extra text like ```json

ðŸ§¾ COLUMNS TO RETURN (EXACT NAMES)
{{
  "Event Name": "",
  "Event Date": "",
  "Domain of the Event": "",
  "Type of the Event": "",
  "Mode of event": "",
  "Resource Persons(If any)": "",
  "No. of Participants": "",
  "Male to Female Ratio": "",
  "Branchwise Participation": "",
  "Insights Gained by Participants": "",
  "Feedback form reviews": "",
  "Percentage Participation": "",
  "Winners (if any)": "",
  "Filled By": "DocuAgent"
}}

ðŸ” FIELD-SPECIFIC EXTRACTION LOGIC
- Event Name: Use the provided event name exactly.
- Event Date: Extract from report if mentioned.
- Domain of the Event: Use the â€œMapping of the eventâ€ or equivalent wording (e.g., Innovation, Entrepreneurship, Technical).
- Type of the Event: Example values: Talk, Workshop, Seminar, Competition.
- Mode of event: One of: Online, Offline, Hybrid.
- Resource Persons(If any): Speakers / judges / guests only. Do NOT include coordinators.
- No. of Participants: Prefer numeric value from report or registration form. Digits only.
- Male to Female Ratio: Strictly as Male:Female (e.g., 14:13). Priority: From forms, then explicit report mentions. Else "".
- Branchwise Participation: Strictly as CSE: 14, AIE: 5, etc. Priority: From forms, then explicit report mentions. Else "". Do NOT use "Auto-filled".
- Insights Gained by Participants: 1â€“2 concise sentences from reports or summaries.
- Feedback form reviews: Overall sentiment (Positive / Mixed / Negative). Prefer feedback form data.
- Percentage Participation: Format: 100% (only if clearly derivable). Else "".
- Winners (if any): If mentioned as Nil, return "Not Applicable".
- Filled By: Return "DocuAgent".

REPORT TEXT:
---
{report_text}
---

ADDITIONAL DATA:
---
{additional_data}
---

Return ONLY the JSON object.
"""
    
    try:
        log.info("Sending request to Gemini API with refined prompt...")
        log.debug(f"Report text length: {len(report_text)} chars")
        log.debug(f"Additional data length: {len(additional_data)} chars")
        
        # Use the centralized helper function with automatic model fallback
        response_text = generate_text_content(prompt)
        
        if not response_text:
            log.error("Gemini returned no response")
            return json.dumps({"error": "Gemini returned no response"})
        
        # Clean up the response
        json_response = response_text.strip()
        
        # Remove markdown code blocks if present
        if json_response.startswith("```"):
            json_response = json_response.split("```")[1]
            if json_response.startswith("json"):
                json_response = json_response[4:]
            json_response = json_response.strip()
        
        # Validate it's actually JSON
        try:
            parsed = json.loads(json_response)
            log.info(f"âœ… Successfully extracted {len(parsed)} fields from report")
            log.debug(f"Extracted fields: {list(parsed.keys())}")
            return json_response
        except json.JSONDecodeError as e:
            log.error(f"Gemini returned invalid JSON: {e}")
            log.error(f"Raw response: {json_response[:500]}")
            return json.dumps({"error": f"Invalid JSON from Gemini: {str(e)}"})
        
    except Exception as e:
        log.error(f"Error calling Gemini API: {e}", exc_info=True)
        return json.dumps({"error": f"Failed to call Gemini API: {str(e)}"})
