import re
import os
import glob
import uuid
import json
import time
import yt_dlp
import webvtt
import nltk
import requests
from dotenv import load_dotenv

from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words
from rake_nltk import Rake


# ------------------ NLTK SETUP ------------------

def ensure_nltk():
    resources = ["punkt", "stopwords", "averaged_perceptron_tagger_eng"]
    for r in resources:
        try:
            if r == "averaged_perceptron_tagger_eng":
                 nltk.data.find("taggers/averaged_perceptron_tagger_eng")
            else:
                 nltk.data.find(f"tokenizers/{r}" if r == "punkt" else f"corpora/{r}")
        except LookupError:
            nltk.download(r)

ensure_nltk()


# ------------------ YOUTUBE UTIL ------------------

def extract_video_id(url: str) -> str | None:
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(regex, url)
    return match.group(1) if match else None


# ------------------ TRANSCRIPT FETCH ------------------

def fetch_transcript(video_id: str) -> str | None:
    url = f"https://www.youtube.com/watch?v={video_id}"
    temp_base = f"temp_{video_id}_{uuid.uuid4().hex[:8]}"

    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en", "en-US", "en-GB"],
        "outtmpl": temp_base,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "retries": 5
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info.get('subtitles') and not info.get('automatic_captions'):
                 raise RuntimeError("This video has no available captions (Manual or Auto).")
            ydl.download([url])

        files = glob.glob(f"{temp_base}*.vtt")
        if not files:
             raise RuntimeError("Captions found on YouTube but failed to download. Try a different video.")

        vtt = webvtt.read(files[0])
        lines = []

        for caption in vtt:
            text = caption.text.strip().replace("\n", " ")
            if not lines or lines[-1] != text:
                lines.append(text)

        return " ".join(lines)
    except Exception as e:
        if "no available captions" in str(e).lower():
            raise e
        raise RuntimeError(f"Could not fetch transcript: {str(e)}")
    finally:
        for f in glob.glob(f"{temp_base}*"):
            try:
                os.remove(f)
            except:
                pass


# ------------------ CLEANING ------------------

def clean_transcript(text: str) -> str:
    fillers = [
        r"\b(um|uh|like|you know|kind of|sort of|i mean|basically|actually|literally)\b",
        r"\b(okay|alright|right|anyway|so yeah)\b",
    ]
    text = text.lower()
    for f in fillers:
        text = re.sub(f, "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\.{2,}", ".", text)
    sentences = re.split(r"[.!?]+", text)
    cleaned = []
    for s in sentences:
        s = s.strip()
        if len(s.split()) < 4 or len(s) < 15:
            continue
        cleaned.append(s.capitalize())
    return ". ".join(cleaned) + "."

