import unittest
import tkinter as tk
from whiteboard import Whiteboard

class TestSmartConnectors(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.app = Whiteboard(self.root)

    def tearDown(self):
        self.root.destroy()

    def test_connector_updates_on_resize(self):
        # 1. Create a Rectangle (100, 100, 200, 200)
        # Manually adding to objects list and canvas to simulate drawing
        rect_id = self.app.c.create_rectangle(100, 100, 200, 200, tags="rectangle")
        self.app.objects.append(rect_id)
        
        # 2. Create a Line connected to it
        # Center of rect is 150, 150. Let's say line goes from there to 300, 300
        line_id = self.app.c.create_line(150, 150, 300, 300, tags="line")
        self.app.objects.append(line_id)
        
        # Create a second object for the line to connect to
        rect2_id = self.app.c.create_rectangle(250, 250, 350, 350, tags="rectangle_2")
        self.app.objects.append(rect2_id)
        
        # Register connection manually
        self.app.connections[line_id] = {'start': rect_id, 'end': rect2_id}
        
        # 3. Resize Rectangle (Target)
        # Simulate selecting the rectangle
        self.app.resize_target = rect_id
        
        # Simulate drag event effectively resizing it
        # Current logic uses old mouse pos vs new mouse pos.
        # But handle_resize_drag calculates new width/height based on event.x/y vs bbox x1/y1
        
        # Let's say we drag the bottom-right corner (200, 200) to (300, 300)
        # New rect should be (100, 100, 300, 300). Center: (200, 200).
        
        class MockEvent:
            x = 300
            y = 300
            
        self.app.handle_resize_drag(MockEvent())
        self.app.root.update() # Process events
        
        # 4. Verify Line Position
        coords = self.app.c.coords(line_id)
        # Expected Start: New Center (200, 200)
        # Expected End: Unchanged (300, 300)
        
        print(f"Line coords after resize: {coords}")
        
        # Allow small margin of error for float calcs
        self.assertAlmostEqual(coords[0], 200, delta=1, msg="Line start X should be new center X")
        self.assertAlmostEqual(coords[1], 200, delta=1, msg="Line start Y should be new center Y")
        
if __name__ == '__main__':
    unittest.main()
