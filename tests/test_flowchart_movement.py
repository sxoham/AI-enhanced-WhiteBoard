import unittest
import tkinter as tk
from whiteboard import Whiteboard
import json
import os

class TestFlowchartMovement(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        # Mocking screen width/height for winfo_width/height 
        self.root.geometry("800x600")
        self.app = Whiteboard(self.root)
        self.app.root.update()

    def tearDown(self):
        self.root.destroy()

    def test_flowchart_grouping_and_handle(self):
        # 1. Mock Graphviz JSON Data
        mock_data = {
            "bb": "0,0,200,200",
            "objects": [
                {"_gvid": 0, "name": "A", "label": "A", "pos": "50,150", "shape": "box"},
                {"_gvid": 1, "name": "B", "label": "B", "pos": "150,50", "shape": "box"}
            ],
            "edges": [
                {"tail": 0, "head": 1, "pos": "50,150 150,50"}
            ]
        }
        
        # 2. Draw Flowchart
        created_ids = self.app.draw_native_graphviz(mock_data, title="Test Flowchart")
        
        # 3. Verify Handle exists
        handles = self.app.c.find_withtag("flowchart_handle")
        self.assertTrue(len(handles) > 0, "Flowchart handle should be created")
        handle_id = handles[0]
        
        # 4. Verify Group registration
        tags = self.app.c.gettags(handle_id)
        group_tag = next((t for t in tags if t.startswith("flowchart_group_")), None)
        self.assertIsNotNone(group_tag, "Handle should have a flowchart group tag")
        self.assertIn(group_tag, self.app.groups, "Group should be registered in app.groups")
        
        # 5. Verify Selection of whole group via handle
        # Simulate click on handle
        class MockEvent:
            x = 100 # Should be around handle pos
            y = 100
            state = 0
            
        # We need actual canvas coords for find_overlapping inside select_object
        bbox = self.app.c.bbox(handle_id)
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        
        # Override event coords for select_object
        event = MockEvent()
        # select_object takes (x, y, event) where x/y are event coords
        # It uses c.canvasx(x) which for 1:1 scale is x.
        self.app.select_object(cx, cy, event)
        
        # check selected objects
        group_members = self.app.groups[group_tag]
        for member in group_members:
            self.assertIn(member, self.app.selected_objects, f"Member {member} should be selected via handle")

    def test_connection_maintenance(self):
        # 1. Mock Data
        mock_data = {
            "bb": "0,0,200,200",
            "objects": [
                {"_gvid": 0, "name": "A", "label": "A", "pos": "50,150", "shape": "box"},
                {"_gvid": 1, "name": "B", "label": "B", "pos": "150,50", "shape": "box"}
            ],
            "edges": [
                {"tail": 0, "head": 1, "pos": "50,150 150,50"}
            ]
        }
        
        # 2. Draw
        self.app.draw_native_graphviz(mock_data)
        
        # 3. Find edge and verify connection
        edges = self.app.c.find_withtag("flowchart_edge")
        self.assertTrue(len(edges) > 0)
        edge_id = edges[0]
        
        self.assertIn(edge_id, self.app.connections, "Edge should be registered in connections")
        
        # 4. Move Node A
        node_a_text = self.app.c.find_withtag("flowchart_text")[0]
        # Simulate moving node A
        old_coords = self.app.c.coords(edge_id)
        self.app.c.move(node_a_text, 100, 100)
        # Update connections for its group
        tags = self.app.c.gettags(node_a_text)
        group_tag = next((t for t in tags if t.startswith("node_group_")), None)
        for part in self.app.c.find_withtag(group_tag):
             self.app.update_connected_lines(part)
        
        new_coords = self.app.c.coords(edge_id)
        self.assertNotEqual(old_coords, new_coords, "Edge should have moved with the node")

if __name__ == '__main__':
    unittest.main()