def chunk_text(text: str, max_words: int = 600) -> list[str]:
    """Splits text into manageable chunks for AI processing."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), max_words):
        chunks.append(" ".join(words[i : i + max_words]))
    return chunks


# ------------------ OFFLINE FALLBACK (ADVANCED) ------------------

def extract_noun_topics(text: str, num_topics=4):
    """Extracts high-quality nouns as topics using NLTK POS tagging."""
    try:
        tokens = nltk.word_tokenize(text)
        tagged = nltk.pos_tag(tokens)
        nouns = [word.capitalize() for word, pos in tagged if pos in ('NN', 'NNP', 'NNS') and len(word) > 3]
        fdist = nltk.FreqDist(nouns)
        common = [word for word, count in fdist.most_common(20) if not re.search(r'\d', word)]
        topics = []
        for word in common:
            if word not in topics:
                topics.append(word)
            if len(topics) >= num_topics:
                break
        return topics
    except:
        rake = Rake()
        rake.extract_keywords_from_text(text)
        return [p.title() for p in rake.get_ranked_phrases()[:num_topics]]

def summarize_text_statistical(text: str) -> dict:
    cleaned = clean_transcript(text)
    if len(cleaned) < 100:
        raise ValueError("Transcript too short")
    topic_names = extract_noun_topics(cleaned)
    topics = [{"name": name, "details": []} for name in topic_names]
    parser = PlaintextParser.from_string(cleaned, Tokenizer("english"))
    stemmer = Stemmer("english")
    summarizer = LexRankSummarizer(stemmer)
    summarizer.stop_words = get_stop_words("english")
    all_sentences = [str(s) for s in summarizer(parser.document, 10)]
    used_sentences = set()
    for topic in topics:
        keyword = topic["name"].lower()
        for s in all_sentences:
            if s in used_sentences: continue
            if keyword in s.lower():
                topic["details"].append(s)
                used_sentences.add(s)
                if len(topic["details"]) >= 2: break
    for topic in topics:
        if not topic["details"]:
            for s in all_sentences:
                if s not in used_sentences:
                    topic["details"].append(s)
                    used_sentences.add(s)
                    break
    return {"title": "Video Analysis (Offline Mode)", "topics": topics}


# ------------------ OLLAMA (LOCAL OFFLINE) ------------------

def summarize_text_with_ollama(text: str, format: str = "mindmap", model: str = "llama3.2:1b", is_recursive: bool = False) -> dict | str:
    try:
        url = "http://localhost:11434/api/generate"
        
        # 1. Pre-Test Ping (Only on top-level call)
        if not is_recursive:
            try:
                print(f"Performing pre-test ping to Ollama ({model})...")
                requests.post(url, json={"model": model, "prompt": "hi", "stream": False}, timeout=300)
            except Exception as e:
                print(f"Ollama pre-test failed: {e}")
                raise RuntimeError(f"Ollama not responsive: {e}")

        # 2. Chunking Logic
        word_count = len(text.split())
        if word_count > 800:
            print(f"Long transcript detected ({word_count} words). Processing in chunks of 600 words...")
            chunks = chunk_text(text, max_words=600)
            chunk_results = []
            for i, chunk in enumerate(chunks):
                print(f"Requesting Ollama summary for chunk {i+1}/{len(chunks)}...")
                for attempt in range(3):
                    try:
                        # Recursive call with is_recursive=True to skip redundant pings
                        chunk_results.append(summarize_text_with_ollama(chunk, format="mindmap", model=model, is_recursive=True))
                        break
                    except Exception as e:
                        if attempt == 2: raise e
                        print(f"Chunk {i+1} failed, retrying in 5s...")
                        time.sleep(5)
            
            print("Synthesizing final overview from chunk summaries...")
            synthesis_prompt = f"Combine these summaries into one cohesive {format}. Return ONLY the final output (JSON for mindmaps, indentation-based for flowcharts)."
            payload = {
                "model": model,
                "prompt": f"Summaries: {json.dumps(chunk_results)}\n\n{synthesis_prompt}",
                "stream": False,
                "format": "json" if format != "flowchart" else ""
            }
            res = requests.post(url, json=payload, timeout=180)
            res.raise_for_status()
            final_raw = res.json().get('response', '').strip()
            if format == "flowchart": return final_raw
            return json.loads(final_raw)

        # Standard Processing
        if format == "qa":
            sys_prompt = "Extract important questions and answers. Return ONLY JSON: [{\"question\":\"?\", \"answer\":\"\"}]"
        elif format == "flowchart":
            sys_prompt = "Transform into 'flowchart-fun' indentation syntax. Rules: Indent (spaces) for edges, Labeled Edges 'Lab: Target', Dec questions?, Cyc (ref). First line Title."
        else:
            sys_prompt = "Return ONLY valid JSON: {\"title\": \"\", \"topics\": [{\"name\": \"\", \"details\": [\"\"]}]}"

        payload = {
            "model": model,
            "prompt": f"{sys_prompt}\n\nTranscript: {text}",
            "stream": False,
            "format": "json" if format != "flowchart" else ""
        }
        res = requests.post(url, json=payload, timeout=90)
        res.raise_for_status()
        raw = res.json().get('response', '').strip()
        if format == "flowchart": return raw
        return json.loads(raw)
    except Exception as e:
        print(f"Ollama failed definitively: {e}")
        raise e


# ------------------ GEMINI ------------------

def summarize_text_with_gemini(text: str, format: str = "mindmap") -> dict | str:
    try:
        import google.generativeai as genai
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key: raise RuntimeError("No Gemini key")
        genai.configure(api_key=api_key)

        if format == "qa":
            prompt = "Extract Q&A from transcript."
        elif format == "flowchart":
            prompt = "Transform into 'flowchart-fun' indentation syntax. Use indentation for edges, Labeled: Target, decisions?, (ref). First line Title."
        else: # Default: mindmap
            prompt = "Extract a comprehensive mindmap outline. Return ONLY JSON: {\"title\": \"\", \"topics\": [{\"name\": \"\", \"details\": [\"\"]}]}"

        model = genai.GenerativeModel("gemini-2.5-flash")
        print(f"Sending {len(text.split())} words to Gemini Flash...")
        response = model.generate_content(f"{prompt}\n\nTranscript: {text}")
        print("Gemini response received.")
        
        raw = response.text.replace("```json", "").replace("```", "").strip()
        if format == "flowchart": return raw
        return json.loads(raw)
    except Exception as e:
        print(f"Gemini failed: {e}")
        raise e


# ------------------ MAIN ENTRY ------------------

def get_video_summary(url: str, format: str = "mindmap") -> dict | str:
    video_id = extract_video_id(url)
    if not video_id: raise ValueError("Invalid YouTube URL")
    try:
        transcript = fetch_transcript(video_id)
    except Exception as e:
        raise RuntimeError(str(e))
    if not transcript: raise RuntimeError("Empty transcript")

    # Fallback Chain: Gemini -> Ollama -> Offline
    try:
        print("Attempting Gemini summarization...")
        return summarize_text_with_gemini(transcript, format=format)
    except Exception as e:
        print(f"Gemini path failed: {e}")
        try:
            print("Attempting Ollama summarization...")
            return summarize_text_with_ollama(transcript, format=format)
        except Exception as e2:
            print(f"Ollama path also failed: {e2}")
            print("Ultimate fallback to offline statistical mode...")
            return summarize_text_statistical(transcript)

if __name__ == "__main__":
    url = "https://www.youtube.com/watch?v=VIDEO_ID"
    # summary = get_video_summary(url)
