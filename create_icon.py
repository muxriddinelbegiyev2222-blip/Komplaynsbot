import os
from PIL import Image, ImageDraw

os.makedirs("assets", exist_ok=True)

# 64x64 - PyInstaller va Windows uchun 100% xavfsiz va xatosiz standart o'lcham
size = (64, 64)
image = Image.new("RGBA", size, (0, 0, 0, 0))
draw = ImageDraw.Draw(image)

# Qalqon foni (Ko'k rang)
draw.rounded_rectangle([4, 4, 60, 60], radius=12, fill="#1f538d", outline="#0d2b4d", width=2)

# Qalqon shakli (Oq va yashil)
draw.polygon([(32, 12), (48, 20), (48, 38), (32, 50), (16, 38), (16, 20)], fill="#ffffff")
draw.polygon([(32, 16), (44, 23), (44, 36), (32, 46), (20, 36), (20, 23)], fill="#2e7d32")

# Faqat standart DIB o'lchamlari (PyInstaller xato bermasligi uchun)
image.save("assets/icon.ico", format="ICO", sizes=[(64, 64), (48, 48), (32, 32), (16, 16)])
print("assets/icon.ico muvaffaqiyatli saqlandi!")
