# capture_region.py - Captura una región de pantalla y la guarda como BMP
# Usado por auto_accept.ahk para ImageSearch
import sys
from ctypes import windll, c_int, byref, create_string_buffer
from ctypes.wintypes import DWORD, LONG, WORD
import struct

def capture_region(x, y, w, h, output_path):
    """Captura una región de pantalla y guarda como BMP usando solo ctypes (sin dependencias)"""
    # Get screen DC
    hdc_screen = windll.user32.GetDC(0)
    hdc_mem = windll.gdi32.CreateCompatibleDC(hdc_screen)
    hbmp = windll.gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
    windll.gdi32.SelectObject(hdc_mem, hbmp)
    
    # Copy screen region
    windll.gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, x, y, 0x00CC0020)  # SRCCOPY
    
    # Get bitmap bits
    class BITMAPINFOHEADER(type(create_string_buffer(40))):
        pass
    
    bmi = create_string_buffer(40)
    struct.pack_into('<IiiHHIIiiII', bmi, 0,
        40,     # biSize
        w,      # biWidth
        -h,     # biHeight (negative = top-down)
        1,      # biPlanes
        24,     # biBitCount
        0,      # biCompression
        0,      # biSizeImage
        0, 0,   # biXPelsPerMeter, biYPelsPerMeter
        0, 0    # biClrUsed, biClrImportant
    )
    
    # Row size must be aligned to 4 bytes
    row_size = ((w * 3 + 3) // 4) * 4
    img_size = row_size * h
    bits = create_string_buffer(img_size)
    
    windll.gdi32.GetDIBits(hdc_mem, hbmp, 0, h, bits, bmi, 0)
    
    # Write BMP file
    file_size = 54 + img_size
    with open(output_path, 'wb') as f:
        # BMP header
        f.write(b'BM')
        f.write(struct.pack('<I', file_size))
        f.write(struct.pack('<HH', 0, 0))
        f.write(struct.pack('<I', 54))
        # Re-pack info header with positive height for standard BMP
        info = struct.pack('<IiiHHIIiiII',
            40, w, h, 1, 24, 0, img_size, 0, 0, 0, 0)
        f.write(info)
        # Write rows bottom-up (standard BMP format)
        for row in range(h - 1, -1, -1):
            offset = row * row_size
            f.write(bits[offset:offset + row_size])
    
    # Cleanup
    windll.gdi32.DeleteObject(hbmp)
    windll.gdi32.DeleteDC(hdc_mem)
    windll.user32.ReleaseDC(0, hdc_screen)
    
    print(f"OK: {w}x{h} saved to {output_path}")

if __name__ == "__main__":
    x, y, w, h = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    output = sys.argv[5]
    capture_region(x, y, w, h, output)
