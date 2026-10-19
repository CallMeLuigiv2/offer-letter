from PIL import Image, ImageDraw
import sys
# 16x16 pixel badge scaled x16 = 256 px: envelope with a green seal
P = {'.': (0,0,0,0), 'k': (20,22,28,255), 'b': (58,110,200,255), 'w': (240,240,235,255), 'g': (90,200,120,255), 'd': (40,70,130,255)}
rows = [
 "................",
 ".kkkkkkkkkkkkkk.",
 ".kbbbbbbbbbbbbk.",
 ".kbkbbbbbbbbkbk.",
 ".kbbkbbbbbbkbbk.",
 ".kbbbkkbbkkbbbk.",
 ".kbbbbbkkbbbbbk.",
 ".kbbbbbbbbbbbbk.",
 ".kbbbbbbbbbbbbk.",
 ".kbbbbbbbbggbbk.",
 ".kbbbbbbbgwwgbk.",
 ".kbbbbbbbgwwgbk.",
 ".kbbbbbbbbggbbk.",
 ".kkkkkkkkkkkkkk.",
 "................",
 "................"]
im = Image.new('RGBA', (16,16))
for y,r in enumerate(rows):
    for x,c in enumerate(r): im.putpixel((x,y), P[c])
im.resize((256,256), Image.NEAREST).save(sys.argv[1])
