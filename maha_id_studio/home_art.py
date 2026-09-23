"""Original six-panel artwork with deterministic demo cards and one button layer."""
from PIL import Image, ImageDraw, ImageFont, ImageOps

def font(size):
    for name in ('C:/Windows/Fonts/arialbd.ttf','DejaVuSans-Bold.ttf'):
        try:return ImageFont.truetype(name,size)
        except OSError:pass
    return ImageFont.load_default()

def text_fit(draw,text,box,size=26):
    for n in range(size,10,-1):
        f=font(n);lines=[];line=''
        for word in text.split():
            candidate=(line+' '+word).strip()
            if line and draw.textlength(candidate,font=f)>box[2]-box[0]-14:lines.append(line);line=word
            else:line=candidate
        lines.append(line)
        if len(lines)*(n+4)<=box[3]-box[1]-6:break
    y=(box[1]+box[3]-len(lines)*(n+4))/2
    for line in lines:
        draw.text(((box[0]+box[2])/2,y),line,font=f,fill='white',anchor='mt');y+=n+4

def demo_card(assets,back=False):
    # Only the runtime home sample is marked. Supplied image files remain intact.
    card=Image.open(assets/('Demo_back.jpg' if back else 'Demo_front.jpg')).convert('RGB').resize((900,570))
    d=ImageDraw.Draw(card)
    if back:
        d.rectangle((240,120,650,455),fill='#e2e5e9')
        d.text((445,270),'DEMO',font=font(75),fill='#657588',anchor='mm')
        d.text((445,350),'NO SCANNABLE CODE',font=font(24),fill='#173650',anchor='mm')
    d.rectangle((0,520,900,570),fill='#b81530')
    d.text((450,545),'DEMO / SAMPLE — NOT A VALID ID',font=font(30),fill='white',anchor='mm')
    return card

def compose_home(assets,modes):
    image=Image.open(assets/'Home_Background_10_35.png').convert('RGB').resize((1672,941))
    draw=ImageDraw.Draw(image);front=demo_card(assets);back=demo_card(assets,True)
    titles=((284,278,548,347),(844,278,1085,347),(1390,278,1638,347),(284,588,548,656),(842,588,1088,656),(1390,588,1638,656))
    subtitles=((282,354,550,456),(842,354,1088,456),(1387,354,1640,456),(282,665,550,771),(840,665,1090,771),(1387,665,1640,771))
    sheets=((62,238,262,493),(598,251,801,493),(1144,237,1362,503),(54,547,274,820),(603,546,817,820),(1139,546,1361,820))
    for index,((title,subtitle,_),tb,sb,pb) in enumerate(zip(modes,titles,subtitles,sheets)):
        if index==1:
            for dx,dy in ((30,-14),(20,-9),(10,-4)):
                draw.rectangle((pb[0]+dx,pb[1]+dy,pb[2]+dx,pb[3]+dy),fill='#dde3e9',outline='#9ca9b7',width=2)
        draw.rectangle(pb,fill='white',outline='#99a6b5',width=2)
        cols=1 if index<2 else 2;rows=2 if index<2 else 4 if index==2 else 5
        w=(pb[2]-pb[0]-12-(cols-1)*4)//cols;h=(pb[3]-pb[1]-12-(rows-1)*4)//rows
        for row in range(rows):
            for col in range(cols):
                is_back=(row==1 if index<2 else row%2==1 if index==2 else col==1 if index==3 else index==5)
                sample=ImageOps.contain(back if is_back else front,(w,h),Image.Resampling.LANCZOS)
                x=pb[0]+6+col*(w+4)+(w-sample.width)//2;y=pb[1]+6+row*(h+4)+(h-sample.height)//2
                image.paste(sample,(x,y))
        draw.rounded_rectangle(tb,radius=14,fill='#850e20',outline='#ef8995',width=2)
        draw.rounded_rectangle((tb[0]+3,tb[1]+3,tb[2]-3,tb[3]-6),radius=11,fill='#c91223')
        draw.line((tb[0]+14,tb[1]+4,tb[2]-14,tb[1]+4),fill='#fa7584',width=2)
        text_fit(draw,title,tb,28);text_fit(draw,subtitle,sb,24)
    return image
