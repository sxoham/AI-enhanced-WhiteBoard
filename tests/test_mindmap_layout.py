import sys
import os
import tkinter as tk

# Ensure current directory is in path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from whiteboard import Whiteboard

def test_layout():
    try:
        root = tk.Tk()
        # Withdraw the root window so it doesn't pop up and steal focus, 
        # but we need it for canvas measurements
        # root.withdraw() 
        
        # Instantiate App
        # Note: This might fail if relative paths for icons are not found correctly if CWD is wrong.
        # So we ensure CWD is set.
        os.chdir(current_dir)
        
        app = Whiteboard(root)
        
        # Dummy Data
        data = {
            "title": "Layout Test Video",
            "topics": [
                {
                    "name": "Topic 1: Introduction",
                    "details": [f"Detail 1.{i}" for i in range(8)]
                },
                {
                    "name": "Topic 2: Main Concepts",
                    "details": [f"Detail 2.{i} - Long Text" for i in range(5)]
                },
                {
                    "name": "Topic 3: Conclusion",
                    "details": [f"Detail 3.{i}" for i in range(12)]
                }
            ]
        }
        
        print("Generating Mind Map...")
        app.create_mind_map(data)
        
        # Validation
        nodes = app.c.find_withtag("mindmap_node")
        print(f"Total logical nodes created: {len(nodes)}")
        
        # Check BBox
        bbox = app.c.bbox("all")
        if bbox:
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            print(f"Total Diagram Size: {w:.1f} x {h:.1f}")
            
            if w > 800 and h > 600:
                print("SUCCESS: Diagram is large and spread out.")
            else:
                print("WARNING: Diagram seems small.")
        else:
            print("ERROR: Empty bbox.")

        # --- ZOOM TEST ---
        print("\nTesting Zoom...")
        # Get a sample text node
        sample_id = nodes[0]
        initial_font = app.c.itemcget(sample_id, "font")
        print(f"Initial Font: {initial_font}")
        
        # Zoom In
        app.zoom_in()
        zoomed_font = app.c.itemcget(sample_id, "font")
        print(f"Zoomed Font (1.1x): {zoomed_font}")
        
        # Parse font size
        # Tkinter font string can be "Arial 10 bold" or "{Arial} 10 bold"
        # We tracked it as tuple ("Arial", 10, "bold") so itemcget might return similar
        
        # Verify change
        if initial_font != zoomed_font:
             print("SUCCESS: Font changed after zoom.")
        else:
             print("FAILURE: Font did NOT change after zoom.")
        
        # --- CLEANUP TEST ---
        print("\nTesting Markdown Cleanup...")
        # Create a dummy node with markdown
        dirty_text = "**Bold** and *Italic*"
        clean_text = app.clean_text_for_display(dirty_text)
        print(f"Original: '{dirty_text}' -> Cleaned: '{clean_text}'")
        
        if "*" not in clean_text:
            print("SUCCESS: Markdown artifacts removed.")
        else:
            print("FAILURE: Markdown artifacts still present.")

        print("Test Complete.")
        
    except Exception as e:
        print(f"TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_layout()
