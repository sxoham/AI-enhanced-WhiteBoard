import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog, PhotoImage
from tkinter.colorchooser import askcolor
from PIL import ImageTk, Image, ImageDraw

class RoundedFrame(tk.Canvas):
    def __init__(self, parent, width, height, corner_radius, padding=0, color="white", bg_color=None, shadow_offset=6, border_width=2, border_color="black", shadow_color=(0, 0, 0, 80), **kwargs):
        tk.Canvas.__init__(self, parent, width=width, height=height, highlightthickness=0, **kwargs)
        self.corner_radius = corner_radius
        self.padding = padding
        self.color = color
        self.shadow_offset = shadow_offset
        self.border_width = border_width
        self.border_color = border_color
        self.shadow_color = shadow_color
        
        # Transparent background support (simulated)
        if bg_color:
            self.configure(bg=bg_color)
        else:
            # Attempt to grab parent bg? fallback to system default
            self.configure(bg=parent.cget("bg") if hasattr(parent, "cget") else "#f0f0f0")

        self.bind("<Configure>", self._draw)

    def _draw(self, event=None):
        # Only delete the background image, preserve other items (buttons)
        self.delete("bg_base")
        
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 2 or h < 2: return

        # Create high-res, transparent image
        image = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Parameters
        radius = self.corner_radius
        shadow_offset = self.shadow_offset
        shadow_color = self.shadow_color
        border_color = self.border_color
        border_width = self.border_width
        
        # Calculate bounds
        x1, y1 = 2, 2
        x2, y2 = w - shadow_offset - 2, h - shadow_offset - 2
        
        # 1. Draw Shadow
        if shadow_offset > 0:
             draw.rounded_rectangle((x1 + shadow_offset, y1 + shadow_offset, x2 + shadow_offset, y2 + shadow_offset), 
                                    radius=radius, fill=shadow_color)
        
        # 2. Draw Main Body
        bg_col = self.color
        if border_width > 0:
            # Pillow's built-in outline draws thick corners incorrectly, yielding artifacts.
            # Instead, we draw a solid border-colored shape, then paint the smaller inner body.
            draw.rounded_rectangle((x1, y1, x2, y2), radius=radius, fill=border_color)
            inner_radius = max(0, radius - border_width)
            draw.rounded_rectangle((x1 + border_width, y1 + border_width, x2 - border_width, y2 - border_width), 
                                   radius=inner_radius, fill=bg_col)
        else:
            draw.rounded_rectangle((x1, y1, x2, y2), radius=radius, fill=bg_col)

        # Convert to PhotoImage and Display
        self._bg_photo = ImageTk.PhotoImage(image)
        self.create_image(0, 0, image=self._bg_photo, anchor="nw", tags="bg_base")
        self.tag_lower("bg_base") # Ensure it stays behind buttons
        
    def set_colors(self, color=None, bg_color=None, border_color=None, shadow_color=None):
        if color:
             self.color = color
        if bg_color:
             self.configure(bg=bg_color)
        if border_color:
             self.border_color = border_color
        if shadow_color:
             self.shadow_color = shadow_color
        self._draw()



