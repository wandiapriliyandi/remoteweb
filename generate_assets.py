"""Generator aset logo dan icon untuk RemoteWebMonitor.

Menghasilkan logo.png (resolusi tinggi) dan icon.ico (format Windows multi-size).
"""
import math
import os
from PIL import Image, ImageDraw, ImageFilter

def create_shield_icon(size: int = 1024) -> Image.Image:
    # Canvas RGBA transparan dengan supersampling
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    center_x = size // 2
    center_y = int(size * 0.48)
    scale = size / 512.0

    # 1. Soft Outer Ambient Glow
    glow_radius = int(220 * scale)
    glow_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_img)
    glow_draw.ellipse(
        [center_x - glow_radius, center_y - glow_radius, center_x + glow_radius, center_y + glow_radius],
        fill=(2, 132, 199, 90)
    )
    glow_img = glow_img.filter(ImageFilter.GaussianBlur(int(40 * scale)))
    img.alpha_composite(glow_img)

    # 2. Outer Shield Geometry (Poly-points aproksimasi kurva halus)
    points_outer = []
    # Kurva atas & samping shield
    steps = 40
    # Top edge (melengkung sedikit ke bawah dari tengah)
    for i in range(steps + 1):
        t = i / steps
        # dari kiri atas ke tengah lalu ke kanan atas
        x = (88 + (424 - 88) * t) * scale
        # kubik halus untuk curve atas
        y = (58 - 14 * math.sin(t * math.pi)) * scale
        points_outer.append((x, y))
    
    # Samping kanan ke bawah runcing
    for i in range(steps + 1):
        t = i / steps
        # x dari 424 ke 256
        x = (424 - (424 - 256) * (t ** 1.3)) * scale
        # y dari ~192 ke 460
        y = (192 + (460 - 192) * (t ** 0.85)) * scale
        points_outer.append((x, y))
        
    # Bawah runcing ke samping kiri
    for i in range(steps + 1):
        t = i / steps
        x = (256 - (256 - 88) * ((1 - t) ** 1.3)) * scale
        y = (460 - (460 - 192) * (t ** 1.15)) * scale
        points_outer.append((x, y))

    # Gambarkan Shield Gradient
    shield_mask = Image.new("L", (size, size), 0)
    s_draw = ImageDraw.Draw(shield_mask)
    s_draw.polygon(points_outer, fill=255)

    # Gradient fill biru laut tech
    shield_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for y in range(size):
        ratio = y / size
        # #0284c7 (2, 132, 199) ke #075985 (7, 89, 133)
        r = int(2 * (1 - ratio) + 7 * ratio)
        g = int(132 * (1 - ratio) + 89 * ratio)
        b = int(199 * (1 - ratio) + 133 * ratio)
        shield_layer.paste((r, g, b, 255), [0, y, size, y + 1])
    
    shield_layer.putalpha(shield_mask)
    img.alpha_composite(shield_layer)

    # Gambar border cyan shield
    draw.line(points_outer + [points_outer[0]], fill=(56, 189, 248, 255), width=int(12 * scale), joint="curve")

    # 3. Inner Dark Shield (Cyber Monitor Center)
    inner_scale = 0.82
    points_inner = [
        (center_x + (x - center_x) * inner_scale, center_y + (y - center_y) * inner_scale + 12 * scale)
        for (x, y) in points_outer
    ]
    inner_mask = Image.new("L", (size, size), 0)
    in_draw = ImageDraw.Draw(inner_mask)
    in_draw.polygon(points_inner, fill=255)

    inner_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for y in range(size):
        ratio = y / size
        # #0f172a (15, 23, 42) ke #1e293b (30, 41, 59)
        r = int(15 * (1 - ratio) + 30 * ratio)
        g = int(23 * (1 - ratio) + 41 * ratio)
        b = int(42 * (1 - ratio) + 59 * ratio)
        inner_layer.paste((r, g, b, 255), [0, y, size, y + 1])
    inner_layer.putalpha(inner_mask)
    img.alpha_composite(inner_layer)
    draw.line(points_inner + [points_inner[0]], fill=(30, 58, 95, 220), width=int(4 * scale))

    # 4. Globe Latitudes & Longitudes (Web Network Monitor)
    globe_r = int(105 * scale)
    globe_y = int(225 * scale)
    globe_box = [center_x - globe_r, globe_y - globe_r, center_x + globe_r, globe_y + globe_r]
    grid_color = (2, 132, 199, 90)
    grid_w = max(1, int(2.5 * scale))

    draw.ellipse(globe_box, outline=grid_color, width=grid_w)
    draw.ellipse([center_x - globe_r, globe_y - int(45 * scale), center_x + globe_r, globe_y + int(45 * scale)], outline=grid_color, width=grid_w)
    draw.ellipse([center_x - globe_r, globe_y - int(80 * scale), center_x + globe_r, globe_y + int(80 * scale)], outline=grid_color, width=grid_w)
    draw.ellipse([center_x - int(45 * scale), globe_y - globe_r, center_x + int(45 * scale), globe_y + globe_r], outline=grid_color, width=grid_w)
    draw.line([(center_x - globe_r, globe_y), (center_x + globe_r, globe_y)], fill=grid_color, width=grid_w)
    draw.line([(center_x, globe_y - globe_r), (center_x, globe_y + globe_r)], fill=grid_color, width=grid_w)

    # 5. Radar Wave Arcs (Monitoring & Sensing)
    cyan_bright = (56, 189, 248, 255)
    wave_box_outer = [center_x - int(90 * scale), int(140 * scale), center_x + int(90 * scale), int(320 * scale)]
    draw.arc(wave_box_outer, start=205, end=335, fill=cyan_bright, width=int(6 * scale))

    wave_box_mid = [center_x - int(65 * scale), int(165 * scale), center_x + int(65 * scale), int(295 * scale)]
    draw.arc(wave_box_mid, start=205, end=335, fill=(14, 165, 233, 255), width=int(5 * scale))

    # 6. Central Radar Pulse Node & Core Light
    draw.ellipse([center_x - int(40 * scale), globe_y - int(40 * scale), center_x + int(40 * scale), globe_y + int(40 * scale)], outline=(14, 165, 233, 160), width=int(3 * scale))
    draw.ellipse([center_x - int(18 * scale), globe_y - int(18 * scale), center_x + int(18 * scale), globe_y + int(18 * scale)], fill=(56, 189, 248, 255))
    draw.ellipse([center_x - int(8 * scale), globe_y - int(8 * scale), center_x + int(8 * scale), globe_y + int(8 * scale)], fill=(255, 255, 255, 255))

    # 7. Checkmark / Shield Defense Anchor Accent at Bottom Center
    chk_w = int(10 * scale)
    chk_p1 = (int(215 * scale), int(320 * scale))
    chk_p2 = (int(245 * scale), int(350 * scale))
    chk_p3 = (int(300 * scale), int(285 * scale))
    draw.line([chk_p1, chk_p2, chk_p3], fill=(56, 189, 248, 255), width=chk_w, joint="curve")

    # 8. Top Glass Reflection Sheen
    sheen_mask = Image.new("L", (size, size), 0)
    sh_draw = ImageDraw.Draw(sheen_mask)
    sheen_points = [
        points_outer[0],
        points_outer[len(points_outer)//6],
        (int(256 * scale), int(240 * scale)),
        points_outer[-len(points_outer)//6]
    ]
    sh_draw.polygon(sheen_points, fill=35)
    sheen_layer = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    sheen_layer.putalpha(sheen_mask)
    img.alpha_composite(sheen_layer)

    return img

def main():
    os.makedirs("assets", exist_ok=True)
    master = create_shield_icon(size=1024)

    # 1. Simpan logo.png resolusi tinggi 512x512
    logo_512 = master.resize((512, 512), Image.Resampling.LANCZOS)
    logo_512.save("assets/logo.png", format="PNG")
    print("Berhasil membuat assets/logo.png (512x512)")

    # 2. Simpan logo_256.png
    logo_256 = master.resize((256, 256), Image.Resampling.LANCZOS)
    logo_256.save("assets/logo_256.png", format="PNG")
    print("Berhasil membuat assets/logo_256.png (256x256)")

    # 3. Simpan icon.ico (format ICO Windows dengan berbagai ukuran standar)
    ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    master.save("assets/icon.ico", format="ICO", sizes=ico_sizes)
    print("Berhasil membuat assets/icon.ico (Multi-size: 16 to 256)")

if __name__ == "__main__":
    main()

