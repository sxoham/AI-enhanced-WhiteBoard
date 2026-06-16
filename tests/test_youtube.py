import yt_dlp
import webvtt
import os
import glob

# url = "https://www.youtube.com/watch?v=rfscVS0vtbw"
url = "https://www.youtube.com/watch?v=jNQXAC9IVRw" # Me at the zoo

# Clean up previous runs
for f in glob.glob("test_sub*"):
    try: os.remove(f)
    except: pass

ydl_opts = {
    'skip_download': True,
    'writesubtitles': True,
    'writeautomaticsub': True,
    'subtitleslangs': ['en'],
    'outtmpl': 'test_sub',
    'quiet': True,
}

print(f"Downloading subs for {url} using yt-dlp...")
try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    # It creates test_sub.en.vtt or similar
    files = glob.glob("test_sub*.vtt")
    if files:
        file = files[0]
        print(f"Parsing {file}...")
        vtt = webvtt.read(file)
        # Parse text avoiding duplicates (webvtt often has duplicates for timing)
        lines = []
        for caption in vtt:
            text = caption.text.strip().replace('\n', ' ')
            if not lines or lines[-1] != text:
                lines.append(text)
        
        full_text = " ".join(lines)
        print(f"Extracted {len(full_text)} chars.")
        print("Sample:", full_text[:100])
        
        # Cleanup
        try: os.remove(file)
        except: pass
    else:
        print("No VTT file found.")

except Exception as e:
    print(f"Error: {e}")



