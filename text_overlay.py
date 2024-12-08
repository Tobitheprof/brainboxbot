from PIL import Image, ImageDraw, ImageFont

def overlay_multiple_texts(
    image_path, 
    output_path, 
    texts_with_coordinates, 
    default_font_path
):
    try:
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        
        for entry in texts_with_coordinates:
            text = entry["text"]
            coordinates = entry["coordinates"]
            color = entry["color"]
            font_size = entry.get("font_size", 40)
            
            font = ImageFont.truetype(default_font_path, font_size)
            
            draw.text(coordinates, text, fill=color, font=font)
        
        img.save(output_path)
        img.show()
        print(f"Image saved to {output_path}")
    except Exception as e:
        print(f"Error: {e}")

image_path = "./bro.png"
output_path = "./image_with_texts_micra.png"
font_path = "./fonts/micra.ttf"

texts_with_coordinates = [
    {"text": "KIKA.THE.BUNNY.PLUSH", "coordinates": (152, 230), "color": (0, 0, 0), "font_size": 30},
    {"text": "0.002", "coordinates": (320, 270), "color": (0, 0, 0), "font_size": 30},
    {"text": "0.002", "coordinates": (320, 310), "color": (255, 0, 0), "font_size": 30},
    {"text": "0.002", "coordinates": (490, 350), "color": (0, 0, 0), "font_size": 30},
    {"text": "1.1BTC $500 100%", "coordinates": (200, 450), "color": (255, 0, 0), "font_size": 30},

]

overlay_multiple_texts(image_path, output_path, texts_with_coordinates, font_path)
