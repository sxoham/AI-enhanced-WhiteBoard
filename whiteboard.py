import json
import os
import warnings
# Suppress Wikipedia/BS4 warning
warnings.filterwarnings("ignore", message="No parser was explicitly specified")
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog, PhotoImage
import time
from tkinter.colorchooser import askcolor
from tkinter import font as tkfont
from tkinter.filedialog import asksaveasfilename, askopenfilename
import math

from PIL import ImageTk, Image, ImageGrab, ImageDraw
Image.MAX_IMAGE_PIXELS = None # Disable decompression bomb safety for large flowcharts
import threading

# Packages for AI features
# from ideageneration import generate_ideas # REMOVED: Using Neural Network only
from textfromimage import extract_text
import voiceassistant
from dotenv import load_dotenv
import google.generativeai as genai
import flowchart_utils
import templates
import youtube_utils

#packages for voice assistant
import fitz # PyMuPDF


from ui_components import RoundedFrame, ToolTip, RoundedButton, ColorPalette
from ai_tools_mixin import AIToolsMixin



class Whiteboard(AIToolsMixin):
    def __init__(self, root):
        self.root = root
        self.root.title("Whiteboard")
        self.root.state('zoomed') # Open maximized by default

        self.color_fg = 'black'
        self.color_bg = 'white'
        self.fill_color = 'white'  # Default fill color
        self.penwidth = 5
        self.eraser_on = False
        self.active_button = None
        self.old_x = None
        self.old_y = None
        self.shape_base_widths = {} # Track base widths for zoom scaling
        self.text_base_sizes = {} # Map ID -> (font_family, base_size) for zooming logic
        self.text_base_widths = {} # Map ID -> width for zooming logic
        self.shape = 'line'
        self.shape_id = None
        
        # Presentation Mode
        self.is_presentation_mode = False
        self.laser_id = None

        self.selected_objects = []  # List of selected objects
        self.selected_object_colors = {} # Map ID -> Original Color
        self.objects = []  # List to keep track of objects
        self.image_files = {}  # Dictionary to map image IDs to file paths
        self.image_metadata = {} # Dictionary to map image IDs to metadata
        self.image_base_sizes = {} # Map ID -> (width, height) for zooming logic
        self.connections = {} # Map line_id -> {'start': obj_id, 'end': obj_id}

        self.undo_stack = []
        self.redo_stack = []
        self.shape = 'brush'  # Default tool is Pen/Brush

        # Image insertion
        self.image = None
        self.image_id = None
        self.dragging = False
        self.resizing = False
        self.offset_x = 0
        self.offset_y = 0
        self.resize_start_state = None

        self.current_font = "Arial"  # Default font

        self.font_size = 24  # Default font size
        self.current_scale = 1.0 # Default Zoom Scale

        # for voice assistant
        self.actions = []
        self.current_filename = None
        self.voice_assistant_on = False
        voiceassistant.init_voice_system(self) 
        self.current_y = 20  # Starting vertical position for text
        self.smart_connect_on = True # Default to on
        
        # Grid & Snap
        self.grid_on = False
        self.snap_on = False
        self.grid_size = 20

        # Auto-Shape & Auto-Text
        self.auto_shape_on = False
        self.auto_ink_to_text_on = False

        self.root.bind("<Control-t>", lambda e: self.speak_selected_text())
        self.root.bind("<Control-T>", lambda e: self.speak_selected_text())
        self.current_stroke_points = []
        self.current_stroke_ids = []

        # UI State for Mini-Map & Contextual Bar
        self.minimap_scale = 0.1 # Scale factor for minimap
        self.property_bar = None
        self.scale = 1.0
        
        # Grouping
        self.groups = {} # GroupID -> List of ItemIDs
        self.group_counter = 0

        self.poly_points = []
        self.poly_line_id = None # Temporary line ID for preview
        
        # Pen Settings
        self.penwidth = 5
        self.eraser_size = 20
        self.pen_settings_frame = None
        self.vector_smooth_on = False # AI Vector Smoothing toggle


        # Clipboard & Shortcuts
        self.clipboard = []
        self.hints_visible = False
        self.hint_labels = []

        # Load images and resize them
        self.pen_color_img = self.load_icon("pen_color.png")
        self.canvas_color_img = self.load_icon("canvas_color.png")
        self.color_fill_img = self.load_icon("bucket.png")
        self.Line_img = self.load_icon("Line.png")
        self.rectangle_img = self.load_icon("rectangle.png")
        self.oval_img = self.load_icon("oval.png")
        self.polygon_img = self.load_icon("polygon.png")
        self.arrow_img = self.load_icon("arrow.png")
        self.eraser_img = self.load_icon("eraser.png")
        self.text_img = self.load_icon("A_text.png")
        self.sticky_img = self.load_icon("Stickynotes.png")
        self.select_img = self.load_icon("selection.png")
        self.insert_image_img = self.load_icon("insert_image.png")
        self.undo_img = self.load_icon("undo.png")
        self.redo_img = self.load_icon("redo.png")
        self.voice_img= self.load_icon("voice.png")
        self.mute_button = self.load_icon("mute_button.png")
        self.clear_img = self.load_icon("clear.png")
        self.bucket_img = self.load_icon("bucket.png")
        self.export_img = self.load_icon("export.png")
        
        # New AI Icons
        self.ai_menu_img = self.load_icon("ai.png")
        self.shapes_menu_img = self.load_icon("shapes.png")
        self.shapes_custom_img = self.load_icon("shapes_custom.png")
        self.triangle_img = self.load_icon("triangle.png")
        self.diamond_img = self.load_icon("diamond.png")
        
        self.idea_gen_img = self.load_icon("idea-generation.png")
        self.info_gen_img = self.load_icon("Generate-information.png")
        self.ocr_img = self.load_icon("Ink_to_Text.png") # Updated to use provided icon
        self.flowchart_img = self.load_icon("flow-chart.png")
        self.magic_flowchart_img = self.load_icon("magic-flow-chart.png")
        self.pencil_img = self.load_icon("pencil.png")
        self.youtube_img = self.load_icon("youtube.png")
        self.color_picker_img = self.load_icon("color-picker.png")
        self.pdf_img = self.load_icon("pdf.png")
        self.laser_img = self.load_icon("laser.png")
        self.highlighter_img = self.load_icon("highlighter.png", size=(24, 24))
        self.save_img = self.load_icon("save.png")
        self.load_img = self.load_icon("open.png")
        self.grid_img = self.load_icon("grid.png")
        self.presentation_img = self.load_icon("presentation.png")
        self.theme_img = self.load_icon("theme.png")
        self.exit_img = self.load_icon("exit.png")
        self.tts_img = self.load_icon("text-to-speech.png") # Updated to use provided icon
        
        # Additional Menu Icons
        self.snap_menu_img = self.load_icon("grid.png")
        self.smooth_menu_img = self.load_icon("ai.png")
        self.mindmap_menu_img = self.load_icon("flow-chart.png")
        self.smart_connect_menu_img = self.load_icon("Line.png")
        self.auto_shape_menu_img = self.load_icon("shapes.png")
        self.auto_ink_to_text_menu_img = self.load_icon("A_text.png") # Updated
        
        self.tool_buttons = {} # Map tool name -> button widget
        
        # Hand Tool Image Fallback
        self.hand_img = self.load_icon("hand.png", size=(24, 24))
        if not self.hand_img:
             # Fallback
             self.hand_img = ImageTk.PhotoImage(Image.new("RGBA", (24, 24), (0, 0, 0, 0)))

        # --- THEME CONFIGURATION ---
        self.light_theme = {
            "bg_primary": "#F0F0F0",    # Light Grey
            "bg_secondary": "#E0E0E0",  # Slightly Darker Grey
            "accent": "#AED6F1",        # Light Blue
            "text_color": "#000000",    # Black Text
            "btn_bg": "#FFFFFF",        # White Buttons
            "btn_hover": "#D5D8DC",     # Grey Hover
            "btn_active": "#3498DB",    # Darker Blue Active
            "canvas_bg": "#FFFFFF",     # White Canvas
            "divider_color": "#CCCCCC", # Light Divider
            "scale_trough": "#FFFFFF"   # Light Trough
        }
        
        self.dark_theme = {
            "bg_primary": "#1E1E1E",    # Main App Background
            "bg_secondary": "#252526",  # Panels / Toolbar
            "accent": "#007ACC",        # Active Blue (VS Code style)
            "text_color": "#CCCCCC",    # Light Grey Text
            "btn_bg": "#333333",        # Dark Button Background
            "btn_hover": "#444444",     # Slightly Lighter Hover
            "btn_active": "#005f9e",    # Active state
            "canvas_bg": "#1E1E1E",     # Canvas Background matching app
            "divider_color": "#555555", # Dark Divider
            "scale_trough": "#2C2C2C"   # Dark Trough
        }
        
        # Default to Light
        self.theme = self.light_theme
        self.tool_buttons = {} # Store tool buttons for state management
        
        # Configure root background
        self.root.configure(bg=self.theme["bg_primary"])

        # --- CANVAS SETUP (Master) ---
        self.c = tk.Canvas(self.root, bg=self.theme["canvas_bg"], width=800, height=600, highlightthickness=0)
        self.c.pack(fill=tk.BOTH, expand=True)

        # Bindings
        self.c.bind('<Button-1>', self.on_button_press)
        self.c.bind('<B1-Motion>', self.paint)
        self.c.bind('<ButtonRelease-1>', self.on_button_release)
        self.c.bind('<Double-Button-1>', self.on_double_click)

        # Middle Mouse Pan
        self.c.bind('<ButtonPress-2>', self.start_pan)
        self.c.bind('<B2-Motion>', self.pan)
        self.c.bind('<ButtonRelease-2>', self.end_pan)
        
        # Spacebar Pan
        self.root.bind('<KeyPress-space>', self.on_space_down)
        self.root.bind('<KeyRelease-space>', self.on_space_up)

        # Context Menu
        self.c.bind("<Button-3>", self.show_context_menu)
        
        self.c.bind("<Motion>", self.on_mouse_move)
        
        self.c.bind("<Configure>", self.on_canvas_configure)
        
        # Zoom, Pan & Group Bindings
        self.root.bind("<Control-plus>", lambda e: self.zoom_in())
        self.root.bind("<Control-minus>", lambda e: self.zoom_out())
        self.root.bind("<Control-equal>", lambda e: self.zoom_in()) # For keyboards without number pad
        self.root.bind("<Control-MouseWheel>", self.zoom_wheel) # Mouse wheel zoom
        
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app) # Confirmation on window close
        
        self.bind_shortcuts()

        # --- FLOATING UI ---
        self.create_floating_interface()

        # Legacy Palette instantiation (for logic reuse, but not packed)
        self.palette = ColorPalette(self.root, self)

    def bind_shortcuts(self):
        """Binds keyboard shortcuts for tools and actions."""
        # Tools
        self.root.bind('v', lambda e: self.deselect_tool()) # V for Select/Move
        self.root.bind('s', lambda e: self.deselect_tool()) # S for Select
        self.root.bind('b', lambda e: self.select_tool('brush')) # B for Brush
        self.root.bind('l', lambda e: self.select_tool('line')) # L for Line
        self.root.bind('r', lambda e: self.select_tool('rectangle')) # R for Rectangle
        self.root.bind('o', lambda e: self.select_tool('oval')) # O for Oval
        self.root.bind('p', lambda e: self.select_tool('polygon')) # P for Polygon
        self.root.bind('e', lambda e: self.activate_eraser()) # E for Eraser
        self.root.bind('t', lambda e: self.add_text()) # T for Text
        self.root.bind('i', lambda e: self.add_image()) # I for Image
        self.root.bind('h', lambda e: self.select_tool('hand')) # H for Hand
        self.root.bind('f', lambda e: self.select_tool('bucket')) # F for Fill/Bucket
        self.root.bind('c', lambda e: self.toggle_palette_popup(e)) # C for Color
        self.root.bind('l', lambda e: self.select_tool('highlighter')) # L for hiLighter
        self.root.bind('+', lambda e: self.show_add_menu()) # + for Add
        
        # Actions
        self.root.bind('<Control-z>', lambda e: self.undo())
        self.root.bind('<Control-y>', lambda e: self.redo())
        self.root.bind('<Delete>', lambda e: self.delete_selected())
        self.root.bind('<BackSpace>', lambda e: self.delete_selected())
        self.root.bind('<Control-s>', lambda e: self.save_project())
        self.root.bind('<Escape>', lambda e: self.cancel_action(e)) # Esc to cancel drawing/selection
        
        # Grouping Shortcuts
        self.root.bind("<Control-g>", self.group_selected)
        
        # Layer Management Shortcuts (Ctrl+Up / Ctrl+Down)
        self.root.bind('<Control-Up>', lambda e: self.layer_bring_to_front())
        self.root.bind('<Control-Down>', lambda e: self.layer_send_to_back())
        self.root.bind('<Control-bracketright>', lambda e: self.layer_bring_forward())
        self.root.bind('<Control-bracketleft>', lambda e: self.layer_send_backward())
        
        # Copy / Paste
        self.root.bind('<Control-c>', self.copy_selection)
        self.root.bind('<Control-v>', self.paste_selection)
        
        # Alt Key Hints
        self.root.bind('<KeyRelease-Alt_L>', self.toggle_key_hints)
        self.root.bind('<KeyRelease-Alt_R>', self.toggle_key_hints)
        
        # Hide hints on interaction
        self.root.bind('<Button-1>', self.hide_key_hints, add='+')
        self.root.bind('<Key>', self.hide_key_hints, add='+')
        
        # Right-click context menu for layer management
        self.c.bind('<Button-3>', self.show_canvas_context_menu)
        
        self.c.bind("<Configure>", self.on_canvas_configure)

    def load_icon(self, filename, size=(24, 24)):
        base_path = os.path.dirname(__file__)
        try:
            path = os.path.join(base_path, "Icons", filename)
            if not os.path.exists(path):
                # Try fallback location if needed, or just return default
                return None
            img = Image.open(path).resize(size, Image.LANCZOS)
            return ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"Error loading icon {filename}: {e}")
            return None

    def update_voice_btn_icon(self):
        """Swaps the voice assistant button icon dynamically."""
        if hasattr(self, 'voice_btn'):
            if getattr(self, 'voice_assistant_on', False):
                self.voice_btn.image = self.mute_button
            else:
                self.voice_btn.image = self.voice_img
            # Redraw custom RoundedButton class to register new image
            self.voice_btn.draw()
            
    def create_floating_interface(self):
        """Creates the new Microsoft Whiteboard-style floating UI."""
        
        # 1. Bottom Dock (Centered) - Rounded Frame
        dock_width = 520 # Increased to accommodate new AI items
        dock_height = 60
        
        # Container for the dock
        self.bottom_dock = RoundedFrame(self.root, width=dock_width, height=dock_height, 
                                        corner_radius=25, color=self.theme["bg_secondary"], bg_color=self.theme["canvas_bg"],
                                        shadow_offset=5)
        self.bottom_dock.place(relx=0.5, rely=0.95, anchor=tk.S)

        # Internal Frame for buttons (Transparent-ish) to pack buttons easily
        # REMOVED dock_content Frame to avoid rectangular clipping.
        # Placing buttons directly on the Canvas (bottom_dock).
        
        # We need to manually layout buttons now since we can't pack into a transparent frame.
        self.dock_items = [] # Store items to place
        
        # 1. Collect all buttons/separators first
        # Select
        self.dock_items.append(('btn', self.select_img, "Select", 'select'))
        self.dock_items.append(('btn', self.hand_img, "Pan", 'hand'))
        
        # Sep
        self.dock_items.append(('sep',))
        
        self.dock_items.append(('btn', self.pencil_img, "Pen", 'brush'))
        self.dock_items.append(('btn', self.Line_img, "Line", 'line'))
        self.dock_items.append(('btn', self.highlighter_img, "Highlight", 'highlighter'))
        self.dock_items.append(('btn', self.eraser_img, "Eraser", 'eraser'))
        self.dock_items.append(('btn', self.bucket_img, "Fill", 'bucket'))
        self.dock_items.append(('btn', self.text_img, "Text", 'text'))
        
        # Voice Assistant Button
        self.dock_items.append(('custom_btn', self.voice_img if not getattr(self, 'voice_assistant_on', False) else self.mute_button, lambda: voiceassistant.toggle_voice_assistant(self), 'voice'))
        
        # New: Text to Speech and Ink to Text directly on dock
        self.dock_items.append(('custom_btn', getattr(self, 'tts_img', self.voice_img), self.speak_selected_text, 'tts'))
        self.dock_items.append(('custom_btn', getattr(self, 'ocr_img', None), self.execute_text_extraction, 'ocr'))

        # New "Ask AI" Button
        if not hasattr(self, 'ai_img'):
             base_path = os.path.dirname(__file__) or "."
             self.ai_img = self.load_icon("ai.png", size=(24, 24))
        self.dock_items.append(('custom_btn', self.ai_img, self.show_ai_dialog))

        self.dock_items.append(('btn', self.clear_img, "Clear", 'clear'))
        
        # Sep
        self.dock_items.append(('sep',))
        
        # Add (Custom logic)
        board_path = os.path.dirname(__file__) or "."
        if not hasattr(self, 'add_img'):
             self.add_img = ImageTk.PhotoImage(Image.open(os.path.join(board_path, "Icons", "add.png")).resize((24, 24), Image.LANCZOS))
        self.dock_items.append(('custom_btn', self.add_img, self.show_add_menu))
        
        # Colors (Custom widgets)
        self.dock_items.append(('color_btn',))
        self.dock_items.append(('custom_btn', self.canvas_color_img, self.change_bg, 'canvas_color'))

        # 2. Place items
        current_x = 20
        center_y = (dock_height // 2) - 3
        
        # Dock Color for Transparency
        dock_bg = self.theme["bg_secondary"] # Match dock body
        # Ensure dock_bg is passed to buttons so they match the rounded dock
        
        for item in self.dock_items:
            kind = item[0]
            
            if kind == 'btn':
                _, img, tooltip, name = item
                # cmd logic from create_dock_btn
                cmd = lambda t=name: self.select_tool(t)
                if name == 'eraser': cmd = self.toggle_eraser
                elif name == 'clear': cmd = self.clear
                
                btn = RoundedButton(self.bottom_dock, width=40, height=40, image=img, 
                                    command=cmd, corner_radius=20, 
                                    bg_hover=self.theme["btn_hover"], # Use themed hover
                                    transparent_on=dock_bg, tooltip=tooltip)
                self.bottom_dock.create_window(current_x, center_y, window=btn, anchor=tk.W)
                current_x += 44 # 40 + padding
                
                # Double-click bindings for settings
                if name == 'brush':
                    btn.bind('<Double-Button-1>', self.show_brush_settings)
                elif name == 'eraser':
                    btn.bind('<Double-Button-1>', self.show_eraser_settings)
                elif name == 'bucket':
                     btn.bind('<Double-Button-1>', self.show_fill_settings)
                elif name == 'text':
                     btn.bind('<Double-Button-1>', self.toggle_text_settings)
                
                if not hasattr(self, 'dock_buttons'): self.dock_buttons = []
                self.dock_buttons.append(btn)
                
                # Register for state updates
                self.tool_buttons[name] = btn
                
            elif kind == 'sep':
                # Draw a line on the canvas directly
                self.bottom_dock.create_line(current_x + 10, 15, current_x + 10, dock_height-15, fill=self.theme["divider_color"], width=1)
                current_x += 20
                
            elif kind == 'custom_btn':
                _, img, cmd, *extras = item
                
                tt_text = ""
                if extras and extras[0] == 'voice':
                     tt_text = "Voice Assistant"
                elif hasattr(self, 'add_img') and img == self.add_img:
                     tt_text = "Shapes & Media"
                elif hasattr(self, 'ai_img') and img == self.ai_img:
                     tt_text = "Ask AI"
                elif extras and extras[0] == 'pen_color':
                     tt_text = "Pen Color"
                elif extras and extras[0] == 'canvas_color':
                     tt_text = "Canvas Color"
                elif extras and extras[0] == 'tts':
                     tt_text = "Text to Speech"
                elif extras and extras[0] == 'ocr':
                     tt_text = "Ink to Text"

                btn = RoundedButton(self.bottom_dock, width=40, height=40, image=img, 
                                  command=cmd, corner_radius=20, 
                                  bg_hover=self.theme["btn_hover"],
                                  transparent_on=dock_bg, tooltip=tt_text)
                self.bottom_dock.create_window(current_x, center_y, window=btn, anchor=tk.W)
                current_x += 44
                
                # Assign specific button references for dynamic updates later
                if extras and extras[0] == 'voice':
                     self.voice_btn = btn
                elif not hasattr(self, 'add_btn') or self.add_img == img:
                     self.add_btn = btn
                
            elif kind == 'color_btn':
                # Color Picker Icon Button
                self.color_btn = RoundedButton(self.bottom_dock, width=40, height=40, image=self.color_picker_img, 
                                  command=self.toggle_palette_popup, corner_radius=20, 
                                  bg_hover=self.theme["btn_hover"],
                                  transparent_on=dock_bg, tooltip="Colors")
                self.bottom_dock.create_window(current_x, center_y, window=self.color_btn, anchor=tk.W)
                current_x += 44
                
        # Update dock width to fit content
        total_width = current_x + 20
        self.bottom_dock.configure(width=total_width)
        # Redraw background with new width
        self.bottom_dock.update_idletasks() # Ensure width is known
        self.bottom_dock._draw()
        
        # KEY FIX: Force re-centering after width change
        # Even though anchor is S, if width changes, the center point relative to relx=0.5 might need refresh?
        # Actually anchor=S means the SOUTH point is at 0.5, 0.95. Width shouldn't affect X centering.
        # However, tk.Canvas might need a nudge.
        self.bottom_dock.place(relx=0.5, rely=0.95, anchor=tk.S)
        
        
        # 2. Top Left Overlay (System) - REMOVED (Moved to Menu/Dock)
        # self.top_left_overlay = tk.Frame(self.root, bg="white", padx=5, pady=5, relief=tk.RAISED, borderwidth=1)
        # self.top_left_overlay.place(relx=0.01, rely=0.01, anchor=tk.NW)
        # self.create_overlay_btn(self.top_left_overlay, self.export_img, self.save_project) # Save
        
        # New Undo/Redo Stack (Left of Dock)
        # We need a separate frame/canvas for this vertical stack
        # Increased size again (70 width) for "slightly bigger"
        # Undo/Redo side-by-side
        stack_width = 140
        stack_height = 60
        
        # Load dark and light icons
        base_path = os.path.dirname(__file__)
        self.l_undo_img = self.load_icon("Lundo.png", size=(24, 24))
        self.d_undo_img = self.load_icon("Dundo.png", size=(24, 24))
        self.l_redo_img = self.load_icon("Lredo.png", size=(24, 24))
        self.d_redo_img = self.load_icon("Dredo.png", size=(24, 24))
        
        is_dark = self.theme.get("bg_primary") == "#1E1E1E"
        self.undo_img = self.d_undo_img if is_dark else self.l_undo_img
        self.redo_img = self.d_redo_img if is_dark else self.l_redo_img
        
        self.undo_redo_dock = RoundedFrame(self.root, width=stack_width, height=stack_height, 
                                           corner_radius=25, color=self.theme["bg_secondary"], bg_color=self.theme["canvas_bg"],
                                           shadow_offset=5)
        
        # Position it to the left of the main dock dynamically based on its width
        undo_x_offset = -(total_width // 2) - 20
        self.undo_redo_dock.place(relx=0.5, rely=0.95, x=undo_x_offset, anchor=tk.SE)  
        
        # Add Undo (Left)
        # Use processed img
        self.undo_btn_dock = RoundedButton(self.undo_redo_dock, width=40, height=40, image=self.undo_img, 
                                      command=self.undo, corner_radius=20, 
                                      bg_hover=self.theme["btn_hover"], transparent_on=dock_bg, tooltip="Undo")
        self.undo_redo_dock.create_window(25, 10, window=self.undo_btn_dock, anchor=tk.NW)

        # Add Redo (Right)
        self.redo_btn_dock = RoundedButton(self.undo_redo_dock, width=40, height=40, image=self.redo_img, 
                                      command=self.redo, corner_radius=20, 
                                      bg_hover=self.theme["btn_hover"], transparent_on=dock_bg, tooltip="Redo")
        self.undo_redo_dock.create_window(75, 10, window=self.redo_btn_dock, anchor=tk.NW)
        
        # 3. Main Menu (Right of Dock) - "Three Dots" style
        # We need a small dock for it
        # 3. Main Menu (Right of Dock) - "Three Dots" style
        # We need a small dock for it
        menu_dock_width = 60
        menu_dock_height = 60

        # Menu Dock (perfect circle)
        self.menu_dock = RoundedFrame(
            self.root,
            width=menu_dock_width,
            height=menu_dock_height,
            corner_radius=30,
            color=self.theme["bg_secondary"],
            bg_color=self.theme["canvas_bg"],
            shadow_offset=5
        )
        # Position it to the right of the main dock dynamically
        menu_x_offset = (total_width // 2) + 20
        self.menu_dock.place(relx=0.5, rely=0.95, x=menu_x_offset, anchor=tk.SW)

        # Menu Button Icon
        try:
            menu_icon_path = os.path.join(base_path, "Icons", "menu.png")
            self.menu_icon_photo = ImageTk.PhotoImage(
                Image.open(menu_icon_path).resize((24, 24), Image.LANCZOS)
            )
        except Exception as e:
            print(f"Error loading menu icon: {e}")
            self.menu_icon_photo = ImageTk.PhotoImage(
                Image.new("RGBA", (24, 24), (200, 200, 200, 255))
            )

        # Menu Button (NO rectangular background)
        self.menu_btn = RoundedButton(
            self.menu_dock,
            width=30,
            height=30,
            image=self.menu_icon_photo,
            command=self.show_main_menu,
            corner_radius=20,
            transparent_on=self.theme["bg_secondary"],
            bg_hover=self.theme["btn_hover"],
            tooltip="Menu"
        )

        # PERFECTLY center the button (prevents corner bleed)
        # Adjusting for shadow_offset=5 to visually center the icon
        self.menu_dock.create_window(
            (menu_dock_width - 5) // 2,
            (menu_dock_height - 5) // 2,
            window=self.menu_btn,
            anchor=tk.CENTER
        )

        # 4. Mini-Map (Bottom Right)
        self.minimap_frame = tk.Frame(self.root, bg=self.theme["bg_secondary"], highlightthickness=1, highlightbackground=self.theme["divider_color"])
        self.minimap_frame.place(relx=0.99, rely=0.95, anchor=tk.SE)
        
        # Minimap Canvas (ENLARGED)
        self.minimap = tk.Canvas(self.minimap_frame, width=220, height=150, bg=self.theme["bg_primary"], highlightthickness=0)
        self.minimap.pack(padx=2, pady=2)
        
        self.minimap.bind("<Button-1>", self.minimap_click)
        self.minimap.bind("<B1-Motion>", self.minimap_click)


    

        
    def toggle_popup(self, popup_attr, create_method, tool_key, offset_y):
        """Generic method to toggle tool setting popups matching Docker theme."""
        popup = getattr(self, popup_attr, None)
        if not popup:
            create_method()
            popup = getattr(self, popup_attr)
        
        if popup.winfo_viewable():
            popup.place_forget()
        else:
            btn = self.tool_buttons.get(tool_key)
            if btn:
                # Force width calculation
                self.root.update_idletasks()
                cx = btn.winfo_rootx() - self.root.winfo_rootx() + (btn.winfo_width() / 2)
                dock_y = self.bottom_dock.winfo_y()
                # Anchor S places it horizontally centered on cx, bottom aligned to dock_y - 12
                popup.place(x=cx, y=dock_y - 12, anchor=tk.S)
                tk.Misc.lift(popup)

    def toggle_pen_settings(self, event=None):
        """Shows/Hides the pen settings popup."""
        self.toggle_popup('pen_settings_frame', self.create_pen_settings_popup, 'brush', 70)

    def create_pen_settings_popup(self):
        """Creates the popup frame for pen settings styled as docker."""
        bg_main = self.theme["canvas_bg"] if hasattr(self, 'theme') else "#F3F3F3"
        bg_bar  = self.theme["bg_secondary"] if hasattr(self, 'theme') else "white"
        fg_text = self.theme.get("text_color", "black") if hasattr(self, 'theme') else "black"

        self.pen_settings_frame = RoundedFrame(self.root, width=180, height=110, corner_radius=12,
                                               bg_color=bg_main, color=bg_bar, shadow_offset=4, border_width=2, border_color="black")
        
        container = tk.Frame(self.pen_settings_frame, bg=bg_bar)
        container.place(relx=0.5, rely=0.5, anchor=tk.CENTER, y=-2)
        
        lbl = tk.Label(container, text="Thickness", bg=bg_bar, fg=fg_text, font=("Segoe UI", 8, "bold"))
        lbl.pack(anchor=tk.W)
        
        scale = ttk.Scale(container, from_=1, to=50, orient=tk.HORIZONTAL, length=140, command=self.changeW)
        scale.set(self.penwidth)
        scale.pack(pady=4)

    def toggle_text_settings(self, event=None):
        """Shows/Hides the text settings popup."""
        self.toggle_popup('text_settings_frame', self.create_text_settings_popup, 'text', 130)

    def create_text_settings_popup(self):
        """Creates the popup frame for text settings styled as docker."""
        bg_main = self.theme["canvas_bg"] if hasattr(self, 'theme') else "#F3F3F3"
        bg_bar  = self.theme["bg_secondary"] if hasattr(self, 'theme') else "white"
        fg_text = self.theme.get("text_color", "black") if hasattr(self, 'theme') else "black"

        self.text_settings_frame = RoundedFrame(self.root, width=190, height=130, corner_radius=12,
                                                bg_color=bg_main, color=bg_bar, shadow_offset=4, border_width=2, border_color="black")
        
        container = tk.Frame(self.text_settings_frame, bg=bg_bar)
        container.place(relx=0.5, rely=0.5, anchor=tk.CENTER, y=-2)
        
        # Font Size
        lbl_size = tk.Label(container, text="Size", bg=bg_bar, fg=fg_text, font=("Segoe UI", 9, "bold"))
        lbl_size.pack(anchor=tk.W)
        
        scale_size = ttk.Scale(container, from_=8, to=72, orient=tk.HORIZONTAL, length=140, command=self.update_font_size_from_slider)
        scale_size.set(self.font_size)
        scale_size.pack(pady=2)

        # Font Family
        lbl_font = tk.Label(container, text="Font", bg=bg_bar, fg=fg_text, font=("Segoe UI", 9, "bold"))
        lbl_font.pack(anchor=tk.W, pady=(5, 0))
        
        fonts = ["Arial", "Times New Roman", "Courier New", "Verdana", "Helvetica", "Comic Sans MS"]
        self.font_var = tk.StringVar(value=self.current_font)
        font_menu = tk.OptionMenu(container, self.font_var, *fonts, command=self.update_font_from_menu)
        font_menu.config(bg=bg_bar, fg=fg_text, highlightthickness=0, bd=0, relief=tk.FLAT, font=("Segoe UI", 8))
        font_menu["menu"].config(bg=bg_bar, fg=fg_text, font=("Segoe UI", 8))
        font_menu.pack(fill=tk.X, pady=2)

    def update_font_size_from_slider(self, val):
        self.font_size = int(float(val))
        if self.selected_objects:
             for obj in self.selected_objects:
                 if self.c.type(obj) == 'text':
                     self.c.itemconfig(obj, font=(self.current_font, self.font_size))
                     
    def update_font_from_menu(self, val):
        self.current_font = val
        if self.selected_objects:
             for obj in self.selected_objects:
                 if self.c.type(obj) == 'text':
                      self.c.itemconfig(obj, font=(self.current_font, self.font_size))
        
    def create_overlay_btn(self, parent, img, cmd):
        btn = tk.Button(parent, image=img, command=cmd, relief=tk.FLAT, bg="white")
        btn.pack(side=tk.LEFT, padx=2)

    def update_dock_color_btn(self):
        # We now use an icon for the color picker button, so we don't need to draw a circle.
        pass
        
    def show_add_menu(self):
        is_open = hasattr(self, 'add_menu_frame') and self.add_menu_frame and self.add_menu_frame.winfo_exists()
        if is_open:
            self.add_menu_frame.unbind_all("<MouseWheel>")
            self.add_menu_frame.destroy()
            self.add_menu_frame = None
            return
            
        bg_main = self.theme["canvas_bg"] if hasattr(self, 'theme') else "#F3F3F3"
        bg_bar  = self.theme["bg_secondary"] if hasattr(self, 'theme') else "white"
        fg_text = self.theme.get("text_color", "black") if hasattr(self, 'theme') else "black"
        
        max_h = min(500, self.root.winfo_height() - 100)
        self.add_menu_frame = RoundedFrame(self.root, width=320, height=max_h, corner_radius=15,
                                           bg_color=bg_main, color=bg_bar, shadow_offset=5, border_width=2, border_color="black")
        self.add_menu_frame.pack_propagate(False)
        
        # Create Scrollable Container
        content_canvas = tk.Canvas(self.add_menu_frame, bg=bg_bar, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.add_menu_frame, orient="vertical", command=content_canvas.yview)
        
        scrollable_frame = tk.Frame(content_canvas, bg=bg_bar)
        
        # Ensure the scrollable_frame is at least as wide as the canvas
        window_id = content_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        def update_scroll_region(event=None):
            content_canvas.configure(scrollregion=content_canvas.bbox("all"))
        
        scrollable_frame.bind("<Configure>", update_scroll_region)
        
        content_canvas.configure(yscrollcommand=scrollbar.set)
        
        # Mousewheel support
        def on_mousewheel(event):
            if content_canvas.winfo_exists():
                content_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.add_menu_frame.bind_all("<MouseWheel>", on_mousewheel)
        
        # Update layout on Resize - Force frame to canvas width
        def on_canvas_configure(event):
             canvas_width = event.width
             content_canvas.itemconfig(window_id, width=canvas_width)
        content_canvas.bind("<Configure>", on_canvas_configure)

        content_canvas.pack(side="left", fill="both", expand=True, padx=10, pady=15)
        scrollbar.pack(side="right", fill="y", pady=15, padx=(0, 5)) 

        def invoke(cmd):
            if hasattr(self, 'add_menu_frame') and self.add_menu_frame:
                 self.add_menu_frame.unbind_all("<MouseWheel>")
                 self.add_menu_frame.destroy()
                 self.add_menu_frame = None
            cmd()

        container = scrollable_frame
        
        def add_category(title):
            tk.Label(container, text=title, bg=bg_bar, fg="gray", font=("Segoe UI", 8, "bold")).pack(anchor=tk.W, pady=(4, 0))
            
        def add_item(label, img, cmd):
            btn = tk.Button(container, text="  " + label, image=img, compound=tk.LEFT, command=lambda c=cmd: invoke(c),
                            bg=bg_bar, fg=fg_text, relief=tk.FLAT, activebackground=self.theme["btn_hover"], 
                            anchor=tk.W, font=("Segoe UI", 9), cursor="hand2")
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=self.theme["btn_hover"]))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=bg_bar))
            btn.pack(fill=tk.X, padx=5, pady=2)

        add_category("Shapes")
        add_item("Rectangle", self.rectangle_img, lambda: self.select_tool('rectangle'))
        add_item("Oval", self.oval_img, lambda: self.select_tool('oval'))
        add_item("Triangle", self.triangle_img, lambda: self.select_tool('triangle'))
        add_item("Diamond", self.diamond_img, lambda: self.select_tool('diamond'))
        add_item("Polygon", self.polygon_img, lambda: self.select_tool('polygon'))
        add_item("Arrow", self.arrow_img, lambda: self.select_tool('arrow'))
        
        add_category("Media")
        add_item("Sticky Note", self.sticky_img, self.create_sticky_note)
        add_item("Image", getattr(self, 'insert_image_img', getattr(self, 'image_img', None)), self.add_image)
        add_item("PDF", getattr(self, 'pdf_img', None), self.import_pdf)
        
        add_category("AI Tools")
        add_item("Idea Generation", getattr(self, 'idea_gen_img', None), self.execute_idea_generation)
        add_item("Flowchart (Magic)", getattr(self, 'magic_flowchart_img', None), self.magic_flowchart_dialog)
        add_item("Flowchart (File)", getattr(self, 'flowchart_img', None), self.generate_flowchart_from_file)
        add_item("Text to Speech", self.tts_img, self.speak_selected_text)
        add_item("OCR", getattr(self, 'ocr_img', None), self.execute_text_extraction)
        add_item("YouTube to Notes", getattr(self, 'youtube_img', None), self.generate_youtube_notes)

        self.root.update_idletasks()
        cx = self.add_btn.winfo_rootx() - self.root.winfo_rootx() + (self.add_btn.winfo_width() / 2)
        y = self.bottom_dock.winfo_y() - 10
        self.add_menu_frame.place(x=cx, y=y, anchor=tk.S)
        tk.Misc.lift(self.add_menu_frame)

    def _speak_threaded(self, full_text):
        """Helper to queue TTS safely in the dedicated worker thread."""
        if not full_text or not full_text.strip():
             return

        import re
        # Windows SAPI5 often crashes on emojis/unicode symbols. Clean the text.
        clean_text = full_text.encode('ascii', 'ignore').decode('ascii')
        # Remove extra punctuation that causes TTS to stutter
        clean_text = re.sub(r'[^\w\s\.,!?\'-]', ' ', clean_text)
        
        if hasattr(self, 'speech_queue'):
            self.speech_queue.put(clean_text)
        else:
            print("Warning: Speech queue not found, skipping TTS.")

    def speak_selected_text(self):
        """Converts selected text items or partial canvas selection to speech."""
        # 1. Check for partial selection on canvas
        sel_item = self.c.select_item()
        if sel_item:
            try:
                content = self.c.itemcget(sel_item, 'text')
                start = self.c.index(sel_item, "sel.first")
                end = self.c.index(sel_item, "sel.last")
                selected_text = content[start:end]
                if selected_text.strip():
                    self._speak_threaded(selected_text.strip())
                    return
            except tk.TclError:
                # No active selection in this item
                pass

        # 2. Fallback to whole objects
        if not self.selected_objects:
            messagebox.showinfo("Text to Speech", "Please select a text object or highlight text first.")
            return

        text_parts = []
        for obj in self.selected_objects:
            if self.c.type(obj) == 'text':
                content = self.c.itemcget(obj, 'text')
                if content.strip():
                    text_parts.append(content.strip())
        
        if not text_parts:
            messagebox.showinfo("Text to Speech", "No text found in selection.")
            return

        full_text = ". ".join(text_parts)
        self._speak_threaded(full_text)

    def show_tts_selection_dialog(self, text_content):
        # REMOVED: Replaced by direct canvas selection
        pass

    def show_main_menu(self):
        is_open = hasattr(self, 'main_menu_frame') and self.main_menu_frame and self.main_menu_frame.winfo_exists()
        if is_open:
            self.main_menu_frame.unbind_all("<MouseWheel>")
            self.main_menu_frame.destroy()
            self.main_menu_frame = None
            return
            
        bg_main = self.theme["canvas_bg"] if hasattr(self, 'theme') else "#F3F3F3"
        bg_bar  = self.theme["bg_secondary"] if hasattr(self, 'theme') else "white"
        fg_text = self.theme.get("text_color", "black") if hasattr(self, 'theme') else "black"
        
        max_h = min(500, self.root.winfo_height() - 100)
        self.main_menu_frame = RoundedFrame(self.root, width=320, height=max_h, corner_radius=15,
                                           bg_color=bg_main, color=bg_bar, shadow_offset=5, border_width=2, border_color="black")
        self.main_menu_frame.pack_propagate(False)
        
        # Create Scrollable Container
        content_canvas = tk.Canvas(self.main_menu_frame, bg=bg_bar, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.main_menu_frame, orient="vertical", command=content_canvas.yview)
        
        scrollable_frame = tk.Frame(content_canvas, bg=bg_bar)
        
        # Ensure the scrollable_frame is at least as wide as the canvas
        window_id = content_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        def update_scroll_region(event=None):
            content_canvas.configure(scrollregion=content_canvas.bbox("all"))
            
        scrollable_frame.bind("<Configure>", update_scroll_region)
        
        content_canvas.configure(yscrollcommand=scrollbar.set)
        
        # Mousewheel support
        def on_mousewheel(event):
            if content_canvas.winfo_exists():
                content_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.main_menu_frame.bind_all("<MouseWheel>", on_mousewheel)
        
        # Update layout on Resize - Force frame to canvas width
        def on_canvas_configure(event):
             canvas_width = event.width
             content_canvas.itemconfig(window_id, width=canvas_width)
        content_canvas.bind("<Configure>", on_canvas_configure)

        content_canvas.pack(side="left", fill="both", expand=True, padx=10, pady=15)
        scrollbar.pack(side="right", fill="y", pady=15, padx=(0, 5))

        def invoke(cmd):
            if hasattr(self, 'main_menu_frame') and self.main_menu_frame:
                 self.main_menu_frame.unbind_all("<MouseWheel>")
                 self.main_menu_frame.destroy()
                 self.main_menu_frame = None
            cmd()

        container = scrollable_frame
        
        def add_category(title):
            tk.Label(container, text=title, bg=bg_bar, fg="gray", font=("Segoe UI", 8, "bold")).pack(anchor=tk.W, pady=(4, 6))
            
        def add_item(label, img, cmd):
            btn = tk.Button(container, text="  " + label, image=img, compound=tk.LEFT, command=lambda c=cmd: invoke(c),
                            bg=bg_bar, fg=fg_text, relief=tk.FLAT, activebackground=self.theme["btn_hover"], 
                            anchor=tk.W, font=("Segoe UI", 9), cursor="hand2")
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=self.theme["btn_hover"]))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=bg_bar))
            btn.pack(fill=tk.X, padx=5, pady=2)

        add_category("File Operations")
        add_item("Save Project", getattr(self, 'save_img', None), self.save_project)
        add_item("Load Project", getattr(self, 'load_img', None), self.load_project)
        add_item("Export to PNG", getattr(self, 'export_img', None), self.export_as_png)
        add_item("Export to PDF", getattr(self, 'pdf_img', None), self.export_as_pdf)
        
        add_category("Options")
        grid_label = "Hide Grid" if getattr(self, 'grid_on', False) else "Show Grid"
        add_item(grid_label, getattr(self, 'grid_img', None), self.toggle_grid)
        snap_label = "Disable Snap" if getattr(self, 'snap_on', False) else "Enable Snap"
        add_item(snap_label, getattr(self, 'snap_menu_img', None), self.toggle_snap)
        
        # Speech Assistant mode toggle
        stt_label = "Speech Engine: Offline (Whisper)" if getattr(self, 'stt_config', None) and self.stt_config.is_offline else "Speech Engine: Online (Google)"
        add_item(stt_label, getattr(self, 'voice_img', None), self.toggle_speech_engine)
        
        # AI Refinement Tools
        smooth_label = "Disable Auto-Smooth" if getattr(self, 'vector_smooth_on', False) else "Enable Auto-Smooth"
        add_item(smooth_label, getattr(self, 'smooth_menu_img', None), self.toggle_vector_smoothing)
        add_item("Auto-Layout Mind Map", getattr(self, 'mindmap_menu_img', None), self.auto_layout_mind_map)
        
        smart_label = "Disable Smart Connectors" if getattr(self, 'smart_connect_on', False) else "Enable Smart Connectors"
        add_item(smart_label, getattr(self, 'smart_connect_menu_img', None), self.toggle_smart_connect)
        auto_label = "Disable Auto-Shape" if getattr(self, 'auto_shape_on', False) else "Enable Auto-Shape"
        add_item(auto_label, getattr(self, 'auto_shape_menu_img', None), self.toggle_auto_shape)
        auto_ink_label = "Disable Auto Ink->Text" if getattr(self, 'auto_ink_to_text_on', False) else "Enable Auto Ink->Text"
        add_item(auto_ink_label, getattr(self, 'auto_ink_to_text_menu_img', None), self.toggle_auto_ink_to_text)
        add_item("Read Selected Text", self.tts_img, self.speak_selected_text)
        
        add_category("Application")
        add_item("Presentation Mode", getattr(self, 'presentation_img', None), self.toggle_presentation_mode)
        add_item("Switch Theme", getattr(self, 'theme_img', None), lambda: self.set_theme("Dark" if self.theme == self.light_theme else "Light"))
        add_item("Exit", getattr(self, 'exit_img', None), self.exit_app)

        self.root.update_idletasks()
        cx = self.menu_btn.winfo_rootx() - self.root.winfo_rootx() + (self.menu_btn.winfo_width() / 2)
        y = self.menu_btn.winfo_rooty() - self.root.winfo_rooty() - 10
        self.main_menu_frame.place(x=cx, y=y, anchor=tk.S)
        tk.Misc.lift(self.main_menu_frame)

    def set_theme(self, theme_name):
        """Sets the theme by name ('Light' or 'Dark')."""
        if theme_name == "Dark":
            self.apply_theme(self.dark_theme)
        else:
            self.apply_theme(self.light_theme)

    def exit_app(self):
        """Asks for confirmation before exiting the application."""
        if messagebox.askokcancel("Exit", "Are you sure you want to exit?"):
            self.root.destroy()
        
    def toggle_speech_engine(self):
        """Toggles the speech engine between Online (Google) and Offline (Faster-Whisper)."""
        if not hasattr(self, 'stt_config') or self.stt_config is None:
            # Fallback initialization if voice assistant hasn't initialized it yet
            from speech_stt import load_stt_config
            self.stt_config = load_stt_config()

        current = self.stt_config.engine
        if current == "google":
            new_engine = "faster-whisper"
        else:
            new_engine = "google"
            
        # Re-create STTConfig with new engine
        from speech_stt import STTConfig, preload_whisper_model
        self.stt_config = STTConfig(
            engine=new_engine,
            model=self.stt_config.model,
            language=self.stt_config.language,
            device=self.stt_config.device,
            compute_type=self.stt_config.compute_type,
            preload=self.stt_config.preload
        )
        
        # Persist choice in .env
        try:
            lines = []
            if os.path.exists(".env"):
                with open(".env", "r") as f:
                    lines = f.readlines()
            
            updated = False
            for i, line in enumerate(lines):
                if line.strip().startswith("STT_ENGINE="):
                    lines[i] = f"STT_ENGINE={new_engine}\n"
                    updated = True
                    break
            
            if not updated:
                lines.append(f"STT_ENGINE={new_engine}\n")
                
            with open(".env", "w") as f:
                f.writelines(lines)
        except Exception as e:
            print(f"Failed to update .env: {e}")

        # Preload the whisper model in a background thread if switched to offline
        if self.stt_config.is_offline:
            import threading
            threading.Thread(
                target=preload_whisper_model, args=(self.stt_config,), daemon=True
            ).start()
            messagebox.showinfo("Speech Assistant", f"Switched to Offline Speech Assistant ({new_engine}). Loading model in background...")
        else:
            messagebox.showinfo("Speech Assistant", "Switched to Online Speech Assistant (Google).")

    def toggle_palette_popup(self, event=None):
        # Position palette above the color button
        # self.palette is a Frame. We need to PLACE it.
        if self.palette.winfo_viewable():
            self.palette.place_forget()
        else:
            # We need to ensure palette has a close button or auto-hide?
            # For now just toggle.
            x = self.bottom_dock.winfo_rootx() + self.color_btn.winfo_x()
            dock_y = self.bottom_dock.winfo_rooty()
            
            # Reparent palette to root if needed? It is child of root (init: ColorPalette(self.root...))
            # Just place it.
            # Width of palette is dynamic.
            
            # Simple offset
            # Closer offset
            # Shift left to center/align better (User requested "more left")
            # Shift by 200 pixels left
            self.palette.place(x=x - 200, y=dock_y - 30, anchor=tk.SW) 
            
            # Correctly raise the widget (Misc.lift)
            tk.Misc.lift(self.palette)

        

    def update_tool_buttons(self):
        for tool_key, btn in self.tool_buttons.items():
            if self.shape == tool_key or (self.shape == 'erase' and tool_key == 'eraser'):
                # Active: Accent Color (Circle/Rounded)
                btn.configure_color(bg_hover=self.theme["accent"], bg_normal=self.theme["accent"])
            else:
                # Inactive: Transparent (matches dock)
                btn.configure_color(bg_hover=self.theme["btn_hover"], bg_normal=None)


    def create_menu(self):
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)

        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save", command=self.save_project)
        file_menu.add_command(label="Open", command=self.load_project)
        file_menu.add_command(label="Clear", command=self.clear)
        file_menu.add_separator()
        
        # Theme Sub-Menu
        theme_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Theme", menu=theme_menu)
        theme_menu.add_command(label="Light (Default)", command=lambda: self.set_theme("Light"))
        theme_menu.add_command(label="Dark", command=lambda: self.set_theme("Dark"))
        
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", command=self.undo)
        edit_menu.add_command(label="Redo", command=self.redo)
        edit_menu.add_command(label="Voice Notes", command=lambda: voiceassistant.start_transcription(self))

        brush_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Brush", menu=brush_menu)
        brush_menu.add_command(label="Brush Size", command=self.set_brush_size)
        brush_menu.add_command(label="Brush Color", command=self.change_fg)
        brush_menu.add_command(label="Eraser", command=self.activate_eraser)
        brush_menu.add_command(label="Text Size", command=self.set_text_size)

        tool_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Tools", menu=tool_menu)
        tool_menu.add_command(label="Brush", command=self.use_brush)
        tool_menu.add_command(label="Text", command=self.add_text)
        tool_menu.add_command(label="Rectangle", command=lambda: self.select_tool('rectangle'))
        tool_menu.add_command(label="Oval", command=lambda: self.select_tool('oval'))
        tool_menu.add_command(label="Line", command=lambda: self.select_tool('line'))
        tool_menu.add_command(label="Sticky Note",command=self.create_sticky_note)  # Sticky note option

        # Templates Menu
        template_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Templates", menu=template_menu)
        template_menu.add_command(label="Venn Diagram", command=lambda: self.apply_template(templates.draw_venn_diagram))
        template_menu.add_command(label="T-Chart", command=lambda: self.apply_template(templates.draw_t_chart))
        template_menu.add_command(label="SWOT Analysis", command=lambda: self.apply_template(templates.draw_swot_analysis))
        template_menu.add_command(label="Kanban Board", command=lambda: self.apply_template(templates.draw_kanban_board))

        ai_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="AI features", menu=ai_menu)
        ai_menu.add_command(label="Idea Generation", command=self.execute_idea_generation)
        ai_menu.add_command(label="Extract text from image", command=self.execute_text_extraction)
        ai_menu.add_command(label="Generate information", command=self.execute_short_info)
        ai_menu.add_command(label="Document to Flowchart", command=self.generate_flowchart_from_file)
        
        # Magic Flowchart with options
        magic_menu = tk.Menu(ai_menu, tearoff=0)
        ai_menu.add_cascade(label="Magic Flowchart Options", menu=magic_menu)
        magic_menu.add_command(label="Standard (Process)", command=lambda: self.set_magic_layout('standard'))
        magic_menu.add_command(label="Wide (Timeline)", command=lambda: self.set_magic_layout('horizontal'))
        magic_menu.add_command(label="Mind Map (Organic)", command=lambda: self.set_magic_layout('mindmap'))

        ai_menu.add_command(label="âœ¨ Magic Flowchart (Run)", command=self.magic_flowchart_dialog) # AI Formatter

    # speech-to-text




