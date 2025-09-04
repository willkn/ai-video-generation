import os
import glob
import json
import subprocess
import math
import moviepy.editor as mp
from pydub import AudioSegment
from fish_audio_sdk import Session, TTSRequest

# ==============================================================================
# 1. DIAGNOSTICS & CONFIGURATION
# ==============================================================================

def check_and_configure_imagemagick():
    """
    Checks for the ImageMagick binary and configures MoviePy to use it.
    This is critical for the TextClip functionality to work reliably.
    """
    print("--- Starting ImageMagick Diagnostic ---")
    imagemagick_binary = None
    try:
        # First, try 'magick' for newer ImageMagick versions
        imagemagick_binary = subprocess.check_output(['which', 'magick'], text=True).strip()
        print(f"ImageMagick 'magick' command found in PATH: {imagemagick_binary}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            # If 'magick' not found, try 'convert' for older versions
            imagemagick_binary = subprocess.check_output(['which', 'convert'], text=True).strip()
            print(f"ImageMagick 'convert' command found in PATH: {imagemagick_binary}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback for common Homebrew paths on macOS
            if os.path.exists("/opt/homebrew/bin/magick"):
                imagemagick_binary = "/opt/homebrew/bin/magick"
                print(f"Found ImageMagick in common Homebrew path: {imagemagick_binary}")

    if imagemagick_binary and os.path.exists(imagemagick_binary):
        os.environ["IMAGEMAGICK_BINARY"] = imagemagick_binary
        print(f"MoviePy's IMAGEMAGICK_BINARY is now set to: {os.environ['IMAGEMAGICK_BINARY']}")
    else:
        print("\nCRITICAL WARNING: ImageMagick binary not found.")
        print("TextClip generation will likely fail.")
        print("Please install ImageMagick and ensure it's in your system's PATH.")
    print("--- ImageMagick Check Complete ---\n")

# ==============================================================================
# 2. HELPER & UTILITY FUNCTIONS
# ==============================================================================

def save_json_to_file(data_to_save, folder_path, filename):
    """Saves a Python dictionary or list to a JSON file in a specific folder."""
    full_path = os.path.join(folder_path, filename)
    try:
        os.makedirs(folder_path, exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as json_file:
            json.dump(data_to_save, json_file, indent=4, ensure_ascii=False)
        print(f"Successfully saved JSON to: {os.path.abspath(full_path)}")
        return True
    except Exception as e:
        print(f"Error saving JSON file: {e}")
        return False

# ==============================================================================
# 3. AUDIO PIPELINE FUNCTIONS
# ==============================================================================

def generate_audio(speaker, dialogue_text, model_reference_id, output_path):
    """Generates a single audio file for a line of dialogue using the TTS SDK."""
    try:
        session = Session('6e3eccd5009e494fa7460edfc099d4b1') 
        with open(output_path, "wb") as f:
            for chunk in session.tts(TTSRequest(reference_id=model_reference_id, text=dialogue_text)):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"  - ERROR generating audio for '{speaker}': {e}")
        return False

def collate_audio_files(input_folder, output_filename="combined_dialogue.mp3", break_duration_ms=500):
    """Collates all audio files in a directory into a single file, saved in the SAME directory."""
    final_output_path = os.path.join(input_folder, output_filename)
    search_paths = [os.path.join(input_folder, '*.mp3'), os.path.join(input_folder, '*.wav')]
    audio_files = sorted([f for path in search_paths for f in glob.glob(path)])
    if not audio_files: return False, 0
    break_segment = AudioSegment.silent(duration=break_duration_ms)
    try:
        combined_audio = AudioSegment.from_file(audio_files[0])
        for file_path in audio_files[1:]:
            combined_audio += break_segment
            combined_audio += AudioSegment.from_file(file_path)
        combined_audio.export(final_output_path, format=final_output_path.split('.')[-1])
        print(f"Successfully collated audio to: {os.path.abspath(final_output_path)}")
        return True, len(combined_audio)
    except Exception as e:
        print(f"An error occurred during collation: {e}")
        return False, 0

def create_script_with_timings(dialogue_turns, audio_folder, break_duration_ms=500):
    """Calculates the duration and timestamps for each dialogue turn."""
    timed_script = [turn.copy() for turn in dialogue_turns]
    current_timestamp_ms = 0
    for i, turn in enumerate(timed_script):
        speaker = turn.get('speaker', 'Unknown').strip()
        audio_filename = os.path.join(audio_folder, f"turn_{i+1:03d}_{speaker}.mp3")
        duration_ms = 0
        if os.path.exists(audio_filename):
            try:
                duration_ms = len(AudioSegment.from_file(audio_filename))
            except Exception as e:
                print(f"Warning: Could not read duration for {audio_filename}. {e}")
        turn.update({'duration_ms': duration_ms, 'start_time_ms': current_timestamp_ms, 'end_time_ms': current_timestamp_ms + duration_ms})
        current_timestamp_ms += duration_ms + break_duration_ms
    return timed_script

# ==============================================================================
# 4. VIDEO PIPELINE FUNCTIONS
# ==============================================================================

def prepare_text_events_from_timed_script(timed_script, text_style):
    """Loads a timed script and converts it into the text_events format."""
    text_events = []
    for turn in timed_script:
        text = f"{turn.get('dialogue', '')}"    
        event = {
            'text': text,
            'start_time': turn.get('start_time_ms', 0) / 1000.0,
            'end_time': turn.get('end_time_ms', 0) / 1000.0
        }
        event.update(text_style)
        text_events.append(event)
    return text_events


def create_text_sequence(video_resolution, text_events, words_per_chunk=6):
    """
    Creates a list of moviepy.editor.TextClip objects from a sequence of text events.
    Includes a targeted fix for text alignment and position.
    """
    final_text_clips = []
    video_w, video_h = video_resolution

    for event in text_events:
        full_text = event.get('text', '')
        start_time = event.get('start_time', 0)
        total_duration = event.get('end_time', start_time) - start_time
        
        if total_duration <= 0:
            continue

        words = full_text.split()

        def generate_clip(text_chunk, start, duration):
            # Get the desired final position from the event
            position_keyword = event.get('position', ('center', 0.5))
            
            # Get offset values from the event, defaulting to 0 if not present
            offset_x = event.get('offset_x', 0)
            offset_y = event.get('offset_y', 0)

            # --- TEXT ALIGNMENT LOGIC ---
            text_internal_align = 'center' # Default for ImageMagick's 'caption'
            
            horizontal_pos_component = 'center'
            if isinstance(position_keyword, tuple):
                horizontal_pos_component = position_keyword[0] 
            elif isinstance(position_keyword, str):
                horizontal_pos_component = position_keyword

            if horizontal_pos_component == 'center':
                text_internal_align = 'center'
            elif horizontal_pos_component == 'left':
                text_internal_align = 'West' 
            elif horizontal_pos_component == 'right':
                text_internal_align = 'East' 

            kwargs = {
                'txt': text_chunk,
                'fontsize': event.get('fontsize', int(video_h*0.05)), # Adjust default font size based on video height
                'color': event.get('color', 'white'),
                'font': event.get('font'),
                'stroke_color': event.get('stroke_color'),
                'stroke_width': event.get('stroke_width'),
                'bg_color': event.get('bg_color'),
                'method': 'caption',
                'size': (video_w * 0.9, 900), 
                'align': text_internal_align
            }
            kwargs_filtered = {k: v for k, v in kwargs.items() if v is not None}

            txt_clip = mp.TextClip(**kwargs_filtered)
            
            final_clip_position = list(position_keyword) # Make it mutable
            
            if isinstance(final_clip_position, str):
                 final_clip_position = (final_clip_position, 'center') # Default vertical if only string provided
            
            txt_clip = txt_clip.set_start(start).set_position(final_clip_position).set_duration(duration)
            
            return txt_clip

        if len(words) <= words_per_chunk:
            clip = generate_clip(full_text, start_time, total_duration)
            final_text_clips.append(clip)
        else:
            num_chunks = math.ceil(len(words) / words_per_chunk)
            duration_per_chunk = total_duration / num_chunks
            
            for i in range(num_chunks):
                chunk_text = " ".join(words[i*words_per_chunk : (i+1)*words_per_chunk])
                chunk_start_time = start_time + (i * duration_per_chunk)
                clip = generate_clip(chunk_text, chunk_start_time, duration_per_chunk)
                final_text_clips.append(clip)

    return final_text_clips


def create_character_clips(video_resolution, character_events, char_height_percentage=0.55, base_y_percentage_from_bottom=0.00):
    """Creates a list of moviepy.editor.ImageClip objects for character appearances."""
    character_clips = []
    video_w, video_h = video_resolution

    for event in character_events:
        char_path, start_time, end_time = event.get('path'), event.get('start_time', 0), event.get('end_time', float('inf'))
        
        position = event.get('position', 'right')
        offset_x = event.get('offset_x', 0)
        offset_y = event.get('offset_y', 0) 

        if not char_path or not os.path.exists(char_path): 
            print(f"Warning: Character image not found at {char_path}. Skipping.")
            continue

        char_clip = mp.ImageClip(char_path).resize(height=video_h * char_height_percentage)
        
        base_y_pixel_from_bottom_calc = video_h - char_clip.h - (video_h * base_y_percentage_from_bottom)
        
        base_x_pixel = 0
        base_y_pixel_from_top = base_y_pixel_from_bottom_calc # Default Y is calculated from bottom

        if isinstance(position, tuple):
            h_pos_component = position[0]
            v_pos_component = position[1] # This is a relative value (0.0 to 1.0) from the top

            # Calculate X position based on horizontal component
            if h_pos_component == 'left': base_x_pixel = video_w * 0.05
            elif h_pos_component == 'right': base_x_pixel = video_w - char_clip.w - (video_w * 0.05)
            elif h_pos_component == 'center': base_x_pixel = (video_w - char_clip.w) / 2
            else: base_x_pixel = float(h_pos_component) # Assume it's a pixel value if not recognized

            # Calculate Y position based on the tuple's vertical component (relative to top)
            base_y_pixel_from_top = v_pos_component * video_h

        elif isinstance(position, str):
            if position == 'left': base_x_pixel = video_w * 0.05
            elif position == 'right': base_x_pixel = video_w - char_clip.w - (video_w * 0.05)
            elif position == 'center': base_x_pixel = (video_w - char_clip.w) / 2
            else: # Unrecognized string, default to center-left for safety
                print(f"Warning: Unrecognized string position '{position}' for character. Defaulting.")
                base_x_pixel = video_w * 0.05 

        final_x_pixel = base_x_pixel + offset_x
        final_y_pixel = base_y_pixel_from_top + offset_y

        # Ensure final positions are within reasonable bounds (optional, but helpful)
        final_x_pixel = max(0, min(final_x_pixel, video_w - char_clip.w))
        final_y_pixel = max(0, min(final_y_pixel, video_h - char_clip.h))
        
        # Set the clip's position using the final calculated pixel coordinates
        final_pos_tuple = (final_x_pixel, final_y_pixel)
        # print(f"DEBUG: Setting position for {char_path} to: {final_pos_tuple}") # Uncomment for debugging
        
        char_clip = char_clip.set_pos(final_pos_tuple).set_start(start_time).set_end(end_time)
        character_clips.append(char_clip)
        
    return character_clips

# ==============================================================================
# 5. MAIN PROJECT CLASS & WORKFLOW
# ==============================================================================

class Video:
    def __init__(self, project_name, dialogue_script, base_video_path, character_assets, text_style={'position': ('center', 0.7), 'color': '#FFFF00', 'font': 'Arial-Bold', 'fontsize': 100}):
        self.project_name = project_name
        self.dialogue_script = dialogue_script
        self.base_video_path = base_video_path
        self.character_assets = character_assets
        self.text_style = text_style
        self.output_folder = os.path.join("projects", self.project_name)
        self.audio_folder = os.path.join(self.output_folder, "audio")
        self.timed_script = None
        
        self.video_resolution = (1080, 1920)

    def run_pipeline(self):
        """Runs the full, robust pipeline: audio -> timings -> video."""
        print("="*60)
        print(f"STARTING PROJECT: {self.project_name}")
        print("="*60)

        # --- PHASE 1 & 2: AUDIO & TIMING (Unchanged) ---
        print("\n[PHASE 1 & 2] Generating Audio & Timings...")
        os.makedirs(self.audio_folder, exist_ok=True)
        for i, turn in enumerate(self.dialogue_script):
            speaker = turn.get('speaker', 'Unknown').strip()
            voice_id = self.character_assets.get(speaker, {}).get('voice_id')
            if not voice_id: continue
            output_filename = os.path.join(self.audio_folder, f"turn_{i+1:03d}_{speaker}.mp3")
            generate_audio(speaker, turn.get('dialogue', ''), voice_id, output_filename)
        
        success, audio_duration_ms = collate_audio_files(self.audio_folder)
        if not success:
            print("Audio collation failed. Aborting.")
            return

        self.timed_script = create_script_with_timings(self.dialogue_script, self.audio_folder)
        save_json_to_file(self.timed_script, self.audio_folder, "timed_script.json")

        # --- PHASE 3: VIDEO COMPOSITION (Rewritten for Robustness) ---
        print("\n[PHASE 3/3] Creating Final Video...")
        collated_audio_path = os.path.join(self.audio_folder, "combined_dialogue.mp3")
        if not os.path.exists(self.base_video_path) or not os.path.exists(collated_audio_path):
            print("CRITICAL ERROR: Base video or collated audio file not found. Aborting.")
            return

        # 1. Load audio and video clips
        final_audio_clip = mp.AudioFileClip(collated_audio_path)
        base_video_clip = mp.VideoFileClip(self.base_video_path)
        final_duration = final_audio_clip.duration

        # 2. Ensure base video has the correct duration
        if base_video_clip.duration < final_duration:
            base_video_clip = base_video_clip.loop(duration=final_duration)
        else:
            base_video_clip = base_video_clip.subclip(0, final_duration)
        
        # Resize to tiktok resolution
        base_video_clip = base_video_clip.resize(height=self.video_resolution[1])
        
        if base_video_clip.w > self.video_resolution[0]:
            # Calculate coordinates for cropping from the sides
            x1 = (base_video_clip.w - self.video_resolution[0]) / 2
            y1 = 0 # Start from the top
            x2 = x1 + self.video_resolution[0] # End at the cropped width
            y2 = self.video_resolution[1] # Go to the bottom
            base_video_clip = base_video_clip.crop(x1=x1, y1=y1, x2=x2, y2=y2)
        elif base_video_clip.w < self.video_resolution[0]:
            # If the width is still too small after height resize, center it and add black bars
            base_video_clip = mp.vfx.pad(base_video_clip, width=self.video_resolution[0], color=(0,0,0)) # Black bars

        # 3. Prepare text and character events
        text_events = prepare_text_events_from_timed_script(self.timed_script, self.text_style)
        character_events = []
        for turn in self.timed_script:
            speaker = turn.get('speaker')
            char_info = self.character_assets.get(speaker)
            if char_info and 'image_path' in char_info and os.path.exists(char_info['image_path']):
                character_events.append({
                    'path': char_info['image_path'],
                    'start_time': turn['start_time_ms'] / 1000.0,
                    'end_time': turn['end_time_ms'] / 1000.0,
                    'position': char_info.get('position', 'right')
                })
        
        # 4. Create all the clip objects
        text_clips = create_text_sequence(self.video_resolution, text_events)
        character_image_clips = create_character_clips(self.video_resolution, character_events)
        
        # 5. Compose the final video
        final_clips_list = [base_video_clip]
        final_clips_list.extend(character_image_clips)
        final_clips_list.extend(text_clips)
        
        # Create the composite clip, explicitly setting the size to TikTok resolution
        final_video = mp.CompositeVideoClip(final_clips_list, size=self.video_resolution)
        
        # 6. Set the final duration and audio
        final_video = final_video.set_duration(final_duration).set_audio(final_audio_clip)
        
        # 7. Write the video file
        final_video_path = os.path.join(self.output_folder, f"{self.project_name}_final_tiktok.mp4")
        print(f"\nWriting {final_duration:.2f} seconds of video to: {os.path.abspath(final_video_path)}")

        final_video.write_videofile(
            final_video_path,
            codec="libx264",
            audio_codec="libmp3lame",
            fps=30,
            logger='bar'
        )
        
        print(f"\n--- WORKFLOW COMPLETE ---")