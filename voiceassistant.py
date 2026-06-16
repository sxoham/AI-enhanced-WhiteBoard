import datetime
import speech_recognition as sr
import pyttsx3
import threading
import tkinter as tk
import queue
import time

from speech_stt import load_stt_config, preload_whisper_model, recognize_text, stt_status_message

def init_voice_system(app):
    """Initializes voice recognition objects on the app instance."""
    app.recognizer = sr.Recognizer()
    app.stt_config = load_stt_config()
    print(f"Speech-to-text: {stt_status_message(app.stt_config)}")
    try:
        app.microphone = sr.Microphone()
    except AttributeError:
        print("Warning: PyAudio not found. Voice commands will be disabled.")
        app.microphone = None
        
    app.voice_assistant_on = False
    app.is_listening = False # For transcription mode
    
    # NEW: Speech Queue to prevent 'run loop already started' errors
    app.speech_queue = queue.Queue()
    threading.Thread(target=speech_worker, args=(app,), daemon=True).start()

    if app.stt_config.preload and app.stt_config.is_offline:
        threading.Thread(
            target=preload_whisper_model, args=(app.stt_config,), daemon=True
        ).start()

def speech_worker(app):
    """Background worker to handle speech queue safely."""
    # Initialize COM object in the correct thread
    try:
        app.engine = pyttsx3.init()
    except Exception as e:
        print(f"Failed to initialize pyttsx3: {e}")
        app.engine = None
        
    while True:
        try:
            text = app.speech_queue.get(timeout=1)
            if text and app.engine:
                app.engine.say(text)
                app.engine.runAndWait()
            app.speech_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Speech Worker Error: {e}")
            # Try to re-init engine if it crashes
            try:
                app.engine = pyttsx3.init()
            except: pass
            time.sleep(1)

def start_transcription(app):
    """Starts the speech-to-text transcription mode (Voice Notes)."""
    if not app.is_listening:
        app.is_listening = True
        print("Starting speech recognition (transcription)...")
        threading.Thread(target=transcribe_loop, args=(app,), daemon=True).start()

def transcribe_loop(app):
    """Loop for transcribing speech to text on the canvas."""
    if not app.microphone:
        print("Microphone not available (PyAudio missing).")
        app.is_listening = False
        return
        
    with app.microphone as source:
        print("Adjusting for ambient noise...")
        app.recognizer.adjust_for_ambient_noise(source, duration=1)
        app.recognizer.dynamic_energy_threshold = True

        while app.is_listening:
            try:
                print("Listening for speech (dictation)...")
                audio_data = app.recognizer.listen(source, timeout=1, phrase_time_limit=3)
                print("Recognizing speech...")
                text = recognize_text(app.recognizer, audio_data, app.stt_config)
                text = text.capitalize()

                if "quit" in text.lower():
                    print("Quit command detected. Stopping transcription...")
                    app.is_listening = False
                    break

                # Print the recognized text on the canvas
                # We need to schedule this on the main thread ideally, but Tkinter is somewhat thread-safe for simple creates sometimes?
                # Safer to use app.root.after or similar, but original code did direct create.
                # We will stick to original pattern for now but wrap in try.
                
                # Check for y position attribute
                if not hasattr(app, 'current_y'): app.current_y = 20
                
                app.c.create_text(10, app.current_y, anchor=tk.NW, text=text, fill="black",
                                    font=("Arial", 12))
                app.current_y += 20  # Move down for next line of text
                # app.root.update() # Not strictly safe in thread but was in original

                print(f"Recognized text: {text}")

            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                if app.stt_config.is_offline:
                    print(f"Speech recognition error: {e}")
                else:
                    print(f"Request error (check network): {e}")
                continue
            except Exception as e:
                print(f"Unexpected error in transcription: {e}")
                app.is_listening = False
                break

    print("Transcription stopped.")
    app.is_listening = False