#main code
    def on_button_press(self, event):
        # Check for Pan: Middle Mouse (2), or Hand Tool
        if self.shape == 'hand' or event.num == 2: 
            self.start_pan(event)
            self.c.config(cursor='fleur')
            # Fix: Initialize screen coordinates for delta calculation
            self.canvas_click_x_screen = event.x_root
            self.canvas_click_y_screen = event.y_root
            return

        if hasattr(self, 'in_crop_mode') and self.in_crop_mode:
            # Check for crop handle clicks
            cx = self.c.canvasx(event.x)
            cy = self.c.canvasy(event.y)
            items = self.c.find_overlapping(cx-2, cy-2, cx+2, cy+2)
            for item in items:
                if 'crop_handle' in self.c.gettags(item):
                    self.active_crop_handle = item
                    return
            self.active_crop_handle = None
            return

        self.old_x = self.snap(self.c.canvasx(event.x))
        self.old_y = self.snap(self.c.canvasy(event.y))
        
        # Track start position for Undo/Redo of Move actions
        self.drag_start_x = self.old_x
        self.drag_start_y = self.old_y

        if self.eraser_on:
            self.current_erase_batch = []
            self.erase(event)
            return

        if self.shape == 'bucket':
            # Identify object under cursor
            # Use a small tolerance
            cx = self.c.canvasx(event.x)
            cy = self.c.canvasy(event.y)
            items = self.c.find_overlapping(cx-1, cy-1, cx+1, cy+1)
            # Filter out grid/guide items? And the laser?
            # Reverse order to get top-most
            for item in reversed(items):
                tags = self.c.gettags(item)
                if "grid_line" in tags or "laser" in tags or "poly_guide" in tags:
                    continue
                
                # Apply color
                # Determine property to change based on type
                itype = self.c.type(item)
                old_color = None
                prop = 'fill'
                
                if itype in ['rectangle', 'oval', 'polygon']:
                    # For shapes, fill the interior
                    # But wait, lines use 'fill' for their stroke color.
                    # Rectangles use 'fill' for background, 'outline' for border.
                    # Standard paint bucket usually fills the *interior*.
                    old_color = self.c.itemcget(item, 'fill')
                    self.c.itemconfig(item, fill=self.color_fg) # Use current FG color as fill
                    prop = 'fill'
                elif itype == 'line':
                    # Lines don't have a fill in the same sense, they use 'fill' for stroke
                    old_color = self.c.itemcget(item, 'fill')
                    self.c.itemconfig(item, fill=self.color_fg)
                    prop = 'fill'
                elif itype == 'text':
                    # Text uses 'fill' for text color
                    old_color = self.c.itemcget(item, 'fill')
                    self.c.itemconfig(item, fill=self.color_fg)
                    prop = 'fill'
                else:
                    continue # Unknown type
                
                # Add to undo stack
                if old_color != self.color_fg:
                    self.undo_stack.append(('config', item, {prop: old_color}, {prop: self.color_fg}))
                    self.redo_stack.clear()
                    
                break # Only fill top-most
            return



        elif self.shape == 'text':
            # Prompt for text input
            text = self.modern_askstring("Input", "Enter text:")
            if text:
                # Create text at clicked location - Account for zoom
                scaled_size = int(self.font_size * self.scale)
                text_id = self.c.create_text(self.old_x, self.old_y, text=text, fill=self.color_fg, 
                                             font=(self.current_font, scaled_size), anchor=tk.NW)
                
                # Register for zooming
                self.text_base_sizes[text_id] = (self.current_font, self.font_size)
                
                self.objects.append(text_id)
                self.undo_stack.append(('create_text', text_id, self.old_x, self.old_y, text, self.color_fg, self.font_size))
                self.redo_stack.clear()
                self.update_scrollregion()
                self.update_minimap()
            return

        if self.shape == 'rectangle':
            scaled_pen = max(1, int(self.penwidth * self.scale))
            self.shape_id = self.c.create_rectangle(self.old_x, self.old_y, self.old_x, self.old_y,
                                                    outline=self.color_fg, width=scaled_pen,
                                                    fill=self.fill_color)
            self.shape_base_widths[self.shape_id] = self.penwidth # Store at 1.0 scale
            self.c.config(cursor='cross')
            self.objects.append(self.shape_id)

        elif self.shape == 'oval':
            scaled_pen = max(1, int(self.penwidth * self.scale))
            self.shape_id = self.c.create_oval(self.old_x, self.old_y, self.old_x, self.old_y,
                                               outline=self.color_fg, width=scaled_pen,
                                               fill=self.fill_color)
            self.shape_base_widths[self.shape_id] = self.penwidth
            self.c.config(cursor='cross')
            self.objects.append(self.shape_id)

        elif self.shape == 'line':
            scaled_pen = max(1, int(self.penwidth * self.scale))
            self.shape_id = self.c.create_line(self.old_x, self.old_y, self.old_x, self.old_y,
                                               width=scaled_pen, fill=self.color_fg)
            self.shape_base_widths[self.shape_id] = self.penwidth
            self.c.config(cursor='cross')
            self.objects.append(self.shape_id)

        elif self.shape in ['triangle', 'diamond']:
            scaled_pen = max(1, int(self.penwidth * self.scale))
            self.shape_id = self.c.create_polygon(self.old_x, self.old_y, self.old_x, self.old_y, self.old_x, self.old_y,
                                                  outline=self.color_fg, width=scaled_pen,
                                                  fill=self.fill_color)
            self.shape_base_widths[self.shape_id] = self.penwidth
            self.c.config(cursor='cross')
            self.objects.append(self.shape_id)

        elif self.shape == 'brush':
             self.current_stroke_points = [(self.old_x, self.old_y)]
             self.current_stroke_ids = []
             
             scaled_pen = max(1, int(self.penwidth * self.scale))
             self.shape_id = self.c.create_line(self.old_x, self.old_y, self.old_x, self.old_y,
                                               width=scaled_pen, fill=self.color_fg, capstyle=tk.ROUND, smooth=True)
             self.shape_base_widths[self.shape_id] = self.penwidth
             self.objects.append(self.shape_id)
             self.current_stroke_ids.append(self.shape_id)

        elif self.shape == 'highlighter':
             self.current_stroke_points = [(self.old_x, self.old_y)]
             self.current_stroke_ids = []
             target_width = max(self.penwidth * 4, 30)
             scaled_hl = max(1, int(target_width * self.scale))
             hl_color = self.color_fg if self.color_fg.lower() not in ('black', '#000000') else '#FFFF00'
             self.shape_id = self.c.create_line(self.old_x, self.old_y, self.old_x, self.old_y,
                                          width=scaled_hl, fill=hl_color, capstyle=tk.ROUND, smooth=True, stipple='gray50')
             self.shape_base_widths[self.shape_id] = target_width
             self.objects.append(self.shape_id)
             self.current_stroke_ids.append(self.shape_id)

        elif self.shape == 'arrow':
            w = self.penwidth
            self.shape_id = self.c.create_line(self.old_x, self.old_y, self.old_x, self.old_y,
                                               width=w, fill=self.color_fg, arrow=tk.LAST, arrowshape=(w*3, w*4, w*1.5))
            self.c.config(cursor='cross')
            self.objects.append(self.shape_id)
        
        elif self.shape == 'polygon':
             x, y = self.snap(event.x), self.snap(event.y)
             self.poly_points.extend([x, y])
             
             # Draw line connecting to previous point
             if len(self.poly_points) >= 4:
                 prev_x, prev_y = self.poly_points[-4], self.poly_points[-3]
                 self.c.create_line(prev_x, prev_y, x, y, width=self.penwidth, fill=self.color_fg, tags="poly_temp")
        
        elif self.shape == 'select':
            # Check if clicked on a resize handle first
            cx = self.c.canvasx(event.x)
            cy = self.c.canvasy(event.y)
            # Standardized 5-pixel buffer for interaction
            items = self.c.find_overlapping(cx-5, cy-5, cx+5, cy+5)
            is_resize = False
            for item in items:
                tags = self.c.gettags(item)
                if 'resize' in tags:
                    self.resizing = True
                    self.start_x = event.x
                    self.start_y = event.y
                    if hasattr(self, 'resize_target') and self.resize_target:
                         self.resize_start_state = self.start_interactive_resize(self.resize_target, event)
                         self.hide_property_bar()
                    is_resize = True
                    break
            
            if not is_resize:
                # Optimized Detection: Find all valid items under cursor (ignoring grid)
                valid_items = [i for i in items if "grid" not in self.c.gettags(i)]
                text_item = next((i for i in valid_items if self.c.type(i) == 'text'), None)
                
                if text_item:
                    # Capture for potential text-selection drag, but DON'T return 
                    # so standard select_object/move logic still runs.
                    self._text_drag_item = text_item
                    self._text_drag_start_pos = (event.x, event.y)
                    self._text_selection_started = False
                
                # Initialize displacement for snapped move
                self._total_dx = 0
                self._total_dy = 0
                
                target = self.select_object(event.x, event.y, event)
                if not target:
                    # Activate multi-select drag bounding box
                    self._prev_shape = getattr(self, 'shape', 'select')
                    self.shape = 'multi_select_drag'

    def on_button_release(self, event):
        self.c.delete("eraser_cursor") # Clean up dynamic cursor
        self._text_drag_item = None # Clear text selection drag
        
        if hasattr(self, 'in_crop_mode') and self.in_crop_mode:
            self.active_crop_handle = None
            return
        
        if self.eraser_on:
            if hasattr(self, 'current_erase_batch') and self.current_erase_batch:
                self.undo_stack.append(('delete', list(self.current_erase_batch)))
                self.redo_stack.clear()
            self.current_erase_batch = []
            
            # Reset speed tracking data
            if hasattr(self, 'last_erase_time'): del self.last_erase_time
            if hasattr(self, 'last_erase_x'): del self.last_erase_x
            
            return

        if self.old_x is None or self.old_y is None:
            return

        if self.shape == 'multi_select_drag':
             cx = self.snap(self.c.canvasx(event.x))
             cy = self.c.canvasy(event.y)
             self.c.delete("select_box")
             
             x1, y1, x2, y2 = min(self.old_x, cx), min(self.old_y, cy), max(self.old_x, cx), max(self.old_y, cy)
             items = self.c.find_overlapping(x1, y1, x2, y2)
             valid_items = [i for i in items if "grid" not in self.c.gettags(i) and "select_box" not in self.c.gettags(i) and "resize" not in self.c.gettags(i) and "laser" not in self.c.gettags(i)]
             
             is_shift = (event.state & 0x1) != 0
             if not is_shift:
                 self.clear_selection()
                 
             for item in valid_items:
                 self.select_item(item)
             
             # Clean up resize handle for multi-selections (only safe for single item)
             if len(self.selected_objects) > 1:
                 self.c.delete('resize')
                 self.resize_target = None
                      
             self.shape = getattr(self, '_prev_shape', 'select')

        elif self.shape == 'rectangle':
            x2, y2 = self.snap(self.c.canvasx(event.x)), self.snap(self.c.canvasy(event.y))
            self.c.coords(self.shape_id, self.old_x, self.old_y, x2, y2)
            self.undo_stack.append(('create_rectangle', self.shape_id, self.old_x, self.old_y, x2, y2,
                                    self.color_fg, self.penwidth))

        elif self.shape == 'oval':
            x2, y2 = self.snap(self.c.canvasx(event.x)), self.snap(self.c.canvasy(event.y))
            self.c.coords(self.shape_id, self.old_x, self.old_y, x2, y2)
            self.undo_stack.append(
                ('create_oval', self.shape_id, self.old_x, self.old_y, x2, y2, self.color_fg, self.penwidth))

        elif self.shape == 'line':
            x1, y1 = self.old_x, self.old_y
            x2, y2 = self.snap(self.c.canvasx(event.x)), self.snap(self.c.canvasy(event.y))
            
            self.c.coords(self.shape_id, x1, y1, x2, y2)
            self.undo_stack.append(
                ('create_line', self.shape_id, x1, y1, x2, y2, self.color_fg, self.penwidth))
            
            if self.smart_connect_on:
                self.process_smart_connection(self.shape_id, x1, y1, x2, y2)

        elif self.shape == 'arrow':
            x1, y1 = self.old_x, self.old_y
            x2, y2 = self.snap(self.c.canvasx(event.x)), self.snap(self.c.canvasy(event.y))
            
            self.c.coords(self.shape_id, x1, y1, x2, y2)
            self.undo_stack.append(
                ('create_arrow', self.shape_id, x1, y1, x2, y2, self.color_fg, self.penwidth))
            
            if self.smart_connect_on:
                self.process_smart_connection(self.shape_id, x1, y1, x2, y2)

        elif self.shape == 'triangle':
            x2, y2 = self.snap(self.c.canvasx(event.x)), self.snap(self.c.canvasy(event.y))
            avg_x = (self.old_x + x2) / 2
            self.c.coords(self.shape_id, avg_x, self.old_y, self.old_x, y2, x2, y2)
            self.undo_stack.append(('create_polygon', self.shape_id, avg_x, self.old_y, self.old_x, y2, x2, y2, self.color_fg, self.penwidth, self.fill_color))

        elif self.shape == 'diamond':
            x2, y2 = self.snap(self.c.canvasx(event.x)), self.snap(self.c.canvasy(event.y))
            avg_x = (self.old_x + x2) / 2
            avg_y = (self.old_y + y2) / 2
            self.c.coords(self.shape_id, avg_x, self.old_y, x2, avg_y, avg_x, y2, self.old_x, avg_y)
            self.undo_stack.append(('create_polygon', self.shape_id, avg_x, self.old_y, x2, avg_y, avg_x, y2, self.old_x, avg_y, self.color_fg, self.penwidth, self.fill_color))

        elif self.shape == 'brush':
            detected = False
            if self.auto_shape_on:
                 detected = self.detect_shape()
            
            if self.shape == 'brush' and not detected:
                 # Apply Vector Smoothing if enabled
                 if getattr(self, 'vector_smooth_on', False):
                      self.apply_vector_smoothing(self.shape_id)

                 try:
                     coords = self.c.coords(self.shape_id)
                     if coords and len(coords) >= 4:
                          self.undo_stack.append(('create_brush', self.shape_id, coords, self.color_fg, self.penwidth))
                          
                          if getattr(self, 'auto_ink_to_text_on', False):
                               if not hasattr(self, '_auto_ink_buffer'):
                                    self._auto_ink_buffer = []
                               self._auto_ink_buffer.append(self.shape_id)
                               
                               if hasattr(self, '_auto_ink_timer') and self._auto_ink_timer:
                                    self.root.after_cancel(self._auto_ink_timer)
                               self._auto_ink_timer = self.root.after(1500, self._process_auto_ink)
                 except tk.TclError:
                     pass

        elif self.shape == 'highlighter':
             try:
                 coords = self.c.coords(self.shape_id)
                 if coords and len(coords) >= 4:
                      hl_width = max(self.penwidth * 4, 30)
                      hl_color = self.color_fg if self.color_fg.lower() not in ('black', '#000000') else '#FFFF00'
                      self.undo_stack.append(('create_highlighter', self.shape_id, coords, hl_color, hl_width))
             except tk.TclError:
                 pass

        # self.c.unbind('<B1-Motion>')  <-- Removed to fix brush dots issue
        self.reset(event)
        
        self.update_scrollregion()
        self.update_minimap()

        # Check for Move or Resize completion
        if self.resizing and getattr(self, 'resize_start_state', None):
             # End of Resize
             # State: (item_id, handle_id, start_coords, start_mouse, start_bbox)
             item_id = self.resize_start_state[0]
             start_coords = self.resize_start_state[2]
             
             # Current Coords
             current_coords = self.c.coords(item_id)
             
             if current_coords != start_coords: # Only if changed
                 self.undo_stack.append(('resize', item_id, start_coords, current_coords))
                 self.redo_stack.clear()
                 
                 # Final High Quality Resize for Images
                 if self.c.type(item_id) == 'image' and hasattr(self, 'stored_images') and item_id in self.stored_images:
                      # Calculate width/height from coords
                      bbox = self.c.bbox(item_id)
                      if bbox:
                          w = bbox[2] - bbox[0]
                          h = bbox[3] - bbox[1]
                          if w > 0 and h > 0:
                              original = self.stored_images[item_id]
                              resized = original.resize((w, h), Image.LANCZOS)
                              new_photo = ImageTk.PhotoImage(resized)
                              self.c.itemconfig(item_id, image=new_photo)
                              
                              # Update long-term ref
                              if not hasattr(self, 'image_refs'): self.image_refs = []
                              self.image_refs.append(new_photo)
                              
                              # Update base size for correct zooming logic later
                              # The base size is the size at zoom scale 1.0.
                              if hasattr(self, 'image_base_sizes'):
                                   self.image_base_sizes[item_id] = (int(w / self.scale), int(h / self.scale))

             self.resizing = False
             self.resize_start_state = None
        
        if self.shape == 'select' and self.selected_objects:
             # End of Move?
             # Check if we moved significantly
             if hasattr(self, 'drag_start_x') and hasattr(self, 'drag_start_y'):
                 # Calculate total delta using canvas coordinates
                 current_x = self.snap(self.c.canvasx(event.x))
                 current_y = self.snap(self.c.canvasy(event.y))
                 
                 total_dx = current_x - self.drag_start_x
                 total_dy = current_y - self.drag_start_y
                 
                 if abs(total_dx) > 1 or abs(total_dy) > 1:
                     self.undo_stack.append(('move', list(self.selected_objects), total_dx, total_dy))
                     self.redo_stack.clear()

        # Reset cursor to default after drawing
        self.c.config(cursor='arrow')

    def toggle_eraser(self):
        self.eraser_on = not self.eraser_on
        self.shape = None  # Deactivate shape drawing when eraser is active

    def on_motion(self, event):
        # Deprecated: Handled in paint
        pass

    def drag_text(self, event):
         # Deprecated: Handled in paint -> move_object
        pass

    def paint(self, event):
        if self.shape == 'hand':
            self.pan(event)
            return
            
        if self.shape == 'laser':
            cx = self.c.canvasx(event.x)
            cy = self.c.canvasy(event.y)
            r = 5
            if hasattr(self, 'laser_id') and self.laser_id:
                self.c.coords(self.laser_id, cx-r, cy-r, cx+r, cy+r)
                self.c.tag_raise(self.laser_id)
            else:
                self.laser_id = self.c.create_oval(cx-r, cy-r, cx+r, cy+r, fill="red", outline="red", tags="laser")
            return
            
        if hasattr(self, 'in_crop_mode') and self.in_crop_mode:
            if hasattr(self, 'active_crop_handle') and self.active_crop_handle:
                self.handle_crop_drag(event)
            return

        if self.eraser_on:
            self.erase(event)
        elif self.resizing:
            # Handle resize dragging
            self.handle_resize_drag(event)
        elif self.shape in ('brush', 'highlighter', 'multi_select_drag'):
             # Freehand and lasso tools go through on_drag
             self.on_drag(event)
        elif self.shape != 'select':
            self.update_shape(event)
        elif self.shape == 'select':
            # Priority 1: Text Selection drag (if started)
            if getattr(self, '_text_selection_started', False) and self._text_drag_item:
                cx, cy = self.c.canvasx(event.x), self.c.canvasy(event.y)
                self.c.select_to(self._text_drag_item, f"@{int(cx)},{int(cy)}")
            
            # Priority 2: Object Movement & Text Selection Logic
            elif self.selected_objects:
                # Decision Case: Single text object
                if len(self.selected_objects) == 1 and self.c.type(self.selected_objects[0]) == 'text':
                    # If we haven't decided yet, check movement thresholds
                    if not getattr(self, 'dragging_object', False) and not getattr(self, '_text_selection_started', False):
                        dx = abs(event.x - self._text_drag_start_pos[0])
                        dy = abs(event.y - self._text_drag_start_pos[1])
                        
                        # If significant movement detected
                        if dx > 15 or dy > 15:
                            if dy > dx * 0.7:  # Primarily vertical or diagonal -> Move
                                self.dragging_object = True
                            elif dx > dy * 1.5: # Primarily horizontal -> Text Selection
                                self._text_selection_started = True
                                self._text_drag_item = self.selected_objects[0]
                                scx = self.c.canvasx(self._text_drag_start_pos[0])
                                scy = self.c.canvasy(self._text_drag_start_pos[1])
                                self.c.select_from(self._text_drag_item, f"@{int(scx)},{int(scy)}")
                                return # Don't move on the very first frame of selection
                        else:
                            return # Wait for more movement to decide
                    
                    # If we decided on text selection, proceed with sync
                    if getattr(self, '_text_selection_started', False):
                        cx, cy = self.c.canvasx(event.x), self.c.canvasy(event.y)
                        self.c.select_to(self._text_drag_item, f"@{int(cx)},{int(cy)}")
                        return

                # Default: Move selected objects
                self.dragging_object = True
                self.move_object(event)

    def on_drag(self, event):
        self.dragging = True
        
        # 0. Pan Logic
        if self.shape == 'hand' or (event.state & 0x0002) or (event.num == 2): # Hand tool or Middle Mouse
             self.pan(event)
             return

        # Map to canvas coordinates
        cx = self.c.canvasx(event.x)
        cy = self.c.canvasy(event.y)
        
        if self.eraser_on:
             self.erase(event)

        elif self.shape == 'multi_select_drag':
             # Rubber-band selection box
             self.c.delete("select_box")
             self.c.create_rectangle(self.old_x, self.old_y, cx, cy,
                                     outline="#0078D4", dash=(4, 4), width=2, tags="select_box")
        
        elif self.shape == 'line':
             # Live preview is handled by update_shape via paint() -> update_shape route
             pass
        
        elif self.shape in ['brush', 'highlighter']:
             if hasattr(self, 'shape_id') and self.shape_id:
                 coords = list(self.c.coords(self.shape_id))
                 
                 # Optimization: Only plot if moved significantly
                 if len(coords) >= 2 and abs(cx - coords[-2]) < 2 and abs(cy - coords[-1]) < 2:
                      return
                      
                 coords.extend([cx, cy])
                 self.c.coords(self.shape_id, *coords)
             
             if hasattr(self, 'current_stroke_points'):
                 self.current_stroke_points.append((cx, cy))

             self.old_x = cx
             self.old_y = cy

    def update_shape(self, event):
        current_x = self.snap(self.c.canvasx(event.x))
        current_y = self.snap(self.c.canvasy(event.y))
        
        if self.shape_id:
            if self.shape == 'line':
                self.c.coords(self.shape_id, self.old_x, self.old_y, current_x, current_y)
            elif self.shape == 'arrow':
                self.c.coords(self.shape_id, self.old_x, self.old_y, current_x, current_y)
            elif self.shape == 'rectangle':
                self.c.coords(self.shape_id, self.old_x, self.old_y, current_x, current_y)
            elif self.shape == 'oval':
                self.c.coords(self.shape_id, self.old_x, self.old_y, current_x, current_y)
            elif self.shape == 'triangle':
                avg_x = (self.old_x + current_x) / 2
                self.c.coords(self.shape_id, avg_x, self.old_y, self.old_x, current_y, current_x, current_y)
            elif self.shape == 'diamond':
                avg_x = (self.old_x + current_x) / 2
                avg_y = (self.old_y + current_y) / 2
                self.c.coords(self.shape_id, avg_x, self.old_y, current_x, avg_y, avg_x, current_y, self.old_x, avg_y)
            elif self.shape == 'brush':
                # Note: Brush usually shouldn't snap strictly or it looks jagged, but we'll apply it if requested
                if self.snap_on:
                     # For brush, maybe only add point if it moved to next grid?
                     pass # Let's skip snapping for brush to keep it smooth or user can turn it off
                
                coords = self.c.coords(self.shape_id)
                self.c.coords(self.shape_id, *coords, self.c.canvasx(event.x), self.c.canvasy(event.y))
                
                # Auto-shape data collection
                self.current_stroke_points.append((self.c.canvasx(event.x), self.c.canvasy(event.y)))

    def start_interactive_resize(self, item_id, event=None):
        """Returns the state needed for resizing: (item_id, handle_id, start_coords, start_mouse, start_bbox)."""
        handle_id = getattr(self, 'resize_handle', None)
        # Mouse start (canvas space)
        if event:
            start_mouse = (event.x, event.y)
        else:
            # Fallback (though event should be passed now)
            start_mouse = (self.c.winfo_pointerx() - self.c.winfo_rootx(),
                           self.c.winfo_pointery() - self.c.winfo_rooty())
        
        start_coords = self.c.coords(item_id)
        start_bbox = self.c.bbox(item_id)
        return item_id, handle_id, start_coords, start_mouse, start_bbox

    def handle_resize_drag(self, event):
        if not self.resize_start_state: return
        
        # Robust unpacking
        try:
             item_id, handle_id, start_coords, start_mouse, start_bbox = self.resize_start_state
        except ValueError:
             # Fallback for old state if any (unlikely after restart, but safe)
             return
             
        dx = (event.x - start_mouse[0]) / self.scale
        dy = (event.y - start_mouse[1]) / self.scale
        
        tags = self.c.gettags(handle_id)
        itype = self.c.type(item_id)
        
        if itype in ['rectangle', 'oval', 'line']:
            if len(start_coords) == 4:
                x0, y0, x1, y1 = start_coords
                
                if "nw" in tags:
                    self.c.coords(item_id, x0+dx, y0+dy, x1, y1)
                elif "ne" in tags:
                    self.c.coords(item_id, x0, y0+dy, x1+dx, y1)
                elif "sw" in tags:
                    self.c.coords(item_id, x0+dx, y0, x1, y1+dy)
                # Default to SE (Bottom-Right) if 'resize' is present but no specific direction
                elif "se" in tags or "resize" in tags:
                    self.c.coords(item_id, x0, y0, x1+dx, y1+dy)
        
        elif itype == 'image':
            if not start_bbox: return
            bx0, by0, bx1, by1 = start_bbox
            
            # Calculate new bbox
            new_x0, new_y0, new_x1, new_y1 = bx0, by0, bx1, by1
            
            if "nw" in tags:
                new_x0 += dx; new_y0 += dy
            elif "ne" in tags:
                new_y0 += dy; new_x1 += dx
            elif "sw" in tags:
                new_x0 += dx; new_y1 += dy
            # Default to SE
            elif "se" in tags or "resize" in tags:
                new_x1 += dx; new_y1 += dy
            
            new_w = int(new_x1 - new_x0)
            new_h = int(new_y1 - new_y0)
            
            if new_w < 10: new_w = 10
            if new_h < 10: new_h = 10
            
            # Resample from original if available
            if hasattr(self, 'stored_images') and item_id in self.stored_images:
                original = self.stored_images[item_id]
                # Resize (Fast for dragging)
                resized = original.resize((new_w, new_h), Image.NEAREST)
                new_photo = ImageTk.PhotoImage(resized)
                
                # Update canvas
                self.c.itemconfigure(item_id, image=new_photo)
                self.c.coords(item_id, new_x0, new_y0) # Ensure pos is correct (NW anchor usually)
                
                # We don't update refs here to save memory/GC, just temp
                # self.image_refs_resized... maybe needed to prevent flickering?
                # Yes, need to keep ref
                if not hasattr(self, 'image_refs_resized'): self.image_refs_resized = {}
                self.image_refs_resized[item_id] = new_photo
            else:
                # Standard Shape Resize (Rect, Oval)
                itype = self.c.type(item_id)
                if itype in ('rectangle', 'oval', 'arc', 'window'):
                    self.c.coords(item_id, new_x0, new_y0, new_x0 + new_w, new_y0 + new_h)
                elif itype == 'line':
                    coords = self.c.coords(item_id)
                    if len(coords) == 4:
                        self.c.coords(item_id, new_x0, new_y0, new_x0 + new_w, new_y0 + new_h)
                # Ignore direct coordinate resizing for text/polygons to avoid crashes
            
            # Update handle position matching the new size (zoom-independent visual size)
            h_size = 10 / self.scale
            # Find current bbox after resize to place handle precisely
            curr_bbox = self.c.bbox(item_id)
            if curr_bbox:
                cx1, cy1, cx2, cy2 = curr_bbox
                self.c.coords(handle_id, cx2 - h_size, cy2 - h_size, cx2, cy2)
            
            # CRITICAL FIX: Update base size so zoom respects the manual resize
            if not hasattr(self, 'image_base_sizes'): self.image_base_sizes = {}
            self.image_base_sizes[item_id] = (new_w / self.scale, new_h / self.scale)
            
        elif itype == 'text':
            if not start_bbox: return
            bx0, by0, bx1, by1 = start_bbox
            
            # Start coordinate represents the text origin anchor
            sx, sy = start_coords[0], start_coords[1]
            
            # Calculate new width
            current_w_logical = (bx1 - bx0) / self.scale
            new_w_logical = current_w_logical + (dx / self.scale)
            
            if new_w_logical < 50:
                new_w_logical = 50
                
            self.c.itemconfig(item_id, width=new_w_logical)
            
            # Calculate the actual applied physical pixel width difference
            actual_dx = (new_w_logical * self.scale) - (bx1 - bx0)
            
            # Shift center coordinates algebraically so left edge stays physically stationary
            anchor = self.c.itemcget(item_id, "anchor")
            if anchor == "center":
                self.c.coords(item_id, sx + (actual_dx / 2), sy)

            # Store the new width configuration so zooming dynamically respects it
            if not hasattr(self, 'text_base_widths'): self.text_base_widths = {}
            self.text_base_widths[item_id] = new_w_logical
            
            # Synchronize background shape geometry if this text is grouped
            tags = self.c.gettags(item_id)
            group_tag = next((t for t in tags if t.startswith("node_group_")), None)
            bg_id = None
            if group_tag:
                 members = self.c.find_withtag(group_tag)
                 bg_id = next((m for m in members if self.c.type(m) in ['rectangle', 'oval', 'polygon']), None)
                 if bg_id:
                      new_bbox = self.c.bbox(item_id)
                      if new_bbox:
                          tx1, ty1, tx2, ty2 = new_bbox
                          bg_type = self.c.type(bg_id)
                          padding = 10 
                          # Re-apply structural bounding box math used during node creation
                          tx1 -= padding; ty1 -= padding; tx2 += padding; ty2 += padding
                          cx, cy = (tx1 + tx2) / 2, (ty1 + ty2) / 2
                          w, h = tx2 - tx1, ty2 - ty1
                          
                          if bg_type == "polygon" and len(self.c.coords(bg_id)) == 8:
                              nx1, nx2 = cx - w * 0.9, cx + w * 0.9
                              ny1, ny2 = cy - h * 0.9, cy + h * 0.9
                              mx, my = (nx1 + nx2) / 2, (ny1 + ny2) / 2
                              self.c.coords(bg_id, mx, ny1, nx2, my, mx, ny2, nx1, my)
                          elif bg_type == "oval":
                              nx1, nx2 = cx - w * 0.75, cx + w * 0.75
                              ny1, ny2 = cy - h * 0.75, cy + h * 0.75
                              self.c.coords(bg_id, nx1, ny1, nx2, ny2)
                          else:
                              self.c.coords(bg_id, tx1, ty1, tx2, ty2)
            
            # Synchronize resize handle perfectly to bottom right boundary
            h_size = 10 / self.scale
            cb = self.c.bbox(bg_id) if bg_id else self.c.bbox(item_id)
            if cb:
                cx1, cy1, cx2, cy2 = cb
                self.c.coords(handle_id, cx2 - h_size, cy2 - h_size, cx2, cy2)

            
        self.update_connected_lines(item_id)
        self.objects_moved = True

    def move_object(self, event):
        cur_x = self.c.canvasx(event.x)
        cur_y = self.c.canvasy(event.y)
        
        # Snapping logic: Accumulate raw movement, move by snapped chunks
        raw_dx = cur_x - self.old_x
        raw_dy = cur_y - self.old_y
        
        self._total_dx += raw_dx
        self._total_dy += raw_dy
        
        # Determine actual movement (snapped if enabled)
        move_dx = self.snap(self._total_dx) if self.snap_on else self._total_dx
        move_dy = self.snap(self._total_dy) if self.snap_on else self._total_dy
        
        if move_dx != 0 or move_dy != 0:
            for obj in self.selected_objects:
                 self.c.move(obj, move_dx, move_dy)
                 # Move resize handle if this object is the selected image/shape
                 target = getattr(self, 'resize_target', None)
                 if target == obj:
                     self.update_resize_handle()
                 # Update any lines connected to this object
                 self.update_connected_lines(obj)
            
            # Update background objects for nodes
            for obj in self.selected_objects:
                 group_tag = next((t for t in self.c.gettags(obj) if t.startswith("node_group_")), None)
                 if group_tag:
                      text_id = group_tag[len("node_group_"):]
                      # If it's the text, we already moved it. If it's the bg, we moved it.
                      # But update_connected_lines usually handles connections. 
                      # The bg resize is handled in rescale_text_for_zoom, but the move is simple.
                      pass

            self._total_dx -= move_dx
            self._total_dy -= move_dy
            self.objects_moved = True

        self.old_x = cur_x
        self.old_y = cur_y
        self.update_scrollregion()
        self.update_minimap()

    def get_line_intersection(self, x1, y1, x2, y2, bbox):
        """
        Calculates the intersection of line (x1,y1)->(x2,y2) with rectangle bbox (bx1, by1, bx2, by2).
        Returns the intersection point (ix, iy) closest to (x1, y1).
        """
        bx1, by1, bx2, by2 = bbox
        
        # 4 segments of the rectangle
        segments = [
            ((bx1, by1), (bx2, by1)), # Top
            ((bx2, by1), (bx2, by2)), # Right
            ((bx2, by2), (bx1, by2)), # Bottom
            ((bx1, by2), (bx1, by1))  # Left
        ]
        
        closest_point = None
        min_dist = float('inf')
        
        for p1, p2 in segments:
            px1, py1 = p1
            px2, py2 = p2
            
            # Intersection of two line segments
            # Line 1: (x1, y1) to (x2, y2)
            # Line 2: (px1, py1) to (px2, py2)
            
            det = (x1 - x2) * (py1 - py2) - (y1 - y2) * (px1 - px2)
            if abs(det) < 1e-9: continue # Parallel
            
            t = ((x1 - px1) * (py1 - py2) - (y1 - py1) * (px1 - px2)) / det
            u = ((x1 - px1) * (y1 - y2) - (y1 - py1) * (x1 - x2)) / det
            
            epsilon = 1e-9
            if 0 - epsilon <= t <= 1 + epsilon and 0 - epsilon <= u <= 1 + epsilon:
                ix = x1 + t * (x2 - x1)
                iy = y1 + t * (y2 - y1)
                
                dist = (ix - x1)**2 + (iy - y1)**2
                if dist < min_dist:
                    min_dist = dist
                    closest_point = (ix, iy)
        
        return closest_point

    def apply_theme(self, theme_data):
        self.theme = theme_data
        
        # Update Root and Containers
        self.root.configure(bg=self.theme["bg_primary"])
        
        if hasattr(self, 'palette'): self.palette.update_theme(self.theme)
        
        # Update MiniMap
        if hasattr(self, 'minimap_frame'):
            self.minimap_frame.configure(bg=self.theme["bg_secondary"])
            self.minimap.configure(bg=self.theme["bg_primary"]) # Canvas bg should be primary
            self.update_minimap()

        # Update Floating UI Docks & Overlays
        floating_frames = ['bottom_dock', 'top_left_overlay', 'top_right_overlay', 'undo_redo_dock', 'menu_dock']
        for frame_name in floating_frames:
            if hasattr(self, frame_name):
                frame = getattr(self, frame_name)
                try:
                    # If it's the RoundedFrame (Canvas), update its main color
                    if isinstance(frame, RoundedFrame):
                         # Fix: Update both fill color AND canvas background (for corners)
                         # Corners should match the ROOT background (bg_primary)
                         
                         # Determine border/shadow based on theme
                         # Dark Mode: White border/shadow? Or just lighter?
                         # User requested "white background behind button" which turned out to be corners.
                         # Now user says "border and shadows to white" in dark mode.
                         
                         is_dark = self.theme["bg_primary"] != "white" and self.theme["bg_primary"] != "#F0F0F0" # More robust check? 
                         # Actually, checking if theme is dark_theme is better, but passing theme_data makes unique identity tricky if copied.
                         # Just check values. Dark theme bg_primary is #1E1E1E. Light is #F0F0F0.
                         
                         is_dark = (self.theme["bg_primary"] == "#1E1E1E")
                         
                         b_color = "white" if is_dark else "black"
                         # Increased shadow opacity as requested (was 80)
                         s_color = (255, 255, 255, 160) if is_dark else (0, 0, 0, 160)
                         
                         # FIX: Use canvas_bg for the CORNERS (bg_color) so they blend with the drawing area
                         # bg_primary is the ROOT background, but these docks float on the CANVAS.
                         frame.set_colors(color=self.theme["bg_secondary"], bg_color=self.theme["canvas_bg"],
                                          border_color=b_color, shadow_color=s_color)
                    else:
                         frame.configure(bg=self.theme["bg_secondary"])

                    # Determine children source
                    # For bottom_dock, buttons are in dock_content (if it existed) or directly on it
                    children = []
                    if frame_name == 'bottom_dock' and hasattr(self, 'dock_content'):
                        # Update the inner frame background too
                        self.dock_content.configure(bg=self.theme["bg_secondary"])
                        children = self.dock_content.winfo_children()
                    else:
                        children = frame.winfo_children()

                    # Update Children (Buttons)
                    for child in children:
                        # Skip special widgets like color_btn canvas container (BUT NOT RoundedButton)
                        if isinstance(child, tk.Canvas) and not isinstance(child, RoundedButton) and frame_name == 'bottom_dock':
                             child.configure(bg=self.theme["bg_secondary"])
                             continue
                        
                        try:
                            # Update Button Backgrounds
                            child.configure(bg=self.theme["bg_secondary"])
                            
                            # Update RoundedButton specifics
                            if isinstance(child, RoundedButton):
                                child.parent_bg = self.theme["bg_secondary"] # UPDATE parent_bg so it doesn't revert to white!
                                child.configure_color(bg_hover=self.theme["btn_hover"])
                                child.draw() # Redraw with new transparency
                            
                            # Handle active background for standard buttons
                            if 'activebackground' in child.keys():
                                try: child['activebackground'] = self.theme["btn_hover"]
                                except: pass
                            
                            if 'fg' in child.keys():
                                try: child['fg'] = self.theme["text_color"]
                                except: pass
                        except: pass
                        
                except Exception as e:
                    print(f"Theme update error for {frame_name}: {e}")
                    
        # Update Undo/Redo explicit icons
        if hasattr(self, 'undo_btn_dock') and hasattr(self, 'l_undo_img'):
            is_dark = (self.theme["bg_primary"] == "#1E1E1E")
            self.undo_btn_dock.image = self.d_undo_img if is_dark else self.l_undo_img
            self.undo_btn_dock.draw()
            
        if hasattr(self, 'redo_btn_dock') and hasattr(self, 'l_redo_img'):
            is_dark = (self.theme["bg_primary"] == "#1E1E1E")
            self.redo_btn_dock.image = self.d_redo_img if is_dark else self.l_redo_img
            self.redo_btn_dock.draw()
        

        
        # Update Pen Settings Popup (if exists)
        if hasattr(self, 'pen_settings_frame') and self.pen_settings_frame:
             try:
                 self.pen_settings_frame.configure(bg="white")
                 pass 
             except: pass

        # Update Canvas
        if hasattr(self, 'c'):
            self.c.configure(bg=self.theme["canvas_bg"])

        # Re-apply active state colors if any
        self.update_tool_buttons()

    def reset(self, event):
        self.resizing = False
        self.dragging = False
        self.dragging_object = False
        self.shape_id = None
        self._text_selection_started = False

        # Only clear selection if we are NOT in select mode
        # or if explicitly forcing a reset (which might be needed elsewhere)
        if self.shape != 'select':
             self.clear_selection()
             self.deselect_tool()
        
        if self.shape != 'bucket': # Don't reset cursor if bucket
             self.c.config(cursor='arrow')

    def cancel_action(self, event=None):
        # If drawing a polygon, Esc completes the drawing if possible
        if self.shape == 'polygon' and hasattr(self, 'poly_points') and self.poly_points:
             if len(self.poly_points) >= 6:
                 self.finish_polygon(event)
             else:
                 self.poly_points = []
                 self.c.delete("poly_temp")
                 self.c.delete("poly_guide")
             self.deselect_tool()
             return
             
        self.reset(event)

    def clear_selection(self):
        self.c.delete('resize')
        if self.selected_objects:
            for obj in self.selected_objects:
                if obj in self.selected_object_colors:
                     orig_color = self.selected_object_colors[obj]
                     item_type = self.c.type(obj)
                     if item_type in ["rectangle", "oval"]:
                        self.c.itemconfig(obj, outline=orig_color)
                     elif item_type in ["line", "text"]:
                        self.c.itemconfig(obj, fill=orig_color)

            self.selected_objects = []
            self.selected_object_colors = {}
        
        self.hide_property_bar()

    def changeW(self, e):
        self.penwidth = int(float(e))

    def clear(self):
        self.c.delete(tk.ALL)
        self.objects.clear()
        self.selected_objects = []
        self.selected_object_colors = {}
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.scale = 1.0 # Reset zoom
        
        if self.grid_on:
            self.draw_grid()
            
        self.update_minimap()

    def change_fg(self):
        color = askcolor(color=self.color_fg)[1]
        if color:
            self.color_fg = color
            for obj in self.selected_objects:
                item_type = self.c.type(obj)
                self.selected_object_colors[obj] = color
                if item_type in ["rectangle", "oval"]:
                    self.c.itemconfig(obj, outline=color)
                elif item_type in ["line", "text"]:
                    self.c.itemconfig(obj, fill=color)

    def change_bg(self):
        color = askcolor(color=self.color_bg)[1]
        if color:
            self.color_bg = color
            self.c['bg'] = self.color_bg

    def change_fill_color(self):
        color = askcolor(color=self.fill_color)[1]
        if color:
            self.fill_color = color
            for obj in self.selected_objects:
                item_type = self.c.type(obj)
                if item_type in ["rectangle", "oval"]:
                    self.c.itemconfig(obj, fill=color)
                # print(f"DEBUG: Changing fill color to {color}")


    def select_tool(self, tool):
        # Toggle logic for Polygon
        if tool == 'polygon' and self.shape == 'polygon':
             if len(self.poly_points) > 2:
                 self.finish_polygon(None)
             else:
                 self.shape = 'brush' 
                 self.poly_points = [] 
                 self.c.delete("poly_temp")
                 self.c.delete("poly_guide")
        else:
             self.shape = tool

        self.eraser_on = False
        if self.shape == 'bucket':
            self.c.config(cursor='target')
        elif self.shape == 'hand':
            self.c.config(cursor='fleur')
        elif self.shape == 'brush':
             self.c.config(cursor='pencil') # Or 'dot', or custom
        else:
            self.c.config(cursor='arrow')
            
        self.update_tool_buttons()

    def deselect_tool(self, event=None):
        """Reset validation or tool to Select/Arrow."""
        self.shape = 'select' # Or None? 'select' logic exists? 
        # Actually usually 'brush' is default? Or just selection mode.
        # Let's map to 'select' which seems to be the default for moving items.
        
        self.shape = 'select' # This enables moving objects
        self.eraser_on = False
        self.c.config(cursor='arrow')
        self.update_tool_buttons()

    def activate_eraser(self):
        self.shape = 'erase'
        self.eraser_on = True
        self.c.config(cursor='dot') # Better cursor for eraser
        self.update_tool_buttons()

    def toggle_eraser(self):
        if self.shape == 'erase':
            # Toggle back to brush
            self.select_tool('brush')
        else:
            self.activate_eraser()

    def erase(self, event):
        import time
        
        # Auto-sizing logic for eraser based on mouse speed
        current_time = time.time()
        
        if not hasattr(self, 'last_erase_time') or not hasattr(self, 'last_erase_x'):
            self.last_erase_time = current_time
            self.last_erase_x, self.last_erase_y = event.x, event.y
            velocity = 0
        else:
            dt = current_time - self.last_erase_time
            dx = event.x - self.last_erase_x
            dy = event.y - self.last_erase_y
            dist = (dx**2 + dy**2)**0.5
            
            # Prevent division by zero
            velocity = dist / dt if dt > 0 else 0
            
        # Map velocity to eraser size (min: 20, max: 80)
        min_size = 20
        max_size = 80 # Reduced from 150 for better control
        
        # Scale velocity to size range (adjust multiplier for sensitivity)
        target_size = min_size + (velocity * 0.04)
        
        # Clamp value
        self.eraser_size = max(min_size, min(target_size, max_size))
        
        # Update references for next frame
        self.last_erase_time = current_time
        self.last_erase_x, self.last_erase_y = event.x, event.y
        
        # Convert to canvas coordinates for accurate detection
        cx = self.c.canvasx(event.x)
        cy = self.c.canvasy(event.y)
        r = (self.eraser_size / 2) / self.scale # Account for zoom
        
        # Visual indicator
        self.c.delete("eraser_cursor")
        self.c.create_oval(cx - r, cy - r, cx + r, cy + r, outline="red", dash=(2, 2), tags=("eraser_cursor", "ui"))
        
        # Precise Circular Detection
        items = self.c.find_overlapping(cx - r, cy - r, cx + r, cy + r)
        for item in items:
            tags = self.c.gettags(item)
            if any(t in tags for t in ["grid_line", "laser", "poly_guide", "minimap", "ui"]):
                continue
            
            # Distance Check for True Circular Erase
            bbox = self.c.bbox(item)
            if bbox:
                # Approximate distance from center to bounding box
                ix = (bbox[0] + bbox[2]) / 2
                iy = (bbox[1] + bbox[3]) / 2
                dist = ((cx - ix)**2 + (cy - iy)**2)**0.5
                
                # If the center of the item is outside the circle, skip it (approximate but much better than square)
                # For lines/large objects, we check if any corner of the bbox is inside
                corners = [(bbox[0], bbox[1]), (bbox[2], bbox[1]), (bbox[0], bbox[3]), (bbox[2], bbox[3])]
                is_inside = any(((cx - px)**2 + (cy - py)**2)**0.5 <= r for px, py in corners)
                
                if not is_inside and dist > r:
                    continue

            try:
                item_data = self.delete_item(item)
                if hasattr(self, 'current_erase_batch'):
                    self.current_erase_batch.append(item_data)
            except Exception:
                pass

        self.old_x = event.x
        self.old_y = event.y

    def restore_item(self, item_data):
        """Re-creates an item on the canvas from its data dictionary."""
        try:
            itype = item_data['type']
            coords = item_data['coords']
            config = item_data.get('config', {})
            tags = item_data.get('tags', [])
            
            new_id = None
            
            if itype == 'line':
                new_id = self.c.create_line(*coords, **config)
            elif itype == 'rectangle':
                new_id = self.c.create_rectangle(*coords, **config)
            elif itype == 'oval':
                new_id = self.c.create_oval(*coords, **config)
            elif itype == 'text':
                base_font = item_data.get('base_font')
                base_width = item_data.get('base_width')
                
                # Apply current scale to font and width
                if base_font:
                    scaled_size = int(base_font[1] * self.scale)
                    # Handle font as tuple/list or string
                    if isinstance(base_font, (tuple, list)):
                        config['font'] = (base_font[0], scaled_size, *base_font[2:])
                    else:
                        # Should not happen with new tracking but be safe
                        pass 
                
                if base_width:
                    config['width'] = base_width * self.scale
                    
                new_id = self.c.create_text(*coords, **config)
                
                # Re-register base zoom data
                if base_font:
                    self.text_base_sizes[new_id] = base_font
                if base_width:
                    if not hasattr(self, 'text_base_widths'): self.text_base_widths = {}
                    self.text_base_widths[new_id] = base_width

            elif itype == 'image':
                # Re-creation of image
                img_obj = None
                if 'stored_image' in item_data:
                    img_obj = item_data['stored_image']
                elif 'image_path' in item_data and os.path.exists(item_data['image_path']):
                    img_obj = Image.open(item_data['image_path'])
                
                if img_obj:
                        # Scaling logic for restoration
                        base_size = item_data.get('image_base_size')
                        if base_size:
                            draw_w = int(base_size[0] * self.scale)
                            draw_h = int(base_size[1] * self.scale)
                        else:
                            # Fallback to current dimensions if base is missing
                            draw_w, draw_h = img_obj.width, img_obj.height
                            
                        photo = ImageTk.PhotoImage(img_obj.resize((max(1, draw_w), max(1, draw_h)), Image.LANCZOS))
                        new_id = self.c.create_image(coords[0], coords[1], image=photo, anchor=getattr(tk, config.get('anchor', 'nw').upper(), tk.NW))
                        
                        # Store reference
                        if not hasattr(self, 'image_refs'): self.image_refs = []
                        self.image_refs.append(photo)
                        
                        # Store High-Res Master
                        if not hasattr(self, 'stored_images'): self.stored_images = {}
                        self.stored_images[new_id] = img_obj
                        
                        # Re-register base size
                        if base_size:
                             self.image_base_sizes[new_id] = base_size
                        else:
                             # Default to scaled-down size as base? No, better estimate.
                             self.image_base_sizes[new_id] = (draw_w / self.scale, draw_h / self.scale)
                        
                        # Store path if available
                        if 'image_path' in item_data:
                            self.image_files[new_id] = item_data['image_path']
                        
                        # Restore metadata if available
                        if 'metadata' in item_data:
                            self.image_metadata[new_id] = item_data['metadata']

            if new_id:
                # Restore tags
                for tag in tags:
                    self.c.addtag_withtag(tag, new_id)
                self.objects.append(new_id)
            
            return new_id
        except Exception as e:
            print(f"Error restoring item: {e}")
            return None

    def undo(self, event=None):
        if self.undo_stack:
            item = self.undo_stack.pop()
            action = item[0]
            
            # Legacy Check: If item is tuple len > 1 but not matching new format?
            # New format: (action, ...)
            # Old format: ('create_line', id, ...)
            
            self.redo_stack.append(item)
            
            if action == 'create_flowchart':
                # ('create_flowchart', created_ids, data)
                created_ids = item[1]
                
                # Cleanup group registration
                if created_ids and isinstance(created_ids, list):
                    tags = self.c.gettags(created_ids[0])
                    group_tag = next((t for t in tags if t.startswith("flowchart_group_")), None)
                    if group_tag and hasattr(self, 'groups') and group_tag in self.groups:
                        del self.groups[group_tag]

                for xid in created_ids if isinstance(created_ids, list) else [created_ids]:
                    self.c.delete(xid)
                    if getattr(self, 'objects', None) and xid in self.objects: 
                        self.objects.remove(xid)
                    # Cleanup connections
                    if hasattr(self, 'connections'):
                        if xid in self.connections:
                            del self.connections[xid]
                        # Also remove if it was a start or end node for any other line
                        to_remove = [lid for lid, conn in self.connections.items() if conn.get('start') == xid or conn.get('end') == xid]
                        for lid in to_remove:
                            if lid in self.connections: del self.connections[lid]

            elif action.startswith('create_'):
                item_id = item[1]
                if action == 'create_node':
                    group_tag = f"node_group_{item_id}"
                    for member in self.c.find_withtag(group_tag):
                        self.c.delete(member)
                        if member in self.objects: self.objects.remove(member)
                else:
                    # Creation -> Undo = Delete
                    self.c.delete(item_id)
                    if item_id in self.objects: self.objects.remove(item_id)
                
            elif action == 'add_image':
                # Creation -> Undo = Delete
                item_id = item[1]
                self.c.delete(item_id)
                # Cleanup handle
                self.c.delete('resize')
                if item_id in self.objects: self.objects.remove(item_id)
                
            elif action == 'move':
                # ('move', [ids], dx, dy)
                ids, dx, dy = item[1], item[2], item[3]
                for xid in ids:
                    self.c.move(xid, -dx, -dy)
                    self.update_connected_lines(xid)
            
            elif action == 'delete':
                # ('delete', [item_data_list]) -> Restore items
                item_data_list = item[1]
                restored_ids = []
                for data in item_data_list:
                    new_id = self.restore_item(data)
                    if new_id: restored_ids.append(new_id)
                
                # CRITICAL: Update the redo stack item to use these specific IDs
                # Replacing ( 'delete', data_list ) with ( 'delete', restored_ids )
                if self.redo_stack:
                    self.redo_stack[-1] = ('delete', restored_ids)
                
                # Selection restoration
                self.selected_objects = restored_ids
                
            elif action == 'resize':
                # ('resize', item_id, start_coords, end_coords)
                item_id, start_coords, end_coords = item[1], item[2], item[3]
                self.c.coords(item_id, *start_coords)
                self.update_connected_lines(item_id)
                # Update handle if selected
                if self.resize_target == item_id:
                    self.update_resize_handle()

            elif action == 'crop':
                # ('crop', item_id, old_img, old_bbox, new_img, new_bbox)
                item_id, old_img, old_bbox, new_img, new_bbox = item[1], item[2], item[3], item[4], item[5]
                self.stored_images[item_id] = old_img
                self.c.coords(item_id, old_bbox[0], old_bbox[1])
                
                # Re-render at current zoom
                new_w = old_bbox[2] - old_bbox[0]
                new_h = old_bbox[3] - old_bbox[1]
                tk_img = ImageTk.PhotoImage(old_img.resize((int(new_w), int(new_h)), Image.LANCZOS))
                self.image_refs.append(tk_img)
                self.c.itemconfig(item_id, image=tk_img)
                
                self.image_base_sizes[item_id] = (new_w / self.scale, new_h / self.scale)

            elif action == 'ink_to_text':
                # ('ink_to_text', text_id, item_data_list)
                text_id, item_data_list = item[1], item[2]
                
                # Serialize text before deleting so we can redo it
                text_data = self.delete_item(text_id)
                self.c.delete(text_id)
                if text_id in self.objects: self.objects.remove(text_id)
                
                restored_ids = []
                for data in item_data_list:
                    new_id = self.restore_item(data)
                    if new_id: restored_ids.append(new_id)
                
                # Transform the redo stack item entirely
                self.redo_stack[-1] = ('ink_to_text_redo', text_data, restored_ids, item_data_list)

            elif action == 'batch_move':
                # ('batch_move', [(members, dx, dy), ...])
                for members, dx, dy in item[1]:
                    for m in members:
                        try:
                            self.c.move(m, -dx, -dy)
                            self.update_connected_lines(m)
                        except tk.TclError:
                            pass


            self.update_scrollregion()
            self.update_minimap()

    def redo(self, event=None):
        if self.redo_stack:
            item = self.redo_stack.pop()
            action = item[0]
            self.undo_stack.append(item)

            if action.startswith('create_'):
                # Creation -> Redo = Re-create (Restore)
                new_id = None
                data = item[2:]
                
                if action == 'create_line':
                     new_id = self.c.create_line(*data[:-2], fill=data[-2], width=data[-1], capstyle=tk.ROUND)
                elif action == 'create_rectangle':
                     new_id = self.c.create_rectangle(*data[:-2], outline=data[-2], width=data[-1])
                elif action == 'create_oval':
                     new_id = self.c.create_oval(*data[:-2], outline=data[-2], width=data[-1])
                elif action == 'create_polygon':
                     new_id = self.c.create_polygon(*data[:-3], outline=data[-3], width=data[-2], fill=data[-1])
                elif action == 'create_text':
                    # x, y, text, color, size, [width]
                    kw = {}
                    if len(data) > 5:
                        kw['width'] = data[5] * self.scale
                    
                    scaled_size = int(data[4] * self.scale)
                    new_id = self.c.create_text(data[0], data[1], text=data[2], fill=data[3], font=("Arial", scaled_size), **kw)
                    # Register base size
                    self.text_base_sizes[new_id] = ("Arial", data[4])
                    if len(data) > 5:
                        if not hasattr(self, 'text_base_widths'): self.text_base_widths = {}
                        self.text_base_widths[new_id] = data[5]
                elif action == 'create_polygon':
                    # id, points, color, fill, width
                    new_id = self.c.create_polygon(data[1], outline=data[2], fill=data[3], width=data[4])
                elif action == 'create_node':
                    # data = (x, y, text, bg_color, font, shape, padding, width_limit)
                    new_id = self.create_node(*data, record_undo=False)
                elif action == 'create_arrow':
                    w = data[-1]
                    new_id = self.c.create_line(*data[:-2], fill=data[-2], width=w, arrow=tk.LAST, arrowshape=(w*3, w*4, w*1.5))
                elif action == 'create_brush':
                    # data = (points, color, width)
                    new_id = self.c.create_line(*data[0], fill=data[1], width=data[2], capstyle=tk.ROUND, smooth=True)
                elif action == 'create_highlighter':
                    new_id = self.c.create_line(*data[0], fill=data[1], width=data[2], capstyle=tk.ROUND, smooth=True, stipple='gray50')

                if new_id:
                    if action != 'create_node':
                        self.objects.append(new_id)
                    # Update stack item with new ID
                    new_item = list(item)
                    new_item[1] = new_id
                    self.undo_stack[-1] = tuple(new_item)

            elif action == 'create_flowchart':
                # Redo = re-draw using stored JSON data
                gv_data = item[2]
                new_ids = self.draw_native_graphviz(gv_data, push_undo=False)
                new_item = ('create_flowchart', new_ids, gv_data)
                self.undo_stack[-1] = new_item
                
            elif action == 'ink_to_text_redo':
                # ('ink_to_text_redo', text_data, restored_ids, item_data_list)
                text_data, current_line_ids, original_item_data_list = item[1], item[2], item[3]
                
                for xid in current_line_ids:
                    self.c.delete(xid)
                    if xid in self.objects: self.objects.remove(xid)
                
                new_text_id = self.restore_item(text_data)
                # Reform the undo logic
                self.undo_stack[-1] = ('ink_to_text', new_text_id, original_item_data_list)
                
            elif action == 'batch_move':
                # ('batch_move', [(members, dx, dy), ...])
                for members, dx, dy in item[1]:
                    for m in members:
                        try:
                            self.c.move(m, dx, dy)
                            self.update_connected_lines(m)
                        except tk.TclError:
                            pass

            elif action == 'add_image':
                # ('add_image', id, path, x, y)
                path, x, y = item[2], item[3], item[4]
                try:
                    # Manually restore image without triggering new action logic
                    if os.path.exists(path):
                        img = Image.open(path)
                        # We try to restore to a sensible size (similar to original logic)
                        view_w = self.c.winfo_width()
                        view_h = self.c.winfo_height()
                        if view_w <= 1: view_w = 800
                        if view_h <= 1: view_h = 600
                        
                        target_w = int(view_w * 0.8)
                        target_h = int(view_h * 0.8)
                        
                        # Use aspect ratio logic
                        aspect = img.width / img.height
                        if aspect < 0.5:
                            if img.width > target_w:
                                ratio = target_w / img.width
                                new_h = int(img.height * ratio)
                                img = img.resize((target_w, new_h), Image.LANCZOS)
                        else:
                            img.thumbnail((target_w, target_h), Image.LANCZOS)
                        
                        photo = ImageTk.PhotoImage(img)
                        new_id = self.c.create_image(x, y, anchor=tk.NW, image=photo)
                        
                        # Restore metadata/refs
                        self.image_base_sizes[new_id] = (img.width, img.height)
                        self.resize_handle = self.c.create_rectangle(x + img.width - 10, y + img.height - 10,
                                                                         x + img.width, y + img.height, outline='', fill='red', tags='resize')
                        self.image_files[new_id] = path
                        if not hasattr(self, 'image_refs'): self.image_refs = []
                        self.image_refs.append(photo)
                        self.objects.append(new_id)
                        
                        # Update Stack with new ID
                        new_item = list(item)
                        new_item[1] = new_id
                        self.undo_stack[-1] = tuple(new_item)
                except Exception as e:
                    print(f"Redo Image Error: {e}")
                

                
            elif action == 'move':
                ids, dx, dy = item[1], item[2], item[3]
                for xid in ids:
                    self.c.move(xid, dx, dy)
                    self.update_connected_lines(xid)

            elif action == 'delete':
                # redo delete: item[1] is now a list of IDs (from undo side) 
                # OR raw data list (if deleted once). Handle both.
                ids_or_data = item[1]
                if ids_or_data and not isinstance(ids_or_data[0], dict):
                    # It's a list of IDs (from a previous Undo)
                    for xid in list(ids_or_data):
                        if self.c.find_withtag(xid):
                            self.delete_item(xid)
                elif self.selected_objects:
                    # Fallback to selection only if we don't have IDs
                    for obj in list(self.selected_objects):
                        self.delete_item(obj)
                    self.selected_objects.clear()
            
            elif action == 'resize':
                item_id, start_coords, end_coords = item[1], item[2], item[3]
                self.c.coords(item_id, *end_coords)
                self.update_connected_lines(item_id)
                if getattr(self, 'resize_target', None) == item_id:
                    self.update_resize_handle()

            elif action == 'crop':
                # ('crop', item_id, old_img, old_bbox, new_img, new_bbox)
                item_id, old_img, old_bbox, new_img, new_bbox = item[1], item[2], item[3], item[4], item[5]
                self.stored_images[item_id] = new_img
                self.c.coords(item_id, new_bbox[0], new_bbox[1])
                
                # Re-render at current zoom
                new_w = new_bbox[2] - new_bbox[0]
                new_h = new_bbox[3] - new_bbox[1]
                tk_img = ImageTk.PhotoImage(new_img.resize((int(new_w), int(new_h)), Image.LANCZOS))
                self.image_refs.append(tk_img)
                self.c.itemconfig(item_id, image=tk_img)
                
                self.image_base_sizes[item_id] = (new_w / self.scale, new_h / self.scale)

            self.update_scrollregion()
            self.update_minimap()

    def modern_askstring(self, title, prompt, initialvalue=""):
        """A modern, theme-aware replacement for simpledialog.askstring."""
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Determine theme colors
        bg_color = self.theme.get("bg_primary", "#F0F0F0")
        fg_color = self.theme.get("text_color", "#000000")
        btn_bg = self.theme.get("btn_bg", "#FFFFFF")
        btn_hover = self.theme.get("btn_hover", "#E0E0E0")
        accent = self.theme.get("accent", "#AED6F1")
        
        dialog.configure(bg=bg_color, padx=20, pady=20)
        
        lbl = tk.Label(dialog, text=prompt, bg=bg_color, fg=fg_color, font=("Segoe UI", 12))
        lbl.pack(anchor="w", pady=(0, 10))
        
        entry = tk.Entry(dialog, bg=btn_bg, fg=fg_color, font=("Segoe UI", 11), 
                         insertbackground=fg_color, relief=tk.FLAT, highlightthickness=1, 
                         highlightbackground=self.theme.get("divider_color", "#CCC"),
                         highlightcolor=accent)
        entry.pack(fill="x", pady=(0, 20), ipady=5)
        if initialvalue:
            entry.insert(0, initialvalue)
        entry.select_range(0, tk.END)
        entry.focus_set()
        
        result = [None]
        
        def on_submit(event=None):
            result[0] = entry.get()
            dialog.destroy()
            
        def on_cancel(event=None):
            dialog.destroy()
            
        dialog.bind('<Return>', on_submit)
        dialog.bind('<Escape>', on_cancel)
        
        btn_frame = tk.Frame(dialog, bg=bg_color)
        btn_frame.pack(fill="x")
        
        # Submit Button
        submit_btn = tk.Button(btn_frame, text="OK", command=on_submit, 
                               bg=accent, fg="white" if accent != "#AED6F1" else "black", 
                               font=("Segoe UI", 10, "bold"), relief=tk.FLAT, cursor="hand2",
                               padx=15, pady=5)
        submit_btn.pack(side="left", expand=True, fill="x", padx=(0, 5))
        
        # Cancel Button
        cancel_btn = tk.Button(btn_frame, text="Cancel", command=on_cancel, 
                               bg=btn_bg, fg=fg_color, 
                               font=("Segoe UI", 10), relief=tk.FLAT, cursor="hand2",
                               padx=15, pady=5)
        cancel_btn.pack(side="left", expand=True, fill="x", padx=(5, 0))
        
        # Center dialog relative to main window
        dialog.update_idletasks()
        w = max(300, dialog.winfo_reqwidth())
        h = dialog.winfo_reqheight()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (w // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (h // 2)
        dialog.geometry(f"{w}x{h}+{x}+{y}")
        
        self.root.wait_window(dialog)
        return result[0]

    def modern_choice(self, title, prompt, options):
        """A modern, theme-aware dialog for choosing from multiple options."""
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Determine theme colors
        bg_color = self.theme.get("bg_primary", "#F0F0F0")
        fg_color = self.theme.get("text_color", "#000000")
        btn_bg = self.theme.get("btn_bg", "#FFFFFF")
        btn_hover = self.theme.get("btn_hover", "#E0E0E0")
        accent = self.theme.get("accent", "#AED6F1")
        
        dialog.configure(bg=bg_color, padx=25, pady=25)
        
        lbl = tk.Label(dialog, text=prompt, bg=bg_color, fg=fg_color, font=("Segoe UI", 13, "bold"))
        lbl.pack(anchor="w", pady=(0, 20))
        
        result = [None]
        
        def select_option(opt):
            result[0] = opt
            dialog.destroy()

        def on_cancel(event=None):
            dialog.destroy()
            
        dialog.bind('<Escape>', on_cancel)
        
        for opt in options:
            btn = tk.Button(dialog, text=opt, command=lambda o=opt: select_option(o), 
                            bg=btn_bg, fg=fg_color, 
                            font=("Segoe UI", 11), relief=tk.FLAT, cursor="hand2",
                            padx=15, pady=10, activebackground=accent)
            btn.pack(fill="x", pady=5)
            
            # Hover effect
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=btn_hover))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=btn_bg))
            
        # Cancel Button
        cancel_btn = tk.Button(dialog, text="Cancel", command=on_cancel, 
                               bg=bg_color, fg="#888", 
                               font=("Segoe UI", 10), relief=tk.FLAT, cursor="hand2",
                               pady=10)
        cancel_btn.pack(fill="x", pady=(10, 0))
        
        # Center dialog relative to main window
        dialog.update_idletasks()
        w = max(350, dialog.winfo_reqwidth())
        h = dialog.winfo_reqheight()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (w // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (h // 2)
        dialog.geometry(f"{w}x{h}+{x}+{y}")
        
        self.root.wait_window(dialog)
        return result[0]

    def add_image(self):
        file_paths = filedialog.askopenfilenames(filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"), ("All files", "*.*")])
        if not file_paths:
            return
            
        if not hasattr(self, 'stored_images'): self.stored_images = {}
        if not hasattr(self, 'photo_images'): self.photo_images = {}
        if not hasattr(self, 'image_base_sizes'): self.image_base_sizes = {}
        
        offset_x = 100
        offset_y = 100
        
        for file_path in file_paths:
            try:
                self.image = Image.open(file_path)
                
                # Limit initial display size if huge, but keep original
                display_w, display_h = self.image.width, self.image.height
                max_dim = 800
                if display_w > max_dim or display_h > max_dim:
                    ratio = min(max_dim/display_w, max_dim/display_h)
                    display_w = int(display_w * ratio)
                    display_h = int(display_h * ratio)
                    self.photo_image = ImageTk.PhotoImage(self.image.resize((display_w, display_h), Image.LANCZOS))
                else:
                    self.photo_image = ImageTk.PhotoImage(self.image)

                self.image_id = self.c.create_image(offset_x, offset_y, anchor=tk.NW, image=self.photo_image)
                
                # Update resize handle to attach to the last inserted image
                h_size = 10 / self.scale
                self.c.delete('resize')
                self.resize_handle = self.c.create_rectangle(offset_x + display_w - h_size, offset_y + display_h - h_size,
                                                             offset_x + display_w, offset_y + display_h, outline='',
                                                             fill='red',
                                                             tags='resize')
                self.resize_target = self.image_id
                
                # Keep hard references so images don't get garbage collected
                self.photo_images[self.image_id] = self.photo_image
                self.image_files[self.image_id] = file_path
                self.stored_images[self.image_id] = self.image
                self.image_base_sizes[self.image_id] = (int(display_w / self.scale), int(display_h / self.scale))
                
                # Save the state for undo
                self.undo_stack.append(('add_image', self.image_id, file_path, offset_x, offset_y))
                self.objects.append(self.image_id)
                self.update_scrollregion()
                self.update_minimap()
                
                # Stagger the next image visually
                offset_x += 40
                offset_y += 40
            except Exception as e:
                messagebox.showerror("Error", f"Could not open image {file_path}: {e}")
                
        self.redo_stack.clear()

    def use_brush(self):
        self.select_tool('brush')

    def create_sticky_note(self):
        text = self.modern_askstring("Sticky Note", "Enter note text:")
        if text is None:
            return
        if not text.strip():
            text = "New Sticky Note\n(Double-click to edit)"
            
        cx = self.c.canvasx(self.c.winfo_width() / 2)
        cy = self.c.canvasy(self.c.winfo_height() / 2)
        
        self.create_node(cx, cy, text, bg_color="#FFF9C4", font=("Arial", 12), shape="rectangle", padding=15, width_limit=250)
        self.update_scrollregion()
        self.update_minimap()

    def update_resize_handle(self):
        target = getattr(self, 'resize_target', None)
        if target:
            bbox = self.c.bbox(target)
            if bbox:
                x1, y1, x2, y2 = bbox
                h_size = 10 / self.scale
                self.c.coords('resize', x2 - h_size, y2 - h_size, x2, y2)

    def display_interactive_image(self, file_path, metadata=None):
        """Loads an image onto the canvas and makes it interactive (movable/resizable)."""
        try:
            # Store ORIGINAL PIL image in stored_images for high-quality zooming
            orig_pil = Image.open(file_path)
            self.image = orig_pil.copy() # Use a copy for display-time thumbnailing
            
            # --- Auto-Fit Logic ---
            # Get current viewport size (or fallback to screen size if not ready)
            view_w = self.c.winfo_width()
            view_h = self.c.winfo_height()
            
            if view_w <= 1: view_w = self.root.winfo_screenwidth()
            if view_h <= 1: view_h = self.root.winfo_screenheight()
            
            # Target size: 80% of view
            target_w = int(view_w * 0.8)
            target_h = int(view_h * 0.8)
            
            # --- Smart Scaling Fix ---
            # If image is very tall (Aspect Ratio < 0.5), DO NOT fit to height.
            # Only fit to width to ensure text remains readable.
            # User can pan to see the rest.
            
            aspect_ratio = self.image.width / self.image.height
            
            if aspect_ratio < 0.5:
                # Tall image: Constrain by width only (if wider than target)
                if self.image.width > target_w:
                     # Resize width to target, keep aspect ratio
                     ratio = target_w / self.image.width
                     new_h = int(self.image.height * ratio)
                     self.image = self.image.resize((target_w, new_h), Image.LANCZOS) # Use resize, thumbnail is strict
                # If width is small enough, keep original size (don't shrink height)
            else:
                # Normal image: Fit inside box (Standard thumbnail behavior)
                self.image.thumbnail((target_w, target_h), Image.LANCZOS)
            
            self.photo_image = ImageTk.PhotoImage(self.image)
            
            # Center it roughly
            x, y = 100, 100
    
            self.image_id = self.c.create_image(x, y, anchor=tk.NW, image=self.photo_image)
            self.resize_target = self.image_id
            
            # Store in high-res master map for zooming quality
            if not hasattr(self, 'stored_images'): self.stored_images = {}
            self.stored_images[self.image_id] = orig_pil
            
            # Store base size tracking (displayed size at current zoom level normalized to scale 1.0)
            self.image_base_sizes[self.image_id] = (int(self.image.width / self.scale), int(self.image.height / self.scale))
            
            # Create resize handle
            self.c.delete('resize')
            h_size = 10 / self.scale
            self.resize_handle = self.c.create_rectangle(x + self.image.width - h_size, y + self.image.height - h_size,
                                                            x + self.image.width, y + self.image.height, outline='',
                                                            fill='red',
                                                            tags='resize')
            
            self.image_files[self.image_id] = file_path
            if metadata:
                self.image_metadata[self.image_id] = metadata
            
            # Save state
            self.undo_stack.append(('add_image', self.image_id, file_path, x, y))
            self.redo_stack.clear()
            
            # Store ref to prevent GC
            if not hasattr(self, 'image_refs'): self.image_refs = []
            self.image_refs.append(self.photo_image)
            self.objects.append(self.image_id)
            self.update_scrollregion()
            self.update_minimap()
            return self.image_id

            
        except Exception as e:
            messagebox.showerror("Error", f"Could not open image: {e}")

    def save_project(self, event=None):
        """Saves the current whiteboard state to a .aiwb JSON file."""
        file_path = filedialog.asksaveasfilename(defaultextension=".aiwb", filetypes=[("AI Whiteboard", "*.aiwb"), ("JSON", "*.json")])
        if not file_path: return

        data = {
            "version": "1.0",
            "canvas_bg": self.c.cget("bg"),
            "scale": self.scale,  # Save current zoom scale
            "objects": [],
            "connections": []
        }

        # 1. Serialize Objects
        for item_id in self.objects:
            tags = self.c.gettags(item_id)
            if "selection_ring" in tags or "preview" in tags: continue
            
            # Determine type
            itype = self.c.type(item_id)
            coords = self.c.coords(item_id)
            
            obj_data = {
                "id": item_id,
                "type": itype,
                "coords": coords,
                "tags": list(tags),
                "config": {}
            }
            
            # Config properties to save
            keys = ['fill', 'outline', 'width', 'dash', 'text', 'font', 'arrow', 'anchor', 'justify', 'stipple', 'capstyle', 'smooth', 'joinstyle', 'arrowshape']
            for key in keys:
                try:
                    val = self.c.itemcget(item_id, key)
                    if val: obj_data["config"][key] = val
                except: pass
            
            # If Image, we need the file path (if stored) or can't save easily
            if itype == "image":
                path = self.image_files.get(item_id)
                if path:
                    obj_data["image_path"] = path
                
                # Save base size for zooming
                if item_id in self.image_base_sizes:
                    obj_data["image_base_size"] = self.image_base_sizes[item_id]
                
                # Save metadata if any
                if hasattr(self, 'image_metadata') and item_id in self.image_metadata:
                    obj_data["metadata"] = self.image_metadata[item_id]
            
            # If Text, save base sizes for zooming
            if itype == "text":
                if item_id in self.text_base_sizes:
                    obj_data["base_font"] = self.text_base_sizes[item_id]
                if item_id in self.text_base_widths:
                    obj_data["base_width"] = self.text_base_widths[item_id]
            
            # If shape/line, save base width for zooming
            if item_id in self.shape_base_widths:
                obj_data["shape_base_width"] = self.shape_base_widths[item_id]
                    
            data["objects"].append(obj_data)

        # 2. Serialize Connections
        for line_id, conn in self.connections.items():
            if line_id in self.objects: # Verify line still exists
                data["connections"].append({
                    "line_id": line_id,
                    "start": conn['start'],
                    "end": conn['end']
                })

        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
            messagebox.showinfo("Success", "Project saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save project: {e}")

    def load_project(self):
        """Loads a .aiwb project file."""
        file_path = filedialog.askopenfilename(filetypes=[("AI Whiteboard", "*.aiwb"), ("JSON", "*.json")])
        if not file_path: return

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                # Fallback for old JSON exports that don't have project structure
                messagebox.showwarning("Legacy Format", "Loading an older file format. Some layout properties (like Mind Map text structure) may not be perfectly preserved.")
                self.clear()
                self.c.configure(bg="white")
                self.scale = 1.0
                
                for item in data:
                    obj_type = item.get('type')
                    coords = item.get('coords')
                    if not obj_type or not coords: continue
                    
                    if obj_type == 'line':
                        self.c.create_line(*coords, fill=item.get('fill', ''), width=item.get('width', 1))
                    elif obj_type == 'rectangle':
                        self.c.create_rectangle(*coords, outline=item.get('outline', ''), width=item.get('width', 1), fill=item.get('fill', ''))
                    elif obj_type == 'oval':
                        self.c.create_oval(*coords, outline=item.get('outline', ''), width=item.get('width', 1), fill=item.get('fill', ''))
                    elif obj_type == 'text':
                        self.c.create_text(*coords, text=item.get('text', ''), fill=item.get('fill', ''), font=item.get('font', ''))
                
                self.objects = list(self.c.find_all())
                return
            
            # Clear Canvas
            self.clear()
            
            # Restore Background
            bg = data.get("canvas_bg", "white")
            self.c.configure(bg=bg) 
            
            # 0. Restore Scale
            self.scale = data.get("scale", 1.0)
            
            id_map = {}
            # 1. Restore Objects
            for obj in data.get("objects", []):
                itype = obj["type"]
                coords = obj["coords"]
                config = obj["config"]
                old_id = obj["id"]
                tags = tuple(obj["tags"])
                
                new_id = None
                
                if itype == "line":
                    new_id = self.c.create_line(coords, **config, tags=tags)
                elif itype == "rectangle":
                    new_id = self.c.create_rectangle(coords, **config, tags=tags)
                elif itype == "oval":
                    new_id = self.c.create_oval(coords, **config, tags=tags)
                elif itype == "polygon":
                    new_id = self.c.create_polygon(coords, **config, tags=tags)
                elif itype == "text":
                    new_id = self.c.create_text(coords, **config, tags=tags)
                    
                    # Track font size and width natively for zooming
                    font_cfg = config.get("font")
                    if font_cfg:
                        try:
                             # Safer parsing using tkfont
                             f = tkfont.Font(font=font_cfg)
                             family = f.actual("family")
                             size = f.actual("size")
                             self.text_base_sizes[new_id] = (family, size)
                        except:
                             # Fallback split logic
                             if isinstance(font_cfg, str):
                                parts = font_cfg.split()
                                if len(parts) >= 2 and parts[1].isdigit():
                                    self.text_base_sizes[new_id] = (parts[0], int(parts[1]))
                             elif isinstance(font_cfg, (list, tuple)) and len(font_cfg) >= 2:
                                self.text_base_sizes[new_id] = (font_cfg[0], int(font_cfg[1]))
                            
                    width_cfg = config.get("width")
                    if width_cfg is not None:
                        if not hasattr(self, 'text_base_widths'): self.text_base_widths = {}
                        try:
                            self.text_base_widths[new_id] = float(width_cfg)
                        except (ValueError, TypeError):
                            pass
                elif itype == "image":
                    path = obj.get("image_path")
                    base_size = obj.get("image_base_size")
                    
                    if path:
                        photo = None
                        pil_img = None
                        if path.startswith("PDF_SOURCE::"):
                            try:
                                # PDF_SOURCE::file_path::PAGE_i
                                parts = path.split("::")
                                if len(parts) >= 3:
                                    pdf_path = parts[1]
                                    page_idx = int(parts[2].replace("PAGE_", ""))
                                    if os.path.exists(pdf_path):
                                        import fitz
                                        pdf_doc = fitz.open(pdf_path)
                                        page = pdf_doc.load_page(page_idx)
                                        # Use high-res matrix for master
                                        pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
                                        pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                                        pdf_doc.close()
                            except Exception as e:
                                print(f"Error reloading PDF page: {e}")
                        elif os.path.exists(path):
                            try:
                                pil_img = Image.open(path)
                            except Exception as e:
                                print(f"Error loading image file: {e}")
                        
                        if not pil_img:
                            # Create a placeholder image if missing or load failed
                            w = base_size[0] if (base_size and isinstance(base_size, (list, tuple)) and len(base_size) >= 2) else 150
                            h = base_size[1] if (base_size and isinstance(base_size, (list, tuple)) and len(base_size) >= 2) else 150
                            try:
                                pil_img = Image.new("RGBA", (w, h), (255, 230, 230, 255))
                                draw = ImageDraw.Draw(pil_img)
                                draw.rectangle([0, 0, w - 1, h - 1], outline="red", width=2)
                                draw.text((5, h // 2 - 5), "Image Missing", fill="red")
                            except:
                                pil_img = Image.new("RGBA", (w, h), (255, 200, 200, 255))

                        # Apply cumulative crop if present in metadata
                        metadata = obj.get("metadata", {})
                        if "cumulative_crop" in metadata:
                            try:
                                crop_box = metadata["cumulative_crop"]
                                # Ensure crop box is within actual image bounds
                                mw, mh = pil_img.size
                                safe_box = (
                                    max(0, min(mw, crop_box[0])),
                                    max(0, min(mh, crop_box[1])),
                                    max(0, min(mw, crop_box[2])),
                                    max(0, min(mh, crop_box[3]))
                                )
                                if safe_box[2] > safe_box[0] and safe_box[3] > safe_box[1]:
                                    pil_img = pil_img.crop(safe_box)
                            except Exception as e:
                                print(f"Error applying restored crop: {e}")

                        # Apply scaling based on base_size and RESTORED scale
                        if base_size and isinstance(base_size, (list, tuple)) and len(base_size) >= 2:
                            target_w = int(base_size[0] * self.scale)
                            target_h = int(base_size[1] * self.scale)
                            if target_w > 0 and target_h > 0:
                                pil_img_resized = pil_img.resize((target_w, target_h), Image.LANCZOS)
                                photo = ImageTk.PhotoImage(pil_img_resized)
                            else:
                                photo = ImageTk.PhotoImage(pil_img)
                        else:
                            photo = ImageTk.PhotoImage(pil_img)
                            
                        if photo:
                            if not hasattr(self, 'image_refs'): self.image_refs = []
                            self.image_refs.append(photo)
                            # CRITICAL: Use **config to restore anchor, justify, etc.
                            new_id = self.c.create_image(coords, image=photo, tags=tags, **config)
                            self.image_files[new_id] = path # Track again
                        
                        # Restore high-res master image for cropping
                        if pil_img and new_id:
                            if not hasattr(self, 'stored_images'): self.stored_images = {}
                            self.stored_images[new_id] = pil_img
                            
                        # Restore metadata
                        if "metadata" in obj and new_id:
                            if not hasattr(self, 'image_metadata'): self.image_metadata = {}
                            self.image_metadata[new_id] = obj["metadata"]
                            
                        # Restore base size for zoom
                        if "image_base_size" in obj and new_id:
                            self.image_base_sizes[new_id] = obj["image_base_size"]
                
                # Restore text base metrics from explicit saved data
                if new_id and itype == "text":
                    if "base_font" in obj:
                        self.text_base_sizes[new_id] = obj["base_font"]
                    if "base_width" in obj:
                        if not hasattr(self, 'text_base_widths'): self.text_base_widths = {}
                        self.text_base_widths[new_id] = obj["base_width"]
                
                # Restore shape base width
                if new_id and "shape_base_width" in obj:
                    self.shape_base_widths[new_id] = obj["shape_base_width"]
                
                if new_id:
                    id_map[old_id] = new_id
                    if new_id not in self.objects:
                        self.objects.append(new_id)
            
            # 2. Rebuild self.groups and self.group_counter
            self.groups = {}
            max_group_num = 0
            for item in self.objects:
                tags = self.c.gettags(item)
                for tag in tags:
                    if tag.startswith("flowchart_group_") or tag.startswith("group_") or tag.startswith("node_group_"):
                        if tag not in self.groups:
                            self.groups[tag] = []
                        self.groups[tag].append(item)
                        
                        if tag.startswith("flowchart_group_"):
                            try:
                                num = int(tag.replace("flowchart_group_", ""))
                                max_group_num = max(max_group_num, num)
                            except: pass
            
            if hasattr(self, 'group_counter'):
                self.group_counter = max(getattr(self, 'group_counter', 0), max_group_num)
            else:
                self.group_counter = max_group_num

            # 3. Restore Connections
            self.connections = {}
            for conn in data.get("connections", []):
                old_line = conn["line_id"]
                old_start = conn["start"]
                old_end = conn["end"]
                
                new_line = id_map.get(old_line)
                new_start = id_map.get(old_start)
                new_end = id_map.get(old_end)
                
                if new_line and new_start and new_end:
                     self.connections[new_line] = {'start': new_start, 'end': new_end}

            messagebox.showinfo("Success", "Project loaded successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load project: {e}")
            print(e)
        
        self.c.update_idletasks() # Ensure all items are rendered to get correct bboxes if needed
        
        # --- Backward compatibility: Upgrade old flowchart geometries ---
        try:
            for item in self.objects:
                itype = self.c.type(item)
                if itype in ("polygon", "oval"):
                    tags = self.c.gettags(item)
                    group_tag = next((t for t in tags if t.startswith("node_group_")), None)
                    if group_tag:
                        members = self.c.find_withtag(group_tag)
                        text_node = next((m for m in members if self.c.type(m) == "text"), None)
                        if text_node:
                            t_bbox = self.c.bbox(text_node)
                            if t_bbox:
                                tx1, ty1, tx2, ty2 = t_bbox
                                # Approximate padding from create_node
                                padding = 10
                                tx1 -= padding; ty1 -= padding; tx2 += padding; ty2 += padding
                                cx, cy = (tx1 + tx2) / 2, (ty1 + ty2) / 2
                                w, h = tx2 - tx1, ty2 - ty1
                                
                                if itype == "polygon" and len(self.c.coords(item)) == 8:
                                    # Fix Diamond Layout
                                    nx1, nx2 = cx - w * 0.9, cx + w * 0.9
                                    ny1, ny2 = cy - h * 0.9, cy + h * 0.9
                                    mx, my = (nx1 + nx2) / 2, (ny1 + ny2) / 2
                                    self.c.coords(item, mx, ny1, nx2, my, mx, ny2, nx1, my)
                                elif itype == "oval":
                                    # Fix Oval Layout
                                    nx1, nx2 = cx - w * 0.75, cx + w * 0.75
                                    ny1, ny2 = cy - h * 0.75, cy + h * 0.75
                                    self.c.coords(item, nx1, ny1, nx2, ny2)
        except Exception as e:
            print(f"Error upgrading node geometry: {e}")
            
        self.update_scrollregion()
        self.update_minimap()




    def add_text(self):
        text = self.modern_askstring("Input", "Enter text:")
        if text:
            raw_x = self.c.winfo_pointerx() - self.c.winfo_rootx()
            raw_y = self.c.winfo_pointery() - self.c.winfo_rooty()
            cx = self.c.canvasx(raw_x)
            cy = self.c.canvasy(raw_y)
            
            # Use current scale for initial size
            scaled_font_size = int(self.font_size * self.scale)
            text_id = self.c.create_text(cx, cy, text=text, fill=self.color_fg, font=(self.current_font, scaled_font_size))
            
            # Register for zooming
            self.text_base_sizes[text_id] = (self.current_font, self.font_size)
            if not hasattr(self, 'text_base_widths'): self.text_base_widths = {}
            # Initialize with no width limit for manual text (0 or None)
            
            self.objects.append(text_id)
            self.undo_stack.append(('create_text', text_id, cx, cy, text, self.color_fg, self.font_size))
            self.redo_stack.clear()
            self.update_scrollregion()
            self.update_minimap()

    def update_font(self, *args):
        self.current_font = self.font_var.get()
        for obj in self.selected_objects:
            self.update_text_properties(obj)

    def update_font_size(self, *args):
        self.font_size = int(self.size_var.get())
        for obj in self.selected_objects:
            self.update_text_properties(obj)

    def set_text_size(self):
        size = simpledialog.askinteger("Text Size", "Enter text size:", minvalue=1, maxvalue=100)
        if size:
            self.font_size = size
            self.size_var.set(size)  # Update the font size in the dropdown menu if you have it

    def set_brush_size(self):
        # Prompt the user to enter a brush size
        size = simpledialog.askinteger("Brush Size", "Enter brush size:", minvalue=1, maxvalue=100)
        if size is not None:
            self.pen_size = size
            # Update the brush size in the drawing tool if necessary
            self.update_brush_size(size)

    def update_brush_size(self, size):
        # This method should update the brush size in your drawing tool
        print(f"Brush size set to {size}")
        # Implement integration with your drawing tool here

    def select_object(self, x, y, event):
        # Check for Shift key (bit 0 or 1 usually, '1' is common for Shift in state)
        # Shift mask in tkinter is 0x0001 (0x1)
        is_shift = (event.state & 0x1) != 0

        # Convert to canvas coordinates
        cx = self.c.canvasx(x)
        cy = self.c.canvasy(y)

        # precise selection with a slightly larger buffer for text/lines
        items = self.c.find_overlapping(cx-5, cy-5, cx+5, cy+5)
        # Filter out grid lines from selection
        valid_items = [i for i in items if "grid" not in self.c.gettags(i)]
        target = valid_items[-1] if valid_items else None

        if not is_shift:
             # If not shfit, clear previous selection unless we clicked ON an unrelated object?
             # Standard behavior: Click without shift -> Deselect all others, select this one.
             if self.selected_objects and (target not in self.selected_objects):
                 self.clear_selection()
        
        if not target:
            # Clicked on empty space -> Deselect all
            if not is_shift:
                self.clear_selection()
            return target

        if target in self.selected_objects:
            if is_shift:
                 # Deselect this one
                 self.deselect_item(target)
        else:
             # Select this one
             self.select_item(target)
             
        # Check if target is part of a group
        tags = self.c.gettags(target)
        group_tag = next((t for t in tags if t.startswith("group_")), None)
        node_group_tag = next((t for t in tags if t.startswith("node_group_")), None)
        flowchart_group_tag = next((t for t in tags if t.startswith("flowchart_group_")), None)
        yt_notes_group_tag = next((t for t in tags if t.startswith("yt_notes_group_")), None)
        is_handle = "flowchart_handle" in tags or "flowchart_handle_bg" in tags
        
        group_items_to_select = []
        if is_handle and (flowchart_group_tag or yt_notes_group_tag):
            target_group = flowchart_group_tag or yt_notes_group_tag
            group_items_to_select = self.groups.get(target_group, [])
            if not group_items_to_select:
                 # Fallback to direct tag search if not in self.groups map
                 group_items_to_select = self.c.find_withtag(target_group)
        elif group_tag and group_tag in self.groups:
            group_items_to_select = self.groups[group_tag]
        elif node_group_tag:
            group_items_to_select = self.c.find_withtag(node_group_tag)
            
        if group_items_to_select:
            # Select ALL members of the group
            for item in group_items_to_select:
                if item not in self.selected_objects:
                     self.selected_objects.append(item)
                     # Highlight
                     itype = self.c.type(item)
                     if itype in ["rectangle", "oval"]:
                         self.selected_object_colors[item] = self.c.itemcget(item, "outline")
                         self.c.itemconfig(item, outline="blue")
                     elif itype in ["line", "text"]:
                          self.selected_object_colors[item] = self.c.itemcget(item, "fill")
                          self.c.itemconfig(item, fill="blue") 
            
        self.show_property_bar(self.selected_objects)
        
        if not group_items_to_select:
             # Add single resize handle only if NOT a group selection (simplification)
             item_bbox = self.c.bbox(target)
             if item_bbox:
                  x1, y1, x2, y2 = item_bbox
                  h_size = 10 / self.scale
                  self.resize_handle = self.c.create_rectangle(x2 - h_size, y2 - h_size, x2, y2, outline='', fill='red', tags='resize')

        return target

    def on_double_click(self, event):
        """Handle double-click to edit text objects."""
        cx = self.c.canvasx(event.x)
        cy = self.c.canvasy(event.y)
        items = self.c.find_overlapping(cx-5, cy-5, cx+5, cy+5)
        valid_items = [i for i in items if "grid" not in self.c.gettags(i)]
        
        if valid_items:
            target = valid_items[-1]
            if self.c.type(target) == 'text':
                self.edit_text_dialog(target)



    def select_item(self, target):
        if target not in self.selected_objects:
             self.selected_objects.append(target)
             item_type = self.c.type(target)

             # Store original color
             if item_type in ["rectangle", "oval"]:
                 self.selected_object_colors[target] = self.c.itemcget(target, "outline")
                 self.c.itemconfig(target, outline="blue")
                 
                 # Add resize handle for shapes too
                 self.resize_target = target
                 self.c.delete('resize')
                 x1, y1, x2, y2 = self.c.bbox(target)
                 h_size = 10 / self.scale
                 self.resize_handle = self.c.create_rectangle(x2 - h_size, y2 - h_size, x2, y2, outline='', fill='red', tags='resize')
             elif item_type == "text":
                 self.selected_object_colors[target] = self.c.itemcget(target, "fill")
                 self.c.itemconfig(target, fill="blue")
                 self.resize_target = target
                 self.c.delete('resize')
                 bbox = self.c.bbox(target)
                 if bbox:
                    x1, y1, x2, y2 = bbox
                    h_size = 10 / self.scale
                    self.resize_handle = self.c.create_rectangle(x2 - h_size, y2 - h_size, x2, y2, outline='', fill='red', tags='resize')
             elif item_type == "line":
                 self.selected_object_colors[target] = self.c.itemcget(target, "fill")
                 self.c.itemconfig(target, fill="blue")
             elif item_type == "image":
                 # Select Image and Show Resize Handle
                 self.image_id = target
                 self.resize_target = target
                 
                 self.c.delete('resize') # Clear old
                 
                 # Create resize handle
                 bbox = self.c.bbox(target)
                 if bbox:
                    x1, y1, x2, y2 = bbox
                    h_size = 10 / self.scale
                    self.resize_handle = self.c.create_rectangle(x2 - h_size, y2 - h_size, x2, y2, outline='', fill='red', tags='resize')

    def deselect_item(self, obj):
        if obj in self.selected_object_colors:
             orig_color = self.selected_object_colors[obj]
             del self.selected_object_colors[obj]
             item_type = self.c.type(obj)
             if item_type in ["rectangle", "oval"]:
                self.c.itemconfig(obj, outline=orig_color)
             elif item_type in ["line", "text"]:
                self.c.itemconfig(obj, fill=orig_color)
             
             if obj in self.selected_objects:
                 self.selected_objects.remove(obj)
             
             # Clear resize handle if this was the target
             if getattr(self, 'resize_target', None) == obj:
                 self.c.delete('resize')
                 self.resize_target = None

    def bucket_fill(self, x, y):
        # Precise selection
        items = self.c.find_overlapping(x-2, y-2, x+2, y+2)
        if not items:
            return

        target = items[-1]
        
        # If target IS selected, fill ALL selected items
        if target in self.selected_objects:
            targets_to_fill = self.selected_objects
        else:
            targets_to_fill = [target]

        for item in targets_to_fill:
             item_type = self.c.type(item)
             if item_type in ["rectangle", "oval"]:
                 self.c.itemconfig(item, fill=self.fill_color)
                 self.undo_stack.append(('itemconfig', item, 'fill', self.c.itemcget(item, 'fill'), self.fill_color))
             else:
                 # Warn only once?
                 pass 
        
        # If filling unselected, maybe flash it? But job done.

    def show_text_edit_options(self):
        pass # Properties are updated via toolbar directly now


    def update_text_properties(self, text_id):
        new_size = int(self.font_size * self.scale)
        self.c.itemconfig(text_id, font=(self.current_font, new_size))
        # Synchronize for zoom persistence
        self.text_base_sizes[text_id] = (self.current_font, self.font_size)

    def select_or_edit_text(self, event):
        items = self.c.find_closest(event.x, event.y)
        if not items:
            return

        item = items[0]
        if self.c.type(item) == "text":
            self.edit_text_dialog(item)

    def edit_text_dialog(self, text_id):
        def apply_changes():
            new_text = text_editor.get("1.0", tk.END).strip()
            old_text = self.c.itemcget(text_id, "text")
            if new_text != old_text:
                self.c.itemconfig(text_id, text=new_text)
                self.undo_stack.append(('itemconfig', text_id, 'text', old_text, new_text))
                self.redo_stack.clear()
            edit_window.destroy()

        current_text = self.c.itemcget(text_id, "text")
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Edit Text")
        edit_window.configure(bg=self.theme["bg_secondary"])
        edit_window.geometry("400x300")
        
        # Label
        tk.Label(edit_window, text="Edit Content:", bg=self.theme["bg_secondary"], 
                 fg=self.theme["text_color"], font=("Arial", 10, "bold")).pack(pady=5)

        text_editor = tk.Text(edit_window, wrap='word', width=40, height=8, 
                             bg=self.theme["bg_primary"], fg=self.theme["text_color"],
                             insertbackground=self.theme["text_color"], relief=tk.FLAT, padx=10, pady=10)
        text_editor.pack(expand=True, fill='both', padx=20, pady=5)
        text_editor.insert(tk.END, current_text)
        text_editor.focus_set()

        btn_fm = tk.Frame(edit_window, bg=self.theme["bg_secondary"])
        btn_fm.pack(pady=10)

        tk.Button(btn_fm, text="Apply", command=apply_changes, bg=self.theme["accent"], 
                  fg="white", relief=tk.FLAT, width=10, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_fm, text="Cancel", command=edit_window.destroy, bg="#eee", 
                  fg="black", relief=tk.FLAT, width=10, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

    def adjust_text_size(self, items, delta):
        """Quickly adjust font size of selected text objects."""
        for item in items:
            if self.c.type(item) == "text":
                try:
                    current_font = self.c.itemcget(item, "font")
                    # Handle font as tuple (Family, Size, Style)
                    if isinstance(current_font, str):
                         import re
                         if current_font.startswith("{"):
                             match = re.search(r'\{([^}]+)\}\s+(-?\d+)', current_font)
                             if match:
                                 family = match.group(1)
                                 size = int(match.group(2))
                             else:
                                 family = "Arial"
                                 size = self.font_size
                         else:
                             parts = current_font.split()
                             family = parts[0]
                             size = int(parts[1]) if len(parts) > 1 else self.font_size
                    else:
                         family = current_font[0]
                         size = int(current_font[1])

                    new_size = size + delta
                    if new_size > 4:
                        self.c.itemconfig(item, font=(family, new_size))
                        # Update base size for zooming
                        if item in self.text_base_sizes:
                             # Store size at scale 1.0
                             self.text_base_sizes[item] = (family, int(new_size / self.scale))
                        
                        self.update_minimap()
                except Exception as e:
                    print(f"Error adjusting text size: {e}")

    def cycle_font(self, items):
        """Cycles through a set of common fonts for selected text objects."""
        fonts = ["Arial", "Verdana", "Courier New", "Times New Roman", "Georgia"]
        for item in items:
            if self.c.type(item) == "text":
                try:
                    current_font_raw = self.c.itemcget(item, "font")
                    # Extract family
                    if isinstance(current_font_raw, str):
                        import re
                        if current_font_raw.startswith("{"):
                            match = re.search(r'\{([^}]+)\}\s+(-?\d+)', current_font_raw)
                            if match:
                                family = match.group(1)
                                size = int(match.group(2))
                            else:
                                family = "Arial"
                                size = self.font_size
                        else:
                            parts = current_font_raw.split()
                            family = parts[0]
                            size = int(parts[1]) if len(parts) > 1 else self.font_size
                    else:
                        family = current_font_raw[0]
                        size = int(current_font_raw[1])
                    
                    try:
                        # Normalize family for comparison
                        idx = -1
                        for i, f in enumerate(fonts):
                            if f.lower() == family.lower():
                                idx = i
                                break
                        next_font = fonts[(idx + 1) % len(fonts)]
                    except ValueError:
                        next_font = fonts[0]
                    
                    self.c.itemconfig(item, font=(next_font, size))
                    if item in self.text_base_sizes:
                        self.text_base_sizes[item] = (next_font, int(size / self.scale))
                except Exception as e:
                    print(f"Error cycling font: {e}")
        self.update_minimap()

    def apply_template(self, template_func):
        """Helper to apply a template, potentially handling undo stack."""
        # Calculate center view positions
        # Uses canvasx/y to place based on current scroll
        cx = self.c.canvasx(100) # Offset slightly
        cy = self.c.canvasy(100)
        
        ids = template_func(self.c, start_x=cx, start_y=cy)
        self.objects.extend(ids)
        # TODO: Add to Undo Stack as a group operation?
        # For now, simple add.

    # --- Magic Flowchart (AI) ---
    def set_magic_layout(self, layout_type):
        self.magic_layout_preference = layout_type
        messagebox.showinfo("Preference Set", f"Flowchart Layout set to: {layout_type.capitalize()}")

    def magic_flowchart_dialog(self):
        """UI to accept messy text for AI flowchart generation."""
        # Ensure default preference exists
        if not hasattr(self, 'magic_layout_preference'):
            self.magic_layout_preference = 'standard'

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Magic Flowchart ({self.magic_layout_preference.capitalize()})")
        dialog.geometry("500x400")
        
        lbl = tk.Label(dialog, text=f"Paste your messy process notes below.\nUsing Layout: {self.magic_layout_preference.capitalize()}", 
                       justify=tk.LEFT, padx=10, pady=10)
        lbl.pack(fill=tk.X)
        
        txt = tk.Text(dialog, height=15, width=50)
        txt.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        
        # Sample placeholder
        txt.insert(tk.END, "User logs in. Check if password is valid. If yes, grant access. If no, show error.")
        
        def on_generate():
            raw_text = txt.get("1.0", tk.END).strip()
            if not raw_text: return
            
            # Close dialog and execute
            dialog.destroy()
            self.execute_magic_flowchart(raw_text)
            
        btn = tk.Button(dialog, text="\u2728 Generate Flowchart", command=on_generate, bg="#D4AC0D", fg="white", font=("Arial", 12, "bold"))
        btn.pack(pady=10)

    def execute_magic_flowchart(self, text):
        """
        Parses natural language into structured flowchart format using AI.
        """
        print(f"DEBUG: Magic Flowchart input: {text}")
        
        # Use AI to restructure messy text into a bulleted hierarchy
        structured_text = self.restructure_text_for_flowchart(text)
        print(f"DEBUG: Structured Text:\n{structured_text}")
        
        # Save to temp file and reuse existing generation logic
        temp_path = "temp_magic_flowchart.txt"
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(structured_text)
            
        # Generate with preference
        layout = getattr(self, 'magic_layout_preference', 'standard')
        self.generate_flowchart_from_file(file_path=temp_path, layout_type=layout)
        
        # Cleanup is handled by caller or kept for debug if needed

    def toggle_presentation_mode(self):
        if not hasattr(self, 'is_presentation_mode'):
            self.is_presentation_mode = False
        
        self.is_presentation_mode = not self.is_presentation_mode
        
        if self.is_presentation_mode:
            # Hide UI
            if hasattr(self, 'top_bar'): self.top_bar.pack_forget()
            if hasattr(self, 'palette'): self.palette.pack_forget()
            if hasattr(self, 'v_scrollbar'): self.v_scrollbar.pack_forget()
            if hasattr(self, 'h_scrollbar'): self.h_scrollbar.pack_forget()
            
            # Hide Floating UI (if exists)
            if hasattr(self, 'bottom_dock'): self.bottom_dock.place_forget()
            if hasattr(self, 'top_left_overlay'): self.top_left_overlay.place_forget()
            if hasattr(self, 'top_right_overlay'): self.top_right_overlay.place_forget()
            if hasattr(self, 'color_palette_win') and self.color_palette_win:
                 self.color_palette_win.place_forget()
                 self.palette_open = False

            # Fullscreen
            self.root.attributes("-fullscreen", True)
            
            # Default to Select Tool when entering presentation mode
            self.select_tool('select')
            
            # Add Floating Presentation Mini-Dock
            self.presentation_dock = RoundedFrame(self.root, width=160, height=60, 
                                                corner_radius=25, color=self.theme["bg_secondary"], 
                                                bg_color=self.theme["canvas_bg"], shadow_offset=4)
            self.presentation_dock.place(relx=0.5, rely=0.95, anchor=tk.S)
            
            dock_bg = self.theme["bg_secondary"]
            center_y = 27 # Vertically center inside height=60
            
            # Mini-Dock: Select Button
            self.pres_select_btn = RoundedButton(self.presentation_dock, width=40, height=40, image=self.select_img, 
                                                command=lambda: self.select_tool('select'), corner_radius=20, 
                                                bg_hover=self.theme["btn_hover"], transparent_on=dock_bg, tooltip="Select")
            self.presentation_dock.create_window(15, center_y, window=self.pres_select_btn, anchor=tk.W)
            
            # Mini-Dock: Pen Button
            self.pres_pen_btn = RoundedButton(self.presentation_dock, width=40, height=40, image=self.pencil_img, 
                                                command=lambda: self.select_tool('brush'), corner_radius=20, 
                                                bg_hover=self.theme["btn_hover"], transparent_on=dock_bg, tooltip="Pen")
            self.presentation_dock.create_window(60, center_y, window=self.pres_pen_btn, anchor=tk.W)
            
            # Mini-Dock: Laser Pointer
            self.pres_laser_btn = RoundedButton(self.presentation_dock, width=40, height=40, image=self.laser_img, 
                                                command=lambda: self.select_tool('laser'), corner_radius=20, 
                                                bg_hover=self.theme["btn_hover"], transparent_on=dock_bg, tooltip="Laser")
            self.presentation_dock.create_window(105, center_y, window=self.pres_laser_btn, anchor=tk.W)
            
            # Add Floating Exit Button (Top Right)
            self.exit_btn_win = tk.Button(self.root, text="Exit Presentation", command=self.toggle_presentation_mode, bg="red", fg="white", font=("Arial", 12, "bold"))
            self.exit_btn_win.place(relx=0.98, rely=0.02, anchor=tk.NE)
            # Hide Cursor
            self.c.config(cursor="none")
            
            messagebox.showinfo("Presentation Mode", "Press 'Exit Presentation' button to return.")
            
        else:
            # Restore UI
            
            # Restore Cursor
            self.c.config(cursor="arrow")
            
            # Remove Laser Pointer
            if self.laser_id:
                self.c.delete(self.laser_id)
                self.laser_id = None

            # Restore Floating UI
            if hasattr(self, 'bottom_dock'): 
                self.bottom_dock.place(relx=0.5, rely=0.95, anchor=tk.S)
            if hasattr(self, 'top_left_overlay'): 
                self.top_left_overlay.place(relx=0.01, rely=0.01, anchor=tk.NW)
            if hasattr(self, 'top_right_overlay'): 
                self.top_right_overlay.place(relx=0.99, rely=0.01, anchor=tk.NE)

            # 1. Unpack Canvas (to ensure order - mainly for Pack layout, but harmless)
            # self.c.pack_forget()
            
            # 2. Repack Legacy UI elements if they exist (For backwards compatibility/mixed mode)
            if hasattr(self, 'top_bar'): 
                # self.top_bar.pack(side=tk.TOP, fill=tk.X) # We disabled this generally
                pass
            if hasattr(self, 'palette'): 
                # self.palette.pack(side=tk.TOP, fill=tk.X)
                pass
            if hasattr(self, 'v_scrollbar'): self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            if hasattr(self, 'h_scrollbar'): self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
            
            # 3. Repack Canvas
            # self.c.pack(fill=tk.BOTH, expand=True) # It's already packed
            
            self.root.attributes("-fullscreen", False)
            
            if hasattr(self, 'exit_btn_win'):
                self.exit_btn_win.destroy()
            if hasattr(self, 'presentation_dock'):
                self.presentation_dock.destroy()

    def toggle_smart_connect(self):
        self.smart_connect_on = not self.smart_connect_on
        if hasattr(self, 'smart_connect_btn'):
            if self.smart_connect_on:
                self.smart_connect_btn.config(text="Smart: ON", bg=self.theme["accent"])
            else:
                 self.smart_connect_btn.config(text="Smart: OFF", bg=self.theme["btn_bg"])

    # --- Grid & Snap Features ---
    def toggle_grid(self):
        self.grid_on = not self.grid_on
        if hasattr(self, 'grid_btn') and self.grid_btn:
             if self.grid_on:
                self.grid_btn.config(text="Grid: ON", bg=self.theme["accent"])
             else:
                self.grid_btn.config(text="Grid: OFF", bg=self.theme["btn_bg"])
        
        if self.grid_on:
            self.draw_grid()
        else:
            self.c.delete("grid") # Remove grid lines

    def toggle_snap(self):
        self.snap_on = not self.snap_on
        if hasattr(self, 'snap_btn') and self.snap_btn:
            if self.snap_on:
                 self.snap_btn.config(text="Snap: ON", bg=self.theme["accent"])
            else:
                 self.snap_btn.config(text="Snap: OFF", bg=self.theme["btn_bg"])
        
    def toggle_vector_smoothing(self):
        self.vector_smooth_on = not self.vector_smooth_on

    def auto_layout_mind_map(self):
        """Organizes connected nodes into a radial tree structure."""
        # 1. Build Full Graph from all connections
        full_adj = {}
        all_nodes = set()
        # Also build undirected graph for component finding
        undirected_adj = {}

        for conn in self.connections.values():
            s, e = conn['start'], conn['end']
            if s not in full_adj: full_adj[s] = []
            full_adj[s].append(e)
            all_nodes.add(s)
            all_nodes.add(e)
            
            # Undirected
            if s not in undirected_adj: undirected_adj[s] = []
            if e not in undirected_adj: undirected_adj[e] = []
            undirected_adj[s].append(e)
            undirected_adj[e].append(s)
        
        if not all_nodes:
            messagebox.showinfo("Auto-Layout", "No connected nodes found to layout.")
            return

        # 2. Determine Root
        root = None
        if self.selected_objects:
            # Prefer the first selected object that is actually a node in the graph
            for obj in self.selected_objects:
                if obj in all_nodes:
                    root = obj
                    break
        
        # Fallback to existing heuristic if no selection or selection isn't a node
        if not root:
            in_degree = {n: 0 for n in all_nodes}
            for targets in full_adj.values():
                for t in targets:
                    in_degree[t] += 1
            
            def is_flowchart(node):
                return any("flowchart" in tag for tag in self.c.gettags(node))
            
            valid_nodes = [n for n in all_nodes if not is_flowchart(n)]
            roots = [n for n in valid_nodes if in_degree[n] == 0]
            
            if not roots:
                if valid_nodes:
                    root = max(valid_nodes, key=lambda n: len(full_adj.get(n, [])))
            else:
                mindmap_roots = [n for n in roots if "mindmap_node" in self.c.gettags(n)]
                root = mindmap_roots[0] if mindmap_roots else roots[0]
                
        if not root:
            messagebox.showinfo("Auto-Layout", "No suitable mind map nodes found to layout.")
            return

        # 3. Find Connected Component (to avoid moving random objects on the canvas)
        # We only want to layout the subgraph reachable from 'root' in an undirected sense
        component = {root}
        queue = [root]
        while queue:
            u = queue.pop(0)
            for v in undirected_adj.get(u, []):
                if v not in component:
                    component.add(v)
                    queue.append(v)
        
        # 4. Filter Graph to Component
        adj = {n: [v for v in full_adj.get(n, []) if v in component] for n in component}
        nodes = component

        # 5. Radial Layout Calculation (using filtered component)
        positions = {}
        level_nodes = {0: [root]}
        visited = {root}
        queue = [(root, 0)]
        parent = {}
        
        while queue:
            u, d = queue.pop(0)
            for v in adj.get(u, []):
                if v not in visited:
                    visited.add(v)
                    parent[v] = u
                    if d+1 not in level_nodes: level_nodes[d+1] = []
                    level_nodes[d+1].append(v)
                    queue.append((v, d+1))

        def layout(u, start_angle, end_angle, depth):
            mid_angle = (start_angle + end_angle) / 2
            # Use larger radius for deeper levels to avoid crowding
            radius = depth * 300 
            
            x = math.cos(mid_angle) * radius
            y = math.sin(mid_angle) * radius
            positions[u] = (x, y)
            
            children = [v for v in adj.get(u, []) if parent.get(v) == u]
            if not children: return
            
            angle_step = (end_angle - start_angle) / len(children)
            for i, v in enumerate(children):
                layout(v, start_angle + i * angle_step, start_angle + (i+1) * angle_step, depth + 1)

        layout(root, 0, 2 * math.pi, 0)

        # 4. Apply New Positions
        cx = self.c.canvasx(self.c.winfo_width() / 2)
        cy = self.c.canvasy(self.c.winfo_height() / 2)
        
        undo_moves = []
        for node_id, (rx, ry) in positions.items():
            bbox = self.c.bbox(node_id)
            if not bbox: continue
            cur_cx = (bbox[0] + bbox[2]) / 2
            cur_cy = (bbox[1] + bbox[3]) / 2
            
            dx = (cx + rx) - cur_cx
            dy = (cy + ry) - cur_cy
            
            # Find all members of the logical node (shape + text)
            group_tag = f"node_group_{node_id}"
            members = list(self.c.find_withtag(group_tag))
            if not members:
                 # Check if it was grouped manually as well? 
                 # Usually nodes created by AI have node_group_ tags.
                 # For manually created shapes, we check for overlapping text.
                 members = [node_id]
                 # Find text inside or very close to the shape
                 overlaps = self.c.find_overlapping(bbox[0], bbox[1], bbox[2], bbox[3])
                 for oid in overlaps:
                      if self.c.type(oid) == 'text' and oid not in members:
                           members.append(oid)
            
            for m in members:
                self.c.move(m, dx, dy)
            
            undo_moves.append((members, dx, dy))
            
        # 5. Refresh Connections
        for node_id in nodes:
            self.update_connected_lines(node_id)
            
        # 6. Record Undo
        self.undo_stack.append(('batch_move', undo_moves))
        self.redo_stack.clear()
        self.update_minimap()
        messagebox.showinfo("Auto-Layout", "Mind map layout complete.")
        # Refresh main menu if open
        if hasattr(self, 'main_menu_frame') and self.main_menu_frame:
            self.show_main_menu() # Toggle back to refresh
            self.show_main_menu()
        print(f"DEBUG: Vector Smoothing is now {'ON' if self.vector_smooth_on else 'OFF'}")

    def apply_vector_smoothing(self, line_id):
        """Applies RDP simplification followed by Chaikin smoothing to a brush stroke."""
        try:
            coords = self.c.coords(line_id)
            if not coords or len(coords) < 6: return
            
            # Convert to list of tuples
            points = []
            for i in range(0, len(coords), 2):
                points.append((coords[i], coords[i+1]))
            
            # 1. Simplify (RDP)
            # Use small epsilon to keep shape but remove jitter
            epsilon = 1.0 
            simplified = self.simplify_points(points, epsilon)
            
            # 2. Smooth (Chaikin)
            smoothed = self.chaikin_smooth(simplified, iterations=2)
            
            # 3. Update Canvas
            final_coords = []
            for p in smoothed:
                final_coords.extend([p[0], p[1]])
            
            self.c.coords(line_id, *final_coords)
            # Enable built-in canvas smoothing for final touch
            self.c.itemconfig(line_id, smooth=True, splinesteps=12)
            
        except Exception as e:
            print(f"Error applying smoothing: {e}")

    def chaikin_smooth(self, points, iterations=2):
        """Applies Chaikin's algorithm to round corners of a polyline."""
        if len(points) < 3: return points
        
        for _ in range(iterations):
            new_points = [points[0]] # Keep first point
            for i in range(len(points) - 1):
                p0 = points[i]
                p1 = points[i+1]
                
                # Cut at 25% and 75%
                q = (0.75 * p0[0] + 0.25 * p1[0], 0.75 * p0[1] + 0.25 * p1[1])
                r = (0.25 * p0[0] + 0.75 * p1[0], 0.25 * p0[1] + 0.75 * p1[1])
                
                new_points.append(q)
                new_points.append(r)
            
            new_points.append(points[-1]) # Keep last point
            points = new_points
        return points

    def toggle_auto_shape(self):
        self.auto_shape_on = not self.auto_shape_on
        if hasattr(self, 'auto_shape_btn') and self.auto_shape_btn:
            if self.auto_shape_on:
                self.auto_shape_btn.config(text="Auto: ON", bg=self.theme["accent"])
            else:
                self.auto_shape_btn.config(text="Auto: OFF", bg=self.theme["btn_bg"])

    def toggle_auto_ink_to_text(self):
        self.auto_ink_to_text_on = not getattr(self, 'auto_ink_to_text_on', False)

    def _process_auto_ink(self):
         if not hasattr(self, '_auto_ink_buffer') or not self._auto_ink_buffer:
             return
         valid_items = [i for i in self._auto_ink_buffer if self.c.type(i) == "line"]
         if valid_items:
             self.convert_ink_to_text(valid_items)
         self._auto_ink_buffer = []

    def draw_grid(self):
        self.c.delete("grid")
        if not self.grid_on: return
        
        # Infinite Grid Strategy: Draw lines over a massive range
        # Tkinter handles off-screen objects efficiently (culling), so 
        # pre-drawing a large area is better than dynamic redrawing on pan.
        limit = 25000 
        step = self.grid_size
        
        # Vertical lines
        for i in range(-limit, limit, step):
            self.c.create_line(i, -limit, i, limit, tags=("grid", "grid_line"), fill="#E0E0E0")
            
        # Horizontal lines
        for i in range(-limit, limit, step):
            self.c.create_line(-limit, i, limit, i, tags=("grid", "grid_line"), fill="#E0E0E0")
        
        self.c.tag_lower("grid") # Ensure grid is behind everything

    def snap(self, coord):
        if self.snap_on:
            return round(coord / self.grid_size) * self.grid_size
        return coord

    def process_smart_connection(self, shape_id, x1, y1, x2, y2):
        """Helper to handle smart connection logic for lines and arrows."""
        range_val = 10
        # Convert to canvas coords if they aren't already (though they should be)
        # Using the snapped coords passed in
        start_items = self.c.find_overlapping(x1-range_val, y1-range_val, x1+range_val, y1+range_val)
        end_items = self.c.find_overlapping(x2-range_val, y2-range_val, x2+range_val, y2+range_val)
        
        connection = {}
        for item in reversed(start_items):
            if item != shape_id and self.c.type(item) in ['rectangle', 'oval', 'image', 'text', 'polygon']:
                connection['start'] = item
                break
        for item in reversed(end_items):
            if item != shape_id and self.c.type(item) in ['rectangle', 'oval', 'image', 'text', 'polygon']:
                connection['end'] = item
                break
        
        if 'start' in connection and 'end' in connection:
            self.connections[shape_id] = connection
            try:
                self.c.tag_lower(shape_id)
                # Apply Orthogonal Routing immediately
                points = self.get_best_route(connection['start'], connection['end'])
                if points:
                    self.c.coords(shape_id, *points)
                    self.c.itemconfig(shape_id, smooth=False)
                # Also set standard connection tags?
                self.c.addtag_withtag('connection_line', shape_id)
            except tk.TclError:
                pass
            print(f"DEBUG: Connected line {shape_id} to {connection}")

    def on_canvas_configure(self, event):
        self.update_scrollregion()
        if self.grid_on:
            self.draw_grid()
        self.update_minimap()

    # --- Export Feature ---
    def export_as_png(self):
        file_path = asksaveasfilename(defaultextension=".png", 
                                      filetypes=[("PNG files", "*.png"), ("All Files", "*.*")])
        if not file_path: return

        doc = self._generate_export_document()
        if doc:
            try:
                page = doc[0]
                # Render the page at high resolution (300 DPI equivalent)
                pix = page.get_pixmap(dpi=300)
                pix.save(file_path)
                doc.close()
                messagebox.showinfo("Export", "Canvas exported as PNG successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save PNG: {e}")

    def export_as_pdf(self):
        file_path = asksaveasfilename(defaultextension=".pdf", 
                                      filetypes=[("PDF files", "*.pdf"), ("All Files", "*.*")])
        if not file_path: return

        doc = self._generate_export_document()
        if doc:
            try:
                doc.save(file_path)
                doc.close()
                messagebox.showinfo("Export", "Canvas exported as PDF successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save PDF: {e}")

    def _generate_export_document(self):
        try:
            import fitz
            import io
            import math
            
            # Figure out bounding box of all items
            all_items = self.c.find_all()
            if not all_items:
                messagebox.showinfo("Export", "Canvas is empty.")
                return None

            bbox = self.c.bbox("all")
            if not bbox: return
            x_min, y_min, x_max, y_max = bbox
            
            # Add some margin
            margin = 50
            x_min -= margin
            y_min -= margin
            x_max += margin
            y_max += margin
            
            width = x_max - x_min
            height = y_max - y_min
            
            doc = fitz.open()
            page = doc.new_page(width=width, height=height)
            
            def tk_to_rgb(tk_color):
                if not tk_color or tk_color == '""' or "transparent" in str(tk_color).lower(): 
                    return None
                try:
                    r, g, b = self.root.winfo_rgb(tk_color)
                    return (r/65535.0, g/65535.0, b/65535.0)
                except:
                    return None

            # 1. Draw Background
            bg_color_raw = self.c.cget('bg')
            bg_rgb = tk_to_rgb(bg_color_raw)
            if bg_rgb:
                shape = page.new_shape()
                shape.draw_rect(fitz.Rect(0, 0, width, height))
                shape.finish(fill=bg_rgb, width=0)
                shape.commit()

            def draw_pdf_arrow(page, p1, p2, color, width, is_both=False):
                # Helper to draw arrowheads
                dx = p2.x - p1.x
                dy = p2.y - p1.y
                length = math.sqrt(dx*dx + dy*dy)
                if length < 1: return
                
                angle = math.atan2(dy, dx)
                arrow_size = 8 + width
                arrow_angle = math.radians(25)
                
                def draw_head(pt, ang, reverse=False):
                    head_ang = ang + math.pi if reverse else ang
                    left = fitz.Point(pt.x - arrow_size * math.cos(head_ang - arrow_angle),
                                     pt.y - arrow_size * math.sin(head_ang - arrow_angle))
                    right = fitz.Point(pt.x - arrow_size * math.cos(head_ang + arrow_angle),
                                      pt.y - arrow_size * math.sin(head_ang + arrow_angle))
                    s = page.new_shape()
                    s.draw_polyline([left, pt, right])
                    s.finish(color=color, width=width, lineCap=1)
                    s.commit()

                draw_head(p2, angle)
                if is_both:
                    draw_head(p1, angle, reverse=True)

            for item in all_items:
                tags = self.c.gettags(item)
                if "grid" in tags or "resize" in tags or "laser" in tags or "select_box" in tags:
                     continue
                     
                item_type = self.c.type(item)
                coords = self.c.coords(item)
                if not coords: continue
                
                # Shift coordinates
                shifted = []
                for i in range(0, len(coords), 2):
                    shifted.append(coords[i] - x_min)
                    shifted.append(coords[i+1] - y_min)
                
                if item_type == 'line':
                    fill_str = self.c.itemcget(item, 'fill')
                    color = tk_to_rgb(fill_str)
                    if not color: continue
                    w = float(self.c.itemcget(item, 'width') or 1)
                    
                    is_h = "highlighter" in tags or self.c.itemcget(item, 'stipple') == 'gray50'
                    alpha = 0.5 if is_h else 1.0
                    
                    pts = [fitz.Point(shifted[i], shifted[i+1]) for i in range(0, len(shifted), 2)]
                    shape = page.new_shape()
                    
                    # Check for smoothing (broken into segments for PyMuPDF)
                    # For simplicity, we use draw_polyline as most bush/highlighter points are dense enough
                    # unless it's a very long smoothed connector
                    shape.draw_polyline(pts)
                    shape.finish(color=color, width=w, stroke_opacity=alpha)
                    shape.commit()
                    
                    # Handle Arrowheads
                    arrow_val = self.c.itemcget(item, 'arrow')
                    if arrow_val and arrow_val != 'none' and len(pts) >= 2:
                         is_both = arrow_val == 'both'
                         draw_pdf_arrow(page, pts[-2], pts[-1], color, w, is_both=is_both)
                    
                elif item_type in ('rectangle', 'oval'):
                    if len(shifted) < 4: continue
                    rect = fitz.Rect(shifted[0], shifted[1], shifted[2], shifted[3])
                    outline = tk_to_rgb(self.c.itemcget(item, 'outline'))
                    fill = tk_to_rgb(self.c.itemcget(item, 'fill'))
                    w = float(self.c.itemcget(item, 'width') or 1)
                    
                    shape = page.new_shape()
                    if item_type == 'rectangle':
                        shape.draw_rect(rect)
                    else:
                        shape.draw_oval(rect)
                    
                    if outline or fill:
                        shape.finish(color=outline, fill=fill, width=w)
                        shape.commit()
                        
                elif item_type == 'polygon':
                    outline = tk_to_rgb(self.c.itemcget(item, 'outline'))
                    fill = tk_to_rgb(self.c.itemcget(item, 'fill'))
                    w = float(self.c.itemcget(item, 'width') or 1)
                    
                    pts = [fitz.Point(shifted[i], shifted[i+1]) for i in range(0, len(shifted), 2)]
                    pts.append(pts[0]) # close polygon
                    shape = page.new_shape()
                    shape.draw_polyline(pts)
                    if outline or fill:
                        shape.finish(color=outline, fill=fill, width=w)
                        shape.commit()
                        
                elif item_type == 'text':
                    text = self.c.itemcget(item, 'text')
                    if not text: continue
                    color = tk_to_rgb(self.c.itemcget(item, 'fill')) or (0,0,0)
                    
                    font_data = self.text_base_sizes.get(item)
                    base_fontsize = font_data[1] if font_data else self.font_size
                    # Scale font size with zoom level so it matches the scaled bounding box
                    fontsize = max(1, int(base_fontsize * self.scale))
                    
                    # Better text handling with insert_textbox and a small padding
                    t_bbox = self.c.bbox(item)
                    if t_bbox:
                        # Convert to page coordinates
                        tx1 = t_bbox[0] - x_min
                        ty1 = t_bbox[1] - y_min
                        tx2 = t_bbox[2] - x_min
                        ty2 = t_bbox[3] - y_min
                        
                        rect = fitz.Rect(tx1, ty1, tx2, ty2)
                        # Expand box to ensure text fits PyMuPDF's tighter line-height calculations
                        rect.x1 += 5  # Right
                        rect.y1 += 5  # Bottom
                        
                        if rect.is_empty or rect.is_infinite: continue
                        
                        align_val = 1 if "node_group" in str(tags) else 0
                        
                        # Try insert_textbox first, fallback to insert_text if it fails
                        # (insert_textbox returns number of un-rendered characters, so check for > 0)
                        rc = page.insert_textbox(rect, text, fontsize=fontsize, color=color, align=align_val)
                        if rc < 0: # Fails if box too small
                             # Fallback to direct text insertion at top-left of box
                             page.insert_text(rect.tl, text, fontsize=fontsize, color=color)
                        
                elif item_type == 'image':
                    img_data = None
                    # Try to get from stored_images (high-res master)
                    if item in getattr(self, 'stored_images', {}):
                        pill_img = self.stored_images[item]
                        img_byte_arr = io.BytesIO()
                        pill_img.save(img_byte_arr, format='PNG')
                        img_data = img_byte_arr.getvalue()
                    else:
                        # Fallback to local file if exists
                        img_path = self.image_files.get(item)
                        if img_path and os.path.exists(img_path):
                            with open(img_path, "rb") as f:
                                img_data = f.read()

                    if img_data:
                        i_bbox = self.c.bbox(item)
                        if i_bbox:
                            rect = fitz.Rect(i_bbox[0]-x_min, i_bbox[1]-y_min, i_bbox[2]-x_min, i_bbox[3]-y_min)
                            page.insert_image(rect, stream=img_data)

            return doc
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generating export document: {e}")
            import traceback
            traceback.print_exc()
            return None


    # --- Zoom & Pan ---
    def zoom_in(self):
        factor = 1.1
        self.scale *= factor
        self.c.scale("all", 0, 0, factor, factor)
        self.rescale_images_for_zoom()
        self.rescale_text_for_zoom()
        self.rescale_shapes_for_zoom()
        self.update_scrollregion()

    def zoom_out(self):
        factor = 0.9
        self.scale *= factor
        self.c.scale("all", 0, 0, factor, factor)
        self.rescale_images_for_zoom()
        self.rescale_text_for_zoom()
        self.rescale_shapes_for_zoom()
        self.update_scrollregion()

    def rescale_text_for_zoom(self):
        """Resizes text objects based on current zoom scale."""
        for text_id, font_data in list(self.text_base_sizes.items()):
            # Check if object still exists
            if not self.c.find_withtag(text_id):
                continue
                
            # font_data is tuple: (family, size, styles...)
            family = font_data[0]
            base_size = font_data[1]
            styles = font_data[2:] if len(font_data) > 2 else ()
            
            new_size = int(base_size * self.scale)
            if new_size < 1: new_size = 1
            
            new_font = (family, new_size, *styles)
            
            # Find base width if it exists from undo stack
            # Since undo_stack contains ('create_text', id, x, y, text, color, size, width)
            # Find the first entry that created this text id
            base_width = None
            if hasattr(self, 'text_base_widths') and text_id in self.text_base_widths:
                base_width = self.text_base_widths[text_id]
            elif hasattr(self, 'undo_stack'):
                for action in self.undo_stack:
                    if action[0] == 'create_text' and action[1] == text_id:
                        if len(action) > 7:
                            base_width = action[7]
                        break
                    elif action[0] == 'create_node' and action[1] == text_id:
                        if len(action) > 9:
                            base_width = action[9]
                        break

            if base_width:
                new_width = int(base_width * self.scale)
                self.c.itemconfig(text_id, font=new_font, width=max(1, new_width))
            else:
                self.c.itemconfig(text_id, font=new_font)
                
            # Sync background rectangles for node groups (Sticky Notes, AI Nodes)
            group_tag = f"node_group_{text_id}"
            bg_id = next((item for item in self.c.find_withtag(group_tag) if item != text_id and self.c.type(item) in ("rectangle", "oval")), None)
            if bg_id:
                bbox = self.c.bbox(text_id)
                if bbox:
                    padding = 10
                    if hasattr(self, 'undo_stack'):
                        for action in self.undo_stack:
                            if action[0] == 'create_node' and action[1] == text_id and len(action) > 8:
                                padding = action[8]
                                break
                    pad = padding * self.scale
                    self.c.coords(bg_id, bbox[0]-pad, bbox[1]-pad, bbox[2]+pad, bbox[3]+pad)


    def rescale_shapes_for_zoom(self):
        """Resizes the thickness of shape outlines and lines based on current zoom scale."""
        for shape_id, base_width in list(self.shape_base_widths.items()):
            # Check if object still exists
            items = self.c.find_withtag(shape_id)
            if not items:
                continue
            
            new_width = max(1, int(base_width * self.scale))
            try:
                self.c.itemconfig(shape_id, width=new_width)
            except:
                pass

    def rescale_images_for_zoom(self):
        """
        Tkinter Canvas.scale() moves images but does not resize them.
        We must manually resize the underlying images based on the current global scale.
        """
        # Memory Optimization: Keep only the most recent set of PhotoImages by clearing the list 
        # but only if it's getting too large. We need to keep CURRENTLY visible images.
        if hasattr(self, 'image_refs') and len(self.image_refs) > 20:
             # Keep only some recent ones. 
             # Better: we really only need references for objects currently on canvas.
             new_refs = []
             for img_id in self.image_files:
                 try:
                     # Check if item still exists
                     if self.c.find_withtag(img_id):
                          # We can't easily get the PhotoImage back from the item in a way that prevents GC
                          # so we refresh the whole list during zoom.
                          pass
                 except: pass
             # For simplicity, we'll let this pass for now and rely on regular garbage collection 
             # when we replace the list below.
             self.image_refs = [] 
        elif not hasattr(self, 'image_refs'):
             self.image_refs = []

        for img_id in list(self.image_files.keys()): # Iterate known images
            # Robust check for missing or None base sizes
            base_data = self.image_base_sizes.get(img_id)
            if not base_data or not isinstance(base_data, (tuple, list)) or len(base_data) < 2:
                continue
                
            base_w, base_h = base_data
            
            # Calculate new size based on global scale
            new_w = int(base_w * self.scale)
            new_h = int(base_h * self.scale)
            
            # Prevent 0 size which crashes
            if new_w < 1: new_w = 1
            if new_h < 1: new_h = 1
            
            # Get original PIL image to quality resize (avoid degradation)
            pil_img = None
            if hasattr(self, 'stored_images') and img_id in self.stored_images:
                pil_img = self.stored_images[img_id]
            else:
                file_path = self.image_files.get(img_id)
                # Skip if invalid path
                if not file_path or not os.path.exists(file_path):
                     continue
                try:
                    pil_img = Image.open(file_path)
                    # Cache it now for future zooms
                    if not hasattr(self, 'stored_images'): self.stored_images = {}
                    self.stored_images[img_id] = pil_img
                except:
                    continue
            
            if not pil_img or not self.c.find_withtag(img_id): continue

            try:
                # High-quality resize from master
                resized_pil = pil_img.resize((new_w, new_h), Image.LANCZOS)
                new_photo = ImageTk.PhotoImage(resized_pil)
                
                self.c.itemconfig(img_id, image=new_photo)
                
                # Update ref to prevent GC
                self.image_refs.append(new_photo)
                
                # Also update resize handles if selected
                if hasattr(self, 'resize_target') and self.resize_target == img_id:
                     self.update_resize_handle()
                     
            except Exception as e:
                print(f"Error rescaling image {img_id}: {e}")

    def zoom_wheel(self, event):
        # Determine direction
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

        self.update_minimap()
        

    def update_minimap(self, event=None):
        """Robust mini-map update with theme awareness and contrast reinforcement."""
        if not hasattr(self, 'minimap') or not self.minimap:
            return
        
        try:
            # Darker background for the minimap containment to make the board stand out
            self.minimap.configure(bg="#D0D0D0")
            self.minimap.delete("all")
            
            # 1. Dimensions
            mw = self.minimap.winfo_width()
            mh = self.minimap.winfo_height()
            if mw <= 1: 
                try:
                    mw = int(self.minimap.cget("width"))
                    mh = int(self.minimap.cget("height"))
                except:
                    mw, mh = 220, 150
            
            vx1, vy1 = self.c.canvasx(0), self.c.canvasy(0)
            vw, vh = self.c.winfo_width(), self.c.winfo_height()
            if vw <= 1: vw, vh = 1000, 800
            vx2, vy2 = self.c.canvasx(vw), self.c.canvasy(vh)

            # 2. Project Bounds - Fixed based on items for a stable map
            items = self.c.find_all()
            drawable_items = []
            bboxes = []
            for i in items:
                tags = self.c.gettags(i)
                if any(t in tags for t in ["grid", "poly_temp", "poly_guide", "resize"]): continue
                b = self.c.bbox(i)
                if b:
                    drawable_items.append(i)
                    bboxes.append(b)
            # 3. Comprehensive Bounds (Items + Viewport)
            all_x = [vx1, vx2] + ([b[0] for b in bboxes] if bboxes else []) + ([b[2] for b in bboxes] if bboxes else [])
            all_y = [vy1, vy2] + ([b[1] for b in bboxes] if bboxes else []) + ([b[3] for b in bboxes] if bboxes else [])
            
            min_x, max_x = min(all_x), max(all_x)
            min_y, max_y = min(all_y), max(all_y)
            
            span_x = max(1, max_x - min_x)
            span_y = max(1, max_y - min_y)
            
            # Use 5% padding around the edges
            s = min(mw / span_x if span_x > 0 else 1, mh / span_y if span_y > 0 else 1) * 0.95
            ox = (mw - span_x * s) / 2
            oy = (mh - span_y * s) / 2

            def m_pt(x, y):
                return (x - min_x) * s + ox, (y - min_y) * s + oy

            self.mm_state = {'min_x': min_x, 'min_y': min_y, 's': s, 'ox': ox, 'oy': oy, 'mw': mw, 'mh': mh}

            # 6. Render Board Boundary
            self.minimap.create_rectangle(ox, oy, ox + span_x*s, oy + span_y*s, fill="#FFFFFF", outline="#777", width=1)
            
            # 6. Render Items
            for i in drawable_items:
                b = self.c.bbox(i)
                if not b: continue
                
                itype = self.c.type(i)
                color = "black"
                try:
                    color = self.c.itemcget(i, "fill")
                    if not color or color == "None": color = self.c.itemcget(i, "outline")
                except: pass
                if not color or color == "None": color = "black"
                
                mx1, my1 = m_pt(b[0], b[1])
                mx2, my2 = m_pt(b[2], b[3])
                
                if itype == "line":
                    raw = self.c.coords(i)
                    m_coords = []
                    for k in range(0, len(raw), 2):
                        px, py = m_pt(raw[k], raw[k+1])
                        m_coords.append(px); m_coords.append(py)
                    if len(m_coords) >= 4:
                        self.minimap.create_line(*m_coords, fill=color, width=1, capstyle=tk.ROUND)
                
                elif itype == "text":
                    try:
                        txt = self.c.itemcget(i, "text")
                        if not txt: continue
                        
                        try:
                            f_info = self.c.itemcget(i, "font")
                            orig_size = 12
                            if f_info:
                                parts = str(f_info).split()
                                for p in parts:
                                    if p.isdigit() or (p.startswith('-') and p[1:].isdigit()):
                                        orig_size = abs(int(p))
                                        break
                            f_size = max(1, int(orig_size * s))
                        except:
                            f_size = max(1, int((my2 - my1) * 0.1))

                        cx, cy = (mx1 + mx2) / 2, (my1 + my2) / 2
                        m_width = int((mx2 - mx1) * 1.1)
                        self.minimap.create_text(cx, cy, text=txt, fill=color, font=("Arial", f_size), anchor="center", width=m_width)
                    except:
                        pass # Removed Greeking logic
                
                elif itype == "image":
                    self.minimap.create_rectangle(mx1, my1, mx2, my2, fill="#a0c4ff", outline="#5e81ac")
                
                else:
                    self.minimap.create_rectangle(mx1, my1, mx2, my2, fill=color, outline="#777", width=1)

            # 7. Render Viewport (Red Rect)
            vx1_m, vy1_m = m_pt(vx1, vy1)
            vx2_m, vy2_m = m_pt(vx2, vy2)
            self.minimap.create_rectangle(vx1_m, vy1_m, vx2_m, vy2_m, outline="red", width=2)
            
            # Status Indicator (Confirmed Active)
            self.minimap.create_text(5, 5, text="LIVE BOARD", fill="#555", font=("Arial", 6, "bold"), anchor="nw")
            
            # Ensure visible
            if hasattr(self, 'minimap_frame'):
                self.minimap_frame.lift()
                
        except Exception as e:
            print(f"Minimap Error: {e}")

    def minimap_click(self, event):
        """Centered navigation when clicking on the minimap."""
        if not hasattr(self, 'mm_state'): return
        
        ms = self.mm_state
        # 1. Calculate target center in Canvas Coordinates
        # target_cx = (event.x - ox) / s + min_x
        target_cx = (event.x - ms['ox']) / ms['s'] + ms['min_x']
        target_cy = (event.y - ms['oy']) / ms['s'] + ms['min_y']
        
        # 2. Get current center
        screen_w = self.c.winfo_width()
        screen_h = self.c.winfo_height()
        current_cx = self.c.canvasx(screen_w/2)
        current_cy = self.c.canvasy(screen_h/2)
        
        # 3. Calculate Delta to move
        dx = int(target_cx - current_cx)
        dy = int(target_cy - current_cy)
        
        # 4. Move using scan_dragto mechanism
        # scan_mark sets the anchor, dragto moves relative to it.
        # To move BY (dx, dy), we can mark (0,0) and drag to (-dx, -dy)
        # OR: simpler approach, use scan_mark/dragto logic:
        # self.c.scan_mark(0, 0)
        # self.c.scan_dragto(-dx, -dy, gain=1)
        # Note: dragto logic is: view moves such that 'mark' ends up at 'dragto'.
        # If we want view to move +dx (right), we need content to move left.
        # So we mark at X, and drag to X-dx.
        
        self.c.scan_mark(0, 0)
        self.c.scan_dragto(-dx, -dy, gain=1)
        
        # Immediate update for responsiveness
        self.update_minimap()
        # Ensure it stays on top during movement
        if hasattr(self, 'minimap_frame'):
            self.minimap_frame.lift()

    def update_scrollregion(self):
        """Expands scrollregion dynamically to include objects AND current view buffer."""
        # Note: We do NOT set self.c.config(scrollregion=...) anymore.
        # This allows infinite panning via scan_dragto without artificial constraints.
        # The minimap handles its own bounds calculation.
        
        self.update_minimap()

    def show_property_bar(self, items):
        """Shows contextual property bar near selected items."""
        if not items:
            self.hide_property_bar()
            return
            
        if self.property_bar: self.hide_property_bar()
        
        # Get aggregate bbox
        bboxes = [self.c.bbox(i) for i in items if self.c.bbox(i)]
        if not bboxes: return
        
        x1 = min(b[0] for b in bboxes)
        y1 = min(b[1] for b in bboxes)
        x2 = max(b[2] for b in bboxes)
        y2 = max(b[3] for b in bboxes)
        
        # Map to root coordinates
        screen_x = self.c.winfo_rootx() + (x1 + x2) / 2 - self.c.canvasx(0)
        screen_y = self.c.winfo_rooty() + y1 - self.c.canvasy(0) - 40 # Above
        
        # Constrain to window
        screen_x = max(10, min(screen_x, self.root.winfo_width() - 200))
        screen_y = max(10, screen_y)

        # Ensure we have access to theme colors
        bg_main = self.theme["canvas_bg"] if hasattr(self, 'theme') else "#F3F3F3"
        bg_bar  = self.theme["bg_secondary"] if hasattr(self, 'theme') else "white"
        fg_text = self.theme.get("text_color", "black") if hasattr(self, 'theme') else "black"
        bg_hover = self.theme.get("btn_hover", "#E0E0E0") if hasattr(self, 'theme') else "#E0E0E0"

        # 1. Create the rounded floating frame
        self.property_bar = RoundedFrame(self.root, width=200, height=45, corner_radius=12,
                                         bg_color=bg_main, color=bg_bar, shadow_offset=4)
        self.property_bar.place(x=screen_x, y=screen_y, anchor=tk.S)
        
        # 2. Inner container for auto-sizing buttons
        container = tk.Frame(self.property_bar, bg=bg_bar)
        
        # Helper to create styled flat buttons
        def add_btn(txt, cmd, fg_override=None):
            btn = tk.Button(container, text=txt, command=cmd, bg=bg_bar, fg=fg_override or fg_text,
                            activebackground=bg_hover, activeforeground=fg_override or fg_text,
                            relief=tk.FLAT, borderwidth=0, font=("Segoe UI", 9, "bold"), cursor="hand2", padx=6, pady=2)
            btn.pack(side=tk.LEFT, padx=1)
            # Hover effects
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=bg_hover))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=bg_bar))
            return btn
            
        # Actions
        add_btn("Delete", self.delete_selected, fg_override="#E81123")
        add_btn("Color", self.change_fg)
        
        # Image/PDF Specific Actions
        is_image = any(self.c.type(i) == "image" for i in items)
        if is_image:
            img_items = [i for i in items if self.c.type(i) == "image"]
            if len(img_items) == 1:
                add_btn("Crop", lambda: self.enter_crop_mode(img_items[0]))

        # Text Specific Actions
        has_text = any(self.c.type(i) == "text" for i in items)
        if has_text:
            text_items = [i for i in items if self.c.type(i) == "text"]
            add_btn("Edit", lambda: self.edit_text_dialog(text_items[0]))
            add_btn("Font", lambda: self.cycle_font(text_items))
            add_btn("A+", lambda: self.adjust_text_size(text_items, 2))
            add_btn("A-", lambda: self.adjust_text_size(text_items, -2))

        # Line Specific Actions (Ink to Text)
        has_lines = any(self.c.type(i) == "line" for i in items)
        if has_lines:
            line_items = [i for i in items if self.c.type(i) == "line"]
            add_btn("Ink -> Text", lambda: self.convert_ink_to_text(line_items), fg_override="#0078D4")
            
        # 3. Auto-resize RoundedFrame to fit buttons
        self.root.update_idletasks()
        req_w = container.winfo_reqwidth()
        req_h = container.winfo_reqheight()
        
        self.property_bar.configure(width=req_w + 24, height=req_h + 16)
        
        # 4. Center container visually accounting for shadow
        container.place(relx=0.5, rely=0.5, anchor=tk.CENTER, x=-2, y=-2)
        
        # More tools can be added here

    def hide_property_bar(self):
        if self.property_bar:
            self.property_bar.destroy()
            self.property_bar = None

    def convert_ink_to_text(self, items):
        """Converts selected brush strokes to digital text using Gemini API."""
        if not items: return
        
        self.c.config(cursor="watch")
        self.root.update()
        
        try:
            # 1. Calculate Bounding Box of all lines
            bboxes = [self.c.bbox(item) for item in items if self.c.bbox(item)]
            if not bboxes:
                self.c.config(cursor="arrow")
                return
                
            min_x = min(b[0] for b in bboxes)
            min_y = min(b[1] for b in bboxes)
            max_x = max(b[2] for b in bboxes)
            max_y = max(b[3] for b in bboxes)
            
            w = max_x - min_x
            h = max_y - min_y
            
            # Padding
            pad = 20
            w += pad * 2
            h += pad * 2
            min_x -= pad
            min_y -= pad
            
            # 2. Draw lines on a new PIL image with 2x Super-Sampling for higher TrOCR accuracy
            from PIL import Image, ImageDraw
            upscale = 2.0
            uw, uh = int(w * upscale), int(h * upscale)
            img = Image.new("RGB", (uw, uh), "white")
            draw = ImageDraw.Draw(img)
            
            for item in items:
                coords = self.c.coords(item)
                # Map coordinates to upscaled space
                shifted = []
                for i in range(0, len(coords), 2):
                    shifted.append((coords[i] - min_x) * upscale)
                    shifted.append((coords[i+1] - min_y) * upscale)
                    
                color = self.c.itemcget(item, "fill") or "black"
                try: 
                    # Normalize width: TrOCR likes strokes around 3-5px in its native space.
                    # We upscale, so we should ensure the virtual stroke isn't too thin.
                    orig_width = float(self.c.itemcget(item, "width"))
                    width = max(3.0, orig_width) * upscale
                except: 
                    width = 4.0 * upscale
                    
                draw.line(shifted, fill=color, width=int(width), joint="curve")
                
            # 3. Call AI
            text = self.extract_ink_text(img)
            
            if text:
                # 4. Serialize and Remove lines
                item_data_list = []
                for item in items:
                    data = self.delete_item(item)
                    if data: item_data_list.append(data)
                    self.c.delete(item)
                    if item in self.objects: self.objects.remove(item)
                
                # 5. Create Text Object
                center_x = min_x + w / 2
                center_y = min_y + h / 2
                self.hide_property_bar()
                
                text_id = self.c.create_text(center_x, center_y, text=text, fill="black", font=(self.current_font, int(20 * self.scale)), tags=("object", "text"))
                self.objects.append(text_id)
                # Ensure base size is scale-independent (20 is the intended design base size)
                self.text_base_sizes[text_id] = (self.current_font, 20)
                
                self.undo_stack.append(('ink_to_text', text_id, item_data_list))
                self.redo_stack.clear()
                self.clear_selection()
            else:
                messagebox.showinfo("Ink to Text", "No legible text was found.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to convert ink to text: {e}")
            
        self.c.config(cursor="arrow")

    def enter_crop_mode(self, item_id):
        """Initializes crop mode for the selected image/PDF page."""
        self.in_crop_mode = True
        self.crop_target = item_id
        self.clear_selection()
        self.hide_property_bar()
        
        # Get image bbox
        bbox = self.c.bbox(item_id)
        if not bbox: return
        x1, y1, x2, y2 = bbox
        
        # Create crop rectangle
        self.crop_rect = self.c.create_rectangle(x1, y1, x2, y2, outline="#0078D4", width=2, dash=(4, 4), tags="crop_ui")
        
        # Create handles
        self.crop_handles = []
        handle_size = 8
        positions = [
            (x1, y1, "nw"), (x2, y1, "ne"), (x1, y2, "sw"), (x2, y2, "se"),
            ((x1+x2)/2, y1, "n"), ((x1+x2)/2, y2, "s"), (x1, (y1+y2)/2, "w"), (x2, (y1+y2)/2, "e")
        ]
        
        for hx, hy, tag in positions:
            h = self.c.create_rectangle(hx-handle_size, hy-handle_size, hx+handle_size, hy+handle_size,
                                         fill="white", outline="#0078D4", tags=("crop_ui", f"crop_handle_{tag}", "crop_handle"))
            self.crop_handles.append(h)
            
        # Show specific property bar for cropping
        self.show_crop_property_bar()
        self.c.config(cursor="cross")

    def show_crop_property_bar(self):
        """Shows Apply/Cancel buttons during crop mode."""
        bbox = self.c.bbox(self.crop_target)
        if not bbox: return
        x1, y1, x2, y2 = bbox
        
        screen_x = self.c.winfo_rootx() + (x1 + x2) / 2 - self.c.canvasx(0)
        screen_y = self.c.winfo_rooty() + y1 - self.c.canvasy(0) - 40
        
        self.property_bar = tk.Frame(self.root, bg="white", padx=5, pady=2, relief=tk.RAISED, borderwidth=1)
        self.property_bar.place(x=screen_x, y=screen_y, anchor=tk.S)
        
        tk.Button(self.property_bar, text="Apply", command=self.apply_crop, bg="#4CAF50", fg="white", relief=tk.FLAT, font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(self.property_bar, text="Cancel", command=self.exit_crop_mode, bg="#f44336", fg="white", relief=tk.FLAT, font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)

    def exit_crop_mode(self):
        """Exits crop mode and cleans up UI."""
        self.in_crop_mode = False
        self.c.delete("crop_ui")
        self.hide_property_bar()
        self.c.config(cursor="arrow")
        self.crop_target = None

    def handle_crop_drag(self, event):
        """Resizes the crop rectangle based on handle dragging."""
        if not hasattr(self, 'active_crop_handle') or not self.active_crop_handle: return
        
        cx = self.c.canvasx(event.x)
        cy = self.c.canvasy(event.y)
        
        # Current crop rect coords
        x1, y1, x2, y2 = self.c.coords(self.crop_rect)
        tags = self.c.gettags(self.active_crop_handle)
        
        if "crop_handle_nw" in tags: x1, y1 = cx, cy
        elif "crop_handle_ne" in tags: x2, y1 = cx, cy
        elif "crop_handle_sw" in tags: x1, y2 = cx, cy
        elif "crop_handle_se" in tags: x2, y2 = cx, cy
        elif "crop_handle_n" in tags: y1 = cy
        elif "crop_handle_s" in tags: y2 = cy
        elif "crop_handle_w" in tags: x1 = cx
        elif "crop_handle_e" in tags: x2 = cx
        
        # Enforce minimum size and bounds (stay within original image)
        img_bbox = self.c.bbox(self.crop_target)
        ix1, iy1, ix2, iy2 = img_bbox
        
        x1 = max(ix1, min(x1, x2 - 10))
        y1 = max(iy1, min(y1, y2 - 10))
        x2 = min(ix2, max(x2, x1 + 10))
        y2 = min(iy2, max(y2, y1 + 10))
        
        self.c.coords(self.crop_rect, x1, y1, x2, y2)
        self.update_crop_handles(x1, y1, x2, y2)

    def update_crop_handles(self, x1, y1, x2, y2):
        positions = [
            (x1, y1, "nw"), (x2, y1, "ne"), (x1, y2, "sw"), (x2, y2, "se"),
            ((x1+x2)/2, y1, "n"), ((x1+x2)/2, y2, "s"), (x1, (y1+y2)/2, "w"), (x2, (y1+y2)/2, "e")
        ]
        handle_size = 8
        for i, (hx, hy, tag) in enumerate(positions):
            self.c.coords(self.crop_handles[i], hx-handle_size, hy-handle_size, hx+handle_size, hy+handle_size)

    def apply_crop(self):
        """Crops the image based on the crop rectangle."""
        print(f"[DEBUG apply_crop] Started. crop_target: getattr returns {getattr(self, 'crop_target', None)}")
        if not getattr(self, 'crop_target', None): return
        
        # Get crop rect relative to image safely
        rect_id = getattr(self, 'crop_rect', -1)
        rect_coords = self.c.coords(rect_id)
        print(f"[DEBUG apply_crop] rect_id: {rect_id}, rect_coords: {rect_coords}")
        if not rect_coords or len(rect_coords) != 4:
            self.exit_crop_mode()
            return

        cx1, cy1, cx2, cy2 = rect_coords
        
        img_bbox = self.c.bbox(self.crop_target)
        print(f"[DEBUG apply_crop] img_bbox: {img_bbox}")
        if not img_bbox or len(img_bbox) != 4:
            self.exit_crop_mode()
            return
            
        ix1, iy1, ix2, iy2 = img_bbox
        
        # Position of image item may be moved, so we use its top-left as (0,0)
        rel_x1 = (cx1 - ix1)
        rel_y1 = (cy1 - iy1)
        rel_x2 = (cx2 - ix1)
        rel_y2 = (cy2 - iy1)
        
        # Current displayed size
        curr_w = ix2 - ix1
        curr_h = iy2 - iy1
        print(f"[DEBUG apply_crop] curr_w: {curr_w}, curr_h: {curr_h}")
        
        if curr_w <= 0 or curr_h <= 0:
            self.exit_crop_mode()
            return
        
        # High-res master image
        print(f"[DEBUG apply_crop] stored_images exists: {hasattr(self, 'stored_images')}, in stored: {self.crop_target in self.stored_images if hasattr(self, 'stored_images') else 'N/A'}")
        if not hasattr(self, 'stored_images') or self.crop_target not in self.stored_images:
            messagebox.showerror("Error", "Original image data not found.")
            self.exit_crop_mode()
            return
            
        master_img = self.stored_images[self.crop_target]
        master_w, master_h = master_img.size
        print(f"[DEBUG apply_crop] master size: {master_w}x{master_h}")
        
        # Scale rel coordinates to master image space
        scale_x = master_w / curr_w
        scale_y = master_h / curr_h
        
        crop_box = (int(rel_x1 * scale_x), int(rel_y1 * scale_y), int(rel_x2 * scale_x), int(rel_y2 * scale_y))
        
        # Update cumulative crop in metadata for project persistence
        if not hasattr(self, 'image_metadata'): self.image_metadata = {}
        metadata = self.image_metadata.get(self.crop_target, {})
        
        # If it's a PDF page, we already have some metadata.
        # Otherwise it's a regular image - initialize metadata if needed.
        if "cumulative_crop" not in metadata:
            metadata["cumulative_crop"] = list(crop_box)
        else:
            old_box = metadata["cumulative_crop"]
            # The new crop_box is relative to the CURRENT master (which is already cropped)
            # So we add the current offsets to the old cumulative offsets
            new_L = old_box[0] + crop_box[0]
            new_T = old_box[1] + crop_box[1]
            new_R = old_box[0] + crop_box[2]
            new_B = old_box[1] + crop_box[3]
            metadata["cumulative_crop"] = [new_L, new_T, new_R, new_B]
        
        self.image_metadata[self.crop_target] = metadata

        try:
            cropped_img = master_img.crop(crop_box)
            
            # Save state for undo
            old_img = master_img
            old_bbox = (ix1, iy1, ix2, iy2)
            
            # Update stored image
            self.stored_images[self.crop_target] = cropped_img
            
            # Update canvas item
            # Resize cropped image for current zoom level
            new_disp_w = int((rel_x2 - rel_x1))
            new_disp_h = int((rel_y2 - rel_y1))
            
            # PhotoImage ref
            tk_img = ImageTk.PhotoImage(cropped_img.resize((new_disp_w, new_disp_h), Image.LANCZOS))
            if not hasattr(self, 'image_refs'): self.image_refs = []
            self.image_refs.append(tk_img)
            
            self.c.itemconfig(self.crop_target, image=tk_img)
            self.c.coords(self.crop_target, cx1, cy1)
            
            # Update base sizes
            # base_size is size at scale 1.0
            self.image_base_sizes[self.crop_target] = (new_disp_w / self.scale, new_disp_h / self.scale)
            
            # Add to undo stack
            # ('crop', item_id, old_img, old_bbox, new_img, new_bbox)
            new_bbox = (cx1, cy1, cx1 + new_disp_w, cy1 + new_disp_h)
            self.undo_stack.append(('crop', self.crop_target, old_img, old_bbox, cropped_img, new_bbox))
            self.redo_stack.clear()
            
            self.exit_crop_mode()
            self.update_minimap()
            messagebox.showinfo("Success", "Image cropped successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Cropping failed: {e}")
            self.exit_crop_mode()

    def start_pan(self, event):
        self.c.config(cursor='fleur')
        self.c.scan_mark(event.x, event.y)

    def pan(self, event):
        self.c.scan_dragto(event.x, event.y, gain=1)
        self.update_scrollregion()

    def is_panning_key_held(self):
        return False 

    def end_pan(self, event):
        if self.shape == 'hand':
            self.c.config(cursor='hand2' if os.name=='nt' else 'hand2') 
        else:
             self.c.config(cursor='arrow')
    
    # --- Grouping Logic ---
    def group_selected(self, event=None):
        if len(self.selected_objects) < 2: return
        
        gid = f"group_{self.group_counter}"
        self.group_counter += 1
        self.groups[gid] = list(self.selected_objects)
        
        for item in self.selected_objects:
            self.c.addtag_withtag(gid, item)
            
        print(f"Created Group: {gid} with items {self.groups[gid]}")

    def ungroup_selected(self, event=None):
        if not self.selected_objects: return
        
        groups_to_dissolve = set()
        for item in self.selected_objects:
            tags = self.c.gettags(item)
            for tag in tags:
                if tag.startswith("group_"):
                    groups_to_dissolve.add(tag)
        
        for gid in groups_to_dissolve:
            if gid in self.groups:
                items = self.groups[gid]
                for item in items:
                    self.c.dtag(item, gid) 
                del self.groups[gid]
                print(f"Ungrouped: {gid}")

    # ==========================================
    # LAYER MANAGEMENT
    # ==========================================
    def _get_layer_targets(self):
        """Returns relevant items to apply layer changes to."""
        if self.selected_objects:
            return list(self.selected_objects)
        # If nothing selected, operate on the topmost item under cursor
        return []

    def layer_bring_to_front(self):
        """Bring selected items to the very top layer."""
        targets = self._get_layer_targets()
        for item in targets:
            try:
                self.c.tag_raise(item)
            except tk.TclError:
                pass

    def layer_send_to_back(self):
        """Send selected items to the very bottom layer (but above grid)."""
        targets = self._get_layer_targets()
        for item in targets:
            try:
                self.c.tag_lower(item)
                # Keep grid lines at bottom
                self.c.tag_lower("grid_line")
            except tk.TclError:
                pass

    def layer_bring_forward(self):
        """Move selected items one step forward in the layer stack."""
        targets = self._get_layer_targets()
        for item in targets:
            try:
                # Find the item above and raise relative to it
                all_items = self.c.find_all()
                idx = list(all_items).index(item)
                if idx < len(all_items) - 1:
                    above = all_items[idx + 1]
                    self.c.tag_raise(item, above)
            except (tk.TclError, ValueError):
                pass

    def layer_send_backward(self):
        """Move selected items one step backward in the layer stack."""
        targets = self._get_layer_targets()
        for item in targets:
            try:
                all_items = self.c.find_all()
                idx = list(all_items).index(item)
                if idx > 0:
                    below = all_items[idx - 1]
                    self.c.tag_lower(item, below)
                    # Don't go below grid
                    self.c.tag_lower("grid_line")
            except (tk.TclError, ValueError):
                pass

    # ==========================================
    # CANVAS CONTEXT MENU (Right-Click)
    # ==========================================
    def show_canvas_context_menu(self, event):
        """Show a rich right-click context menu with layer management options."""
        menu = tk.Menu(self.root, tearoff=0, 
                       bg=self.theme["bg_secondary"], fg=self.theme["text_color"],
                       activebackground=self.theme["accent"], activeforeground="white",
                       relief=tk.FLAT, bd=0)
        
        # Detect item under cursor
        items = self.c.find_overlapping(event.x-3, event.y-3, event.x+3, event.y+3)
        valid = [i for i in items if "grid_line" not in self.c.gettags(i) and 
                 "laser" not in self.c.gettags(i)]
        clicked_item = valid[-1] if valid else None

        if clicked_item:
            if clicked_item not in self.selected_objects:
                self.clear_selection()
                self.selected_objects.append(clicked_item)
                self.draw_selection_handles(clicked_item)
            
            # Layer Controls
            menu.add_command(label="⬆ Bring to Front   Ctrl+↑", 
                           command=self.layer_bring_to_front)
            menu.add_command(label="⬇ Send to Back      Ctrl+↓", 
                           command=self.layer_send_to_back)
            menu.add_command(label="↑ Bring Forward     Ctrl+]", 
                           command=self.layer_bring_forward)
            menu.add_command(label="↓ Send Backward     Ctrl+[", 
                           command=self.layer_send_backward)
            menu.add_separator()
            
            # Grouping
            if len(self.selected_objects) >= 2:
                menu.add_command(label="â¬¡ Group             Ctrl+G", 
                               command=self.group_selected)
            if len(self.selected_objects) >= 1:
                menu.add_command(label="â¬¡ Ungroup", command=self.ungroup_selected)
            menu.add_separator()
            
            # Delete
            menu.add_command(label="âœ• Delete", command=self.delete_selected)
        else:
            # Clicked on empty canvas
            menu.add_command(label="ðŸ”² Paste", command=lambda: self.paste_selection(event))
            menu.add_separator()
            menu.add_command(label="ðŸ“„ Export as SVG...", command=self.export_svg)
            menu.add_command(label="ðŸ“„ Export as PNG...", command=self.export_image)
            menu.add_separator()
            menu.add_command(label="ðŸ—‘ Clear Canvas", command=self.clear)

        menu.tk_popup(event.x_root, event.y_root)
        menu.grab_release()

    # ==========================================
    # SVG EXPORT
    # ==========================================
    def export_svg(self):
        """Export canvas contents to an SVG file."""
        from tkinter.filedialog import asksaveasfilename
        
        filename = asksaveasfilename(
            defaultextension=".svg",
            filetypes=[("SVG Files", "*.svg"), ("All Files", "*.*")],
            title="Export as SVG"
        )
        if not filename:
            return
        
        # Get canvas dimensions
        cw = self.c.winfo_width()
        ch = self.c.winfo_height()
        
        svg_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{cw}" height="{ch}" viewBox="0 0 {cw} {ch}">',
            f'  <rect width="{cw}" height="{ch}" fill="{self.color_bg}"/>'
        ]
        
        ignored_tags = {"grid_line", "laser", "poly_guide", "select_box", "eraser_cursor",
                        "selection_handle", "selection_rect", "ui", "minimap"}
        
        for item in self.c.find_all():
            tags = set(self.c.gettags(item))
            if tags & ignored_tags:
                continue

            itype = self.c.type(item)
            coords = self.c.coords(item)
            
            try:
                if itype == "line":
                    cfg = self.c.itemconfigure(item)
                    color = cfg.get("fill", [None, None, None, None, "black"])[4] or "black"
                    width = cfg.get("width", [None, None, None, None, "1"])[4] or "1"
                    opacity = "0.5" if "stipple" in str(cfg.get("stipple", ["","","","",""])[4]) and cfg.get("stipple", ["","","","",""])[4] else "1"
                    
                    if len(coords) >= 4:
                        points_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(coords[::2], coords[1::2]))
                        svg_lines.append(
                            f'  <polyline points="{points_str}" stroke="{color}" '
                            f'stroke-width="{width}" fill="none" stroke-linecap="round" opacity="{opacity}"/>'
                        )
                
                elif itype == "rectangle":
                    cfg = self.c.itemconfigure(item)
                    outline = cfg.get("outline", [None, None, None, None, "black"])[4] or "none"
                    fill = cfg.get("fill", [None, None, None, None, ""])[4] or "none"
                    width = cfg.get("width", [None, None, None, None, "1"])[4] or "1"
                    
                    if len(coords) >= 4:
                        x1, y1, x2, y2 = coords[:4]
                        svg_lines.append(
                            f'  <rect x="{x1:.1f}" y="{y1:.1f}" width="{x2-x1:.1f}" height="{y2-y1:.1f}" '
                            f'fill="{fill}" stroke="{outline}" stroke-width="{width}"/>'
                        )

                elif itype == "oval":
                    cfg = self.c.itemconfigure(item)
                    outline = cfg.get("outline", [None, None, None, None, "black"])[4] or "none"
                    fill = cfg.get("fill", [None, None, None, None, ""])[4] or "none"
                    width = cfg.get("width", [None, None, None, None, "1"])[4] or "1"
                    
                    if len(coords) >= 4:
                        x1, y1, x2, y2 = coords[:4]
                        cx_val = (x1 + x2) / 2
                        cy_val = (y1 + y2) / 2
                        rx = (x2 - x1) / 2
                        ry = (y2 - y1) / 2
                        svg_lines.append(
                            f'  <ellipse cx="{cx_val:.1f}" cy="{cy_val:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" '
                            f'fill="{fill}" stroke="{outline}" stroke-width="{width}"/>'
                        )

                elif itype == "text":
                    cfg = self.c.itemconfigure(item)
                    text_val = cfg.get("text", [None, None, None, None, ""])[4] or ""
                    color = cfg.get("fill", [None, None, None, None, "black"])[4] or "black"
                    font_raw = cfg.get("font", [None, None, None, None, ""])[4]
                    font_size = 14
                    try:
                        if font_raw:
                            parts = str(font_raw).split()
                            for part in parts:
                                if part.isdigit():
                                    font_size = int(part)
                                    break
                    except Exception:
                        pass
                    
                    if coords and len(coords) >= 2:
                        # Escape XML characters
                        safe_text = text_val.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        svg_lines.append(
                            f'  <text x="{coords[0]:.1f}" y="{coords[1]:.1f}" '
                            f'fill="{color}" font-size="{font_size}" '
                            f'font-family="Arial, sans-serif" text-anchor="middle">{safe_text}</text>'
                        )

                elif itype == "polygon":
                    cfg = self.c.itemconfigure(item)
                    outline = cfg.get("outline", [None, None, None, None, "black"])[4] or "none"
                    fill = cfg.get("fill", [None, None, None, None, ""])[4] or "none"
                    width = cfg.get("width", [None, None, None, None, "1"])[4] or "1"
                    
                    if len(coords) >= 4:
                        points_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(coords[::2], coords[1::2]))
                        svg_lines.append(
                            f'  <polygon points="{points_str}" fill="{fill}" '
                            f'stroke="{outline}" stroke-width="{width}"/>'
                        )
            except Exception as e:
                print(f"SVG export: skipping item {item} ({itype}): {e}")
                continue
        
        svg_lines.append("</svg>")
        
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write("\n".join(svg_lines))
            from tkinter import messagebox
            messagebox.showinfo("Export Successful", f"Canvas exported to:\n{filename}")
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Export Failed", f"Could not save SVG:\n{e}")

    def show_context_menu(self, event):
        items = self.c.find_overlapping(event.x-5, event.y-5, event.x+5, event.y+5)
        valid_items = [i for i in items if "grid" not in self.c.gettags(i)]
        target = valid_items[-1] if valid_items else None
        
        if not target:
             return
             
        if target not in self.selected_objects:
             self.clear_selection()
             self.select_object(event.x, event.y, event)
        
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Bring to Front", command=self.bring_to_front)
        menu.add_command(label="Send to Back", command=self.send_to_back)
        menu.add_separator()
        
        if len(self.selected_objects) > 1:
            menu.add_command(label="Group", command=self.group_selected)
        
        in_group = False
        for obj in self.selected_objects:
            tags = self.c.gettags(obj)
            if any(t.startswith("group_") for t in tags):
                in_group = True
                break
        
        if in_group:
            menu.add_command(label="Ungroup", command=self.ungroup_selected)
            
        menu.add_separator()
        menu.add_command(label="Delete", command=self.delete_selected)
        
        menu.post(event.x_root, event.y_root)

    def bring_to_front(self):
        for item in self.selected_objects:
            self.c.tag_raise(item)
            
    def send_to_back(self):
        for item in self.selected_objects:
            self.c.tag_lower(item)
        self.c.tag_lower("grid")
        
    def delete_item(self, item):
         item_data = {}
         item_type = self.c.type(item)
         item_data['type'] = item_type
         item_data['coords'] = self.c.coords(item)
         item_data['tags'] = self.c.gettags(item)
         
         # Config
         config = {}
         keys = ['fill', 'outline', 'width', 'font', 'text', 'arrow', 'capstyle', 'smooth', 'splinesteps', 'anchor', 'arrowshape']
         for k in keys:
             try:
                 val = self.c.itemcget(item, k)
                 if val: config[k] = val
             except: pass
         item_data['config'] = config
         
         # Image specific
         if item_type == 'image':
             if hasattr(self, 'stored_images') and item in self.stored_images:
                 item_data['stored_image'] = self.stored_images[item]
             if hasattr(self, 'image_files') and item in self.image_files:
                 item_data['image_path'] = self.image_files[item]
             if hasattr(self, 'image_metadata') and item in self.image_metadata:
                 item_data['metadata'] = self.image_metadata[item]
             if hasattr(self, 'image_base_sizes') and item in self.image_base_sizes:
                 item_data['image_base_size'] = self.image_base_sizes[item]
         
         # Zoom specific (Base metrics)
         if item_type == 'text':
             if item in self.text_base_sizes:
                 item_data['base_font'] = self.text_base_sizes[item]
             if hasattr(self, 'text_base_widths') and item in self.text_base_widths:
                 item_data['base_width'] = self.text_base_widths[item]
         
         self.c.delete(item)
         if hasattr(self, 'objects') and item in self.objects: self.objects.remove(item)
         if hasattr(self, 'image_files') and item in self.image_files: del self.image_files[item]
         if hasattr(self, 'image_metadata') and item in self.image_metadata: del self.image_metadata[item]
         
         # Cleanup connections for deleted item
         if hasattr(self, 'connections'):
             if item in self.connections:
                 del self.connections[item]
             to_rem = [lid for lid, conn in self.connections.items() if conn.get('start') == item or conn.get('end') == item]
             for lid in to_rem:
                 if lid in self.connections: del self.connections[lid]
         
         return item_data

    def delete_selected(self, event=None):
        if not self.selected_objects: return
        
        undo_data_list = []
        for item in list(self.selected_objects):
             try:
                 item_data = self.delete_item(item)
                 undo_data_list.append(item_data)
             except Exception:
                 pass
        
        self.undo_stack.append(('delete', undo_data_list))
        self.redo_stack.clear()
        
        self.selected_objects.clear()
        self.clear_selection() 
        self.update_minimap()

    # --- Polygon Tool Logic ---
    def on_mouse_move(self, event):
        # Laser Pointer Logic
        if self.shape == 'laser':
            # Use canvas coordinates to ensure it draws effectively on the canvas surface
            cx = self.c.canvasx(event.x)
            cy = self.c.canvasy(event.y)
            r = 5 # Radius
            
            if hasattr(self, 'laser_id') and self.laser_id:
                # Move existing laser
                self.c.coords(self.laser_id, cx-r, cy-r, cx+r, cy+r)
                self.c.tag_raise(self.laser_id) # Ensure it stays on top
            else:
                # Create laser if not exists
                self.laser_id = self.c.create_oval(cx-r, cy-r, cx+r, cy+r, fill="red", outline="red", tags="laser")
            return
        else:
            # Ensure laser disappears when switching tools
            if hasattr(self, 'laser_id') and self.laser_id:
                self.c.delete(self.laser_id)
                self.laser_id = None

        if self.shape == 'polygon' and len(self.poly_points) >= 2:
            x, y = self.snap(event.x), self.snap(event.y)
            last_x, last_y = self.poly_points[-2], self.poly_points[-1]
            
            self.c.delete("poly_guide")
            self.c.create_line(last_x, last_y, x, y, fill="grey", dash=(4, 4), tags="poly_guide")

    def finish_polygon(self, event):
        if self.shape == 'polygon' and len(self.poly_points) >= 6: 
            self.c.delete("poly_temp")
            self.c.delete("poly_guide")
            
            self.shape_id = self.c.create_polygon(self.poly_points, outline=self.color_fg, 
                                                  fill=self.fill_color, width=self.penwidth)
            self.objects.append(self.shape_id)
            self.undo_stack.append(('create_polygon', self.shape_id, list(self.poly_points), 
                                    self.color_fg, self.fill_color, self.penwidth))
            
            self.poly_points = []
            self.update_scrollregion()
             
        elif self.shape == 'select' or self.shape == 'text':
             self.select_or_edit_text(event)
    
    def reset(self, event):
        self.resizing = False
        self.dragging = False
        self.shape_id = None
        
        if self.shape != 'select':
            self.clear_selection()

    def on_space_down(self, event):
        if not hasattr(self, 'previous_tool_before_space'):
             if self.shape != 'hand':
                 self.previous_tool_before_space = self.shape
                 self.select_tool('hand')
    
    def on_space_up(self, event):
        if hasattr(self, 'previous_tool_before_space'):
             self.select_tool(self.previous_tool_before_space)
             del self.previous_tool_before_space

    def perp_dist(self, p, p1, p2):
        """Calculates perpendicular distance from point p to line segment p1-p2."""
        x, y = p
        x1, y1 = p1
        x2, y2 = p2
        if x1 == x2 and y1 == y2:
            return math.sqrt((x - x1)**2 + (y - y1)**2)
        return abs((y2 - y1) * x - (x2 - x1) * y + x2 * y1 - y2 * x1) / math.sqrt((y2 - y1)**2 + (x2 - x1)**2)

    def simplify_points(self, points, epsilon):
        """Simplifies a path of points using the Ramer-Douglas-Peucker algorithm."""
        dmax = 0.0
        index = 0
        for i in range(1, len(points) - 1):
            d = self.perp_dist(points[i], points[0], points[-1])
            if d > dmax:
                index = i
                dmax = d
        
        if dmax > epsilon:
            rec_results1 = self.simplify_points(points[:index+1], epsilon)
            rec_results2 = self.simplify_points(points[index:], epsilon)
            return rec_results1[:-1] + rec_results2
        else:
            return [points[0], points[-1]]

    def create_regular_polygon(self, cx, cy, r, sides):
        """Generates points for a regular polygon."""
        points = []
        import math
        # Offset angle to make them "standing up" usually -pi/2 starts at top
        offset = -math.pi / 2
        for i in range(sides):
            angle = offset + 2 * math.pi * i / sides
            points.append(cx + r * math.cos(angle))
            points.append(cy + r * math.sin(angle))
        return points

    def is_right_triangle(self, p1, p2, p3):
        """Checks if a triangle defined by 3 points is roughly right-angled."""
        def dist_sq(a, b): return (a[0]-b[0])**2 + (a[1]-b[1])**2
        d1 = dist_sq(p1, p2)
        d2 = dist_sq(p2, p3)
        d3 = dist_sq(p3, p1)
        sides = sorted([d1, d2, d3])
        # tolerance for hand drawing
        # Pythagoras: a^2 + b^2 = c^2
        # We are using squared distances already.
        # Check: |(a+b) - c| < tolerance
        tolerance = sides[2] * 0.15 # 15% tolerance
        return abs((sides[0] + sides[1]) - sides[2]) < tolerance

    def detect_shape(self):
        try:
            points = self.current_stroke_points
            if len(points) < 5: return False 
            
            import math
            
            # 1. Analyze for Line (Straightness) - Keep existing fast check
            start = points[0]
            end = points[-1]
            dist_direct = math.sqrt((end[0]-start[0])**2 + (end[1]-start[1])**2)
            
            dist_path = 0
            for i in range(len(points)-1):
                p1, p2 = points[i], points[i+1]
                dist_path += math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
            
            sensitivity = 0.96 
            if dist_path > 0 and (dist_direct / dist_path) > sensitivity:
                self.replace_stroke_with_shape('line', start, end)
                return True

            # 2. Vertex Counting (RDP Algorithm)
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            width = max_x - min_x
            height = max_y - min_y
            diag = math.sqrt(width**2 + height**2)
            
            epsilon = max(5.0, diag * 0.035) 
            
            simplified = self.simplify_points(points, epsilon)
            
            # Check if closed
            is_closed = dist_direct < max(30, diag * 0.15)
            
            vertices = len(simplified)
            if is_closed:
                vertices -= 1 
            
            print(f"DEBUG: RDP Vertices: {vertices}")

            # Circularity check 
            area = 0.0
            for i in range(len(points)):
                j = (i + 1) % len(points)
                area += points[i][0] * points[j][1]
                area -= points[j][0] * points[i][1]
            area = abs(area) / 2.0
            perimeter = dist_path
            circularity = (4 * math.pi * area) / (perimeter**2) if perimeter > 0 else 0
            
            # Classification
            # Vertices check first!
            # RDP is robust for corners. Using it primarily.
            
            if vertices == 3 and is_closed:
                # Triangle
                poly = simplified[:3]
                if self.is_right_triangle(poly[0], poly[1], poly[2]):
                     # Create a perfect right triangle aligned to axes
                     # The right angle corner will be at (min_x, max_y) assuming standard orientation
                     # Or we can just use the bounding box points to create a clean right triangle
                     perfect_right_triangle = [min_x, max_y, max_x, max_y, min_x, min_y]
                     self.replace_stroke_with_shape('triangle', perfect_right_triangle, None)
                else:
                     self.replace_stroke_with_shape('triangle', poly, None)

            elif 4 <= vertices <= 6 and is_closed:
                # Geometric Rectangle/Quad Check
                bbox_area = width * height
                fill_ratio = area / bbox_area if bbox_area > 0 else 0
                
                if fill_ratio > 0.82 and circularity < 0.85:
                    # Very likely a rectangle, even if there are 5 or 6 vertices due to drawing errors
                    self.replace_stroke_with_shape('rectangle', (min_x, min_y), (max_x, max_y))
                else:
                    poly = simplified[:vertices]
                    if fill_ratio < 0.6:
                         # Distinguish between sloppy triangle and rhombus
                         relaxed_simplified = self.simplify_points(points, epsilon * 2.0)
                         relaxed_vertices = len(relaxed_simplified) - (1 if is_closed else 0)
                         if relaxed_vertices <= 3:
                             # Ensure we have at least 3 points for a triangle
                             poly_t = relaxed_simplified[:3] if len(relaxed_simplified) >= 3 else poly[:3]
                             self.replace_stroke_with_shape('triangle', poly_t, None)
                         else:
                             mid_x = (min_x + max_x) / 2
                             mid_y = (min_y + max_y) / 2
                             rhombus_points = [mid_x, min_y, max_x, mid_y, mid_x, max_y, min_x, mid_y]
                             self.replace_stroke_with_shape('rhombus', rhombus_points, None)
                    elif vertices == 4:
                         self.replace_stroke_with_shape('parallelogram', poly, None)
                    elif vertices == 5:
                        cx = (min_x + max_x) / 2
                        cy = (min_y + max_y) / 2
                        radius = min(width, height) / 2
                        poly_points = self.create_regular_polygon(cx, cy, radius, 5)
                        self.replace_stroke_with_shape('pentagon', poly_points, None)
                    elif vertices == 6:
                        cx = (min_x + max_x) / 2
                        cy = (min_y + max_y) / 2
                        radius = min(width, height) / 2
                        poly_points = self.create_regular_polygon(cx, cy, radius, 6)
                        self.replace_stroke_with_shape('hexagon', poly_points, None)

            elif (vertices > 6 or circularity > 0.8) and is_closed:
                 # Circle/Oval fallback
                if circularity > 0.88 and 0.8 < (width/height) < 1.2:
                     # Perfect Circle: Force equal width and height from center
                     cx = (min_x + max_x) / 2
                     cy = (min_y + max_y) / 2
                     r = max(width, height) / 2
                     self.replace_stroke_with_shape('oval', (cx - r, cy - r), (cx + r, cy + r))
                else:
                     self.replace_stroke_with_shape('oval', (min_x, min_y), (max_x, max_y))
            
            else:
                 if is_closed:
                      self.replace_stroke_with_shape('polygon', simplified[:-1], None)
                 
            return True

        except Exception as e:
            print(f"Error in shape detection: {e}")
            return False

    def replace_stroke_with_shape(self, shape_type, p1, p2):
        # Remove old stroke lines
        for item_id in self.current_stroke_ids:
            self.c.delete(item_id)
            if item_id in self.objects: self.objects.remove(item_id)
        
        # Styles
        outline = self.color_fg
        fill = self.fill_color
        width = self.penwidth
        
        shape_id = None
        undo_entry = None
        
        if shape_type in ['triangle', 'rhombus', 'parallelogram', 'pentagon', 'hexagon', 'polygon']:
             # p1 is points list
             shape_id = self.c.create_polygon(p1, outline=outline, fill=fill, width=width)
             # Undo for polygon?
             undo_entry = ('create_polygon', shape_id, list(p1), outline, fill, width)
        else:
             x1, y1 = p1
             x2, y2 = p2
        
             if shape_type == 'line':
                 shape_id = self.c.create_line(x1, y1, x2, y2, fill=outline, width=width, capstyle=tk.ROUND)
                 undo_entry = ('create_line', shape_id, x1, y1, x2, y2, outline, width)
                 
             elif shape_type == 'rectangle':
                 shape_id = self.c.create_rectangle(x1, y1, x2, y2, outline=outline, fill=fill, width=width)
                 undo_entry = ('create_rectangle', shape_id, x1, y1, x2, y2, outline, width)
                 
             elif shape_type == 'oval':
                 shape_id = self.c.create_oval(x1, y1, x2, y2, outline=outline, fill=fill, width=width)
                 undo_entry = ('create_oval', shape_id, x1, y1, x2, y2, outline, width)
        
        if shape_id:
            self.shape_id = shape_id
            self.objects.append(shape_id)
            if undo_entry:
                self.undo_stack.append(undo_entry)
            print(f"Auto-Shape: Converted to {shape_type}")


    # --- Copy / Paste Logic ---
    def copy_selection(self, event=None):
        """Copies selected objects to the clipboard."""
        self.clipboard = []
        if not self.selected_objects: return

        for obj in self.selected_objects:
            item_data = {}
            item_type = self.c.type(obj)
            item_data['type'] = item_type
            item_data['coords'] = self.c.coords(obj)
            item_data['tags'] = self.c.gettags(obj)
            
            # Capture config options
            # We explicitly grab common properties to avoid grabbing everything including defaults
            config = {}
            keys = ['fill', 'outline', 'width', 'font', 'text', 'arrow', 'capstyle', 'smooth', 'splinesteps', 'arrowshape']
            for k in keys:
                try:
                    val = self.c.itemcget(obj, k)
                    if val: config[k] = val
                except: pass
            
            item_data['config'] = config
            
            # Special Handling for Images
            if item_type == 'image':
                # Check for stored high-res image
                if hasattr(self, 'stored_images') and obj in self.stored_images:
                    item_data['stored_image'] = self.stored_images[obj]
                elif hasattr(self, 'image_files') and obj in self.image_files:
                     item_data['image_path'] = self.image_files[obj]
            
            self.clipboard.append(item_data)
        
        print(f"Copied {len(self.clipboard)} items.")

    def paste_selection(self, event=None):
        """Pasts objects from clipboard with an offset."""
        if not self.clipboard: return
        
        self.clear_selection()
        
        offset_x, offset_y = 20, 20
        new_selection = []
        
        for item in self.clipboard:
            try:
                itype = item['type']
                coords = [c + offset_x if i % 2 == 0 else c + offset_y for i, c in enumerate(item['coords'])]
                config = item['config']
                
                new_id = None
                
                if itype == 'line':
                    new_id = self.c.create_line(*coords, **config)
                elif itype == 'rectangle':
                    new_id = self.c.create_rectangle(*coords, **config)
                elif itype == 'oval':
                    new_id = self.c.create_oval(*coords, **config)
                elif itype == 'text':
                    new_id = self.c.create_text(*coords, **config)
                elif itype == 'image':
                    # Re-creation of image is tricky because we need the PhotoImage
                    # 1. From Stored Image
                    img_obj = None
                    if 'stored_image' in item:
                        img_obj = item['stored_image']
                    elif 'image_path' in item and os.path.exists(item['image_path']):
                        img_obj = Image.open(item['image_path'])
                    
                    if img_obj:
                         # Create new PhotoImage
                         # We need to respect current size? 
                         # The coords for create_image is x,y (anchor). 
                         # item['coords'] is likely [x,y].
                         # But wait, resizing might have changed the display size.
                         # If we accept that we paste the ORIGINAL high-res at original size or previous size?
                         # Let's try to match the copied size.
                         
                         # Get width/height from coords? No, image coords is just anchor.
                         # We can't easily get the 'current' size of the image on canvas from 'coords' alone unless we tracked it.
                         # However, if we simply use the stored PIL image and create a PhotoImage, it will be original size.
                         # If the user resized the original object, we might lose that resize on paste unless we tracked 'current_size' in clipboard.
                         # For now, let's just paste.
                         
                         photo = ImageTk.PhotoImage(img_obj)
                         new_id = self.c.create_image(coords[0], coords[1], image=photo, anchor=getattr(tk, config.get('anchor', 'nw').upper(), tk.NW))
                         
                         # Store reference
                         if not hasattr(self, 'image_refs'): self.image_refs = []
                         self.image_refs.append(photo)
                         
                         # Store High-Res
                         if not hasattr(self, 'stored_images'): self.stored_images = {}
                         self.stored_images[new_id] = img_obj
                         
                         # Store path if available
                         if 'image_path' in item:
                             self.image_files[new_id] = item['image_path']

                if new_id:
                    self.objects.append(new_id)
                    self.selected_objects.append(new_id)
            except Exception as e:
                print(f"Paste Error: {e}")
        
        # Highlight new selection
        self.select_object(0, 0, event) # Trigger update logic? No, this event logic is click-based.
        # Manually highlight
        for obj in self.selected_objects:
             # Re-use highlight logic or just set directly
             pass
        
        # Easier: just call select_object logic for the last item?
        # Or iterating to set outline blue.
        for obj in self.selected_objects:
            self.c.itemconfig(obj, outline="blue" if self.c.type(obj) in ['rectangle','oval'] else None)
            if self.c.type(obj) in ['line','text']:
                 self.c.itemconfig(obj, fill="blue")

    # --- Alt Key Hints ---
    def toggle_key_hints(self, event=None):
        if self.hints_visible:
            self.hide_key_hints()
        else:
            self.show_key_hints()
            
    def hide_key_hints(self, event=None):
        # Only hide if we aren't just toggling it via Alt
        if event and event.keysym in ['Alt_L', 'Alt_R']: return
        
        if self.hints_visible:
            for lbl in self.hint_labels:
                lbl.destroy()
            self.hint_labels = []
            self.hints_visible = False

    def show_key_hints(self):
        if self.hints_visible: return
        self.hints_visible = True
        
        # Map: Index in self.dock_buttons -> Key
        # Or infer from button commands? Harder.
        # Explicit map based on creation order in create_floating_interface:
        # 0: Select (V)
        # 1: Pan (H)
        # 2: Pen (B)
        # 3: Eraser (E)
        # 4: Fill (F)
        # 5: Text (T)
        
        shortcuts = ['V', 'H', 'B', 'E', 'F', 'T']
        
        if hasattr(self, 'dock_buttons'):
            for i, btn in enumerate(self.dock_buttons):
                if i < len(shortcuts):
                    self.create_hint_badge(btn, shortcuts[i])
                    
        # Add +, Color
        if hasattr(self, 'add_btn'): self.create_hint_badge(self.add_btn, '+')
        # Color button is weird, it's a Canvas.
        if hasattr(self, 'color_btn'): self.create_hint_badge(self.color_btn, 'C')

    def create_hint_badge(self, widget, text):
        try:
            # We need screen coordinates
            x = widget.winfo_rootx() - self.root.winfo_rootx() + widget.winfo_width() // 2 - 10
            y = widget.winfo_rooty() - self.root.winfo_rooty() - 15
            
            lbl = tk.Label(self.root, text=text, bg="#f9d71c", fg="black", font=("Arial", 10, "bold"), padx=2, pady=0)
            lbl.place(x=x, y=y)
            self.hint_labels.append(lbl)
        except:
            pass


    def show_brush_settings(self, event=None):
        """Shows a popup to adjust brush size styling matching docker."""
        current_type = getattr(self, '_open_pen_settings_type', None)
        if hasattr(self, 'pen_settings_frame') and self.pen_settings_frame and self.pen_settings_frame.winfo_exists():
            self.pen_settings_frame.destroy()
            self.pen_settings_frame = None
            if current_type == 'brush':
                 self._open_pen_settings_type = None
                 return
                 
        self._open_pen_settings_type = 'brush'
            
        bg_main = self.theme["canvas_bg"] if hasattr(self, 'theme') else "#F3F3F3"
        bg_bar  = self.theme["bg_secondary"] if hasattr(self, 'theme') else "white"
        fg_text = self.theme.get("text_color", "black") if hasattr(self, 'theme') else "black"

        self.pen_settings_frame = RoundedFrame(self.root, width=200, height=110, corner_radius=12,
                                               bg_color=bg_main, color=bg_bar, shadow_offset=4, border_width=2, border_color="black")
        
        # Calculate dock-relative coordinates to float directly above the tool icon
        if event and hasattr(event, 'widget') and hasattr(self, 'bottom_dock'):
            cx = event.widget.winfo_rootx() - self.root.winfo_rootx() + (event.widget.winfo_width() / 2)
            y = self.bottom_dock.winfo_y() - 10
        else:
            cx = self.root.winfo_pointerx() - self.root.winfo_rootx()
            y = self.root.winfo_pointery() - self.root.winfo_rooty() - 30

        x = cx - 100
        x = max(10, min(x, self.root.winfo_width() - 210))
        self.pen_settings_frame.place(x=x, y=y, anchor=tk.SW)
        
        container = tk.Frame(self.pen_settings_frame, bg=bg_bar)
        container.place(relx=0.5, rely=0.5, anchor=tk.CENTER, y=-2)
        
        tk.Label(container, text="Brush Size", bg=bg_bar, fg=fg_text, font=("Segoe UI", 10, "bold")).pack(pady=2)
        
        val_label = tk.Label(container, text=str(self.penwidth), bg=bg_bar, fg=fg_text, font=("Segoe UI", 9))
        val_label.pack()
        
        def update_brush(val):
            self.changeW(val)
            val_label.config(text=str(int(float(val))))
        
        slider = ttk.Scale(container, from_=1, to=50, value=self.penwidth, command=update_brush)
        slider.pack(fill=tk.X, padx=10, pady=4)
        
        self.pen_settings_frame.bind('<Leave>', lambda e: self.pen_settings_frame.destroy())
        container.bind('<Leave>', lambda e: self.pen_settings_frame.destroy())

    def show_fill_settings(self, event=None):
        """Shows fill settings (Color Palette) on double click."""
        self.toggle_palette_popup(event)

    def show_eraser_settings(self, event=None):
        """Shows a popup to adjust eraser size matching docker."""
        current_type = getattr(self, '_open_pen_settings_type', None)
        if hasattr(self, 'pen_settings_frame') and self.pen_settings_frame and self.pen_settings_frame.winfo_exists():
            self.pen_settings_frame.destroy()
            self.pen_settings_frame = None
            if current_type == 'eraser':
                 self._open_pen_settings_type = None
                 return
                 
        self._open_pen_settings_type = 'eraser'
            
        bg_main = self.theme["canvas_bg"] if hasattr(self, 'theme') else "#F3F3F3"
        bg_bar  = self.theme["bg_secondary"] if hasattr(self, 'theme') else "white"
        fg_text = self.theme.get("text_color", "black") if hasattr(self, 'theme') else "black"

        self.pen_settings_frame = RoundedFrame(self.root, width=200, height=110, corner_radius=12,
                                               bg_color=bg_main, color=bg_bar, shadow_offset=4, border_width=2, border_color="black")
        
        if event and hasattr(event, 'widget') and hasattr(self, 'bottom_dock'):
            cx = event.widget.winfo_rootx() - self.root.winfo_rootx() + (event.widget.winfo_width() / 2)
            y = self.bottom_dock.winfo_y() - 10
        else:
            cx = self.root.winfo_pointerx() - self.root.winfo_rootx()
            y = self.root.winfo_pointery() - self.root.winfo_rooty() - 30

        x = cx - 100
        x = max(10, min(x, self.root.winfo_width() - 210))
        self.pen_settings_frame.place(x=x, y=y, anchor=tk.SW)
        
        container = tk.Frame(self.pen_settings_frame, bg=bg_bar)
        container.place(relx=0.5, rely=0.5, anchor=tk.CENTER, y=-2)
        
        tk.Label(container, text="Eraser Size", bg=bg_bar, fg=fg_text, font=("Segoe UI", 10, "bold")).pack(pady=2)
        
        val_label = tk.Label(container, text=str(self.eraser_size), bg=bg_bar, fg=fg_text, font=("Segoe UI", 9))
        val_label.pack()
        
        def update_eraser(val):
            self.eraser_size = int(float(val))
            val_label.config(text=str(self.eraser_size))
            
        slider = ttk.Scale(container, from_=5, to=100, value=self.eraser_size, command=update_eraser)
        slider.pack(fill=tk.X, padx=10, pady=4)
        
        self.pen_settings_frame.bind('<Leave>', lambda e: self.pen_settings_frame.destroy())
        container.bind('<Leave>', lambda e: self.pen_settings_frame.destroy())



if __name__ == '__main__':
    root = tk.Tk()
    app = Whiteboard(root)
    root.mainloop()
