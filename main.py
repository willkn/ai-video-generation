import os
import json
import create_video
import project_scaffolding

# --- Configuration Loading ---
def load_config(filename):
    """Loads JSON data from a file."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Config file not found at {filename}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {filename}")
        return None

# --- Load Data ---
prompts_data = load_config('default_environments.json')
character_catalog_data = load_config('character_catalog.json')

# Check if prompts_data is a list, as expected for iterating scenes
if not isinstance(prompts_data, list):
    print("Error: 'default_environments.json' did not load as a list. Please check the file structure and the load_config function.")
    exit()

# Check if character_catalog_data is a dictionary (as expected for looking up characters)
if not isinstance(character_catalog_data, dict):
    print("Error: 'character_catalog.json' did not load as a dictionary. Please check the file structure and the load_config function.")
    exit()

# --- User Interaction ---
def get_user_choices():
    """Presents choices to the user and returns selected scene and topic."""
    print("--- Select a Scene ---")
    
    for i, scene_config in enumerate(prompts_data):
        if not isinstance(scene_config, dict) or 'Title' not in scene_config:
            print(f"Warning: Skipping malformed scene entry at index {i}. Expected a dictionary with a 'Title' key.")
            continue # Skip the problematic entry and continue to the next.
            
        print(f"{i + 1}. {scene_config['Title']}")

    while True:
        try:
            scene_choice_input = input("Enter the number for your chosen scene: ")
            scene_choice = int(scene_choice_input)
            
            if 1 <= scene_choice <= len(prompts_data):
                selected_scene_config = prompts_data[scene_choice - 1]
                if not isinstance(selected_scene_config, dict) or 'Title' not in selected_scene_config:
                    print("The selected scene configuration is invalid. Please choose another.")
                    continue # Prompt again if the chosen one is bad
                break # Exit loop if valid scene is selected
            else:
                print("Invalid scene number. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except IndexError:
            print("Invalid scene number. Please try again.")


    print("\n--- Enter Your Topic ---")
    default_topic = selected_scene_config.get('DefaultTopic', '')
    topic_input = input(f"Enter the topic to explain (or press Enter for default: '{default_topic}'): ")
    topic = topic_input.strip() if topic_input.strip() else default_topic
    
    if not topic:
        print("Topic cannot be empty. Please re-select the scene or enter a topic.")
        return get_user_choices()

    return selected_scene_config, topic

# --- Main Flow ---
if __name__ == "__main__":
    # Ensure ImageMagick is configured
    create_video.check_and_configure_imagemagick()

    selected_scene_config, user_topic = get_user_choices()

    if not selected_scene_config:
        print("Failed to get valid scene selection. Exiting.")
        exit()
    
    # 1. project_name
    scene_title_clean = selected_scene_config['Title'].replace(' ', '_').replace('(', '').replace(')', '').replace('&', 'and')
    topic_clean = user_topic.replace(' ', '_').replace('(', '').replace(')', '').replace('&', 'and')
    project_name = f"{scene_title_clean}_{topic_clean}"

    # 2. prompt
    prompt_template = selected_scene_config['Prompt']
    if '{topic}' in prompt_template:
        specific_prompt = prompt_template.format(topic=user_topic)
    else:
        specific_prompt = prompt_template

    # 3. topic
    topic = user_topic

    # 4. characters and assets
    characters_in_scene = selected_scene_config.get('Characters', [])
    scene_character_catalog = {}
    char1_name = None
    char2_name = None
    
    if len(characters_in_scene) > 0:
        char1_name = characters_in_scene[0]
        if char1_name in character_catalog_data:
            scene_character_catalog[char1_name] = character_catalog_data[char1_name]
        else:
            print(f"Warning: Character '{char1_name}' not found in character_catalog.json.")

    if len(characters_in_scene) > 1:
        char2_name = characters_in_scene[1]
        if char2_name in character_catalog_data:
            scene_character_catalog[char2_name] = character_catalog_data[char2_name]
        else:
            print(f"Warning: Character '{char2_name}' not found in character_catalog.json.")

    # 5. video_path
    video_path = "assets/videos/minecraft.mp4" # Edit this if you wish to use a different background video
    if not video_path:
        print("No default base video path found for this scene. Please provide one.")

    print(f"\n--- Creating Project: {project_name} ---")
    print(f"  Topic: {topic}")
    print(f"  Scene: {selected_scene_config['Title']}")
    print(f"  Characters: {characters_in_scene}")

    try:
        project = project_scaffolding.Project(
            project_name=project_name,
            prompt=specific_prompt,
            topic=topic,
            character1=char1_name,
            character2=char2_name,
            video_path=video_path
        )

        project.create_script()

    except Exception as e:
        print(f"\nAn error occurred during project creation or execution: {e}")
        import traceback
        traceback.print_exc()

    try: 
        video = create_video.Video(project.project_name, project.script, project.video_path, scene_character_catalog)
        video.run_pipeline()
    
    except Exception as e: 
        print(f"Error: {e}")
