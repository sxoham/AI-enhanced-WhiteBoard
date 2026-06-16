
import tkinter as tk

def draw_venn_diagram(canvas, start_x=100, start_y=100):
    """Draws a 2-circle Venn Diagram."""
    radius = 150
    # Circle 1 (Left)
    c1 = canvas.create_oval(start_x, start_y, start_x + 2*radius, start_y + 2*radius, 
                            outline="black", width=3)
    # Circle 2 (Right, overlapping)
    # Overlap by radius
    x2 = start_x + radius
    c2 = canvas.create_oval(x2, start_y, x2 + 2*radius, start_y + 2*radius, 
                            outline="black", width=3)
    
    # Labels
    canvas.create_text(start_x + radius/2, start_y + radius/2, text="Set A", font=("Arial", 14, "bold"))
    canvas.create_text(x2 + 1.5*radius, start_y + radius/2, text="Set B", font=("Arial", 14, "bold"))
    
    return [c1, c2]

def draw_t_chart(canvas, start_x=100, start_y=100):
    """Draws a T-Chart."""
    width = 600
    height = 500
    
    # Header Line (Horizontal)
    h_line = canvas.create_line(start_x, start_y + 50, start_x + width, start_y + 50, width=4)
    
    # Split Line (Vertical) - Starts from header line text area usually, or below it
    # T-chart usually has a big header "Topic" then split.
    # Let's do standard T: Top bar, middle bar down.
    
    # Center vertical
    center_x = start_x + width / 2
    v_line = canvas.create_line(center_x, start_y, center_x, start_y + height, width=4)
    
    # Top Horizontal
    top_line = canvas.create_line(start_x, start_y, start_x + width, start_y, width=4)
    # Actually T-Chart is just a T.
    
    l1 = canvas.create_text(start_x + width/4, start_y + 25, text="Pros / Left", font=("Arial", 16, "bold"))
    l2 = canvas.create_text(start_x + 3*width/4, start_y + 25, text="Cons / Right", font=("Arial", 16, "bold"))
    
    return [h_line, v_line, l1, l2]

def draw_swot_analysis(canvas, start_x=100, start_y=100):
    """Draws a 2x2 SWOT Grid."""
    width = 800
    height = 600
    mid_x = start_x + width / 2
    mid_y = start_y + height / 2
    
    # Outer Box
    rect = canvas.create_rectangle(start_x, start_y, start_x + width, start_y + height, width=3)
    
    # Dividing Lines
    # Vertical
    v_line = canvas.create_line(mid_x, start_y, mid_x, start_y + height, width=2)
    # Horizontal
    h_line = canvas.create_line(start_x, mid_y, start_x + width, mid_y, width=2)
    
    # Labels
    # Top Left: Strengths
    l1 = canvas.create_text(start_x + 20, start_y + 20, anchor=tk.NW, text="STRENGTHS", font=("Arial", 14, "bold"), fill="green")
    # Top Right: Weaknesses
    l2 = canvas.create_text(mid_x + 20, start_y + 20, anchor=tk.NW, text="WEAKNESSES", font=("Arial", 14, "bold"), fill="red")
    # Bottom Left: Opportunities
    l3 = canvas.create_text(start_x + 20, mid_y + 20, anchor=tk.NW, text="OPPORTUNITIES", font=("Arial", 14, "bold"), fill="blue")
    # Bottom Right: Threats
    l4 = canvas.create_text(mid_x + 20, mid_y + 20, anchor=tk.NW, text="THREATS", font=("Arial", 14, "bold"), fill="orange")
    
    return [rect, v_line, h_line, l1, l2, l3, l4]

def draw_kanban_board(canvas, start_x=50, start_y=50):
    """Draws 3 columns: To Do, Doing, Done."""
    # Assuming screen width allows ~900px
    col_width = 300
    height = 600
    
    headers = ["To Do", "Doing", "Done"]
    colors = ["#FFCDD2", "#FFF9C4", "#C8E6C9"] # Light Red, Yellow, Green
    
    ids = []
    
    for i, header in enumerate(headers):
        x = start_x + (i * col_width)
        # Column bg (optional, maybe just header?)
        # Let's draw header box
        h_rect = canvas.create_rectangle(x, start_y, x + col_width - 10, start_y + 50, fill=colors[i], outline="black")
        h_text = canvas.create_text(x + col_width/2 - 5, start_y + 25, text=header, font=("Arial", 14, "bold"))
        
        # Column divider/box
        col_rect = canvas.create_rectangle(x, start_y + 50, x + col_width - 10, start_y + height, outline="gray")
        
        ids.extend([h_rect, h_text, col_rect])
        
    return ids
