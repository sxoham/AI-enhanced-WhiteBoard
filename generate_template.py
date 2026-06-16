import json
import os

template_data = {
    "version": "1.0",
    "canvas_bg": "#FFFFFF",
    "objects": [
        {
            "id": 1,
            "type": "text",
            "coords": [450, 100],
            "tags": [],
            "config": {
                "text": "Welcome to AI Whiteboard! 🚀",
                "font": "Arial 24 bold",
                "fill": "#333333"
            }
        },
        {
            "id": 2,
            "type": "text",
            "coords": [450, 140],
            "tags": [],
            "config": {
                "text": "Explore the features by interacting with the objects below.",
                "font": "Arial 12 italic",
                "fill": "#666666"
            }
        },
        # Sticky Note
        {
            "id": 10,
            "type": "rectangle",
            "coords": [100, 250, 300, 400],
            "tags": ["node_group_11"],
            "config": {
                "fill": "#FFF9C4",
                "outline": "gray"
            }
        },
        {
            "id": 11,
            "type": "text",
            "coords": [200, 325],
            "tags": ["node_group_11"],
            "config": {
                "text": "I am a Sticky Note!\nTry dragging me around.\nI stay grouped together!",
                "font": "Arial 12",
                "fill": "black"
            }
        },
        # Hand-drawn Brush Stroke
        {
            "id": 12,
            "type": "line",
            "coords": [350, 250, 380, 230, 400, 280, 430, 240, 460, 290, 490, 220],
            "tags": [],
            "config": {
                "fill": "#E91E63",
                "width": 4,
                "smooth": "1",
                "capstyle": "round"
            }
        },
        {
            "id": 13,
            "type": "text",
            "coords": [420, 320],
            "tags": [],
            "config": {
                "text": "↑ Smooth Brush Strokes",
                "font": "Arial 10",
                "fill": "#E91E63"
            }
        },
        # Flowchart / Mind Map Nodes
        {
            "id": 20,
            "type": "oval",
            "coords": [600, 200, 800, 280],
            "tags": ["node_group_21"],
            "config": {
                "fill": "#E3F2FD",
                "outline": "#1565C0",
                "width": 2
            }
        },
        {
            "id": 21,
            "type": "text",
            "coords": [700, 240],
            "tags": ["node_group_21"],
            "config": {
                "text": "AI Node",
                "font": "Arial 16 bold",
                "fill": "#0D47A1"
            }
        },
        {
            "id": 30,
            "type": "rectangle",
            "coords": [600, 400, 800, 460],
            "tags": ["node_group_31"],
            "config": {
                "fill": "#E8F5E9",
                "outline": "#2E7D32",
                "width": 2
            }
        },
        {
            "id": 31,
            "type": "text",
            "coords": [700, 430],
            "tags": ["node_group_31"],
            "config": {
                "text": "Smart Flowcharts",
                "font": "Arial 14 bold",
                "fill": "#1B5E20"
            }
        },
        # Connecting Line
        {
            "id": 40,
            "type": "line",
            "coords": [700, 280, 700, 400],
            "tags": [],
            "config": {
                "fill": "gray",
                "width": 2,
                "arrow": "last"
            }
        },
        # Magic features explanation
        {
            "id": 50,
            "type": "text",
            "coords": [450, 520],
            "tags": [],
            "config": {
                "text": "Try out the ✨ Magic button below to parse text into flowcharts!\nYou can also draw rough shapes and have them snap into perfect shapes.",
                "font": "Arial 14",
                "fill": "#333"
            }
        }
    ],
    "connections": [
        {
            "line_id": 40,
            "start": 20,
            "end": 30
        }
    ]
}

file_path = "f:/soham/Project/AI Whiteboard/Showcase_Template.aiwb"

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(template_data, f, indent=4)

print(f"Successfully generated template at {file_path}")
