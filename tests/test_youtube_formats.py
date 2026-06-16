import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import youtube_utils

class TestYouTubeFormats(unittest.TestCase):
    @patch('google.generativeai.GenerativeModel')
    def test_qa_format_prompt(self, MockModel):
        # Mock Gemini response for Q&A (JSON list)
        mock_response = MagicMock()
        mock_response.text = '[{"question": "What is AI?", "answer": "Artificial Intelligence"}]'
        MockModel.return_value.generate_content.return_value = mock_response
        
        with patch('os.getenv', return_value='fake_key'):
            result = youtube_utils.summarize_text_with_gemini("fake transcript", format="qa")
            
        self.assertIsInstance(result, list)
        self.assertEqual(result[0]["question"], "What is AI?")
        self.assertEqual(result[0]["answer"], "Artificial Intelligence")

    @patch('google.generativeai.GenerativeModel')
    def test_flowchart_format_prompt(self, MockModel):
        # Mock Gemini response for Flowchart
        mock_response = MagicMock()
        mock_response.text = "* Step 1\n* Step 2?"
        MockModel.return_value.generate_content.return_value = mock_response
        
        with patch('os.getenv', return_value='fake_key'):
            result = youtube_utils.summarize_text_with_gemini("fake transcript", format="flowchart")
            
        self.assertIsInstance(result, str)
        self.assertIn("* Step 1", result)

if __name__ == '__main__':
    unittest.main()
