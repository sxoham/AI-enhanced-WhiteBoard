import unittest
import tkinter as tk
from whiteboard import Whiteboard

class TestMultipleFlowcharts(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.geometry("800x600")
        self.app = Whiteboard(self.root)
        self.app.root.update()

    def tearDown(self):
        self.root.destroy()

    def test_independent_selection(self):
        # 1. Draw Flowchart 1
        data1 = {
            "bb": "0,0,100,100",
            "objects": [{"_gvid": 0, "name": "A", "label": "A", "pos": "50,50", "shape": "box"}],
            "edges": []
        }
        self.app.draw_native_graphviz(data1, title="Flowchart 1")
        
        # 2. Draw Flowchart 2 (At a different location)
        data2 = {
            "bb": "0,0,100,100",
            "objects": [{"_gvid": 0, "name": "B", "label": "B", "pos": "50,50", "shape": "box"}],
            "edges": []
        }
        # Displace flowchart 2
        # Actually draw_native_graphviz centers it based on winfo_width/height
        # So we should probably give it a different bb or just move it after
        self.app.draw_native_graphviz(data2, title="Flowchart 2")
        
        groups = [g for g in self.app.groups if g.startswith("flowchart_group_")]
        self.assertEqual(len(groups), 2, "Should have 2 independent flowchart groups")
        
        # 3. Select Handle of Flowchart 2
        handles = self.app.c.find_withtag("flowchart_handle")
        self.assertEqual(len(handles), 2)
        h2 = handles[1] # Follows creation order ideally
        
        bbox = self.app.c.bbox(h2)
        cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
        
        class MockEvent:
            x = cx
            y = cy
            state = 0
            
        self.app.select_object(cx, cy, MockEvent())
        
        # 4. Verify ONLY Flowchart 2 items are selected
        f1_tag = groups[0]
        f2_tag = groups[1]
        
        f1_items = self.app.groups[f1_tag]
        f2_items = self.app.groups[f2_tag]
        
        for item in f1_items:
            self.assertNotIn(item, self.app.selected_objects, "Flowchart 1 items should NOT be selected")
        for item in f2_items:
            self.assertIn(item, self.app.selected_objects, "Flowchart 2 items SHOULD be selected")

    def test_undo_redo_group_pollution(self):
        # 1. Draw Flowchart 1
        data1 = {"bb": "0,0,50,50", "objects": [{"_gvid": 0, "name": "A", "pos": "25,25"}], "edges": []}
        self.app.draw_native_graphviz(data1, title="F1")
        f1_tag = next(g for g in self.app.groups if g.startswith("flowchart_group_"))
        
        # 2. Undo it
        self.app.undo()
        # Item is deleted from canvas, but is it removed from self.groups? 
        # (Based on my theory, it's NOT)
        
        # 3. Draw Flowchart 2
        # If Tkinter reuses IDs, Flowchart 2 items might get the same IDs as Flowchart 1
        self.app.draw_native_graphviz(data1, title="F2")
        f2_tag = [g for g in self.app.groups if g.startswith("flowchart_group_") and g != f1_tag][0]
        
        # 4. If ID reuse happened, self.groups[f1_tag] might now point to Flowchart 2 items!
        # If I click handle of F2, it selects F2. Correct.
        # But if f1_tag was NOT deleted, and it contains reused IDs, then some other logic might pick it up.
        
        # Actually, let's just check if f1_tag still exists in self.groups
        self.assertNotIn(f1_tag, self.app.groups, "Group should be deleted from self.groups on undo")

if __name__ == '__main__':
    unittest.main()