def toggle_voice_assistant(app):
    if not hasattr(app, 'microphone') or not app.microphone:
        print("Microphone not available (PyAudio missing). Cannot start voice assistant.")
        speak(app, "Voice assistant is unavailable due to missing audio drivers.")
        app.voice_assistant_on = False
        return
        
    app.voice_assistant_on = not app.voice_assistant_on
    if app.voice_assistant_on:
        mode_str = "offline" if getattr(app.stt_config, 'is_offline', False) else "online"
        speak(app, f"Voice Assistant is now ON in {mode_str} mode........please tell me how may I help you")
        if not getattr(app, 'voice_thread_running', False):
            threading.Thread(target=listen_for_commands, args=(app,), daemon=True).start()
    else:
        speak(app, "Voice Assistant is now OFF")
    
    # Update UI button icon if available
    if hasattr(app, 'update_voice_btn_icon'):
        app.update_voice_btn_icon()

def speak(app, text):
    """Adds text to the speech queue (non-blocking)."""
    if hasattr(app, 'speech_queue'):
        app.speech_queue.put(text)
    else:
        # Fallback if queue not initialized
        try:
            app.engine.say(text)
            app.engine.runAndWait()
        except:
            pass
def listen_for_commands(app):
    if not app.microphone:
        return
        
    app.voice_thread_running = True
    try:
        # Adjust for noise ONCE at the start
        try:
            with app.microphone as source:
                print("Adjusting for ambient noise... Please wait.")
                app.recognizer.adjust_for_ambient_noise(source, duration=1)
                app.recognizer.dynamic_energy_threshold = True
                app.recognizer.pause_threshold = 0.8  # Wait 0.8s of silence before considering command done
        except AssertionError:
            print("Microphone already in use.")
            return
            
        while app.voice_assistant_on:
            try:
                with app.microphone as source:
                    print("Listening for commands...")
                    try:
                        # Add timeout so it doesn't hang indefinitely if no speech
                        audio = app.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                    except sr.WaitTimeoutError:
                        continue # Listen again
            except AssertionError:
                print("Microphone context blocked, retrying...")
                import time
                time.sleep(1)
                continue
                
            try:
                command = recognize_text(app.recognizer, audio, app.stt_config).lower()
                print("Command recognized:", command)
                app.root.after(0, lambda c=command: execute_command(app, c))
            except sr.UnknownValueError:
                print("Could not understand the command")
            except sr.RequestError as e:
                if app.stt_config.is_offline:
                    print(f"Speech recognition error: {e}")
                else:
                    print("Could not request results; check your network connection")
            except Exception as e:
                print(f"Voice Assistant Error during speech recognition: {e}")
                speak(app, "Voice assistant encountered an error. Disabling assistant.")
                app.voice_assistant_on = False
                if hasattr(app, 'update_voice_btn_icon'):
                    app.root.after(0, app.update_voice_btn_icon)
                break
    finally:
        app.voice_thread_running = False

