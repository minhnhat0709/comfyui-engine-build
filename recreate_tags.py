import json
from supabase import Client, create_client
import os
import google.generativeai as genai
from PIL import Image
import requests
from io import BytesIO
import ast


GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AIzaSyDpZRwP5DCitkrQiPJIdRCIRDP4Ba_UvPU')
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-002')

url: str = os.environ.get('SUPABASE_ENDPOINT') or "https://rtfoijxfymuizzxzbnld.supabase.co"
key: str = os.environ.get('SUPABASE_KEY') or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ0Zm9panhmeW11aXp6eHpibmxkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTY5NjU3NzgxNCwiZXhwIjoyMDEyMTUzODE0fQ.huosB8bfQgkZ_YY7-E67YB5HbFsPjAM7rTg2Jt54x7M"
supabase: Client = create_client(url, key)



parent_tags =  ['interior', 'architecture']
tags = ['townhouse', 'villa', 'house', 'apartment', 'office', 'hotel', 'restaurant', 'bar', 'cafe', 'shop', 'school', 'hospital', 'park', 'library', 'museum', 'art', 'music', 'sport', 'travel', 'technology', 'other']

# loras = supabase.table("Models").select("*").eq("type", "lora").execute().data

# Add these constants at the top of the file after imports
VALID_CONCEPTS = {'interior', 'exterior'}

VALID_TYPES = {
    'interior': {
        'normal',
        'office',
        'restaurant',
        'retail',
        'lobby',
        'hallway',
        'bar',
        'cafe'
    },
    'exterior': {
        'townhouse',
        'apartment',
        'office',
        'school',
        'hospital',
        'mall',
        'hotel',
        'restaurant',
        'church',
        'temple',
        'museum',
        'library',
        'factory',
        'warehouse',
        'house',
        'villa'
    }
}

STYLE_MAPPING = {
    # Common variations to standardized terms
    'modern': 'modern',
    'contemporary': 'modern',
    'traditional': 'traditional',
    'classic': 'traditional',
    'minimal': 'minimalist',
    'minimalistic': 'minimalist',
    'industrial': 'industrial',
    'rustic': 'rustic',
    'country': 'rustic',
    'scandinavian': 'scandinavian',
    'nordic': 'scandinavian',
    'town house': 'townhouse',
    'town-house': 'townhouse',
    # Add more mappings as needed
}

def normalize_tag(tag: str) -> str:
    """Normalize a tag to its standard form"""
    # Convert to lowercase and remove extra spaces
    normalized = tag.lower().strip()
    
    # Remove multiple spaces and replace with single space
    normalized = ' '.join(normalized.split())
    
    # Check if we have a standard mapping for this tag
    return STYLE_MAPPING.get(normalized, normalized)

def validate_classification(concept: str, building_type: str, style: str) -> tuple:
    """Validate and normalize classification results"""
    # Normalize all inputs
    concept = normalize_tag(concept)
    building_type = normalize_tag(building_type)
    style = normalize_tag(style)
    
    # Validate concept
    if concept not in VALID_CONCEPTS:
        concept = 'interior'  # Default fallback
    
    # Validate building type
    if building_type not in VALID_TYPES[concept]:
        # Try to find closest match or use default
        building_type = 'normal' if concept == 'interior' else 'house'
    
    return concept, building_type, style

def get_tags_from_gemini(file_name: str, image_path: str, existing_tags: list) -> list:
    """Use Gemini to generate and organize tags based on filename, image, and existing tags"""
    try:
        image = Image.open(image_path)
        
        # Format existing tags for the prompt
        existing_tags_str = "\n".join([
            f"- {tag['name']}" + (f" (child of {tag['parent_id']})" if tag['parent_id'] else " (parent tag)")
            for tag in existing_tags
        ])
        
        prompt = f"""
        Analyze this sample image to identify background and scene elements. This is for a background changing application.

        sample image name: {file_name}

        Existing tags in the system:
        {existing_tags_str}

        Please:
        1. Focus primarily on background elements and scenes (e.g., beach, forest, city, indoor)
        2. IMPORTANT: Each image MUST have exactly ONE of these parent tags:
           - studio (for indoor images)
           - landscape (for nature/outdoor scenes)
           - product (for commercial/product shots)
           - art (for artistic/Surrealism images like giant flower, giant leaf, dragon, abstract objects)
        4. Consider but not limited to below tags, be creative:
           - Location type (indoor/outdoor/beach/etc)
           - Scene setting (urban/nature/event/etc)
           - Style (modern/vintage/minimal/etc)
           - Lighting (bright/dark/moody/etc)
           - Weather/Time (sunny/rainy/night/day)
        5. Additional important tags to consider:
          - man
          - woman
          - child
          - wedding
          - studio
          - garden
          - beach
          - fantasy
          - romantic

        Return ONLY the most relevant hierarchical tags in this exact format:
        <child_tag1>: None
        <child_tag2>: None
        <child_tag3>: None

        Maximum 6 tag relationships. First tag MUST be one of the mandatory parent tags.
        """
        
        response = model.generate_content([prompt, image])
        print(response.text)
        
        # Process the response
        tag_relations = {}
        for line in response.text.strip().split('\n'):
            if ':' in line:
                tag, parent = map(str.strip, line.split(':'))
                tag_relations[tag.lower()] = None if parent.lower() == 'none' else parent.lower()
        
        return tag_relations
        
    except Exception as e:
        print(f"Error generating tags: {str(e)}")
        return {'outdoor': None, 'scene': None}  # Default fallback tags


def get_loras(tag):
    loras = supabase.table("Models").select("*").eq("type", "lora").eq("tags", tag).execute().data
    return loras

