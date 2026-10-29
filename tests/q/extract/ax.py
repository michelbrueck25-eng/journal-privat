import pytesseract,re,numpy as np
from PIL import Image,ImageOps
def _ocr(crop,scale,psm,thr):
    g=ImageOps.invert(crop.convert('L'))
    if thr: g=g.point(lambda v:0 if v<thr else 255)
    big=g.resize((g.width*scale,g.height*scale),Image.LANCZOS)
    return pytesseract.image_to_data(big,config=f'--psm {psm} -c tessedit_char_whitelist=0123456789,.',output_type=pytesseract.Output.DICT)
def yaxis(img):
    W,H=img.size; crop=img.crop((W-(115 if H>900 else 85),0,W,H)); out=[]
    for scale,psm,thr in ((4,11,150),(4,6,0),(3,11,170),(5,11,130)):
        d=_ocr(crop,scale,psm,thr)
        for t,y,h in zip(d['text'],d['top'],d['height']):
            t=t.strip().replace('.',',')
            if re.fullmatch(r'\d{1,3},\d{3,5}',t): out.append(((y+h/2)/scale,float(t.replace(',','.')),t))
    return out
def xaxis(img):
    W,H=img.size; crop=img.crop((0,H-85,W-80,H-35)); out=[]
    for scale,psm,thr in ((3,11,150),(3,6,0)):
        d=_ocr(crop,scale,psm,thr)
        for t,x,w in zip(d['text'],d['left'],d['width']):
            t=t.strip()
            if re.fullmatch(r'20\d\d',t): out.append(((x+w/2)/scale,int(t)))
    # Duplikate zusammenfassen
    res=[]
    for x,y in sorted(out):
        if res and abs(res[-1][0]-x)<20 and res[-1][1]==y: continue
        res.append((x,y))
    return res
