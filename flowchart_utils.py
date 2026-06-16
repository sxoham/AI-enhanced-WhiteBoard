import re
import textwrap

try:
    import docx
except ImportError:
    docx = None
    
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
    
try:
    from graphviz import Digraph
except ImportError:
    Digraph = None


def parse_text(text):
    """
    Parses flowchart-fun syntax.
    Returns a list of dicts representing nodes and their hierarchical relationships.
    """
    lines = text.strip().split('\n')
    parsed_data = []
    
    for line in lines:
        if not line.strip(): continue
        
        # Calculate indent: count leading spaces
        indent = len(line) - len(line.lstrip(' '))
        
        content = line.strip()
        
        # Handle cases where AI stubbornly includes bullet points
        if content.startswith('* ') or content.startswith('- '):
            content = content[2:].strip()
            
        # Edge label detection
        edge_label = ""
        # Check if there's a colon indicating an edge label
        if ':' in content and not content.startswith('('):
            parts = content.split(':', 1)
            # Ensure the colon wasn't just part of a standard sentence (label shouldn't be too long)
            if len(parts[0].strip()) < 30:
                edge_label = parts[0].strip()
                content = parts[1].strip()
            
        is_ref = content.startswith('(') and content.endswith(')')
        if is_ref:
            content = content[1:-1].strip()
            
        is_decision = content.endswith('?')
            
        parsed_data.append({
            'indent': indent,
            'label': content,
            'edge_label': edge_label,
            'is_ref': is_ref,
            'is_decision': is_decision
        })
        
    return parsed_data

def add_sequential_edges(dot, parsed_data, layout_type='standard'):
    """
    Builds the GraphViz logic using the flowchart-fun hierarchical structure.
    """
    if layout_type == 'horizontal':
         dot.attr(rankdir='LR', nodesep='0.5', ranksep='0.5')
    elif layout_type == 'mindmap':
         dot.attr(layout='twopi', ranksep='2.0', ratio='auto', overlap='false')
    else:
         dot.attr(rankdir='TB', nodesep='0.5', ranksep='0.5')
         
    level_tracker = {} # Maps indent level to the node ID
    node_id_counter = 0
    
    # Track created nodes by exact label text for back-references "(Node)"
    label_to_id = {}
    
    # Map raw indents to absolute logical levels safely
    raw_indents = [item['indent'] for item in parsed_data]
    unique_indents = sorted(list(set(raw_indents)))
    indent_map = {val: idx for idx, val in enumerate(unique_indents)}
    
    for item in parsed_data:
        # Use logical level ranking
        level = indent_map.get(item['indent'], 0)
        label = item['label']
        edge_label = item['edge_label']
        is_ref = item['is_ref']
        is_decision = item['is_decision']
        
        if not label: continue
        
        # Word Wrap
        display_label = textwrap.fill(label, width=25)
        
        # Node Resolution
        if is_ref and label in label_to_id:
            current_id = label_to_id[label]
        else:
            node_id_counter += 1
            current_id = f"node_{node_id_counter}"
            
            shape = 'diamond' if is_decision else 'box'
            fillcolor = '#F1C40F' if is_decision else 'white'
            
            dot.node(current_id, label=display_label, shape=shape, style='filled', fillcolor=fillcolor, fontname='Arial')
            
            # Save root references to be linked back to later
            if label not in label_to_id:
                label_to_id[label] = current_id
                
        # Form Edges to Ancestors
        if level > 0:
            # Find the closest parent linearly
            parent_ids = [level_tracker[k] for k in sorted(level_tracker.keys()) if k < level]
            parent_id = parent_ids[-1] if parent_ids else level_tracker.get(0)
            
            if parent_id:
                dot.edge(parent_id, current_id, label=edge_label, fontname='Arial', fontsize='10')
                
        # Update trackers
        level_tracker[level] = current_id
        
        # Clear deeper levels as we traverse back up the tree
        to_remove = [k for k in level_tracker if k > level]
        for k in to_remove:
            del level_tracker[k]


# --- Legacy Support functions ---

def read_text_from_plain_file(file_path):
    with open(file_path, 'r', encoding="utf-8") as file:
        return file.read()

def read_text_from_docx(file_path):
    if not docx: return ""
    doc = docx.Document(file_path)
    full_text = [para.text for para in doc.paragraphs]
    return '\\n'.join(full_text)

def read_text_from_pdf(file_path):
    if not PyPDF2: return ""
    text = ""
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text += page.extract_text()
    return text

def sanitize_label(label):
    return re.sub(r'[^\w\s]', '_', label)
