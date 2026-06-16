import os
import json
import time
import math
import random
import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter.filedialog import asksaveasfilename, askopenfilename
from PIL import Image, ImageTk
from dotenv import load_dotenv
import google.generativeai as genai
import flowchart_utils
import youtube_utils
import voiceassistant
import textfromimage
from textfromimage import extract_text
import templates
import fitz # PyMuPDF

class AIToolsMixin:
    """
    Mixin class containing all AI-powered generation and document import methods for the Whiteboard.
    """
    def show_ai_dialog(self):
        """Shows a simple dialog to get prompt for AI."""
        # Check if an object is selected to provide context
        context = ""
        if self.selected_objects:
            # Try to get text from selected object if possible
            try:
                item_type = self.c.type(self.selected_objects[0])
                if item_type == "text":
                    context = self.c.itemcget(self.selected_objects[0], "text")
            except:
                pass

        prompt = self.modern_askstring("Ask AI", "What do you want to generate?", initialvalue=f"Refine: {context}" if context else "")
        if prompt:
            self.generate_ai_content(prompt)

    def generate_ai_content(self, prompt):
        """Generates content using Google Gemini API."""
        print(f"Generating for: {prompt}")
        
        self.c.config(cursor="watch")
        self.root.update()
        
        response_text = ""
        
        # 0. Check for "Flowchart" intent (Redirect to specialized tool)
        if "flowchart" in prompt.lower():
            # Reset cursor
            self.c.config(cursor="arrow")
            # Close/Cancel current generation placeholder
            # Call the specific tool
            self.magic_flowchart_dialog() 
            return # Exit this function

        try:
            # 1. Load API Key
            load_dotenv()
            api_key = os.getenv("GOOGLE_API_KEY")
            
            if not api_key:
                response_text = "Error: GOOGLE_API_KEY not found in .env file."
            else:
                # 2. Configure Gemini
                genai.configure(api_key=api_key)
                
                # 3. Generate
                # Using 'gemini-2.5-flash' which is the verified model for this environment
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                # Enhanced System Instruction for directness and quality
                system_instruction = (
                    "Role: Expert Knowledge Assistant for a Professional Digital Whiteboard.\n"
                    "Rules:\n"
                    "1. Provide DIRECT, FACTUAL, and CONCISE answers.\n"
                    "2. NO PREAMBLE: Do not use phrases like 'Sure!', 'I can help with that', or 'Here is your information'.\n"
                    "3. NO FOLLOW-UP QUESTIONS: Always provide an answer; never ask the user for more details.\n"
                    "4. FORMATTING: Use clean bullet points and short sentences for easy reading on a canvas.\n"
                    "5. BRAINSTORMING: If the user wants ideas, provide a numbered list of distinct, creative concepts.\n"
                    "6. LIMIT: Keep responses under 50 words unless the topic requires technical depth."
                )
                
                full_prompt = f"{system_instruction}\n\nUSER PROMPT: {prompt}"
                
                result = model.generate_content(full_prompt)
                response_text = result.text.strip()
                
                # Post-processing: Remove common AI conversational tags just in case
                tags_to_strip = ["Certainly!", "Sure!", "I can help with that.", "I hope this helps!", "Let me know if you need anything else."]
                for tag in tags_to_strip:
                    if response_text.startswith(tag):
                        response_text = response_text[len(tag):].strip()
                    if response_text.endswith(tag):
                        response_text = response_text[:-len(tag)].strip()
                
        except Exception as e:
            response_text = f"AI Error: {str(e)}"
            print(f"AI Exception: {e}")

        self.c.config(cursor="arrow")
        
        # Create text object at center of screen
        cx = self.c.canvasx(self.c.winfo_width()/2)
        cy = self.c.canvasy(self.c.winfo_height()/2)
        
        # Calculate max width (80% of screen or roughly 600-800px)
        max_width = min(800, self.c.winfo_width() * 0.8)
        
        
        # Clean text
        response_text = self.clean_text_for_display(response_text)
        
        self.create_text_object(cx, cy, text=response_text, font_size=20, fill="blue", width=max_width)
        
        # Read the generated response out loud automatically
        if hasattr(self, '_speak_threaded'):
            self._speak_threaded(response_text)
        elif hasattr(self, 'speech_queue'):
            self.speech_queue.put(response_text)


    def restructure_text_for_flowchart(self, raw_text):
        """Uses AI to transform messy text into a structured bullet-point format for flowcharting."""
        print("Restructuring text for flowchart...")
        prompt = f"""Transform the following messy process description into a structured hierarchical list suitable for a flowchart using the EXACT 'flowchart-fun' syntax.
RULES STRICTLY REQUIRED:
1. ONLY USE INDENTATION (spaces) to indicate parent-child edge connections. DO NOT use bullet points (* or -)!
2. LABELED EDGES: If an edge needs a label (like 'Yes' or 'No'), place it before a colon (e.g., "Yes: Go to checkout").
3. DECISIONS: A node that asks a question should just end in a question mark (e.g., "Items found?"). Its indented children should be the edge labels (e.g., "Yes: (Go to checkout)").
4. CYCLES: If a child node should connect to an existing node rather than creating a duplicate, wrap its exact name in parentheses (e.g. "(Leave store)").
5. The very first line MUST be the main starting concept Title.

Input Text:
{raw_text}
"""
        try:
            load_dotenv()
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                return raw_text # Fallback

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            result = model.generate_content(prompt)
            return result.text.strip()
            
        except Exception as e:
            print(f"Gemini Restructure Error: {e}, attempting Ollama fallback...")
            import requests
            try:
                url = "http://localhost:11434/api/generate"
                payload = {
                    "model": "llama3",
                    "prompt": prompt,
                    "stream": False
                }
                response = requests.post(url, json=payload, timeout=60)
                response.raise_for_status()
                return response.json().get('response', '').strip()
            except Exception as e_ollama:
                print(f"Ollama Fallback Error: {e_ollama}")
                return raw_text # Fallback to original text if both AI routines fail

    def create_text_object(self, x, y, text="Text", font_size=24, fill="black", width=None):
        """Helper to create text object safely."""
        font_spec = (self.current_font, font_size)
        
        # Optional kwargs for create_text
        kw = {}
        if width:
            kw['width'] = width
            
        text_id = self.c.create_text(x, y, text=text, font=font_spec, fill=fill, tags=("text",), **kw)
        self.objects.append(text_id)
        
        # Track base font size for zooming
        self.text_base_sizes[text_id] = (self.current_font, font_size)
        
        # Register undo
        # Fix: Push tuple, not dict, and include optional width
        self.undo_stack.append(('create_text', text_id, x, y, text, fill, font_size, width))
        self.redo_stack.clear()
        return text_id

    def save_canvas(self):
        # Determine filename
        if hasattr(self, 'current_filename') and self.current_filename:
            filename = self.current_filename
        else:
            filename = asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
            if filename:
                self.current_filename = filename
            else:
                return

        # Collect canvas data
        canvas_data = []
        for obj in self.c.find_all():
            obj_type = self.c.type(obj)
            coords = self.c.coords(obj)
            item_data = {
                'type': obj_type,
                'coords': coords
            }
            if obj_type == 'line':
                item_data['width'] = self.c.itemcget(obj, 'width')
                item_data['fill'] = self.c.itemcget(obj, 'fill')
            elif obj_type in ['rectangle', 'oval']:
                item_data['outline'] = self.c.itemcget(obj, 'outline')
                item_data['width'] = self.c.itemcget(obj, 'width')
                item_data['fill'] = self.c.itemcget(obj, 'fill')
            elif obj_type == 'text':
                item_data['text'] = self.c.itemcget(obj, 'text')
                item_data['fill'] = self.c.itemcget(obj, 'fill')
                item_data['font'] = self.c.itemcget(obj, 'font')
            elif obj_type == 'image':
                # Use obj (ID) to get the file path
                image_file = self.image_files.get(obj, '')
                item_data['image'] = image_file
                
                # Save metadata if present
                if obj in self.image_metadata:
                    item_data['metadata'] = self.image_metadata[obj]

            canvas_data.append(item_data)

        # Save data to file
        with open(filename, 'w') as file:
            json.dump(canvas_data, file)

    def open_canvas(self):
        # Prompt for a file to open
        filename = askopenfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if filename:
            try:
                with open(filename, 'r') as file:
                    canvas_data = json.load(file)

                # Clear current canvas
                self.c.delete("all")
                self.image_refs = []  # Reset image references list
                self.objects = []
                self.selected_objects = []
                self.image_files = {}
                self.image_metadata = {}

                # Load all items to the canvas
                for item in canvas_data:
                    obj_type = item['type']
                    coords = item['coords']
                    if obj_type == 'line':
                        line_id = self.c.create_line(*coords, fill=item.get('fill', ''), width=max(1, int(item.get('width', 1) * self.scale)))
                        self.shape_base_widths[line_id] = item.get('width', 1)
                    elif obj_type == 'rectangle':
                        rect_id = self.c.create_rectangle(*coords, outline=item.get('outline', ''), width=max(1, int(item.get('width', 1) * self.scale)),
                                                fill=item.get('fill', ''))
                        self.shape_base_widths[rect_id] = item.get('width', 1)
                    elif obj_type == 'oval':
                        oval_id = self.c.create_oval(*coords, outline=item.get('outline', ''), width=max(1, int(item.get('width', 1) * self.scale)),
                                           fill=item.get('fill', ''))
                        self.shape_base_widths[oval_id] = item.get('width', 1)
                    elif obj_type == 'text':
                        self.c.create_text(*coords, text=item.get('text', ''), fill=item.get('fill', ''),
                                           font=item.get('font', ''))
                    elif obj_type == 'image':
                        image_path = item.get('image', '')
                        if image_path and os.path.exists(image_path):
                            try:
                                image = Image.open(image_path)
                                # Resize? The saved coords are top-left? NO, coords is 2 points? 
                                # create_image takes x, y. coords(image) returns x, y.
                                # Check how coords were saved. self.c.coords(obj) for image returns [x, y].
                                
                                # Wait, we need to respect size.
                                # Canvas image item doesn't store size directly?
                                # We need to rely on the file and maybe resize if we had width/height?
                                # But we didn't save width/height. We just load original.
                                # For now, simple load.
                                
                                photo_image = ImageTk.PhotoImage(image)
                                self.c.create_image(*coords, image=photo_image, anchor=tk.NW, tags="image_tag")
                                # Store reference to avoid garbage collection
                                self.image_refs.append(photo_image)
                                
                                # Find the ID
                                all_items = self.c.find_all()
                                if all_items:
                                    current_id = all_items[-1]
                                    self.image_files[current_id] = image_path
                                    if not hasattr(self, 'stored_images'): self.stored_images = {}
                                    self.stored_images[current_id] = image
                                    
                                    # Load Metadata
                                    if 'metadata' in item:
                                        self.image_metadata[current_id] = item['metadata']
                                        
                            except Exception as e:
                                print(f"Error loading image: {e}")
                
                 # Restore self.objects list so we can undo/manipulate later
                self.objects = list(self.c.find_all())

                # Save the filename for future saves
                self.current_filename = filename
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
            except Exception as e:
                print(f"Error opening file: {e}")



    def add_action_to_canvas(self, item):
        action_type, item_id, *item_data = item

        if action_type == 'create_line':
            x0, y0, x1, y1, color, width = item_data
            line_id = self.c.create_line(x0, y0, x1, y1, fill=color, width=max(1, int(width * self.scale)))
            self.shape_base_widths[line_id] = width
            self.actions[self.actions.index(item)] = (action_type, line_id, x0, y0, x1, y1, color, width)

        elif action_type == 'create_rectangle':
            x0, y0, x1, y1, color, width = item_data
            rect_id = self.c.create_rectangle(x0, y0, x1, y1, outline=color, width=max(1, int(width * self.scale)))
            self.shape_base_widths[rect_id] = width
            self.actions[self.actions.index(item)] = (action_type, rect_id, x0, y0, x1, y1, color, width)

        elif action_type == 'create_oval':
            x0, y0, x1, y1, color, width = item_data
            oval_id = self.c.create_oval(x0, y0, x1, y1, outline=color, width=max(1, int(width * self.scale)))
            self.shape_base_widths[oval_id] = width
            self.actions[self.actions.index(item)] = (action_type, oval_id, x0, y0, x1, y1, color, width)

        elif action_type == 'create_text':
            x, y, text, color, font_size = item_data
            text_id = self.c.create_text(x, y, text=text, fill=color, font=("Arial", font_size))
            self.actions[self.actions.index(item)] = (action_type, text_id, x, y, text, color, font_size)




    #AI FEATURES
    def get_canvas_context_keywords(self, items=None):
        """Scans the canvas for text (or provided items) to provide context to AI."""
        context = []
        target_objects = items if items is not None else self.c.find_all()
        for obj in target_objects:
            if self.c.type(obj) == 'text':
                text = self.c.itemcget(obj, 'text')
                if text and len(text.strip()) > 2:
                    context.append(text.strip())
            elif self.c.type(obj) == 'image':
                 # Check if this image has metadata
                 if obj in self.image_metadata:
                     meta_text = self.image_metadata[obj]
                     # Simple keyword extraction: split by logic?
                     # Ideally we just dump the text, but for "Context", maybe we grab 
                     # lines or just append it and let the idea generator filter.
                     # Let's clean it up a bit.
                     if meta_text:
                         # Handle both string (direct text) and dict (structured metadata)
                         if isinstance(meta_text, dict):
                             # Try to find a logical text key
                             text_to_split = meta_text.get("text", "")
                             if not text_to_split and meta_text.get("type") == "pdf_page":
                                 # For PDFs, maybe use the source filename as context?
                                 text_to_split = os.path.basename(meta_text.get("source", ""))
                         else:
                             text_to_split = str(meta_text)

                         if text_to_split:
                             lines = text_to_split.split('\n')
                             for line in lines:
                                 if len(line.strip()) > 3:
                                     context.append(line.strip())
        return context

    def execute_idea_generation(self):
        print("DEBUG: executing idea generation")
        # 1. Determine Topic (Selection > Input > None)
        topic = None
        center_x, center_y = 400, 300 # Default center
        
        if self.selected_objects:
            print(f"DEBUG: Selected objects: {self.selected_objects}")
            # Try to find text in selection
            for obj in self.selected_objects:
                obj_type = self.c.type(obj)
                print(f"DEBUG: Object {obj} type: {obj_type}")
                if obj_type == 'text':
                    topic = self.c.itemcget(obj, 'text')
                    coords = self.c.coords(obj)
                    center_x, center_y = coords[0], coords[1]
                    break
                elif obj_type == 'image':
                     # Check for metadata
                     if obj in self.image_metadata:
                         meta_text = self.image_metadata[obj]
                         print(f"DEBUG: Metadata found for image {obj}: {repr(meta_text)}")
                         if meta_text:
                             # Handle both string and dict
                             if isinstance(meta_text, dict):
                                 topic_text = meta_text.get("text", "")
                                 if not topic_text and meta_text.get("type") == "pdf_page":
                                     topic_text = f"PDF: {os.path.basename(meta_text.get('source', ''))} (Page {meta_text.get('page', 0)+1})"
                             else:
                                 topic_text = str(meta_text)

                             if topic_text:
                                 # Use first NON-EMPTY line as topic
                                 lines = topic_text.strip().split('\n')
                                 for line in lines:
                                     if line.strip():
                                         topic = line.strip()
                                         break
                             
                             if topic:
                                 # Calculate center of image
                                 # bbox is reliable.
                                 bbox = self.c.bbox(obj)
                                 if bbox:
                                     center_x = (bbox[0] + bbox[2]) / 2
                                     center_y = (bbox[1] + bbox[3]) / 2
                                 else:
                                     x1, y1 = self.c.coords(obj)
                                     center_x, center_y = x1, y1
                                 break
                     else:
                         print(f"DEBUG: No metadata for image {obj}. Keys: {list(self.image_metadata.keys())}")
        
        if not topic:
            topic = self.modern_askstring("Idea Generation", "Enter a topic (or leave empty to suggest based on context):")
            if topic: 
                topic = topic.strip().lower()
        
        # 2. Get Context (ONLY from selected objects if any)
        context = self.get_canvas_context_keywords(self.selected_objects) if self.selected_objects else []
        print(f"DEBUG: Topic: '{topic}', Context: {context}")
        
        if not topic and not context:
             messagebox.showinfo("Idea Generation", "Please select some text/nodes on the board or enter a topic!")
             return

        # 3. Generate
        prompt = f"Brainstorm exactly 5 very short ideas (max 5 words) about '{topic}'. Use context: {context}. Return ONLY a bulleted list."
        response_text = self.generate_ai_content(prompt)
        ideas = []
        if response_text:
            for line in response_text.split('\n'):
                # Clean bullet markers
                clean_line = line.strip().lstrip('-*Ã¢â‚¬Â¢1234567890. ')
                if clean_line:
                    ideas.append(clean_line)
        # 4. Visualize (Mind Map Style)
        if ideas:
            import math
            radius = 150
            angle_step = 2 * math.pi / len(ideas)
            
            for i, idea in enumerate(ideas):
                angle = i * angle_step
                # Calculate position around the center/selected object
                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
                
                # Create a text node
                idea = self.clean_text_for_display(idea)
                self.create_text_entry_display(idea, x, y)
                
                # Draw a line connecting to center? (Optional, if we had a center ID)
                # For now just placing them is good enough for brainstorming.
        else:
             messagebox.showinfo("Idea Generation", "No ideas found.")


    def create_text_entry_display(self, text, x=10, y=10):
        """Unified entry point for placing text from various AI tools."""
        return self.create_text_object(x, y, text=text, font_size=self.font_size, fill=self.color_fg)

    def execute_text_extraction(self):
        image_path = filedialog.askopenfilename(title="Select an image",
                                                filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.tiff")])
        # If a file was selected
        if image_path:
            # Extract and display the text from the selected image
            text = extract_text(image_path)

            if text:
                text = self.clean_text_for_display(text)
                self.create_text_entry_display(text)
            else:
                messagebox.showinfo("Error", "No text found in image")
        else:
            messagebox.showinfo("Error", "No image selected")


    def generate_flowchart_from_file(self, file_path=None, layout_type='standard'):
        if not file_path:
            file_path = filedialog.askopenfilename()

        if file_path:
            try:
                # ... (reading code remains same) ...
                if file_path.lower().endswith('.txt'):
                     text = flowchart_utils.read_text_from_plain_file(file_path)
                elif file_path.lower().endswith('.docx'):
                     text = flowchart_utils.read_text_from_docx(file_path)
                elif file_path.lower().endswith('.pdf'):
                     text = flowchart_utils.read_text_from_pdf(file_path)
                else:
                    messagebox.showerror("Error", "Unsupported file format.")
                    return

                if not text.strip():
                     messagebox.showerror("Error", "No content in the file.")
                     return

                # Restructure text using AI for better flowchart logic
                structured_text = self.restructure_text_for_flowchart(text)
                print(f"DEBUG: Structured file text:\n{structured_text}")

                # Updated Logic: Get Parsed Data
                parsed_data = flowchart_utils.parse_text(structured_text)
                
                # Initialize Digraph
                # Render at 72 DPI (Standard Graphviz default)
                if flowchart_utils.Digraph is None:
                    messagebox.showerror("Error", "Graphviz Python package is not installed. Please install graphviz to use flowchart features.")
                    return
                dot = flowchart_utils.Digraph(graph_attr={'dpi': '72', 'bgcolor': 'white', 'rankdir': 'LR'})

                # Use Sequential Logic with parsed sub-steps AND LAYOUT TYPE
                flowchart_utils.add_sequential_edges(dot, parsed_data, layout_type=layout_type)

                try:
                    # Output path
                    output_path = os.path.join(os.path.dirname(__file__), 'ai_generated_flowchart')
                    dot.render(output_path, format='json', view=False, cleanup=True)
                    json_path = output_path + ".json"
                    
                    if os.path.exists(json_path):
                        with open(json_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        title = parsed_data[0]['label'] if parsed_data else "Generated Flowchart"
                        self.draw_native_graphviz(data, title=title)
                    else:
                        messagebox.showerror("Error", "Flowchart JSON not found after generation.")

                except Exception as e:
                    messagebox.showerror("Error", f"Error generating flowchart: {e}")
            except FileNotFoundError:
                messagebox.showerror("Error", f"File '{file_path}' not found.")
            except Exception as e:
                messagebox.showerror("Error", f"Error reading file: {e}")

    def get_resizing_state(self, item_id):
        item_type = self.c.type(item_id)
        # For shapes, use logical coords to avoid stroke width offsets from bbox
        if item_type in ['rectangle', 'oval', 'line', 'polygon']:
             return {'type': item_type, 'coords': self.c.coords(item_id)}
        else:
             bbox = self.c.bbox(item_id)
             return {'type': item_type, 'bbox': bbox}

    def apply_resizing_state(self, item_id, state):
        item_type = state['type']
        
        if item_type == 'image':
             bbox = state['bbox'] # x1, y1, x2, y2
             path = self.image_files.get(item_id)
             if path and (os.path.exists(path) or (hasattr(self, 'stored_images') and item_id in self.stored_images)):
                 w = int(bbox[2] - bbox[0])
                 h = int(bbox[3] - bbox[1])
                 if w < 10: w = 10
                 if h < 10: h = 10
                 
                 # Optimization: Use stored master if available to avoid disk I/O and maintain quality
                 if hasattr(self, 'stored_images') and item_id in self.stored_images:
                     orig_image = self.stored_images[item_id]
                 else:
                     orig_image = Image.open(path)
                     
                 resized = orig_image.resize((w, h), Image.LANCZOS)
                 self.photo_image = ImageTk.PhotoImage(resized) 
                 
                 if not hasattr(self, 'image_refs'): self.image_refs = []
                 self.image_refs.append(self.photo_image)
                 
                 self.c.itemconfig(item_id, image=self.photo_image)
                 self.c.coords(item_id, bbox[0], bbox[1])
        
        elif item_type in ['rectangle', 'oval', 'line', 'polygon']:
            coords = state['coords']
            self.c.coords(item_id, *coords)
        
        if getattr(self, 'resize_target', None) == item_id:
            self.update_resize_handle()
        self.update_connected_lines(item_id)

    def get_anchors(self, item_id):
        """Returns N, S, E, W anchor points for an item."""
        bbox = self.c.bbox(item_id)
        if not bbox: return {}
        x1, y1, x2, y2 = bbox
        mx, my = (x1+x2)/2, (y1+y2)/2
        return {
            'n': (mx, y1),
            's': (mx, y2),
            'e': (x2, my),
            'w': (x1, my),
            'center': (mx, my)
        }

    def get_best_route(self, start_id, end_id):
        """Calculates orthogonal path between two objects."""
        anchors1 = self.get_anchors(start_id)
        anchors2 = self.get_anchors(end_id)
        if not anchors1 or not anchors2: return None
        
        # Simple heuristic: Choose closest pair of anchors specific for orthogonal routing
        # Preference: N-S, E-W, etc.
        
        # For now, simplistic approach:
        # Determine relative position
        c1 = anchors1['center']
        c2 = anchors2['center']
        dx = c2[0] - c1[0]
        dy = c2[1] - c1[1]
        
        start_node = 'e' if dx > 0 else 'w'
        end_node = 'w' if dx > 0 else 'e'
        
        if abs(dy) > abs(dx): # Vertical dominance
            start_node = 's' if dy > 0 else 'n'
            end_node = 'n' if dy > 0 else 's'
            
        p1 = anchors1[start_node]
        p2 = anchors2[end_node]
        
        # Orthogonal path generation
        # 1. Start -> Mid -> End mechanism
        points = [p1[0], p1[1]]
        
        if start_node in ['n', 's']:
            # Vertical start
            mid_y = (p1[1] + p2[1]) / 2
            points.extend([p1[0], mid_y])
            points.extend([p2[0], mid_y])
        else:
            # Horizontal start
            mid_x = (p1[0] + p2[0]) / 2
            points.extend([mid_x, p1[1]])
            points.extend([mid_x, p2[1]])
            
        points.extend([p2[0], p2[1]])
        return points

    def update_connected_lines(self, item_id):
        """Updates all lines connected to this item."""
        if not hasattr(self, 'connections'): return
        
        for line_id, conn in self.connections.items():
            if conn['start'] == item_id or conn['end'] == item_id:
                start_id = conn['start']
                end_id = conn.get('end')
                
                if not end_id:
                     continue

                # Check if objects still exist
                if start_id not in self.objects or end_id not in self.objects:
                    continue # Should cleanup?
                
                points = self.get_best_route(start_id, end_id)
                if points:
                    try:
                        self.c.coords(line_id, *points)
                    except Exception as e: 
                        pass
    
    def insert_image(self):
        """Allows user to upload an image from the system."""
        file_path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")])
        if not file_path:
            return

        try:
            # Open Image
            pil_img = Image.open(file_path)
            
            # Initial Resize if too large (e.g., > 1000px dimension)
            # keeping aspect ratio
            # This is optional but good for performance
            # width, height = pil_img.size
            # max_dim = 1000
            # if width > max_dim or height > max_dim:
            #    pil_img.thumbnail((max_dim, max_dim))
            
            tk_img = ImageTk.PhotoImage(pil_img)

            # Center on current view
            try:
                # Find center of visible scroll region? 
                # Or just offset from top left scroll
                base_x = self.c.canvasx(100)
                base_y = self.c.canvasy(100)
            except:
                base_x, base_y = 100, 100
                
            img_id = self.c.create_image(base_x, base_y, image=tk_img, anchor=tk.NW, tags=("object", "image"))
            
            # Store everything needed
            self.image_files[img_id] = file_path 
            self.objects.append(img_id)
            # Store metadata for save/load or resizing
            self.image_metadata[img_id] = {
                "type": "image", 
                "source": file_path, 
                "pil_image": pil_img, 
                "tk_image": tk_img # Keep ref!
            }
            self.image_base_sizes[img_id] = pil_img.size
            
            # Store in high-res master map for zooming
            if not hasattr(self, 'stored_images'): self.stored_images = {}
            self.stored_images[img_id] = pil_img
            
            if not hasattr(self, 'image_refs'): self.image_refs = []
            self.image_refs.append(tk_img)

            self.update_scrollregion()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to insert image: {e}")
            print(f"Insert Image Error: {e}")



    def import_pdf(self):
        """Imports a PDF and renders its pages as images on the canvas."""
        file_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if not file_path:
            return

        try:
            doc = fitz.open(file_path)
            total_pages = len(doc)
            
            # Single Dialog for Page Selection
            prompt = f"Total Pages: {total_pages}\nEnter pages to load (Max 3).\nExamples: '1,3,5' or '5-7'"
            selection = self.modern_askstring("Import PDF", prompt)
            
            if not selection:
                doc.close()
                return

            # Parse Selection
            pages_to_load = set()
            try:
                parts = selection.split(',')
                for part in parts:
                    part = part.strip()
                    if '-' in part:
                        start, end = map(int, part.split('-'))
                        # Handle reverse range or just sort? standard is start-end
                        if start > end: start, end = end, start
                        for p in range(start, end + 1):
                            pages_to_load.add(p)
                    else:
                        pages_to_load.add(int(part))
            except ValueError:
                messagebox.showerror("Error", "Invalid format. Please use numbers separated by commas or ranges (e.g., 1-3).")
                doc.close()
                return

            # Validate Pages
            valid_pages = sorted([p for p in pages_to_load if 1 <= p <= total_pages])
            
            if not valid_pages:
                 messagebox.showerror("Error", "No valid pages selected.")
                 doc.close()
                 return

            if len(valid_pages) > 3:
                messagebox.showerror("Error", "You can only import up to 3 pages at a time.")
                doc.close()
                return
            
            # Base Position Calculation
            # Base Position Calculation
            try:
                base_x = self.c.canvasx(100)
                base_y = self.c.canvasy(100)
                
                view_w = self.c.winfo_width()
                view_h = self.c.winfo_height()
                if view_w <= 1: 
                    view_w = self.root.winfo_screenwidth()
                    view_h = self.root.winfo_screenheight()
                
                # Target dimensions in screen pixels (80% of current view)
                target_w_screen = int(view_w * 0.8)
                target_h_screen = int(view_h * 0.8)
                
                # Convert screen target to canvas units (size at 1.0 zoom)
                # Ensure we handle current scale to prevent oversized/overlapping imports
                target_w = target_w_screen / self.scale
                target_h = target_h_screen / self.scale
            except:
                base_x, base_y = 100, 100
                target_w, target_h = 800, 600

            current_x = base_x
            current_y = base_y
            padding = 20 # Canvas units
            
            messagebox.showinfo("Importing PDF", f"Importing pages: {valid_pages}...")
            
            for page_num in valid_pages:
                i = page_num - 1 # 0-indexed for fitz
                page = doc.load_page(i)
                
                # --- HIGH RESOLUTION RENDERING ---
                # Render at 300 DPI for high quality (4.16 zoom factor relative to 72 DPI)
                high_res_zoom = 300 / 72 
                mat = fitz.Matrix(high_res_zoom, high_res_zoom)
                pix = page.get_pixmap(matrix=mat)
                
                # Convert to PIL (This is our High-Quality Master)
                high_res_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Calculate display scale for CANVAS UNITS (size at 1.0 zoom)
                display_scale_w = target_w / page.rect.width
                display_scale_h = target_h / page.rect.height
                display_scale = min(display_scale_w, display_scale_h)
                
                # Dimensions in canvas units (size at 1.0 zoom)
                base_w = page.rect.width * display_scale
                base_h = page.rect.height * display_scale
                
                # Rescale high-res master to the CURRENT zoom size for immediate display
                disp_w = int(base_w * self.scale)
                disp_h = int(base_h * self.scale)
                
                img_display = high_res_img.resize((disp_w, disp_h), Image.LANCZOS)
                tk_img = ImageTk.PhotoImage(img_display)
                
                # Create on Canvas
                img_id = self.c.create_image(current_x, current_y, image=tk_img, anchor=tk.NW, tags=("object", "image"))
                
                # Register Object
                self.objects.append(img_id)
                self.image_files[img_id] = f"PDF_SOURCE::{file_path}::PAGE_{i}" 
                
                self.image_metadata[img_id] = {
                    "type": "pdf_page",
                    "source": file_path,
                    "page": i,
                    "original_width": page.rect.width,
                    "original_height": page.rect.height
                }
                
                # CRITICAL: Store base dimensions (size at 1.0 zoom) for correct layout and future zooming
                self.image_base_sizes[img_id] = (base_w, base_h)
                
                # Store HIGH-RES MASTER for rescaling/zooming (maintains quality)
                if not hasattr(self, 'stored_images'): self.stored_images = {}
                self.stored_images[img_id] = high_res_img
                
                if not hasattr(self, 'image_refs'): self.image_refs = []
                self.image_refs.append(tk_img)
                
                # Increment layout position based on canvas units
                current_x += base_w + padding 
            
            doc.close()
            self.update_scrollregion()
            self.update_minimap()
            
            messagebox.showinfo("Success", "PDF Pages imported successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import PDF: {e}")
            print(f"PDF Import Error: {e}")

    def toggle_voice_assistant(self):
        """Toggles the voice assistant on/off."""
        voiceassistant.toggle_voice_assistant(self)

    def generate_youtube_notes(self):
        """Fetches and displays summary notes from a YouTube video as a Mind Map."""
        url = self.modern_askstring("YouTube to Notes", "Enter YouTube URL:")
        if not url: return
        
        messagebox.showinfo("Processing", "Fetching transcript and generating Mind Map... This may take a moment.")
        self.root.update()
        
        try:
            summary = youtube_utils.get_video_summary(url)
            
            # Summary is now a dictionary
            if isinstance(summary, dict):
                self.create_mind_map(summary)
            else:
                self.create_text_note(summary)
            
        except Exception as e:
            print(f"Error generating notes: {e}")
            messagebox.showerror("Error", f"Failed to generate notes: {str(e)}")

    def create_text_note(self, text):
        # Clean text
        text = self.clean_text_for_display(text)
        
        x, y = self.c.canvasx(self.c.winfo_width()/2), self.c.canvasy(self.c.winfo_height()/2)
        text_id = self.c.create_text(x, y, text=text, width=500, font=("Arial", 10), anchor="center", justify="left")
        bbox = self.c.bbox(text_id)
        
        bg_rect_id = None
        if bbox:
            bg_rect_id = self.c.create_rectangle(bbox[0]-10, bbox[1]-10, bbox[2]+10, bbox[3]+10, fill="#E3F2FD", outline="#2196F3", width=2)
            self.c.tag_raise(text_id, bg_rect_id)
            
        if bg_rect_id is not None:
            self.objects.extend([bg_rect_id, text_id])
        else:
            self.objects.append(text_id)

    def create_mind_map(self, data):
        """Generates a Mind Map with collision-avoidance layout."""
        # Center of view
        cx = self.c.canvasx(self.c.winfo_width()/2)
        cy = self.c.canvasy(self.c.winfo_height()/2)
        
        import math
        import random
        
        # 1. Main Title Node
        title = data.get("title", "Video Notes")
        title = self.clean_text_for_display(title)
        title_id = self.create_node(cx, cy, title, bg_color="#FFEB3B", font=("Arial", 14, "bold"), shape="oval", padding=20)
        self.c.addtag_withtag("mindmap_node", title_id) # Tag for collision detection
        
        topics = data.get("topics", [])
        if not topics: return
        
        # --- PHASE 1: Create Topic Nodes (First Pass - Measurement) ---
        topic_nodes = []
        for topic in topics:
            name = topic.get("name", "Topic")
            name = self.clean_text_for_display(name)
            # Create at temp location to measure
            tid = self.create_node(cx, cy, name, bg_color="#BBDEFB", font=("Arial", 12, "bold"), shape="rectangle", padding=15)
            self.c.addtag_withtag("mindmap_node", tid)
            bbox = self.c.bbox(tid)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            topic_nodes.append({'id': tid, 'w': w, 'h': h, 'data': topic, 'angle': 0})

        # --- PHASE 2: Calculate Topic Placement ---
        # Calculate minimum circumference needed
        total_width = sum(t['w'] for t in topic_nodes)
        min_circumference = total_width * 3.5 # Increased spacing
        min_radius = max(450, min_circumference / (2 * math.pi))
        
        angle_step = 2 * math.pi / len(topic_nodes)
        
        for i, node in enumerate(topic_nodes):
            angle = i * angle_step
            node['angle'] = angle
            tx = cx + min_radius * math.cos(angle)
            ty = cy + min_radius * math.sin(angle)
            
            # Move to position
            self.move_node_center(node['id'], tx, ty)
            
            # Connect to Center
            self.connect_nodes(title_id, node['id'], color="#90CAF9", width=3)
            
            # --- PHASE 3: Detail Nodes (Staggered Layout) ---
            details = node['data'].get("details", [])
            if not details: continue
            
            # Place details for this topic
            parent_id = node['id']
            base_detail_radius = 220 
            
            num_details = len(details)
            angle_spread = math.radians(120) 
            
            start_angle = angle - (angle_spread / 2)
            if num_details > 1:
                detail_angle_step = angle_spread / (num_details - 1)
            else:
                detail_angle_step = 0
                start_angle = angle

            for j, detail_text in enumerate(details):
                detail_text = self.clean_text_for_display(detail_text)
                did = self.create_node(cx, cy, detail_text, bg_color="#FFFFFF", font=("Arial", 10), shape="rectangle", width_limit=220)
                self.c.addtag_withtag("mindmap_node", did)
                
                placed = False
                current_dist = base_detail_radius
                
                if num_details > 1:
                    d_angle = start_angle + (j * detail_angle_step)
                else:
                    d_angle = angle
                
                # Collision resolution loop
                for attempt in range(25):
                    dx = tx + current_dist * math.cos(d_angle)
                    dy = ty + current_dist * math.sin(d_angle)
                    
                    self.move_node_center(did, dx, dy)
                    
                    if not self.check_node_collision(did, buffer=30):
                        placed = True
                        break
                    else:
                        current_dist += 60
                        d_angle += random.uniform(-0.1, 0.1)
                
                self.connect_nodes(parent_id, did, color="#E0E0E0", width=2)

    def clean_text_for_display(self, text):
        """Removes markdown artifacts like **bold** markers."""
        if not text: return ""
        text = text.replace("**", "").replace("*", "")
        text = text.replace("##", "").replace("#", "")
        return text.strip()

    def move_node_center(self, item_id, cx, cy):
        """Moves a node (group) so its center is at (cx, cy)."""
        tags = self.c.gettags(item_id)
        group_tag = next((t for t in tags if t.startswith("node_group_")), None)
        
        if not group_tag:
            target_ids = [item_id]
            bbox = self.c.bbox(item_id)
        else:
            target_ids = self.c.find_withtag(group_tag)
            bbox = self.c.bbox(group_tag)
            
        if not bbox: return
        
        current_cx = (bbox[0] + bbox[2]) / 2
        current_cy = (bbox[1] + bbox[3]) / 2
        
        dx = cx - current_cx
        dy = cy - current_cy
        
        for tid in target_ids:
            self.c.move(tid, dx, dy)

    def check_node_collision(self, item_id, buffer=10):
        """Checks if item_id overlaps with other mindmap nodes."""
        tags = self.c.gettags(item_id)
        group_tag = next((t for t in tags if t.startswith("node_group_")), None)
        
        if group_tag:
            bbox = self.c.bbox(group_tag)
            my_items = set(self.c.find_withtag(group_tag))
        else:
            bbox = self.c.bbox(item_id)
            my_items = {item_id}
            
        if not bbox: return False
        
        x1, y1, x2, y2 = bbox
        search_box = (x1-buffer, y1-buffer, x2+buffer, y2+buffer)
        
        overlaps = self.c.find_overlapping(*search_box)
        
        for oid in overlaps:
            if oid in my_items: continue
            
            otags = self.c.gettags(oid)
            if "mindmap_node" in otags or any(t.startswith("node_group_") for t in otags):
                return True
        return False
                    
    def create_node(self, x, y, text, bg_color="white", font=("Arial", 10), shape="rectangle", padding=10, width_limit=200, record_undo=True):
        """Creates a text node with a background shape, handles scaling, and tags for group movement."""
        # Scale initial font and width based on current zoom
        scaled_font = (font[0], int(font[1] * self.scale)) if isinstance(font, (tuple, list)) and len(font) >= 2 else font
        scaled_width = width_limit * self.scale if width_limit else None
        
        text_id = self.c.create_text(x, y, text=text, width=scaled_width, font=scaled_font, justify="center")
        
        if isinstance(font, (tuple, list)) and len(font) >= 2:
            self.text_base_sizes[text_id] = font
            
        if record_undo:
            # Register for base metrics scaling
            if not hasattr(self, 'text_base_widths'): self.text_base_widths = {}
            self.text_base_widths[text_id] = width_limit
            self.undo_stack.append(('create_node', text_id, x, y, text, bg_color, font, shape, padding, width_limit))
            
        bbox = self.c.bbox(text_id)
        if bbox:
            x1, y1, x2, y2 = bbox
            x1 -= padding; y1 -= padding; x2 += padding; y2 += padding
            
            # Geometrically adjust bounding box for shapes that clip corners
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            w, h = x2 - x1, y2 - y1
            
            if shape == "diamond":
                # Diamond needs to be roughly 2x the size to encapsulate a rectangle
                x1 = cx - w * 0.9
                x2 = cx + w * 0.9
                y1 = cy - h * 0.9
                y2 = cy + h * 0.9
            elif shape == "oval":
                # Oval needs to be roughly 1.414x (sqrt 2) to encapsulate a rectangle
                x1 = cx - w * 0.75
                x2 = cx + w * 0.75
                y1 = cy - h * 0.75
                y2 = cy + h * 0.75

            scaled_outline = max(1, int(1 * self.scale))
            if shape == "oval":
                bg_id = self.c.create_oval(x1, y1, x2, y2, fill=bg_color, outline="gray", width=scaled_outline)
            elif shape == "diamond":
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                bg_id = self.c.create_polygon(mx, y1, x2, my, mx, y2, x1, my, fill=bg_color, outline="gray", width=scaled_outline)
            else:
                bg_id = self.c.create_rectangle(x1, y1, x2, y2, fill=bg_color, outline="gray", width=scaled_outline)
            
            self.shape_base_widths[bg_id] = 1 # Base outline width
            
            self.c.tag_lower(bg_id, text_id)
            
            # Vital for group movement: Tag them together
            node_tag = f"node_group_{text_id}"
            self.c.addtag_withtag(node_tag, text_id)
            self.c.addtag_withtag(node_tag, bg_id)
            
            # Register for persistence and selection
            self.c.addtag_withtag("object", bg_id)
            self.c.addtag_withtag("object", text_id)
            self.objects.extend([bg_id, text_id])
            return text_id
        return text_id

    def get_node_bbox(self, item_id):
        tags = self.c.gettags(item_id)
        group_tag = next((t for t in tags if t.startswith("node_group_")), None)
        if group_tag:
            return self.c.bbox(group_tag)
        else:
            return self.c.bbox(item_id)

    def connect_nodes(self, id1, id2, color="gray", width=1):
        """Draws a connector between two nodes (closest points) and registers it."""
        bbox1 = self.get_node_bbox(id1)
        bbox2 = self.get_node_bbox(id2)
        if not bbox1 or not bbox2: return None
        
        c1x, c1y = (bbox1[0]+bbox1[2])/2, (bbox1[1]+bbox1[3])/2
        c2x, c2y = (bbox2[0]+bbox2[2])/2, (bbox2[1]+bbox2[3])/2
        
        line_id = self.c.create_line(c1x, c1y, c2x, c2y, fill=color, width=max(1, int(width * self.scale)), tags=("connection_line", "object"))
        self.shape_base_widths[line_id] = width
        self.c.tag_lower(line_id) 
        self.objects.append(line_id)
        
        # Register connection so lines track movement and survive save/load!
        if hasattr(self, 'connections'):
            self.connections[line_id] = {'start': id1, 'end': id2}
            
        self.undo_stack.append(('create_line', line_id, c1x, c1y, c2x, c2y, color, width))
        self.update_scrollregion()
        return line_id


    def create_text_note(self, text):
        print("DEBUG: Executing NEW create_text_note logic (v2)")
        
        # Clean text
        text = self.clean_text_for_display(text)
        
        x, y = self.c.canvasx(self.c.winfo_width()/2), self.c.canvasy(self.c.winfo_height()/2)
        text_id = self.c.create_text(x, y, text=text, width=500, font=("Arial", 10), anchor="center", justify="left")
        bbox = self.c.bbox(text_id)
        
        bg_rect_id = None
        if bbox:
            bg_rect_id = self.c.create_rectangle(bbox[0]-10, bbox[1]-10, bbox[2]+10, bbox[3]+10, fill="#E3F2FD", outline="#2196F3", width=2)
            self.c.tag_raise(text_id, bg_rect_id)
            
        if bg_rect_id is not None:
            self.objects.extend([bg_rect_id, text_id])
        else:
            self.objects.append(text_id)

    def create_mind_map(self, data):
        """Generates a Mind Map with collision-avoidance layout and a move handle."""
        import time
        import random
        # Create a unique group tag for this mind map
        group_id = int(time.time() * 1000)
        group_tag = f"yt_notes_group_{group_id}"
        
        # Center of view
        cx = self.c.canvasx(self.c.winfo_width()/2)
        cy = self.c.canvasy(self.c.winfo_height()/2)
        
        # 1. Main Title Node
        title = data.get("title", "Video Notes")
        title = self.clean_text_for_display(title)
        title_id = self.create_node(cx, cy, title, bg_color="#FFEB3B", font=("Arial", 14, "bold"), shape="oval", padding=20)
        
        # Initial tagging for the title node
        self.c.addtag_withtag("mindmap_node", title_id)
        self.c.addtag_withtag(group_tag, f"node_group_{title_id}")
        
        topics = data.get("topics", [])
        if not topics: return
        
        # --- PHASE 1: Create Topic Nodes (First Pass - Measurement) ---
        topic_nodes = []
        for topic in topics:
            name = topic.get("name", "Topic")
            name = self.clean_text_for_display(name)
            # Create at temp location to measure
            tid = self.create_node(cx, cy, name, bg_color="#BBDEFB", font=("Arial", 12, "bold"), shape="rectangle", padding=15)
            self.c.addtag_withtag("mindmap_node", tid)
            self.c.addtag_withtag(group_tag, f"node_group_{tid}")
            
            bbox = self.c.bbox(tid)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            topic_nodes.append({'id': tid, 'w': w, 'h': h, 'data': topic, 'angle': 0})

        # --- PHASE 2: Calculate Topic Placement ---
        total_width = sum(t['w'] for t in topic_nodes)
        min_circumference = total_width * 3.5 # Increased spacing
        min_radius = max(450, min_circumference / (2 * math.pi))
        
        angle_step = 2 * math.pi / len(topic_nodes)
        
        for i, node in enumerate(topic_nodes):
            angle = i * angle_step
            node['angle'] = angle
            tx = cx + min_radius * math.cos(angle)
            ty = cy + min_radius * math.sin(angle)
            
            # Move to position
            self.move_node_center(node['id'], tx, ty)
            
            # Connect to Center and tag the line
            line_id = self.connect_nodes(title_id, node['id'], color="#90CAF9", width=3)
            if line_id: self.c.addtag_withtag(group_tag, line_id)
            
            # --- PHASE 3: Detail Nodes (Staggered Layout) ---
            details = node['data'].get("details", [])
            if not details: continue
            
            # Place details for this topic
            parent_id = node['id']
            base_detail_radius = 220 # Distance from topic increased
            
            # Staggered offsets strategy - spread out details more aggressively
            num_details = len(details)
            angle_spread = math.radians(120) # 120 degree spread for details
            
            start_angle = angle - (angle_spread / 2)
            detail_angle_step = angle_spread / (num_details - 1) if num_details > 1 else 0

            for j, detail_text in enumerate(details):
                # Clean text
                detail_text = self.clean_text_for_display(detail_text)
                
                # Create Node (slightly wider to fit text better)
                did = self.create_node(cx, cy, detail_text, bg_color="#FFFFFF", font=("Arial", 10), shape="rectangle", width_limit=220)
                self.c.addtag_withtag("mindmap_node", did)
                self.c.addtag_withtag(group_tag, f"node_group_{did}")
                
                placed = False
                current_dist = base_detail_radius
                d_angle = start_angle + (j * detail_angle_step) if num_details > 1 else angle
                
                # Collision resolution loop
                for attempt in range(25): # Increased attempts
                    dx = tx + current_dist * math.cos(d_angle)
                    dy = ty + current_dist * math.sin(d_angle)
                    
                    # Move to test
                    self.move_node_center(did, dx, dy)
                    
                    # Check Collision (with buffer)
                    if not self.check_node_collision(did, buffer=30): # increased buffer
                        placed = True
                        break
                    else:
                        # Collision!
                        # Strategy: Push further out significantly
                        current_dist += 60
                        # Slight jitter to break symmetrical overlaps
                        d_angle += random.uniform(-0.1, 0.1)
                
                # Connect and tag the line
                line_id = self.connect_nodes(parent_id, did, color="#E0E0E0", width=2)
                if line_id: self.c.addtag_withtag(group_tag, line_id)

        # --- PHASE 4: Add Figure Handle ---
        self.c.update_idletasks()
        total_bbox = self.c.bbox(group_tag)
        if total_bbox:
            handle_x = (total_bbox[0] + total_bbox[2]) / 2
            handle_y = total_bbox[3] + 40
            
            clean_title = title.rstrip(":").strip()
            handle_id = self.c.create_text(handle_x, handle_y, text=f"Fig: {clean_title}", 
                                         font=("Arial", 10, "bold italic"), fill="gray", tags=(group_tag, "flowchart_handle"))
            
            # Make bg for easier clicking
            h_bbox = self.c.bbox(handle_id)
            if h_bbox:
                bg_id = self.c.create_rectangle(h_bbox[0]-5, h_bbox[1]-2, h_bbox[2]+5, h_bbox[3]+2, 
                                               fill="#F5F5F5", outline="gray", tags=(group_tag, "flowchart_handle_bg"))
                self.c.tag_lower(bg_id, handle_id)
                self.objects.extend([bg_id, handle_id])

    def clean_text_for_display(self, text):
        """Removes markdown artifacts like **bold** markers."""
        if not text: return ""
        # Remove bold/italic markers
        text = text.replace("**", "").replace("*", "")
        # Remove hashtags if used for headers
        text = text.replace("##", "").replace("#", "")
        return text.strip()

    def move_node_center(self, item_id, cx, cy):
        """Moves a node (group) so its center is at (cx, cy)."""
        tags = self.c.gettags(item_id)
        group_tag = next((t for t in tags if t.startswith("node_group_")), None)
        
        if not group_tag:
            target_ids = [item_id]
            bbox = self.c.bbox(item_id)
        else:
            target_ids = self.c.find_withtag(group_tag)
            bbox = self.c.bbox(group_tag)
            
        if not bbox: return
        
        current_cx = (bbox[0] + bbox[2]) / 2
        current_cy = (bbox[1] + bbox[3]) / 2
        
        dx = cx - current_cx
        dy = cy - current_cy
        
        for tid in target_ids:
            self.c.move(tid, dx, dy)

    def check_node_collision(self, item_id, buffer=10):
        """Checks if item_id overlaps with other mindmap nodes."""
        tags = self.c.gettags(item_id)
        group_tag = next((t for t in tags if t.startswith("node_group_")), None)
        
        if group_tag:
            bbox = self.c.bbox(group_tag)
            my_items = set(self.c.find_withtag(group_tag))
        else:
            bbox = self.c.bbox(item_id)
            my_items = {item_id}
            
        if not bbox: return False
        
        x1, y1, x2, y2 = bbox
        search_box = (x1-buffer, y1-buffer, x2+buffer, y2+buffer)
        
        overlaps = self.c.find_overlapping(*search_box)
        
        for oid in overlaps:
            if oid in my_items: continue
            
            otags = self.c.gettags(oid)
            # Check if overlapping item is a node part
            if "mindmap_node" in otags or any(t.startswith("node_group_") for t in otags):
                return True
                
        return False

    def draw_native_graphviz(self, data, title="Generated Flowchart", push_undo=True):
        """Draws Graphviz JSON output natively on the Tkinter canvas."""
        created_ids = []
        
        # Unique group for this entire flowchart
        if not hasattr(self, 'group_counter'): self.group_counter = 0
        self.group_counter += 1
        flowchart_group_tag = f"flowchart_group_{self.group_counter}"
        self.groups[flowchart_group_tag] = []
        
        bb_str = data.get('bb', '0,0,1000,1000')
        parts = bb_str.split(',')
        if len(parts) >= 4:
            max_y = float(parts[3])
        else:
            max_y = 1000.0
            
        try:
            view_w = self.c.winfo_width() / 2
            view_h = self.c.winfo_height() / 2
            
            GRAPH_SCALE = 1.0
            
            base_x = self.c.canvasx(view_w) - (float(parts[2]) / 2) * GRAPH_SCALE
            base_y = self.c.canvasy(view_h) - (max_y / 2) * GRAPH_SCALE
        except:
            GRAPH_SCALE = 1.0
            base_x, base_y = 100, 100
            
        # 1. Draw Edges
        temp_edges = []
        for edge in data.get('edges', []):
            pos_str = edge.get('pos', '')
            if not pos_str: continue
            
            points = []
            tokens = pos_str.split(' ')
            for token in tokens:
                if token.startswith('e,') or token.startswith('s,'):
                    continue
                coords = token.split(',')
                if len(coords) >= 2:
                    try:
                        px = base_x + float(coords[0]) * GRAPH_SCALE
                        py = base_y + max_y * GRAPH_SCALE - (float(coords[1]) * GRAPH_SCALE)
                        points.extend([px, py])
                    except ValueError: pass
                        
            if len(points) >= 4:
                line_id = self.c.create_line(*points, smooth=True, arrow=tk.LAST, fill="gray", width=2, 
                                            tags=("object", "line", "flowchart_edge", flowchart_group_tag))
                self.objects.append(line_id)
                created_ids.append(line_id)
                self.groups[flowchart_group_tag].append(line_id)
                temp_edges.append({'id': line_id, 'tail': edge.get('tail'), 'head': edge.get('head')})

        # 2. Draw Nodes
        node_ids = {}
        for node in data.get('objects', []):
            pt = node.get('pos', '0,0').split(',')
            # Graphviz gives inverted Y coords
            x = base_x + float(pt[0]) * GRAPH_SCALE
            y = base_y + max_y * GRAPH_SCALE - (float(pt[1]) * GRAPH_SCALE)
            
            label = node.get('label', '')
            if label == '\\N': label = node.get('name', '')
            label = str(label).replace('\\n', '\n')
            
            shape = node.get('shape', 'rectangle')
            fill_color = "white"
            
            # Extract color from graphviz _draw_ ops
            for draw_op in node.get('_draw_', []):
                if draw_op.get('op') == 'C':
                    fill_color = draw_op.get('color', fill_color)
            
            # Map graphviz shapes to tkinter rendering in create_node
            if shape in ('box', 'rectangle', 'flowchart_box'):
                shape = 'rectangle'
            elif shape in ('diamond', 'decision'):
                shape = 'diamond'
            elif shape in ('circle', 'oval', 'ellipse'):
                shape = 'oval'
            else:
                shape = 'rectangle' # Fallback
            
            text_id = self.create_node(x, y, text=label, bg_color=fill_color, shape=shape, padding=10, record_undo=False)
            # Add basic tags so double clicking it works naturally
            self.c.itemconfig(text_id, tags=self.c.gettags(text_id) + ("object", "text", "flowchart_text", flowchart_group_tag))
            node_ids[node.get('_gvid')] = text_id
            
            # Find the group and all its components to add to created_ids
            group_tag = f"node_group_{text_id}"
            member_ids = self.c.find_withtag(group_tag)
            for member in member_ids:
                created_ids.append(member)
                self.groups[flowchart_group_tag].append(member)
                # Ensure each part also has the flowchart_group_tag
                self.c.addtag_withtag(flowchart_group_tag, member)

        # 3. Create Flowchart Move Handle (Title at the bottom)
        try:
            self.c.update_idletasks() # Refresh positions
            total_bbox = self.c.bbox(flowchart_group_tag)
            if total_bbox:
                handle_x = (total_bbox[0] + total_bbox[2]) / 2
                handle_y = total_bbox[3] + 20
                
                # Clean title to avoid redundant colons
                clean_title = title.rstrip(":").strip()
                handle_id = self.c.create_text(handle_x, handle_y, text=f"Fig: {clean_title}", 
                                               fill="black", font=("Arial", 9, "italic"),
                                               tags=("object", "text", "flowchart_handle", flowchart_group_tag))
                # Background for handle
                h_bbox = self.c.bbox(handle_id)
                if h_bbox:
                    padding_x, padding_y = 15, 5
                    h_bg = self.c.create_rectangle(h_bbox[0]-padding_x, h_bbox[1]-padding_y, 
                                                   h_bbox[2]+padding_x, h_bbox[3]+padding_y,
                                                   fill="white", outline="black", width=1,
                                                   tags=("object", "shape", "flowchart_handle_bg", flowchart_group_tag))
                    self.c.tag_lower(h_bg, handle_id)
                    created_ids.extend([handle_id, h_bg])
                    self.groups[flowchart_group_tag].extend([handle_id, h_bg])
                    self.objects.extend([handle_id, h_bg])
        except Exception as e:
            print(f"Error creating flowchart handle: {e}")

        # 4. Register connections
        if hasattr(self, 'connections') and node_ids:
            for te in temp_edges:
                start_node = node_ids.get(te['tail'])
                end_node = node_ids.get(te['head'])
                if start_node and end_node:
                    self.connections[te['id']] = {'start': start_node, 'end': end_node}
                    self.c.addtag_withtag('connection_line', te['id'])

        if push_undo:
            self.undo_stack.append(('create_flowchart', created_ids, data))
            self.redo_stack.clear()
            
        self.update_scrollregion()
        self.update_minimap()
        return created_ids

    def generate_ideas(self):
        """Generates related ideas for selected text object."""
        target = None
        if self.selected_objects:
            # Prefer Text object
            for obj in reversed(self.selected_objects):
                if self.c.type(obj) == 'text':
                    target = obj
                    break
        
        if not target:
            # Fallback: Ask user for topic
            topic = self.modern_askstring("Generate Ideas", "Enter topic:")
            if not topic: return
            
            # Create a center text node for them
            x, y = self.c.canvasx(self.root.winfo_width()/2), self.c.canvasy(self.root.winfo_height()/2)
            target = self.c.create_text(x, y, text=topic, font=("Arial", 14, "bold"), tags=("object", "text"))
            self.objects.append(target)
            self.select_object(x, y, None) # Use dummy event or manual select logic?
            # select_object expects event with x,y. Let's manual select.
            self.selected_objects.append(target)
        else:
            topic = self.c.itemcget(target, 'text')
            
        prompt = f"Brainstorm exactly 5 very short ideas (max 5 words) about '{topic}'. Return ONLY a bulleted list."
        response_text = self.generate_ai_content(prompt)
        ideas = []
        if response_text:
            for line in response_text.split('\n'):
                clean_line = line.strip().lstrip('-*Ã¢â‚¬Â¢1234567890. ')
                if clean_line:
                    ideas.append(clean_line)
        
        # Display ideas around the topic (Mind Map style)
        cx, cy = self.c.coords(target)
        import math
        radius = 150
        angle_step = 360 / max(1, len(ideas))
        
        for i, idea in enumerate(ideas):
            angle = math.radians(i * angle_step)
            nx = cx + radius * math.cos(angle)
            ny = cy + radius * math.sin(angle)
            
            # Create node
            node = self.c.create_text(nx, ny, text=idea, font=("Arial", 12), tags=("object", "text"))
            self.objects.append(node)
            
            # Connect
            line_id = self.c.create_line(cx, cy, nx, ny, fill="gray", dash=(4, 2), width=max(1, int(1 * self.scale)))
            self.objects.append(line_id)
            self.shape_base_widths[line_id] = 1 # Base width for Mind Map connectors


    def extract_text_from_selection(self):
        """OCR on selected image."""
        target = None
        if self.selected_objects:
             for obj in reversed(self.selected_objects):
                if self.c.type(obj) == 'image':
                    target = obj
                    break
        
        if not target:
            messagebox.showwarning("OCR", "Please select an image first.")
            return

        # Get file path
        if target in self.image_files:
            path = self.image_files[target]
            try:
                text = textfromimage.extract_text(path)
                if text and text.strip():
                    # Create text object
                    x, y = self.c.coords(target)
                    self.c.create_text(x + 20, y + 20, text=text, anchor=tk.NW, font=("Arial", 12), fill="black", width=300, tags=("object", "text"))
                    messagebox.showinfo("OCR Success", "Text extracted and added to canvas.")
                else:
                    messagebox.showinfo("OCR", "No text found.")
            except Exception as e:
                messagebox.showerror("OCR Error", str(e))
        else:
             messagebox.showerror("Error", "Could not find source file for image.")


    def extract_ink_text(self, pil_image):
        """Uses a local Flask Backend with OpenCV and Tesseract to extract handwriting."""
        print("Extracting ink to text via local Flask backend...")
        import io
        import base64
        import requests
        
        try:
            # 1. Convert PIL image to Base64
            buffered = io.BytesIO()
            pil_image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            # 2. Fire POST request to local Flask server
            url = "http://127.0.0.1:5000/ocr"
            payload = {"image": img_str}
            
            # Use high timeout (120s) because massive TrOCR deep learning models on CPU are computationally intensive
            response = requests.post(url, json=payload, timeout=120)
            
            if response.status_code == 200:
                data = response.json()
                if 'text' in data:
                    return data['text']
                else:
                    messagebox.showerror("OCR Error", "No text key in response.")
                    return ""
            else:
                error_msg = response.json().get('error', 'Unknown Error')
                messagebox.showerror("OCR Error", f"Server returned {response.status_code}: {error_msg}")
                return ""
                
        except requests.exceptions.ConnectionError:
            messagebox.showerror("Connection Error", "Could not connect to OCR backend. Is flask_ocr_server.py running?")
            return ""
        except Exception as e:
            print(f"Ink-to-Text Local Error: {e}")
            messagebox.showerror("Error", f"Failed to extract text: {e}")
            return ""

    def generate_flowchart(self):
        """Generates flowchart from text description."""
        text = self.modern_askstring("Magic Flowchart", "Describe the process (steps separated by lines):")
        if not text: return
        
        try:
            # restructure text using AI
            structured_text = self.restructure_text_for_flowchart(text)
            print(f"DEBUG: Structured text:\n{structured_text}")

            # 1. Parse
            parsed = flowchart_utils.parse_text(structured_text)
            
            # 2. Generate Graphviz
            # Need to import Digraph locally or assume available
            try:
                from graphviz import Digraph
            except ImportError:
                messagebox.showerror("Error", "Graphviz library not found. pip install graphviz")
                return

            # Render at 72 DPI (Standard Graphviz default)
            dot = Digraph(comment='Flowchart', graph_attr={'dpi': '72'})
            flowchart_utils.add_sequential_edges(dot, parsed)
            
            # 3. Render natively
            output_path = "temp_magic_flowchart"
            dot.render(output_path, format='json', cleanup=True)
            json_path = output_path + ".json"
            
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Extract title from the first line of the structured text
                title = "AI Flowchart"
                lines = [l for l in structured_text.strip().split('\n') if l.strip()]
                if lines:
                    title = lines[0].strip().lstrip('-*# ').rstrip(':')
                    
                self.draw_native_graphviz(data, title=title)
            else:
                 messagebox.showerror("Error", "Failed to generate flowchart data.")
                 
        except Exception as e:
            print(f"Flowchart Generation Error: {e}")
            messagebox.showerror("Error", f"Failed to generate flowchart: {e}")
            if hasattr(self, 'update_scrollregion'):
                self.update_scrollregion()
            if hasattr(self, 'update_minimap'):
                self.update_minimap()
