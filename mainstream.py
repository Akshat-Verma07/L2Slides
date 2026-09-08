import sys
from transcription import get_t
from info import ollama_summarize 
from info import build_slide_prompt
from info import generate_presentation

def main():
    if len(sys.argv) < 2:
        print("Usage: python mainstream.py <video>")
        return

    video = sys.argv[1]
    
#trancription
    print("Transcribing...")
    text_file = get_t(video)

#info
    print("Summarizing into major topics...")
    topics = ollama_summarize(text_file)

    print("Building slide prompt...")
    slide_prompt = build_slide_prompt(topics)

    print("Generating presentation...")
    result = generate_presentation(slide_prompt)

    print("\nPresentation generated successfully.")
    print("Presentation ID:", result.get("presentation_id"))
    print("Download link:", result.get("path"))
    print("Edit link:", result.get("edit_path"))


if __name__ == "__main__":
    main()