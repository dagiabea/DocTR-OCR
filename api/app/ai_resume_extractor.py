# Copyright (C) 2021-2025, Mindee.
# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://opensource.org/licenses/Apache-2.0> for full license details.

import json
import os
from typing import Any

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None


def extract_resume_with_ai(
    text: str,
    provider: str = "openai",
    model: str | None = None,
    api_key: str | None = None
) -> dict[str, Any]:
    """
    Extract structured resume information using AI/LLM API.
    
    Args:
        text: Raw resume text
        provider: AI provider ("openai" or "anthropic")
        model: Model name (optional, uses defaults if not provided)
        api_key: API key (optional, can use environment variable)
        
    Returns:
        Dictionary with extracted resume fields
    """
    # Get API key from parameter or environment
    if not api_key:
        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key:
        raise ValueError(
            f"API key required for {provider}. "
            f"Set {provider.upper()}_API_KEY environment variable or pass api_key parameter."
        )
    
    # Prepare the prompt
    prompt = f"""Extract structured information from the following resume text. Return ONLY valid JSON with this exact structure:
{{
    "name": "Full name of the candidate",
    "email": "Email address or null",
    "phone": "Phone number or null",
    "skills": "Comma-separated list of skills or null",
    "experience": [
        {{
            "company": "Company name",
            "position": "Job title/position",
            "duration": "Date range (e.g., '2020-2023' or 'Jan 2020 - Present')",
            "description": "Brief description of responsibilities/achievements"
        }}
    ],
    "education": [
        {{
            "institution": "School/University name",
            "degree": "Degree type and field",
            "duration": "Date range or graduation year",
            "details": "Additional details like GPA, honors, etc."
        }}
    ]
}}

Resume text:
{text}

Return ONLY the JSON object, no additional text or explanation."""

    try:
        if provider == "openai":
            if not OPENAI_AVAILABLE:
                raise ValueError("openai package not installed. Install with: pip install openai")
            
            client = openai.OpenAI(api_key=api_key)
            model_name = model or "gpt-4o-mini"  # Use cheaper model by default
            
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a resume parser. Extract structured information and return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for consistent extraction
                response_format={"type": "json_object"}  # Force JSON response
            )
            
            result_text = response.choices[0].message.content
            extracted_data = json.loads(result_text)
            
        elif provider == "anthropic":
            if not ANTHROPIC_AVAILABLE:
                raise ValueError("anthropic package not installed. Install with: pip install anthropic")
            
            client = anthropic.Anthropic(api_key=api_key)
            model_name = model or "claude-3-haiku-20240307"  # Use cheaper model by default
            
            response = client.messages.create(
                model=model_name,
                max_tokens=2000,
                temperature=0.1,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            result_text = response.content[0].text
            # Extract JSON from response (Claude may add some text)
            json_start = result_text.find('{')
            json_end = result_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                result_text = result_text[json_start:json_end]
            extracted_data = json.loads(result_text)
        else:
            raise ValueError(f"Unsupported provider: {provider}. Use 'openai' or 'anthropic'")
        
        # Convert to our standard format
        return convert_ai_response_to_standard_format(extracted_data, text)
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse AI response as JSON: {str(e)}")
    except Exception as e:
        raise ValueError(f"AI extraction failed: {str(e)}")


def convert_ai_response_to_standard_format(ai_data: dict[str, Any], raw_text: str) -> dict[str, Any]:
    """Convert AI response to our standard ResumeField format."""
    from app.schemas import ResumeField
    
    errors = []
    
    # Convert name
    name_value = ai_data.get("name")
    name_field = ResumeField(
        value=name_value,
        confidence=0.95 if name_value else 0.0,
        is_missing=not name_value
    )
    if not name_value:
        errors.append("Name not found")
    
    # Convert email
    email_value = ai_data.get("email")
    email_field = ResumeField(
        value=email_value,
        confidence=1.0 if email_value else 0.0,
        is_missing=not email_value
    )
    if not email_value:
        errors.append("Email not found")
    
    # Convert phone
    phone_value = ai_data.get("phone")
    phone_field = ResumeField(
        value=phone_value,
        confidence=0.95 if phone_value else 0.0,
        is_missing=not phone_value
    )
    if not phone_value:
        errors.append("Phone not found")
    
    # Convert skills
    skills_value = ai_data.get("skills")
    if isinstance(skills_value, list):
        skills_value = ", ".join(skills_value)
    skills_field = ResumeField(
        value=skills_value,
        confidence=0.9 if skills_value else 0.0,
        is_missing=not skills_value
    )
    if not skills_value:
        errors.append("Skills not found")
    
    # Convert experience
    experience_list = ai_data.get("experience", [])
    experience_fields = []
    if experience_list:
        for exp in experience_list:
            # Format experience entry
            exp_parts = []
            if exp.get("position"):
                exp_parts.append(exp["position"])
            if exp.get("company"):
                exp_parts.append(f"at {exp['company']}")
            if exp.get("duration"):
                exp_parts.append(f"({exp['duration']})")
            if exp.get("description"):
                exp_parts.append(f"\n{exp['description']}")
            
            exp_text = " ".join(exp_parts)
            experience_fields.append(
                ResumeField(
                    value=exp_text,
                    confidence=0.9,
                    is_missing=False
                )
            )
    else:
        experience_fields.append(
            ResumeField(value=None, confidence=0.0, is_missing=True)
        )
        errors.append("Experience not found")
    
    # Convert education
    education_list = ai_data.get("education", [])
    if education_list:
        edu_parts = []
        for edu in education_list:
            edu_entry = []
            if edu.get("degree"):
                edu_entry.append(edu["degree"])
            if edu.get("institution"):
                edu_entry.append(f"from {edu['institution']}")
            if edu.get("duration"):
                edu_entry.append(f"({edu['duration']})")
            if edu.get("details"):
                edu_entry.append(f"- {edu['details']}")
            edu_parts.append(", ".join(edu_entry))
        
        education_value = "\n".join(edu_parts)
        education_field = ResumeField(
            value=education_value,
            confidence=0.9,
            is_missing=False
        )
    else:
        education_field = ResumeField(value=None, confidence=0.0, is_missing=True)
        errors.append("Education not found")
    
    return {
        "name": name_field,
        "email": email_field,
        "phone": phone_field,
        "skills": skills_field,
        "experience": experience_fields,
        "education": education_field,
        "errors": errors
    }