# for tag in parent_tags:
#     supabase.table("tags").insert({"name": tag, "parent_id": None}).execute()

# Add this constant after other constants
REFERENCE_SAMPLE_SIZE = 5  # Number of recent classifications to use as reference

# Add this new function
def format_reference_examples(recent_classifications: list) -> str:
    """Format recent classifications as reference examples for Gemini"""
    if not recent_classifications:
        return ""
        
    reference_text = "\nRecent classification examples:\n"
    for item in recent_classifications:
        reference_text += f"""
Image: {item['name']}
- Concept: {item['concept']}
- Type: {item['type']}
- Style: {item['style']}
---"""
    return reference_text

def classify_lora_images():
    """Classify loras using both name and image for comprehensive analysis"""
    try:
        # Get all loras
        loras = supabase.table("Models").select("*").eq("type", "lora").execute().data
        
        classified_loras = []
        recent_classifications = []  # Store recent classifications for reference
        
        for lora in loras:
            if not lora.get('images') or not lora['images']:  # Skip if no images
                continue
                
            image_url = lora['images'][0]
            lora_name = lora.get('name', 'Unknown')
            
            try:
                # Update the analysis prompt to include recent examples
                reference_examples = format_reference_examples(recent_classifications)
                
                analysis_prompt = f"""
                Analyze this architectural image and provide three pieces of information.
                
                {reference_examples}
                
                Based on these recent classifications and maintaining consistency, please analyze the current image:
                
                1. CONCEPT: Determine if this is interior or exterior
                2. TYPE: Identify the specific building/space type
                3. VISUAL_STYLE: Analyze the architectural/design style visible in the image
                
                For exterior, consider these types:
                {', '.join(VALID_TYPES['exterior'])}
                
                For interior, consider these types:
                {', '.join(VALID_TYPES['interior'])}
                
                Return in this EXACT format:
                CONCEPT: [interior/exterior]
                TYPE: [specific type from list above]
                VISUAL_STYLE: [architectural/design style visible in image]
                
                Important: Maintain consistency with similar recent classifications.
                """
                
                # Download image for classification
                response = requests.get(image_url)
                image = Image.open(BytesIO(response.content))
                
                # Determine concept, type and visual style from image
                response = model.generate_content([analysis_prompt, image])
                lines = response.text.strip().split('\n')
                
                # Parse response
                concept = lines[0].split(': ')[1].strip().lower()
                building_type = lines[1].split(': ')[1].strip()
                visual_style = lines[2].split(': ')[1].strip()
                
                # Determine style from lora name
                name_prompt = f"""
                Analyze this LoRA name: "{lora_name}"
                Extract any architectural or design style mentioned in the name.
                Return ONLY the style name, nothing else.
                If no clear style is mentioned, return "Unknown"


                {reference_examples}
                Please maintain consistency with these recent classifications.
                """
                
                name_response = model.generate_content(name_prompt)
                name_style = name_response.text.strip()
                
                # Combine styles, prioritizing name if it's not "Unknown"
                final_style = name_style if name_style != "Unknown" else visual_style
                
                # Add validation step
                concept, building_type, final_style = validate_classification(
                    concept,
                    building_type,
                    final_style
                )
                
                # Store result with validated data
                classified_loras.append({
                    'id': lora['id'],
                    'name': lora_name,
                    'image': image_url,
                    'concept': concept,
                    'type': building_type,
                    'style': final_style,
                    'visual_style': visual_style,
                    'name_style': name_style
                })
                
                # After successful classification, add to recent examples
                recent_classifications.append({
                    'name': lora_name,
                    'concept': concept,
                    'type': building_type,
                    'style': final_style
                })
                
                # Print immediate result for monitoring
                print(f"Processed: {lora_name}")
                print(f"Concept: {concept}")
                print(f"Type: {building_type}")
                print(f"Style from name: {name_style}")
                print(f"Style from image: {visual_style}")
                print(f"Final style: {final_style}")
                print("-" * 40)
                
            except requests.RequestException as e:
                print(f"Error downloading image for {lora_name}: {str(e)}")
                continue
            except Exception as e:
                print(f"Error processing {lora_name}: {str(e)}")
                continue
        
        # Print final organized results
        print("\nClassified Architectural Types:")
        print("============================")
        
        # write the classified_loras to a json file
        with open('classified_loras.json', 'w') as f:
            json.dump(classified_loras, f)
            
    except Exception as e:
        print(f"Error classifying images: {str(e)}")
        raise e

# read tags from json file then update the Models table
def update_tags():
    try:
        with open('Ready_Lora.json', 'r') as f:
            json_file = json.load(f)
        
        for lora in json_file:
            try:
                # First try json.loads if the tags are JSON string
                try:
                    tags = json.loads(lora['tags'])
                except json.JSONDecodeError:
                    # If that fails, try ast.literal_eval with error handling
                    tags = ast.literal_eval(lora['tags'])
                
                # print(f"Processing tags for lora {lora.get('id', 'unknown')}: {tags}")
                # Uncomment when ready to update database
                supabase.table("Models").update({"tags": tags}).eq("id", lora['id']).execute()
                
            except (json.JSONDecodeError, ValueError, SyntaxError) as e:
                print(f"Error processing tags for lora {lora.get('id', 'unknown')}: {str(e)}")
                continue
            
    except FileNotFoundError:
        print("Ready_Lora.json file not found")
    except json.JSONDecodeError:
        print("Invalid JSON format in Ready_Lora.json")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")

# Add this line at the end of the file to run the classification
if __name__ == "__main__":
    update_tags()