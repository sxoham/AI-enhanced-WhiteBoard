import os
import pytest
from graphviz import Digraph
import flowchart_utils

def test_add_sequential_edges_structure():
    # Model a simple hierarchy: Root -> Child 1, Root -> Child 2
    parsed_data = [
        {'indent': 0, 'label': 'Root Node', 'edge_label': '', 'is_ref': False, 'is_decision': False},
        {'indent': 4, 'label': 'Child One', 'edge_label': 'Go', 'is_ref': False, 'is_decision': False},
        {'indent': 4, 'label': 'Child Two', 'edge_label': 'Stop', 'is_ref': False, 'is_decision': False},
    ]
    dot = Digraph()
    flowchart_utils.add_sequential_edges(dot, parsed_data)
    src = dot.source
    
    # Check for nodes
    assert 'node_1 [label="Root Node"' in src
    assert 'node_2 [label="Child One"' in src
    assert 'node_3 [label="Child Two"' in src
    
    # Check for hierarchical edges
    assert 'node_1 -> node_2' in src
    assert 'label=Go' in src
    assert 'node_1 -> node_3' in src
    assert 'label=Stop' in src
