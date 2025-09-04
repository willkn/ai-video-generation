import os
import glob
import json
from pydub import AudioSegment
from fish_audio_sdk import Session, TTSRequest
from dotenv import load_dotenv

load_dotenv()
FISH_AI_API_KEY = os.getenv("FISH_AUDIO_API_KEY")

# --- Helper Functions ---
def save_json_to_file(data_to_save, folder_path, filename):
    """Saves a Python dictionary or list to a JSON file in a specific folder."""
    full_path = os.path.join(folder_path, filename)
    try:
        os.makedirs(folder_path, exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as json_file:
            json.dump(data_to_save, json_file, indent=4, ensure_ascii=False)
        print(f"\n--- Script Saved ---")
        print(f"Successfully saved timed script to: {os.path.abspath(full_path)}")
        return True
    except Exception as e:
        print(f"Error saving JSON file: {e}")
        return False

def generate_audio(speaker, dialogue_text, model_reference_id, output_path):
    """Generates a single audio file for a line of dialogue using the TTS SDK."""
    try:
        session = Session(FISH_AI_API_KEY)
        print(f"  - Generating audio for '{speaker}' with model ID: '{model_reference_id}'...")
        print(f"  - Saving to: {output_path}")
        with open(output_path, "wb") as f:
            for chunk in session.tts(TTSRequest(reference_id=model_reference_id, text=dialogue_text, prosody=1.75, backend='speech-1.6"')):
                f.write(chunk)
        print(f"  - Successfully generated audio file.")
        return True
    except Exception as e:
        print(f"  - ERROR: Failed to generate audio. Reason: {e}")
        return False

def collate_audio_files(input_folder, output_filename="combined_dialogue.mp3", break_duration_ms=500):
    """Collates all audio files in a directory into a single file, saved in the SAME directory."""
    final_output_path = os.path.join(input_folder, output_filename)
    print(f"\n--- Starting Audio Collation ---")
    search_paths = [os.path.join(input_folder, '*.mp3'), os.path.join(input_folder, '*.wav')]
    audio_files = sorted([f for path in search_paths for f in glob.glob(path)])

    if not audio_files:
        print("Error: No audio files found to collate.")
        return False
        
    print(f"Found {len(audio_files)} files to collate.")
    break_segment = AudioSegment.silent(duration=break_duration_ms)
    
    try:
        combined_audio = AudioSegment.from_file(audio_files[0])
        for file_path in audio_files[1:]:
            combined_audio += break_segment
            combined_audio += AudioSegment.from_file(file_path)

        output_format = final_output_path.split('.')[-1]
        print(f"\nExporting combined audio to: {os.path.abspath(final_output_path)}")
        combined_audio.export(final_output_path, format=output_format)
        print("--- Collation Successful ---")
        return True
    except Exception as e:
        print(f"An error occurred during collation: {e}")
        return False

def create_script_with_timings(dialogue_turns, audio_folder, break_duration_ms=500):
    """Calculates the duration and timestamps for each dialogue turn."""
    print("\n--- Calculating Timings for Script ---")
    timed_script = [turn.copy() for turn in dialogue_turns]
    current_timestamp_ms = 0
    
    for i, turn in enumerate(timed_script):
        speaker = turn.get('speaker', 'Unknown Speaker').strip()
        audio_filename = os.path.join(audio_folder, f"turn_{i+1:03d}_{speaker}.mp3")
        
        if not os.path.exists(audio_filename):
            print(f"Warning: Audio file not found for Turn {i+1}. Setting duration to 0.")
            duration_ms = 0
        else:
            try:
                duration_ms = len(AudioSegment.from_file(audio_filename))
            except Exception as e:
                print(f"Error processing {audio_filename}: {e}. Setting duration to 0.")
                duration_ms = 0

        turn['duration_ms'] = duration_ms
        turn['start_time_ms'] = current_timestamp_ms
        turn['end_time_ms'] = current_timestamp_ms + duration_ms
        print(f"  - Turn {i+1} ({speaker}): Duration = {duration_ms}ms, Starts at {current_timestamp_ms}ms")
        current_timestamp_ms += duration_ms + break_duration_ms
    
    return timed_script

# --- Main Workflow ---
def generate_audio_for_script(dialogue_turns, output_folder, *args):
    """
    Processes a script, generates audio, collates it, creates a timed script,
    and saves all assets to the output folder.
    """
    characters = {}
    default_voice_id = "88d465f1189846ed98a0240298cf3e02"
    if args and len(args) % 2 == 0:
        for i in range(0, len(args), 2):
            characters[args[i].strip()] = args[i+1]
        print("--- Character Map Loaded ---\n", characters)
    else:
        print(f"--- No valid character map. Using default: {default_voice_id} ---")

    print("\n--- Starting Audio Generation ---")
    os.makedirs(output_folder, exist_ok=True)
    
    # Step 1: Generate individual audio files
    for i, turn in enumerate(dialogue_turns):
        speaker = turn.get('speaker', 'Unknown Speaker').strip()
        dialogue = turn.get('dialogue', 'No dialogue text.')
        voice_id_to_use = characters.get(speaker, default_voice_id)
        output_filename = os.path.join(output_folder, f"turn_{i+1:03d}_{speaker}.mp3")
        print(f"\nProcessing Turn {i+1}:")
        generate_audio(speaker, dialogue, voice_id_to_use, output_filename)
        
    # Step 2: Collate the generated audio files
    break_time = 500 # Define break time in one place
    collate_audio_files(output_folder, break_duration_ms=break_time)
    
    # Step 3: Create the final script with timing data
    timed_script = create_script_with_timings(dialogue_turns, output_folder, break_duration_ms=break_time)
    
    # Step 4: Save the timed script to the same directory
    if timed_script:
        save_json_to_file(timed_script, output_folder, "timed_script.json")
    
    return timed_script