def execute_command(app, command):
    # --- File Management ---
    if "save file" in command:
        app.save_project()
    elif "open file" in command:
        app.load_project()
    
    # --- System & Canvas ---
    elif "clear canvas" in command:
        speak(app, "Clearing canvas...")
        app.clear()
    elif "delete" in command or "remove" in command:
        speak(app, "Deleting selected items...")
        app.delete_selected()
    elif "undo" in command:
        speak(app, "Undoing last action...")
        app.undo()
    elif "redo" in command:
        speak(app, "Redoing last action...")
        app.redo()
    
    # --- Toggles & View ---
    elif "zoom in" in command:
        speak(app, "Zooming in...")
        app.zoom_in()
    elif "zoom out" in command:
        speak(app, "Zooming out...")
        app.zoom_out()
    elif "grid" in command:
        speak(app, "Toggling grid...")
        app.toggle_grid()
    elif "smart connect" in command:
        speak(app, "Toggling smart connect...")
        app.toggle_smart_connect()
    elif "dark mode" in command or "theme" in command:
        speak(app, "Toggling theme...")
        app.toggle_theme()
    elif "auto shape" in command:
        speak(app, "Toggling auto shape snapping...")
        app.toggle_auto_shape()
    elif "presentation" in command:
        speak(app, "Starting presentation mode...")
        app.toggle_presentation_mode()
        
    # --- Tools & Shapes ---
    elif command in ["draw", "brush", "pen", "select brush", "select pen", "draw tool", "brush tool"]:
        speak(app, "Selecting brush tool...")
        app.select_tool('brush')
    elif "eraser" in command or "erase" in command:
        speak(app, "Selecting eraser tool...")
        app.select_tool('erase')
    elif "rectangle" in command or "square" in command:
        speak(app, "Drawing rectangle...")
        cx, cy = app.c.canvasx(app.root.winfo_width()/2), app.c.canvasy(app.root.winfo_height()/2)
        item_id = app.c.create_rectangle(cx-50, cy-50, cx+50, cy+50, outline=app.color_fg, width=app.penwidth, tags=("object", "rectangle"))
        app.objects.append(item_id)
        app.undo_stack.append(('create', item_id))
    elif "circle" in command or "oval" in command:
        speak(app, "Drawing circle...")
        cx, cy = app.c.canvasx(app.root.winfo_width()/2), app.c.canvasy(app.root.winfo_height()/2)
        item_id = app.c.create_oval(cx-50, cy-50, cx+50, cy+50, outline=app.color_fg, width=app.penwidth, tags=("object", "oval"))
        app.objects.append(item_id)
        app.undo_stack.append(('create', item_id))
    elif "line" in command or "arrow" in command:
        speak(app, "Drawing line...")
        cx, cy = app.c.canvasx(app.root.winfo_width()/2), app.c.canvasy(app.root.winfo_height()/2)
        item_id = app.c.create_line(cx-50, cy, cx+50, cy, fill=app.color_fg, width=app.penwidth, tags=("object", "line"))
        app.objects.append(item_id)
        app.undo_stack.append(('create', item_id))
    elif command.startswith("write ") and len(command.strip()) > 5:
        text_to_write = command[6:].strip().capitalize()
        speak(app, f"Writing {text_to_write}...")
        cx, cy = app.c.canvasx(app.root.winfo_width()/2), app.c.canvasy(app.root.winfo_height()/2)
        font_family = getattr(app, 'current_font', 'Arial')
        font_size = getattr(app, 'font_size', 24)
        item_id = app.c.create_text(cx, cy, text=text_to_write, fill=getattr(app, 'color_fg', 'black'), font=(font_family, font_size), tags=("object", "text"))
        if hasattr(app, 'objects'): app.objects.append(item_id)
        if hasattr(app, 'undo_stack'): app.undo_stack.append(('create', item_id))
    elif "add text" in command or command.strip() == "write":
        speak(app, "Adding text...")
        app.add_text()
    elif "start dictation" in command or "start transcription" in command:
        speak(app, "Starting dictation mode...")
        start_transcription(app)
    elif "sticky note" in command:
        speak(app, "Adding sticky note...")
        app.create_sticky_note()
        
    # --- Colors ---
    elif "color red" in command:
        speak(app, "Changing color to red...")
        if hasattr(app, 'color_fg'): app.color_fg = "red"
    elif "color blue" in command:
        speak(app, "Changing color to blue...")
        if hasattr(app, 'color_fg'): app.color_fg = "blue"
    elif "color green" in command:
        speak(app, "Changing color to green...")
        if hasattr(app, 'color_fg'): app.color_fg = "green"
    elif "color black" in command:
        speak(app, "Changing color to black...")
        if hasattr(app, 'color_fg'): app.color_fg = "black"
        
    # --- AI Features ---
    elif "brainstorm" in command or "ideas" in command:
        speak(app, "Generating ideas...")
        app.execute_idea_generation()
    elif "analyze drawing" in command or "magic" in command:
        speak(app, "Running magic flowchart analysis...")
        app.execute_magic_flowchart()
        
    # --- Exit ---
    elif "exit" in command or "close" in command:
        speak(app, "Exiting the application...")
        app.voice_assistant_on = False
        app.root.quit()
    else:
        speak(app, "Command not recognized")