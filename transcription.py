import whisper
import os


def get_t(video):
    model = whisper.load_model("base")
    print("Transcribing lecture...")

    lecture = model.transcribe(video)

    os.makedirs("review", exist_ok=True)
    lecture_path = "review/lecture.txt"

    with open(lecture_path, "w", encoding="utf-8") as f:
        f.write(lecture["text"].strip())

    return lecture_path