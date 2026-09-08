import os
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2"

# Presenton cloud API
PRESENTON_URL = "https://api.presenton.ai/api/v1/ppt/presentation/generate"
PRESENTON_API_KEY = "API key to be added  of api.presentation.ai taht user will create"

MAX_CHARS = 6000

def chunk_text(text, max_chars=MAX_CHARS):
    chunks = []

    while len(text) > max_chars:
        split_point = text.rfind(" ", 0, max_chars)
        if split_point == -1:
            split_point = max_chars

        chunks.append(text[:split_point].strip())
        text = text[split_point:].strip()

    if text:
        chunks.append(text)

    return chunks


def analyze(chunk):
    prompt = f"""
You are analyzing a university Machine Learning lecture transcript.

Your task is to extract ONLY the concepts that are ACTUALLY TAUGHT in this lecture chunk.

STRICT RULES:
- Include a topic ONLY if it is explained, defined, or discussed in detail
- EXCLUDE topics that are:
  • Mentioned as future syllabus ("we will study...", "next class...")
  • Just listed without explanation
  • Administrative or planning discussion

DEFINITION:
A topic is considered "taught" ONLY if:
- The instructor explains it
- OR gives an example
- OR elaborates on it

If a topic is only mentioned → IGNORE it

OUTPUT FORMAT:
- Topic 1
- Topic 2
- Topic 3

Do NOT explain.
Do NOT summarize.

You are analyzing a university Machine Learning lecture transcript.

Your task is to extract ONLY the concepts that are ACTUALLY TAUGHT.

STEP 1:
For each concept mentioned, classify it as:
- TAUGHT (explained in detail)
- NOT_TAUGHT (only mentioned, listed, or discussed as future topic)

STEP 2:
ONLY include concepts classified as TAUGHT.

STRICT RULES:
- If a concept is only mentioned without explanation → mark as NOT_TAUGHT
- If the instructor says "we will study", "next class", "later" → NOT_TAUGHT
- If no definition, example, or explanation is given → NOT_TAUGHT

DEFINITION OF TAUGHT:
A concept is TAUGHT only if:
- It is explained in at least 2 meaningful sentences
OR
- The instructor defines or elaborates on it

OUTPUT:
- Topic 1
- Topic 2

Do NOT include NOT_TAUGHT concepts.
Do NOT explain anything.
If no concepts are properly taught in this chunk, return: NONE

Transcript:
{chunk}
"""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_ctx": 8192
        }
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=300)
    response.raise_for_status()

    result = response.json().get("response", "").strip()
    if not result:
        raise RuntimeError("Empty response from Ollama during chunk analysis")

    return result


def ollama_summarize(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        transcript = f.read()

    chunks = chunk_text(transcript)
    print(f"Total chunks: {len(chunks)}")

    summaries = []
    for i, chunk in enumerate(chunks, start=1):
        print(f"Analyzing chunk {i}/{len(chunks)}")
        summary = analyze(chunk)
        summaries.append(summary)

    combined_summary = "\n".join(summaries)

    print("Refining topic list...")
    refine_prompt = f"""
The following is a list of academic topics extracted from different parts of a Machine Learning lecture.

Your task:
1. Remove duplicate topics
2. Merge highly similar topics
3. Keep only the major concepts
4. Arrange them in a logical teaching order

Rules:
- Keep only presentation-worthy main topics
- Remove repeated or overly narrow subtopics
- Use concise academic phrasing
- Prefer broader concepts over fragmented ones
- Output only the final cleaned topic list
- One topic per line

Topics:
{combined_summary}
"""

    payload = {
        "model": MODEL_NAME,
        "prompt": refine_prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_ctx": 8192
        }
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=300)
    response.raise_for_status()

    final_summary = response.json().get("response", "").strip()
    if not final_summary:
        raise RuntimeError("Empty refinement response from Ollama")

    os.makedirs("summarized_results", exist_ok=True)

    base_name = os.path.splitext(os.path.basename(file_path))[0]
    summary_file = os.path.join(
        "summarized_results",
        f"{base_name}_summary.txt"
    )

    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(final_summary)

    print(f"Summary saved at: {summary_file}")
    return final_summary


def build_slide_prompt(cleaned_topics):
    return f"""
Create professional, content-rich presentation slides from the following lecture topics.

GOAL:
Slides should feel informative, full, and useful for exam revision.

RULES:
- Do not use a fixed number of slides
- Create 1–2 slides per major topic
- Add a title slide at the beginning
- Add a summary slide at the end

CONTENT REQUIREMENTS:
Each content slide MUST include:
- A clear title
- 4 to 7 bullet points

Each slide MUST explain the topic using:
- Definition (what it is)
- Key idea or working (how it works)
- Important properties or components
- Example or application (if applicable)

IMPORTANT:
- If a topic cannot be explained with meaningful points → discard it
- Do NOT include vague bullets like "important concept" or "widely used"
- Every bullet must add real learning value

STRUCTURE:
- Break large topics into multiple slides if needed
- Maintain logical flow
- Avoid overcrowding or underfilling

STYLE:
- Academic, clear, and precise
- No repetition
- No filler content

OUTPUT FORMAT:
Slide 1: Title

Slide 2: Topic X
- Definition:
- Working:
- Key points:
- Example:

Slide 3: Topic X (continued)
...

Only structured slide content.
No paragraphs.

Topics:
{cleaned_topics}
""".strip()


def generate_presentation(slide_prompt):
    if not PRESENTON_API_KEY:
        raise RuntimeError("Missing PRESENTON_API_KEY. Set it in your environment first.")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {PRESENTON_API_KEY}"
    }
    MAX_SLIDE_PROMPT_CHARS = 12000

    if len(slide_prompt) > MAX_SLIDE_PROMPT_CHARS:
        slide_prompt = slide_prompt[:MAX_SLIDE_PROMPT_CHARS]
        
    payload = {
        "content": slide_prompt,
        "language": "English",
        "template": "general",
        "export_as": "pptx"
    }

    print("Slide prompt length:", len(slide_prompt))
    print("Sending payload to Presenton...")

    try:
        response = requests.post(
            PRESENTON_URL,
            json=payload,
            headers=headers,
            timeout=300
        )

        print("Status code:", response.status_code)
        print("Raw response:", response.text)

        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        raise RuntimeError(
            f"Presenton API request failed: {e}\n"
            f"Response body: {response.text if 'response' in locals() else 'No response'}"
        ) from e

    data = response.json()

    if not data:
        raise RuntimeError("Empty response from Presenton")

    return data
