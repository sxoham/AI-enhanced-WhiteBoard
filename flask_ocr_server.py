import io
import base64
from flask import Flask, request, jsonify
from PIL import Image

print("Loading TrOCR dependencies (this may take a moment)...")
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

# Initializing Flask app
app = Flask(__name__)

# Initialize TrOCR models globally so they don't reload on every request
# Using the base handwritten model. It will auto-download on first use.
print("Loading TrOCR Model (microsoft/trocr-base-handwritten)...")
processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")

# Optimization: Move to GPU if available
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model.to(device)
print(f"TrOCR Model loaded successfully on {device}.")

@app.route('/ocr', methods=['POST'])
def process_ocr():
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'error': 'No image data provided'}), 400
            
        base64_image = data['image']
        
        # Decode base64 to PIL Image
        image_data = base64.b64decode(base64_image)
        img_pil = Image.open(io.BytesIO(image_data)).convert("RGB")
        
        # 2. Preprocess: Sharpening can help the Vision Encoder find cleaner stroke edges
        from PIL import ImageFilter
        img_pil = img_pil.filter(ImageFilter.SHARPEN)
        
        # 3. TrOCR Extraction with Optimized Beam Search
        pixel_values = processor(img_pil, return_tensors="pt").pixel_values.to(device)
        
        # Refined parameters for better handwriting segmentation
        generated_ids = model.generate(
            pixel_values,
            max_new_tokens=128,
            num_beams=8, # Increased beams for deeper search
            early_stopping=True,
            length_penalty=1.0,
            no_repeat_ngram_size=3,
            do_sample=False, # Deterministic greedy/beam search is usually better for OCR
        )
        
        generated_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        return jsonify({'text': generated_text.strip()})
        
    except Exception as e:
        print(f"Error during TrOCR processing: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting Local Flask TrOCR Server on port 5000...")
    app.run(host='127.0.0.1', port=5000)
