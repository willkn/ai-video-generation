import script_generation
import audio_generation

import os
import json

''' 
example prompt
system_prompt = system_prompt = (
    "You are an expert dialogue writer for the animated series 'Rick and Morty'. Your task is to generate a conversation "
    "between Rick Sanchez and Morty Smith."
    "The conversation should intuitively explain a complex concept in approximately one to two minutes of spoken dialogue. "
    "The output MUST be a JSON object with a single key, 'dialogue_turns', whose value is a JSON array. "
    "Each element in this array must be an object with two keys: 'speaker' (either 'Rick' or 'Morty') and 'dialogue' (the spoken text). "
    "The dialogue should be natural for the characters but strictly plain text, suitable for Text-to-Speech (TTS). "
    "Avoid all onomatopoeia (e.g., 'burp', 'gasp'), stage directions, parentheticals, or any non-spoken elements. "
    "Morty will initiate the conversation by asking a simple question about the concept. Rick will then provide an intuitive, "
    "often cynical or irreverent, explanation. Morty should interject with clarifying questions or typical Morty-esque reactions throughout. "
    "Keep each character's turns relatively short and impactful to maintain a quick pace suitable for a one to two-minute explanation, let Rick speak for longer if the explanation warrants it.    "
    "You are banned from using apostrophes."
)

'''

class Project(): 
    def __init__(self, project_name, prompt, topic, character1, character2, video_path='assets/videos/minecraft.mp4'):
        self.project_name = project_name
        self.output_folder = f"projects/{project_name}"
        self.prompt = prompt
        self.topic = topic
        self.character1 = character1
        self.character2 = character2
        self.script = ''
        self.video_path = video_path
        self.TEXT_STYLING = {
            'position': ('center', 0.2),
            'color': '#FFFF00',       
            'font': 'Arial-Bold',
            'fontsize': 72             
            }

    def create_script(self):
        filepath = f'projects/{self.project_name}'
        self.script = json.loads(script_generation.generate_explanation(self.topic, self.prompt))
        
        try: 
            os.makedirs(filepath)
        except OSError as e:
            print('Could not create directory: ', e)
        
        full_path = os.path.join(filepath, 'script.json')

        try:
            with open(full_path, 'w') as script_json:
                json.dump(self.script, script_json, indent=4)

                return True
            
        except e:
            print('Error:', e)

    def load_character_assets_from_json(default_position: str = "center", default_offset_x: int = 0, default_offset_y: int = 0, json_filepath='character_catalog.json') -> dict:
        """
        Loads character assets from a JSON file and transforms them into the expected format.
        (Function definition from above goes here)
        """
        character_assets = {}
        
        if not os.path.exists(json_filepath):
            print(f"Error: Character JSON file not found at '{json_filepath}'")
            return character_assets

        try:
            with open(json_filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if not isinstance(data, list) or not data:
                print(f"Error: Invalid JSON structure in '{json_filepath}'. Expected a list with one dictionary.")
                return character_assets
                
            character_data_dict = data[0] 

            for char_name, char_info in character_data_dict.items():
                if not isinstance(char_info, dict):
                    print(f"Warning: Skipping invalid entry for character '{char_name}' in '{json_filepath}'. Expected a dictionary.")
                    continue

                voice_id = char_info.get('voice_id')
                image_path = char_info.get('image_path')

                if not voice_id or not image_path:
                    print(f"Warning: Skipping character '{char_name}' due to missing 'voice_id' or 'image_path' in '{json_filepath}'.")
                    continue

                character_assets[char_name] = {
                    "voice_id": voice_id,
                    "image_path": image_path,
                    "position": char_info.get("position", default_position),
                    "offset_x": char_info.get("offset_x", default_offset_x),
                    "offset_y": char_info.get("offset_y", default_offset_y)
                }
                
            return character_assets

        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from '{json_filepath}'. Please check the file's format.")
            return {}
        except Exception as e:
            print(f"An unexpected error occurred while processing '{json_filepath}': {e}")
            return {}


    def generate_audio(self):
        audio_generation.generate_audio_for_script(self.script, self.output_folder, 'Rick', '88d465f1189846ed98a0240298cf3e02','Morty', '377e4ac186da47faa3b644d033775954', )

