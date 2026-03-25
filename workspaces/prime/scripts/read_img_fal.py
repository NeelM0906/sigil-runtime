import fal_client, base64, os, sys

with open('uploads/IMG_0255.png', 'rb') as f:
    img_b64 = base64.b64encode(f.read()).decode()

data_url = f"data:image/png;base64,{img_b64}"

result = fal_client.run(
    "fal-ai/florence-2-large/detailed-caption",
    arguments={"image_url": data_url}
)
print(result)

result2 = fal_client.run(
    "fal-ai/florence-2-large/ocr",
    arguments={"image_url": data_url}
)
print(result2)