class ToolTip(object):
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        
    def schedule(self, event=None):
        self.unschedule()
        self.id = self.widget.after(500, self.showtip)
        
    def unschedule(self, event=None):
        id_ = self.id
        self.id = None
        if id_:
            self.widget.after_cancel(id_)
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None

    def showtip(self):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + (self.widget.winfo_width() // 2)
        y = self.widget.winfo_rooty() - 35
        
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        
        label = tk.Label(tw, text=self.text, justify=tk.CENTER,
                      background="#242424", foreground="white", relief=tk.FLAT, borderwidth=0,
                      font=("Segoe UI", 10, "bold"), padx=10, pady=4)
        label.pack()
        
        tw.update_idletasks()
        tw.wm_geometry("+%d+%d" % (x - (tw.winfo_width()//2), y))


class RoundedButton(tk.Canvas):
    def __init__(self, parent, width, height, image, command=None, corner_radius=10, bg_hover="#e0e0e0", bg_normal=None, transparent_on=None, tooltip=None, **kwargs):
        # Remove conflicting args from kwargs if present
        kwargs.pop('highlightthickness', None)
        kwargs.pop('bd', None)
        kwargs.pop('borderwidth', None)
        kwargs.pop('bg_color', None) # Also remove bg_color if it sneaks in
        kwargs.pop('border_width', None)
        
        tk.Canvas.__init__(self, parent, width=width, height=height, highlightthickness=0, bd=0, **kwargs)
        self.image = image
        self.command = command
        self.corner_radius = corner_radius
        self.bg_hover = bg_hover
        self.bg_normal = bg_normal # None for transparent
        
        # Determine parent bg for transparency simulation
        if transparent_on:
            self.parent_bg = transparent_on
        else:
            self.parent_bg = parent.cget("bg") if hasattr(parent, "cget") else "white"
            
        self.configure(bg=self.parent_bg, cursor="hand2") # Default bg matches parent and use hand cursor

        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)
        
        if tooltip:
            self.tooltip = ToolTip(self, tooltip)
            
        self.draw()

    def draw(self, state="normal"):
        self.delete("all")
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        if w < 2 or h < 2: return
        
        # Decide color
        bg = self.bg_normal if state == "normal" else self.bg_hover
        
        if bg:
             # PIL Generation
             image = Image.new("RGBA", (w, h), (0, 0, 0, 0))
             draw = ImageDraw.Draw(image)
             
             draw.rounded_rectangle((0, 0, w-1, h-1), radius=self.corner_radius, fill=bg)
             
             # Cache and display
             self._bg_photo = ImageTk.PhotoImage(image)
             self.create_image(0, 0, image=self._bg_photo, anchor="nw")

        # Draw Image (Icon)
        if self.image:
            # Use float centers to match the geometry perfectly
            self.create_image(w // 2, h // 2, image=self.image, anchor=tk.CENTER, tags="img")

    def on_enter(self, event):
        self.draw(state="hover")
        if hasattr(self, 'tooltip'):
            self.tooltip.schedule()

    def on_leave(self, event):
        self.draw(state="normal")
        if hasattr(self, 'tooltip'):
            self.tooltip.unschedule()
        
    def on_click(self, event):
        if hasattr(self, 'tooltip'):
            self.tooltip.unschedule()
        if self.command:
            self.command()

    # _round_rect removed
    
    def configure_color(self, bg_hover, bg_normal=None):
        self.bg_hover = bg_hover
        self.bg_normal = bg_normal
        self.configure(bg=self.parent_bg) # Reset canvas bg if needed?
        self.draw(state="normal")

class ColorPalette(RoundedFrame):
    def __init__(self, parent, whiteboard, *args, **kwargs):
        # Determine background color based on theme for RoundedFrame
        self.whiteboard = whiteboard
        bg = "SystemButtonFace"
        if hasattr(self.whiteboard, 'theme'):
             bg = self.whiteboard.theme["bg_secondary"]
        
        # Initialize as RoundedFrame (which is a Canvas) with transparent support (parent bg)
        # Fix: Use canvas_bg to blend with the drawing canvas if floating over it
        parent_bg = self.whiteboard.theme["canvas_bg"] if hasattr(self.whiteboard, 'theme') else "white"
        
        # We need a large enough width/height initially, will resize
        super().__init__(parent, width=400, height=50, corner_radius=25, color=bg, bg_color=parent_bg, **kwargs)
        
        self.selected_color = "#000000"
        self.swatch_size = 24
        self.padding = 6
        self.swatches = []
        self.selected_id = None
        
        self.bg_color = bg
        
        # We draw directly on 'self' (which is the Canvas) instead of self.canvas
        # But wait, RoundedFrame draws its OWN background on _draw.
        # So we should append our palette items.
        
        self.bind("<Button-1>", self.on_click)
        self.create_palette()
        

    def create_palette(self, event=None):
        # We need to ensure background is drawn first by RoundedFrame
        # But we can just draw on top.
        
        colors = [
            "#000000", "#808080", "#FF0000", "#800000", "#FFA500", "#808000",
            "#FFFF00", "#00FF00", "#008000", "#00FFFF", "#008080", "#0000FF",
            "#000080", "#800080", "#FF00FF", "#FFC0CB", "#FFA07A", "#FFFFFF"
        ]
        
        # Clear items but NOT the background (tag 'bg_base')
        # RoundedFrame uses 'bg_base' tag.
        for item in self.find_all():
            if "bg_base" not in self.gettags(item):
                self.delete(item)
                
        self.swatches = []
        
        x = self.padding
        y = 20 # Center vertically
        
        for color in colors:
            # Draw outer ring (selection area)
            # Center of the circle
            cx, cy = x + self.swatch_size/2, y
            r = self.swatch_size/2
            
            # Use tags to identify
            tag = f"color_{color}"
            
            # Draw color circle
            # Use 'self' instead of 'self.canvas'
            oid = self.create_oval(cx-r, cy-r, cx+r, cy+r, fill=color, outline="#AAAAAA", width=1, tags=("swatch", color))
            
            self.swatches.append({'id': oid, 'color': color, 'cx': cx, 'cy': cy})
            
            x += self.swatch_size + self.padding
            
        # Add Custom Color Button (+)
        cx, cy = x + self.swatch_size/2, y
        r = self.swatch_size/2
        
        # Plus icon or just text
        # Plus icon
        self.create_oval(cx-r, cy-r, cx+r, cy+r, fill=self.bg_color, outline=self.whiteboard.theme.get("text_color", "black"), width=1, tags="custom")
        self.create_text(cx, cy, text="+", fill=self.whiteboard.theme.get("text_color", "black"), font=("Arial", 12, "bold"), tags="custom")
        
        # Configure Width/Height of Canvas (RoundedFrame)
        total_width = x + self.swatch_size + self.padding + 10
        total_height = 50 # Fixed height
        self.configure(width=total_width, height=total_height)
        
        # Trigger redraw of background
        self._draw()
        
        # Initial selection
        self.highlight_color(self.whiteboard.color_fg if hasattr(self.whiteboard, 'color_fg') else "#000000")

    def highlight_color(self, color):
        self.delete("selection_ring")
        
        # Find swatch
        target_swatch = None
        for s in self.swatches:
            if s['color'] == color:
                target_swatch = s
                break
        
        if target_swatch:
            cx, cy = target_swatch['cx'], target_swatch['cy']
            # Small, tight ring
            r = self.swatch_size/2 + 2
            
            # Using 'btn_active' for a stronger color than 'accent' (which can be pale)
            # Or default to black/white specific high contrast
            highlight_col = self.whiteboard.theme.get("btn_active", "blue") if hasattr(self.whiteboard, 'theme') else "black"
            
            # Draw strong ring
            self.create_oval(cx-r, cy-r, cx+r, cy+r, outline=highlight_col, width=2, tags="selection_ring")

    def on_click(self, event):
        item = self.find_closest(event.x, event.y)[0]
        tags = self.gettags(item)
        
        if "swatch" in tags:
            # Get color from tags (we stored it as second tag)
            # Or replicate find
            for tag in tags:
                if tag.startswith("#"):
                    color = tag
                    self.set_color(color)
                    break
        elif "custom" in tags:
            self.choose_custom_color()

    def update_theme(self, theme):
        self.bg_color = theme["bg_secondary"]
        self.color = self.bg_color # Update RoundedFrame color
        self.configure(bg=theme["canvas_bg"]) # Update transparent background
        
        # Redraw
        self.create_palette()
        self.highlight_color(self.whiteboard.color_fg)

    def set_color(self, color):
        self.whiteboard.color_fg = color
        self.highlight_color(color)

    def choose_custom_color(self):
        color_code = askcolor(title="Choose color")[1]
        if color_code:
            self.set_color(color_code)
