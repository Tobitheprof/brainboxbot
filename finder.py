from PIL import Image
import pytesseract

image_path = "./2.png"
image = Image.open(image_path)

data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

texts_to_find = ["BITCOIN.BRO.BEAR", "0.01", "0.015", "0.005"]

coordinates = []

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
