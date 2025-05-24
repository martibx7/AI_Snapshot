# fantasy-backend/utils/player_utils.py
from typing import Dict, Optional, Set
# import re # 're' was not used in the provided functions, can be removed if not needed elsewhere

PLAYER_NAME_SUFFIXES: Set[str] = {
    " jr.", " jr", " sr.", " sr", " iii", " ii", " iv", " v" # Keys for suffix removal
}

# --- SPECIFIC_NAME_CORRECTIONS ---
# The KEY is the raw input name (case-insensitive match from any source).
# The VALUE is the EXACT final canonical name you want in your DB and for all lookups.
# This value should already be stripped of periods, apostrophes, unwanted suffixes
# according to your canonicalization rules.
SPECIFIC_NAME_CORRECTIONS: Dict[str, str] = {
    # Raw input name : Canonical Stripped Name
    "Ken Walker Iii": "Kenneth Walker",
    "Ken Walker": "Kenneth Walker",
    "Marquise Brown": "Hollywood Brown",
    "Gabriel Davis": "Gabe Davis",
    "Josh Palmer": "Joshua Palmer",
    "D'Wayne Eskridge": "Dee Eskridge",
    "Andrew Ogletree": "Drew Ogletree",
    "Cam Ward": "Cameron Ward",
    "Kyle T Williams": "Kyle Williams",
    "Kyle T. Williams": "Kyle Williams", # Handles variation with period
    "Chigoziem Okonkwo": "Chig Okonkwo",
    "Jeffery Wilson": "Jeff Wilson",

    # Canonical forms for common initialed names (ensure these are what you want stored)
    "J.J. McCarthy": "JJ McCarthy",
    "C.J. Stroud": "CJ Stroud",
    "De'Von Achane": "Devon Achane",    # Apostrophe removed, "D" becomes "Dev"
    "D'Andre Swift": "Dandre Swift",    # Apostrophe removed
    "Ja'Marr Chase": "Jamarr Chase",    # Apostrophe removed
    "A.J. Brown": "AJ Brown",
    "D.J. Moore": "DJ Moore",          # Canonical is "DJ Moore" (uppercase DJ)
    "DJ Moore": "DJ Moore",            # Handles if source already has "DJ Moore"
    "DK Metcalf": "DK Metcalf",          # Canonical is "DK Metcalf" (uppercase DK)
    "Amon-Ra St. Brown": "Amon Ra St Brown", # Hyphen to space, period removed from St. by general rules if not in map
    "Jaxon Smith-Njigba": "Jaxon Smith Njigba", # Hyphen to space

    # General rules will handle these correctly if the input is clean enough,
    # but explicit entries are fine if you want to be certain or handle minor input variations.
    "CeeDee Lamb": "Ceedee Lamb",          # General capitalize makes "Ceedee"
    "Christian McCaffrey": "Christian Mccaffrey", # General capitalize makes "Mccaffrey"
    # Add more entries as you encounter names from various sources (Sleeper, KTC, Clay, FPros)
    # that don't perfectly convert to your desired canonical form via the general rules below.
}

def normalize_player_name(name: Optional[str]) -> str:
    if name is None:
        return ""

    name_input_cleaned = name.strip()

    # 1. Check SPECIFIC_NAME_CORRECTIONS for a direct canonical mapping.
    #    The key matching is case-insensitive.
    for raw_key, canonical_value in SPECIFIC_NAME_CORRECTIONS.items():
        if raw_key.lower() == name_input_cleaned.lower():
            return canonical_value  # Return the pre-defined canonical name directly

    # 2. If no specific correction, apply general normalization rules.
    name_lower = name_input_cleaned.lower() # Work with lowercase for consistent rule application

    # Remove suffixes
    # The suffix set includes variations with/without leading space.
    # The .lower().strip() on the suffix in the loop makes this robust.
    for suffix_to_remove in PLAYER_NAME_SUFFIXES:
        if name_lower.endswith(suffix_to_remove.lower().strip()): # Compare against normalized suffix
            name_lower = name_lower[:-len(suffix_to_remove.strip())].strip() # Strip suffix for length calculation
            break  # Assume only one suffix per name is primary

    # Aggressively strip unwanted characters according to your strategy:
    name_lower = name_lower.replace('.', '')  # Remove ALL periods
    name_lower = name_lower.replace("'", "")  # Remove ALL apostrophes
    name_lower = name_lower.replace('-', ' ') # Replace hyphens with spaces

    # Clean up any leading/trailing spaces and multiple internal spaces created by replacements
    name_lower = name_lower.strip()
    name_parts = name_lower.split() # Splits by any whitespace and removes empty strings

    # Consistent capitalization for the remaining parts.
    # Note: 'jj' becomes 'Jj', 'dj' becomes 'Dj'. If you want 'JJ', 'DJ',
    # those specific names MUST be handled by SPECIFIC_NAME_CORRECTIONS to output that exact form.
    capitalized_parts = [part.capitalize() for part in name_parts if part]
    final_name = ' '.join(capitalized_parts)

    return final_name