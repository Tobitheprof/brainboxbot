from PIL import Image
import pytesseract

# Load the image
image_path = "./2.png"
image = Image.open(image_path)

# Use pytesseract to extract text with their bounding boxes
data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

# Define the text we are looking for
texts_to_find = ["BITCOIN.BRO.BEAR", "0.01", "0.015", "0.005"]

# Store coordinates of matches
coordinates = []

# Loop through the detected text
for i, text in enumerate(data['text']):
    if text in texts_to_find:
        coordinates.append({
            "text": text,
            "left": data['left'][i],
            "top": data['top'][i],
            "width": data['width'][i],
            "height": data['height'][i]
        })

print(coordinates)
