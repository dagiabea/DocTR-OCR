# Copyright (C) 2021-2025, Mindee.
# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://opensource.org/licenses/Apache-2.0> for full license details.

import re
from typing import Any

from app.schemas import ResumeField


def extract_email(text: str) -> tuple[str | None, float]:
    """Extract email address from text using regex."""
    # First, try to find email after "e-mail:" or "email:" prefix
    email_prefix_pattern = r'(?:e-?mail|email)[:\s]+([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})'
    prefix_match = re.search(email_prefix_pattern, text, re.IGNORECASE)
    if prefix_match:
        return prefix_match.group(1), 1.0
    
    # Fallback to general email pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    matches = re.findall(email_pattern, text)
    if matches:
        # Return first match with high confidence
        return matches[0], 1.0
    return None, 0.0


def extract_phone(text: str) -> tuple[str | None, float]:
    """Extract phone number from text using regex."""
    # First, try to find phone after "tel:" or "phone:" prefix
    phone_prefix_pattern = r'(?:tel|phone|mobile|mob)[:\s]+([+\d\s\-\(\)\.]{10,20})'
    prefix_match = re.search(phone_prefix_pattern, text, re.IGNORECASE)
    if prefix_match:
        phone_candidate = prefix_match.group(1).strip()
        # Clean and validate
        phone_clean = re.sub(r'[-.\s()]', '', phone_candidate)
        if 10 <= len(phone_clean) <= 15:
            return phone_candidate, 0.95
    
    # Patterns for various phone formats
    patterns = [
        r'\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',  # International format
        r'\+?\d{10,15}',  # Simple numeric
        r'\(\d{3}\)\s?\d{3}[-.\s]?\d{4}',  # US format (123) 456-7890
        r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',  # US format 123-456-7890
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            # Clean up the match
            phone = re.sub(r'[-.\s()]', '', matches[0])
            # Validate length (10-15 digits)
            if 10 <= len(phone) <= 15:
                confidence = 0.95 if len(phone) >= 11 else 0.85
                return matches[0], confidence
    
    return None, 0.0


def extract_name(text: str) -> tuple[str | None, float]:
    """Extract name from text (usually first few lines, capitalized)."""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    if not lines:
        return None, 0.0
    
    phone_pattern = r'[+\d\s\-\(\)\.]{8,}'
    email_pattern = r'@'
    location_pattern = r',\s*[A-Z][a-z]+'  # Pattern like "City, State/Country"
    
    # First, try to find name by looking for two single-word lines (can be non-consecutive)
    # Collect potential name lines (single words, not phone/email/location)
    potential_name_lines = []
    for i, line in enumerate(lines[:6]):  # Check first 6 lines
        line_stripped = line.strip()
        # Skip lines with phone, email, or location patterns
        if (re.search(phone_pattern, line_stripped) or 
            re.search(email_pattern, line_stripped) or
            re.search(location_pattern, line_stripped)):
            continue
        
        # Check if it's a single word (potential name part)
        if len(line_stripped.split()) == 1 and len(line_stripped) > 1:
            line_lower = line_stripped.lower()
            # Exclude common non-name patterns
            excluded_keywords = ['email', 'phone', 'contact', 'www', 'http', 'address', 'profile', 'mobileapp', 'm']
            section_headers = ['registered', 'nurse', 'engineer', 'developer', 'manager', 'director', 'contact', 'cv', 'resume']
            
            if (not any(keyword in line_lower for keyword in excluded_keywords) and
                line_lower not in [h.lower() for h in section_headers]):
                potential_name_lines.append((i, line_stripped))
    
    # If we found 2+ potential name lines, use first two
    if len(potential_name_lines) >= 2:
        first_name = potential_name_lines[0][1]
        second_name = potential_name_lines[1][1]
        
        # Capitalize both names properly for display
        first_capitalized = first_name.capitalize() if first_name[0].islower() else first_name
        second_capitalized = second_name.capitalize() if second_name[0].islower() else second_name
        return f"{first_capitalized} {second_capitalized}", 0.9
    
    # Fallback: try consecutive lines
    for i in range(min(5, len(lines) - 1)):
        first_line = lines[i].strip()
        second_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
        
        # Skip lines with phone, email, or location patterns
        if (re.search(phone_pattern, first_line) or 
            re.search(email_pattern, first_line) or
            re.search(location_pattern, first_line) or
            re.search(phone_pattern, second_line) or 
            re.search(email_pattern, second_line) or
            re.search(location_pattern, second_line)):
            continue
        
        # Check if both lines are single words (likely first and last name)
        if (len(first_line.split()) == 1 and len(second_line.split()) == 1 and
            len(first_line) > 1 and len(second_line) > 1):
            
            first_lower = first_line.lower()
            second_lower = second_line.lower()
            
            # Exclude common non-name patterns
            excluded_keywords = ['email', 'phone', 'contact', 'www', 'http', 'address', 'profile', 'mobileapp']
            section_headers = ['registered', 'nurse', 'engineer', 'developer', 'manager', 'director', 'contact', 'cv', 'resume']
            
            # Check if second line matches any section header exactly
            is_section_header = second_lower in [h.lower() for h in section_headers]
            
            # Check if second line looks like a job title
            looks_like_job_title = any(header in second_lower for header in ['nurse', 'engineer', 'developer', 'manager', 'director', 'analyst', 'specialist', 'mobileapp'])
            
            # Check if either line looks like a common non-name word
            non_name_words = ['contact', 'address', 'phone', 'email', 'www', 'http', 'profile', 'resume', 'cv', 'mobileapp']
            is_non_name = (first_lower in non_name_words or second_lower in non_name_words)
            
            if (not any(keyword in first_lower for keyword in excluded_keywords) and
                not any(keyword in second_lower for keyword in excluded_keywords) and
                not is_section_header and
                not looks_like_job_title and
                not is_non_name):
                # Capitalize both names properly for display
                first_capitalized = first_line.capitalize() if first_line[0].islower() else first_line
                second_capitalized = second_line.capitalize() if second_line[0].islower() else second_line
                return f"{first_capitalized} {second_capitalized}", 0.9
    
    # Fallback: Check first few lines for single-line names (2-4 words)
    for i, line in enumerate(lines[:5]):
        # Skip lines with phone, email, or location
        if (re.search(phone_pattern, line) or 
            re.search(email_pattern, line) or
            re.search(location_pattern, line)):
            continue
            
        words = line.split()
        if 2 <= len(words) <= 4:
            # Check if it looks like a name (mostly capitalized/title case)
            capitalized_count = sum(1 for w in words if w and w[0].isupper())
            if capitalized_count >= len(words) * 0.7:
                # Exclude common non-name patterns
                excluded_keywords = ['email', 'phone', 'profile', 'resume', 'cv', 'contact', 'address', 'www', 'http', 'registered', 'mobileapp']
                if not any(word.lower() in excluded_keywords for word in words):
                    confidence = 0.9 if i == 0 else 0.7 - (i * 0.1)
                    return line, max(confidence, 0.5)
    
    return None, 0.0


def extract_skills(text: str) -> tuple[str | None, float]:
    """Extract skills section from text, including soft skills like Communication and Leadership."""
    text_lower = text.lower()
    
    # Look for skills section header - must be a standalone line (section header)
    skills_keywords = ['skills', 'technical skills', 'competencies', 'expertise', 'technologies', 'core competencies']
    # Also include common soft skill sections
    soft_skills_keywords = ['communication', 'leadership', 'technical skills', 'soft skills', 'interpersonal skills']
    
    all_skills_sections = []
    lines = text.split('\n')
    
    # Find all skills-related sections
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        # Check if this line is a skills section header (standalone, capitalized)
        if line_lower in [kw.lower() for kw in skills_keywords + soft_skills_keywords]:
            # Verify it's a section header (short, capitalized, likely standalone)
            if len(line_lower.split()) <= 3 and line.strip() and line.strip()[0].isupper():
                all_skills_sections.append((i, line.strip()))
    
    if not all_skills_sections:
        return None, 0.0
    
    # Extract text from all skills-related sections
    all_skills_lines = []
    section_end_keywords = ['experience', 'work experience', 'work', 'employment', 'projects', 'languages', 'certifications', 'references', 'contact', 'workexperience', 'profile']
    
    for section_idx, section_header in all_skills_sections:
        remaining_lines = lines[section_idx + 1:]  # Skip header line
        section_skills = []
        
        for i, line in enumerate(remaining_lines):
            line_lower = line.lower().strip()
            # Stop at next major section (check if line is a section header)
            # Check for exact matches or common variations
            if (line_lower in [kw.lower() for kw in section_end_keywords] or
                'work experience' in line_lower or 'workexperience' in line_lower.replace(' ', '')):
                # Verify it's a section header (short, capitalized, standalone)
                if len(line_lower.split()) <= 3 and line.strip() and line.strip()[0].isupper():
                    # Always stop at section headers
                    break
            
            # Also stop if we hit another skills-related section (to avoid duplicates)
            if line_lower in [kw.lower() for kw in soft_skills_keywords + skills_keywords]:
                if len(line_lower.split()) <= 3 and line.strip() and line.strip()[0].isupper():
                    # Don't break if it's the same section type, but do break if different
                    if line_lower != section_header.lower():
                        break
            
            if line.strip() and len(line.strip()) > 2:
                section_skills.append(line.strip())
            
            # Limit each section to reasonable length
            if len('\n'.join(section_skills)) > 300:
                break
        
        if section_skills:
            # Add section header and content
            all_skills_lines.append(f"{section_header}:")
            all_skills_lines.extend(section_skills)
            all_skills_lines.append('')  # Blank line between sections
    
    if all_skills_lines:
        skills_text = '\n'.join(all_skills_lines).strip()
        # Limit total length
        if len(skills_text) > 1000:
            skills_text = '\n'.join(skills_text.split('\n')[:20])
        return skills_text, 0.85
    
    return None, 0.0


def extract_experience(text: str) -> tuple[list[str] | None, float]:
    """Extract work experience section from text and split into individual experiences."""
    text_lower = text.lower()
    
    # Look for experience section header - must be a standalone line (section header)
    exp_keywords = ['work experience', 'employment', 'professional experience', 'experience', 'career', 'workexperience']
    exp_section_start = None
    exp_line_index = None
    
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        # Check if this line is an experience section header (standalone, capitalized)
        if line_lower in [kw.lower() for kw in exp_keywords] or 'workexperience' in line_lower.replace(' ', ''):
            # Verify it's a section header (short, capitalized, likely standalone)
            if len(line_lower.split()) <= 3 and line.strip() and line.strip()[0].isupper():
                exp_section_start = text.find(line)
                exp_line_index = i
                break
    
    if exp_section_start is None:
        return None, 0.0
    
    # Extract experience text (up to next major section)
    remaining_lines = lines[exp_line_index + 1:]  # Skip header line
    exp_lines = []
    section_end_keywords = ['education', 'skills', 'projects', 'certifications', 'languages', 'references', 'additional information', 'interests', 'achievements', 'profile']
    
    for i, line in enumerate(remaining_lines):
        line_lower = line.lower().strip()
        # Stop at next major section (check if line is a section header)
        if line_lower in [kw.lower() for kw in section_end_keywords]:
            # Verify it's a section header (short, capitalized, standalone)
            if len(line_lower.split()) <= 3 and line.strip() and line.strip()[0].isupper():
                break
        
        if line.strip():
            exp_lines.append(line.strip())
    
    if not exp_lines:
        return None, 0.0
    
    # Split into individual experiences based on date patterns
    # More specific date patterns: "Nov 20XX - Oct 20XX", "2022- PRESENT", "INSA-2 2022- PRESENT", etc.
    # Look for date ranges at the START of a line (not in the middle)
    date_pattern = r'^([A-Z][a-z]{2,}\s+\d{4}|[A-Z][a-z]{2,}\s+\d{2}[X]{2}|\d{4}|[A-Z]+-\d+\s+\d{4})\s*[-–—]\s*([A-Z][a-z]{2,}\s+\d{4}|[A-Z][a-z]{2,}\s+\d{2}[X]{2}|\d{4}|PRESENT|CURRENT|NOW)'
    
    experiences = []
    current_exp = []
    
    for line in exp_lines:
        line_stripped = line.strip()
        # Check if line STARTS with a date pattern (new experience entry)
        # Must be at the beginning of the line and look like a date range
        if re.match(date_pattern, line_stripped, re.IGNORECASE):
            # Save previous experience if exists and has meaningful content
            if current_exp:
                exp_text = '\n'.join(current_exp).strip()
                # Only add if it has more than just a date (has actual content)
                if exp_text and len(exp_text.split('\n')) > 1:
                    experiences.append(exp_text)
            # Start new experience
            current_exp = [line_stripped]
        else:
            # Continue current experience (always add if we have a current experience started)
            if current_exp:
                current_exp.append(line_stripped)
            # Or start new if line looks like it could be a job entry start
            elif any(keyword in line.lower() for keyword in ['company', 'city', 'country', 'job', 'title', 'role', 'developer', 'engineer', 'manager']):
                current_exp.append(line_stripped)
    
    # Add last experience
    if current_exp:
        exp_text = '\n'.join(current_exp).strip()
        if exp_text:
            experiences.append(exp_text)
    
    # If no date-based splitting worked, try splitting by common patterns
    if not experiences:
        # Fallback: look for patterns like "Company Name", "Job Title | Company" format
        experiences = []
        current_exp = []
        
        for i, line in enumerate(exp_lines):
            line_stripped = line.strip()
            # Look for lines with "|" separator (common format: "Job Title | Company")
            # Or lines that are all caps (likely company names)
            # Or lines ending with location patterns
            looks_like_job_header = (
                '|' in line_stripped or  # "Job Title | Company"
                (line_stripped.isupper() and len(line_stripped.split()) <= 5) or  # Company name in caps
                bool(re.search(r',\s*[A-Z][a-z]+$', line_stripped))  # Ends with "City, State/Country"
            )
            
            if looks_like_job_header and current_exp:
                # Save previous experience
                exp_text = '\n'.join(current_exp).strip()
                if exp_text and len(exp_text.split('\n')) > 1:
                    experiences.append(exp_text)
                current_exp = [line_stripped]
            else:
                current_exp.append(line_stripped)
        
        if current_exp:
            exp_text = '\n'.join(current_exp).strip()
            if exp_text and len(exp_text.split('\n')) > 1:
                experiences.append(exp_text)
    
    # If still no splitting, return as single experience (but filter out single-word entries)
    if not experiences:
        # Filter out single-word lines that aren't meaningful
        meaningful_lines = [line for line in exp_lines if len(line.split()) > 1 or len(line) > 3]
        if meaningful_lines:
            full_text = '\n'.join(meaningful_lines[:30])  # Limit to first 30 lines
            return [full_text], 0.75
        else:
            return None, 0.0
    
    # Filter and limit experiences
    limited_experiences = []
    for exp in experiences[:10]:  # Max 10 experiences
        lines = exp.split('\n')
        # Filter out single-word lines that aren't meaningful
        meaningful_lines = [line for line in lines if len(line.split()) > 1 or len(line.strip()) > 3]
        if meaningful_lines and len(meaningful_lines) > 1:  # Must have at least 2 lines
            if len(meaningful_lines) > 15:  # Limit to 15 lines per experience
                meaningful_lines = meaningful_lines[:15]
            limited_experiences.append('\n'.join(meaningful_lines))
    
    if limited_experiences:
        return limited_experiences, 0.85
    else:
        # Fallback: return all experience text as single entry
        meaningful_lines = [line for line in exp_lines if len(line.split()) > 1 or len(line.strip()) > 3]
        if meaningful_lines:
            return ['\n'.join(meaningful_lines[:30])], 0.75
        return None, 0.0


def extract_education(text: str) -> tuple[str | None, float]:
    """Extract education section from text."""
    text_lower = text.lower()
    
    # Look for education section header - must be a standalone line (section header)
    edu_keywords = ['education', 'academic', 'qualifications', 'degree', 'educational background']
    edu_section_start = None
    edu_line_index = None
    
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        # Check if this line is an education section header (standalone, capitalized)
        if line_lower in [kw.lower() for kw in edu_keywords]:
            # Verify it's a section header (short, capitalized, likely standalone)
            if len(line_lower.split()) <= 3 and line.strip() and line.strip()[0].isupper():
                edu_section_start = text.find(line)
                edu_line_index = i
                break
    
    if edu_section_start is None:
        return None, 0.0
    
    # Extract education text (up to next major section or ~500 chars)
    remaining_lines = lines[edu_line_index + 1:]  # Skip header line
    edu_lines = []
    section_end_keywords = ['experience', 'skills', 'work', 'employment', 'projects', 'certifications', 'languages', 'references', 'leadership', 'communication', 'contact']
    
    for i, line in enumerate(remaining_lines):
        line_lower = line.lower().strip()
        # Stop at next major section (check if line is a section header)
        # Check if this line exactly matches a section header keyword
        if line_lower in [kw.lower() for kw in section_end_keywords]:
            # Verify it's a section header (short, capitalized, standalone)
            if len(line_lower.split()) <= 3 and line.strip() and line.strip()[0].isupper():
                # Always stop at section headers - they mark the end of current section
                break
        
        if line.strip():
            edu_lines.append(line.strip())
        
        # Limit to reasonable length
        if len('\n'.join(edu_lines)) > 500:
            break
    
    if edu_lines:
        edu_text = '\n'.join(edu_lines[:10])  # Limit to first 10 lines
        return edu_text, 0.9
    
    return None, 0.0


def extract_resume_fields(text: str) -> dict[str, Any]:
    """Extract all resume fields from text and return structured data."""
    errors = []
    
    # Extract each field
    name, name_conf = extract_name(text)
    email, email_conf = extract_email(text)
    phone, phone_conf = extract_phone(text)
    skills, skills_conf = extract_skills(text)
    experiences_list, exp_conf = extract_experience(text)
    education, edu_conf = extract_education(text)
    
    # Collect errors for missing/low-confidence fields
    if not name or name_conf < 0.5:
        errors.append("Name not found or low confidence")
    if not email or email_conf < 0.8:
        errors.append("Email not found or low confidence")
    if not phone or phone_conf < 0.7:
        errors.append("Phone not found or low confidence")
    if not skills or skills_conf < 0.6:
        errors.append("Skills section not found or low confidence")
    if not experiences_list or exp_conf < 0.6:
        errors.append("Experience section not found or low confidence")
    if not education or edu_conf < 0.6:
        errors.append("Education section not found or low confidence")
    
    # Convert experiences list to list of ResumeField objects
    experience_fields = []
    if experiences_list:
        for exp in experiences_list:
            experience_fields.append(
                ResumeField(
                    value=exp,
                    confidence=round(exp_conf, 2),
                    is_missing=False
                )
            )
    else:
        experience_fields.append(
            ResumeField(
                value=None,
                confidence=0.0,
                is_missing=True
            )
        )
    
    return {
        "name": ResumeField(
            value=name,
            confidence=round(name_conf, 2),
            is_missing=name is None or name_conf < 0.5
        ),
        "email": ResumeField(
            value=email,
            confidence=round(email_conf, 2),
            is_missing=email is None or email_conf < 0.8
        ),
        "phone": ResumeField(
            value=phone,
            confidence=round(phone_conf, 2),
            is_missing=phone is None or phone_conf < 0.7
        ),
        "skills": ResumeField(
            value=skills,
            confidence=round(skills_conf, 2),
            is_missing=skills is None or skills_conf < 0.6
        ),
        "experience": experience_fields,
        "education": ResumeField(
            value=education,
            confidence=round(edu_conf, 2),
            is_missing=education is None or edu_conf < 0.6
        ),
        "errors": errors
    }
