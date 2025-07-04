from flask import Flask, request, send_file
from flask_cors import CORS  # ✅ CORS for frontend access
from rembg import remove
from PIL import Image, ImageEnhance, ImageOps
import io
import cv2
import numpy as np
import os

app = Flask(__name__)
CORS(app)  # ✅ Enable CORS for all routes

def convert_unit(value, unit, dpi=96):
    if unit == "px":
        return int(value)
    elif unit == "in":
        return int(float(value) * dpi)
    elif unit == "cm":
        return int(float(value) * dpi / 2.54)
    else:
        return int(value)

def enhance_image_light(img):
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.1)
    enhancer = ImageEnhance.Contrast(img)
    return enhancer.enhance(1.1)

def apply_blur_background(original, mask):
    original_np = np.array(original.convert("RGB"))
    mask_np = np.array(mask.convert("L"))

    blurred = cv2.GaussianBlur(original_np, (51, 51), 0)
    result_np = np.where(mask_np[:, :, None] > 0, original_np, blurred)
    result_img = Image.fromarray(result_np.astype('uint8'), 'RGB')
    return result_img

@app.route('/')
def home():
    return "Hello from Flask on Render!"

@app.route('/process-image', methods=['POST'])
def process_image():
    if 'image' not in request.files:
        return "No image uploaded", 400

    image_file = request.files['image']
    image = Image.open(image_file.stream).convert("RGBA")

    remove_bg = request.form.get("remove_bg", "false").lower() == "true"
    bg_blur = request.form.get("bg_blur", "false").lower() == "true"
    bg_color = request.form.get("bg_color", "").strip()

    if remove_bg:
        mask = remove(image, only_mask=True)
        image_no_bg = remove(image)

        if bg_blur:
            image = apply_blur_background(image, mask)
        elif bg_color:
            try:
                background = Image.new("RGBA", image.size, bg_color)
                image = Image.alpha_composite(background, image_no_bg)
            except:
                pass
        else:
            image = image_no_bg

    if request.form.get("light_fix", "false").lower() == "true":
        image = enhance_image_light(image)

    try:
        width = int(request.form.get("resize_width", 0))
        height = int(request.form.get("resize_height", 0))
        unit = request.form.get("resize_unit", "px")
        if width > 0 and height > 0:
            width_px = convert_unit(width, unit)
            height_px = convert_unit(height, unit)
            image = image.resize((width_px, height_px))
    except:
        pass

    output_format = request.form.get("output_format", "png").lower()
    if output_format == "jpg":
        output_format = "jpeg"

    compress = request.form.get("compress", "false").lower() == "true"

    output_io = io.BytesIO()
    save_kwargs = {"format": output_format.upper()}
    if compress and output_format in ["jpeg", "webp"]:
        save_kwargs["optimize"] = True
        save_kwargs["quality"] = 75

    image = image.convert("RGB") if output_format != "png" else image
    image.save(output_io, **save_kwargs)
    output_io.seek(0)

    return send_file(output_io, mimetype=f"image/{output_format}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
