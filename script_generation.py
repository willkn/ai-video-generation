import json
from openai import OpenAI

def generate_explanation(topic: str, system_prompt) -> str:
    """
    Generates a one-minute intuitive explanation of a concept by Rick and Morty,
    formatted as a JSON array suitable for TTS.

    Args:
        topic (str): The concept for Rick and Morty to explain.

    Returns:
        str: A JSON string containing the dialogue turns.
             Each turn is an object with "speaker" and "dialogue" keys.
    """

    client = OpenAI()

    user_prompt = f"The concept to be explained is: {topic}."

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        response_content = response.choices[0].message.content
        parsed_json = json.loads(response_content)

        if "dialogue_turns" in parsed_json and isinstance(parsed_json["dialogue_turns"], list):
            return json.dumps(parsed_json["dialogue_turns"], indent=2)
        else:
            print("Warning: GPT-4o did not return the expected 'dialogue_turns' key or it was not a list.")
            return response_content # Return raw content for debugging/inspection

    except Exception as e:
        print(f"An error occurred: {e}")
        return json.dumps({"error": str(e)})
