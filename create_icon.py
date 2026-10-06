import os
from PIL import Image, ImageDraw

def generate_compliance_icon():
    os.makedirs("assets", exist_ok=True)
    icon_path = os.path.join("assets", "app_icon.ico")
    png_path = os.path.join("assets", "app_icon.png")

    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    base_size = 256
    img = Image.new("RGBA", (base_size, base_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Tashqi himoya qalqoni (To'q ko'k #0F2537 va Oltin hoshiya #D4AF37)
    shield_pts = [
        (128, 12),
        (236, 52),
        (236, 152),
        (128, 244),
        (20, 152),
        (20, 52)
    ]
    draw.polygon(shield_pts, fill="#0F2537", outline="#D4AF37", width=8)

    # 2. Ichki himoya qatlami (#16324F)
    inner_pts = [
        (128, 28),
        (220, 62),
        (220, 146),
        (128, 226),
        (36, 146),
        (36, 62)
    ]
    draw.polygon(inner_pts, fill="#16324F", outline="#204060", width=4)

    # 3. Telegram bot ramzi (Moviy samolyot)
    plane_pts = [
        (60, 124),
        (196, 76),
        (136, 184),
        (116, 144)
    ]
    draw.polygon(plane_pts, fill="#2AABEE")
    draw.polygon([(116, 144), (196, 76), (136, 184)], fill="#229ED9")
    draw.polygon([(116, 144), (140, 144), (136, 184)], fill="#1E88C7")

    # 4. Komplayens adolat tarozisi (Oltin rangda)
    draw.line([(128, 150), (128, 206)], fill="#D4AF37", width=6)
    draw.line([(96, 170), (160, 170)], fill="#D4AF37", width=5)
    draw.arc([(84, 170), (108, 194)], 0, 180, fill="#FFFFFF", width=3)
    draw.arc([(148, 170), (172, 194)], 0, 180, fill="#FFFFFF", width=3)

    img.save(png_path, format="PNG")
    img.save(icon_path, format="ICO", sizes=[(s[0], s[1]) for s in sizes])
    print("Rasmiy Kadastr Komplayens logotipi yaratildi!")

if __name__ == "__main__":
    generate_compliance_icon()
