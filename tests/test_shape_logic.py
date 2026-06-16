
import math

# Mocking the whiteboard class to test detect_shape logic
class MockWhiteboard:
    def __init__(self):
        self.current_stroke_points = []
        self.penwidth = 2
        self.color_fg = 'black'
        self.fill_color = 'none'
        self.detected_shape = None
        self.objects = []
        self.undo_stack = []
        self.current_stroke_ids = []
        self.c = MockCanvas()

    def replace_stroke_with_shape(self, shape_type, p1, p2):
        self.detected_shape = shape_type
        print(f"Detected: {shape_type}")

    def perp_dist(self, p, p1, p2):
        x, y = p
        x1, y1 = p1
        x2, y2 = p2
        if x1 == x2 and y1 == y2:
            return math.sqrt((x - x1)**2 + (y - y1)**2)
        return abs((y2 - y1) * x - (x2 - x1) * y + x2 * y1 - y2 * x1) / math.sqrt((y2 - y1)**2 + (x2 - x1)**2)

    def simplify_points(self, points, epsilon):
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
        points = []
        offset = -math.pi / 2
        for i in range(sides):
            angle = offset + 2 * math.pi * i / sides
            points.append(cx + r * math.cos(angle))
            points.append(cy + r * math.sin(angle))
        return points

    def is_right_triangle(self, p1, p2, p3):
        def dist_sq(a, b): return (a[0]-b[0])**2 + (a[1]-b[1])**2
        d1 = dist_sq(p1, p2)
        d2 = dist_sq(p2, p3)
        d3 = dist_sq(p3, p1)
        sides = sorted([d1, d2, d3])
        tolerance = sides[2] * 0.15 
        return abs((sides[0] + sides[1]) - sides[2]) < tolerance

    def detect_shape(self):
        try:
            points = self.current_stroke_points
            if len(points) < 5: return False 
            
            import math
            
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

            # Vertex Counting (RDP)
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            width = max_x - min_x
            height = max_y - min_y
            diag = math.sqrt(width**2 + height**2)
            
            epsilon = max(5.0, diag * 0.035) 
            
            simplified = self.simplify_points(points, epsilon)
            is_closed = dist_direct < max(30, diag * 0.15)
            
            vertices = len(simplified)
            if is_closed:
                vertices -= 1 
            
            print(f"DEBUG: RDP Vertices: {vertices} (Epsilon: {epsilon:.1f})")

            area = 0.0
            for i in range(len(points)):
                j = (i + 1) % len(points)
                area += points[i][0] * points[j][1]
                area -= points[j][0] * points[i][1]
            area = abs(area) / 2.0
            perimeter = dist_path
            circularity = (4 * math.pi * area) / (perimeter**2) if perimeter > 0 else 0
            
            # Classification
            if vertices == 3 and is_closed:
                poly = simplified[:3]
                if self.is_right_triangle(poly[0], poly[1], poly[2]):
                     self.replace_stroke_with_shape('triangle (right)', poly, None)
                else:
                     self.replace_stroke_with_shape('triangle', poly, None)

            elif vertices == 4 and is_closed:
                poly = simplified[:4]
                bbox_area = width * height
                fill_ratio = area / bbox_area if bbox_area > 0 else 0
                
                if fill_ratio > 0.85:
                    self.replace_stroke_with_shape('rectangle', (min_x, min_y), (max_x, max_y))
                else:
                    if fill_ratio < 0.6:
                         mid_x = (min_x + max_x) / 2
                         mid_y = (min_y + max_y) / 2
                         rhombus_points = [mid_x, min_y, max_x, mid_y, mid_x, max_y, min_x, mid_y]
                         self.replace_stroke_with_shape('rhombus', rhombus_points, None)
                    else:
                         self.replace_stroke_with_shape('parallelogram', poly, None)

            elif vertices == 5 and is_closed:
                cx = (min_x + max_x) / 2
                cy = (min_y + max_y) / 2
                radius = min(width, height) / 2
                poly_points = self.create_regular_polygon(cx, cy, radius, 5)
                self.replace_stroke_with_shape('pentagon', poly_points, None)

            elif vertices == 6 and is_closed:
                cx = (min_x + max_x) / 2
                cy = (min_y + max_y) / 2
                radius = min(width, height) / 2
                poly_points = self.create_regular_polygon(cx, cy, radius, 6)
                self.replace_stroke_with_shape('hexagon', poly_points, None)
            
            elif (vertices > 6 or circularity > 0.8) and is_closed:
                if circularity > 0.88 and 0.8 < (width/height) < 1.2:
                     self.replace_stroke_with_shape('oval', (min_x, min_y), (max_x, max_y))
                else:
                     self.replace_stroke_with_shape('oval', (min_x, min_y), (max_x, max_y))
            
            else:
                 if is_closed:
                      self.replace_stroke_with_shape('polygon', simplified[:-1], None)
                 
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False

class MockCanvas:
    def delete(self, *args): pass
    def create_line(self, *args, **kwargs): return 1
    def create_polygon(self, *args, **kwargs): return 1
    def create_rectangle(self, *args, **kwargs): return 1
    def create_oval(self, *args, **kwargs): return 1

# Generate Shapes
def rect(x, y, w, h):
    return [(x, y), (x+w, y), (x+w, y+h), (x, y+h), (x, y)]

def circle(cx, cy, r, steps=20):
    return [(cx + r*math.cos(2*math.pi*i/steps), cy + r*math.sin(2*math.pi*i/steps)) for i in range(steps+1)]

def triangle(x, y, w, h):
    return [(x + w/2, y), (x+w, y+h), (x, y+h), (x + w/2, y)]

def rhombus(x, y, w, h):
    return [(x + w/2, y), (x+w, y+h/2), (x + w/2, y+h), (x, y+h/2), (x + w/2, y)]

def noisy(points, amount=2):
    import random
    return [(p[0] + random.uniform(-amount, amount), p[1] + random.uniform(-amount, amount)) for p in points]

def pentagon(x, y, r):
    points = []
    for i in range(5):
        angle = 2 * math.pi * i / 5 - math.pi / 2
        points.append((x + r * math.cos(angle), y + r * math.sin(angle)))
    points.append(points[0])
    return points

def hexagon(x, y, r):
    points = []
    for i in range(6):
        angle = 2 * math.pi * i / 6 - math.pi / 2
        points.append((x + r * math.cos(angle), y + r * math.sin(angle)))
    points.append(points[0])
    return points

def test():
    wb = MockWhiteboard()
    
    print("\n--- Test Rectangle ---")
    wb.current_stroke_points = noisy(rect(0, 0, 100, 50))
    wb.detect_shape()
    
    print("\n--- Test Square ---")
    wb.current_stroke_points = noisy(rect(0, 0, 100, 100))
    wb.detect_shape()

    print("\n--- Test Circle ---")
    wb.current_stroke_points = noisy(circle(50, 50, 40))
    wb.detect_shape()

    print("\n--- Test Triangle ---")
    wb.current_stroke_points = noisy(triangle(0, 0, 100, 100))
    wb.detect_shape()
    
    print("\n--- Test Rhombus ---")
    wb.current_stroke_points = noisy(rhombus(0, 0, 100, 100))
    wb.detect_shape()
    
    print("\n--- Test Pentagon ---")
    wb.current_stroke_points = noisy(pentagon(100, 100, 50))
    wb.detect_shape()
    
    print("\n--- Test Hexagon ---")
    wb.current_stroke_points = noisy(hexagon(100, 100, 50))
    wb.detect_shape()

if __name__ == "__main__":
    test()
