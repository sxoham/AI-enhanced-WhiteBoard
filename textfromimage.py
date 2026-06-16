from PIL import Image
from pytesseract import pytesseract
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import os
import shutil


# Function to extract text from an image using Tesseract
def extract_text(image_path):
    # Defining path to tesseract.exe
    path_to_tesseract = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    if os.path.exists(path_to_tesseract):
        pytesseract.tesseract_cmd = path_to_tesseract
    elif shutil.which("tesseract"):
        # Tesseract is in PATH, no need to set cmd
        pass
    else:

        print("Warning: Tesseract-OCR not found. Please install it or update the path in textfromimage.py")
        from tkinter import messagebox
        try:
           messagebox.showwarning("Tesseract Not Found", "Tesseract-OCR was not found at standard locations.\nOCR features may not work.\nPlease install it or update path in textfromimage.py")
        except:
           pass # In case tk root not ready


    # Opening the image & storing it in an image object
    try:
        img = Image.open(image_path)
    except Exception as e:
        print(f"Error opening image file '{image_path}': {e}")
        try:
            from tkinter import messagebox
            messagebox.showerror("Image Load Error", f"Cannot open the selected image file. It may be corrupted or an unsupported format.\n\nError details: {e}")
        except Exception:
            pass
        return None

    # Passing the image object to image_to_string() function
    # This function will extract the text from the image
    try:
        text = pytesseract.image_to_string(img)
    except Exception as e:
        print(f"Error processing image for OCR: {e}")
        try:
            from tkinter import messagebox
            messagebox.showerror("OCR Error", f"An error occurred while extracting text from the image.\n\nError details: {e}")
        except Exception:
            pass
        return None

    return text


# Main function
def main():
    # Hiding the root Tkinter window
    Tk().withdraw()

    # Open file dialog to select an image file
    image_path = askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.tiff;*.webp")])

    # If a file was selected
    if image_path:
        # Extract and display the text from the selected image
        text = extract_text(image_path)

        if text:
            print(text[:-1])
        else:
            print("No text found")
    else:
        print("No file selected")


# Run the main function
if __name__ == "__main__":
    main()