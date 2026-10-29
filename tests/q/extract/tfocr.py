import re,json,sys,pytesseract
from PIL import Image,ImageOps
def tf_of(path,c):
    im=Image.open(path).convert('RGB'); H=im.size[1]
    y0=max(0,int(c['ymin']-45)); y1=min(H,int(c['ymax']*0+c['ymin']+30))
    crop=im.crop((10,y0,640,y1)); g=ImageOps.invert(crop.convert('L')).point(lambda v:0 if v<150 else 255)
    big=g.resize((g.width*3,g.height*3),Image.LANCZOS)
    t=pytesseract.image_to_string(big,config='--psm 6')
    m=re.search(r'[·\-—\s]\s*1\s*([WTDMH])\b|\b1\s*([WTDM])\s*[·\.]',t)
    mm=re.search(r'\b(1\s?[WTM]|4\s?[SH]|1\s?[DH])\b',t)
    return t.replace('\n',' | ')[:120], (m.group(1) or m.group(2)) if m else None
if __name__=='__main__':
    for i in sys.argv[1:]:
        c=json.load(open(f'/tmp/C3/{i}.json')); print(i,tf_of(f'/home/claude/journal-privat/bilder/{i}_0.jpg',c))
