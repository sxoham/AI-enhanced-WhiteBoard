
import pytest
pytest.importorskip('graphviz')
from graphviz import Digraph
import flowchart_utils

def test_conditional_logic():
    # Model the new Flowchart Fun syntax with indents
    parsed_data = [
        {'indent': 0, 'label': 'Check if valid?', 'edge_label': '', 'is_ref': False, 'is_decision': True},
        {'indent': 4, 'label': 'grant access', 'edge_label': 'Yes', 'is_ref': False, 'is_decision': False},
        {'indent': 4, 'label': 'deny access', 'edge_label': 'No', 'is_ref': False, 'is_decision': False},
    ]
    dot = Digraph()
    flowchart_utils.add_sequential_edges(dot, parsed_data)
    src = dot.source
    
    # New IDs follow node_n format
    # node_1: Check if valid?
    # node_2: grant access
    # node_3: deny access
    
    # Verify edges branch from node_1 with Yes/No labels
    assert 'node_1 -> node_2' in src
    assert 'label=Yes' in src
    assert 'node_1 -> node_3' in src
    assert 'label=No' in src
    
    # Check shape for decision node
    assert 'node_1 [label="Check if valid?"' in src
    assert 'shape=diamond' in src
    assert 'fillcolor="#F1C40F"' in src
