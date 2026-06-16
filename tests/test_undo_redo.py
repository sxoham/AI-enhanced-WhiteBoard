import tkinter as tk
from whiteboard import Whiteboard
import time

def test_undo_redo():
    root = tk.Tk()
    wb = Whiteboard(root)
    wb.root.update()

    print("--- Test 1: Creation Undo ---")
    # Create Line
    start_objs = len(wb.objects)
    wb.shape = 'line'
    wb.old_x, wb.old_y = 10, 10
    wb.fill_color = 'black'
    wb.color_fg = 'black'
    
    # Simulate creation via on_button_press/release cycle? 
    # Or just call internal creation logic?
    # Let's call internal logic to keep it simple, mimicking what on_button_release does.
    line_id = wb.c.create_line(10, 10, 100, 100, fill='black', width=5)
    wb.objects.append(line_id)
    wb.undo_stack.append(('create_line', line_id, 10, 10, 100, 100, 'black', 5))
    
    assert len(wb.objects) == start_objs + 1
    
    wb.undo()
    assert len(wb.objects) == start_objs
    print("Undo Creation: PASSED")
    
    wb.redo()
    assert len(wb.objects) == start_objs + 1
    item_id = wb.objects[-1]
    print("Redo Creation: PASSED")
    
    print("--- Test 2: Move Undo ---")
    # Move object by (50, 50)
    original_coords = wb.c.coords(item_id)
    dx, dy = 50, 50
    wb.c.move(item_id, dx, dy)
    wb.undo_stack.append(('move', [item_id], dx, dy))
    
    moved_coords = wb.c.coords(item_id)
    assert moved_coords[0] == original_coords[0] + dx
    
    wb.undo()
    undo_coords = wb.c.coords(item_id)
    assert undo_coords == original_coords
    print("Undo Move: PASSED")
    
    wb.redo()
    redo_coords = wb.c.coords(item_id)
    assert redo_coords == moved_coords
    print("Redo Move: PASSED")
    
    print("--- Test 3: Delete Undo ---")
    # Capture state manually as delete_selected does
    undo_data_list = []
    item_data = {
        'type': wb.c.type(item_id),
        'coords': wb.c.coords(item_id),
        'tags': wb.c.gettags(item_id),
        'config': {'fill': 'black', 'width': 5.0} # float from itemcget usually
    }
    undo_data_list.append(item_data)
    
    wb.c.delete(item_id)
    wb.objects.remove(item_id)
    wb.undo_stack.append(('delete', undo_data_list))
    
    assert len(wb.objects) == start_objs
    
    wb.undo() # Should restore
    assert len(wb.objects) == start_objs + 1
    restored_id = wb.objects[-1]
    print(f"Restored ID: {restored_id}")
    assert wb.c.type(restored_id) == 'line'
    print("Undo Delete: PASSED")
    
    # Redo Delete?
    # wb.redo()
    # assert len(wb.objects) == start_objs
    # print("Redo Delete: PASSED")
    
    print("All Tests Passed!")
    root.destroy()

if __name__ == "__main__":
    test_undo_redo()
