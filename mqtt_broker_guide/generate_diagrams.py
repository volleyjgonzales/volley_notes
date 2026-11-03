from pathlib import Path
from xml.sax.saxutils import escape
P=Path(__file__).parent/'assets';P.mkdir(exist_ok=True)
NAVY='#101d2e';INK='#20324b';MUTED='#61728b';BG='#f5f8fc';WHITE='#ffffff';TEAL='#0b9488';BLUE='#2f6dd5';ORANGE='#ef9d37';LINE='#cbd7e5'
def canvas(title,subtitle,w=1000,h=390):
 return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="100%" height="100%" fill="{BG}"/><rect x="22" y="20" width="{w-44}" height="{h-40}" rx="18" fill="{WHITE}" stroke="{LINE}"/><text x="52" y="63" fill="{NAVY}" font-size="23" font-weight="700" font-family="Inter,Arial,sans-serif">{escape(title)}</text><text x="52" y="88" fill="{MUTED}" font-size="14" font-family="Inter,Arial,sans-serif">{escape(subtitle)}</text>']
def rect(a,x,y,w,h,title,body,accent=TEAL):
 a.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="13" fill="{WHITE}" stroke="{accent}" stroke-width="2"/><rect x="{x}" y="{y}" width="7" height="{h}" rx="3" fill="{accent}"/><text x="{x+20}" y="{y+33}" fill="{INK}" font-size="19" font-weight="700" font-family="Inter,Arial">{escape(title)}</text>')
 for i,s in enumerate(body):a.append(f'<text x="{x+20}" y="{y+57+i*20}" fill="{MUTED}" font-size="14" font-family="Inter,Arial">{escape(s)}</text>')
def path(a,d,label=None,x=0,y=0):
 a.append(f'<path d="{d}" stroke="{BLUE}" stroke-width="3" fill="none" stroke-linecap="round" marker-end="url(#arrow)"/>')
 if label:a.append(f'<text x="{x}" y="{y}" fill="{BLUE}" font-size="13" text-anchor="middle" font-weight="600" font-family="Inter,Arial">{escape(label)}</text>')
def save(name,a):
 a.insert(1,f'<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{BLUE}"/></marker></defs>')
 (P/name).write_text(''.join(a)+'</svg>')
a=canvas('MQTT topology | Who connects to whom','A broker relays published messages to subscribed clients. AGV broker location is not yet confirmed.',1000,420)
rect(a,70,140,245,110,'Lenovo Legion',['MQTT Explorer client','10.0.1.254'],BLUE)
rect(a,385,255,255,105,'MQTT broker',['Discovered: 10.0.1.173','TCP port: 1883'],TEAL)
rect(a,690,140,245,110,'AGV',['Possible MQTT client','Address not verified'],ORANGE)
path(a,'M 230 251 L 230 304 L 383 304','Connect + subscribe',304,292)
path(a,'M 810 251 L 810 304 L 643 304','Publish / subscribe',728,292)
save('01-topology.svg',a)
# Bit-level /22 explanation: 32 columns in four octets.
a=canvas('IPv4 address anatomy | 10.0.1.254/22','22 network bits stay fixed; 10 host bits vary across 1,024 addresses.',1100,560)
left=104; cw=28.4; space=13; gap=1.6; label_x=92
starts=[left+i*(8*cw+space) for i in range(4)]
net='#0b9488';host='#e6a044';
a.append(f'<rect x="60" y="105" width="16" height="16" rx="3" fill="{net}"/><text x="84" y="118" font-family="Inter,Arial" font-size="14" fill="{INK}">Network prefix (22 bits)</text>')
a.append(f'<rect x="300" y="105" width="16" height="16" rx="3" fill="{host}"/><text x="324" y="118" font-family="Inter,Arial" font-size="14" fill="{INK}">Host portion (10 bits)</text>')
for octet,(number,value,mask) in enumerate([(1,10,255),(2,0,255),(3,1,252),(4,254,0)]):
 x0=starts[octet]
 a.append(f'<text x="{x0+8*cw/2}" y="154" font-size="14" font-weight="700" fill="{INK}" text-anchor="middle" font-family="Inter,Arial">Octet {number} = {value}</text>')
 bits=f'{value:08b}';mbits=f'{mask:08b}'
 for j,b in enumerate(bits):
  idx=octet*8+j;xx=x0+j*cw;clr=net if idx<22 else host
  a.append(f'<rect x="{xx:.1f}" y="169" width="{cw-gap:.1f}" height="42" rx="5" fill="{clr}"/>')
  a.append(f'<text x="{xx+(cw-gap)/2:.1f}" y="197" text-anchor="middle" font-size="18" font-weight="700" fill="white" font-family="monospace">{b}</text>')
  a.append(f'<text x="{xx+(cw-gap)/2:.1f}" y="240" text-anchor="middle" font-size="15" fill="{MUTED}" font-family="monospace">{mbits[j]}</text>')
 a.append(f'<text x="{x0+8*cw/2}" y="268" text-anchor="middle" font-size="13" fill="{MUTED}" font-family="Inter,Arial">{mask}</text>')
for yy,lbl in [(196,'IP'),(240,'MASK'),(268,'DEC')]:
 a.append(f'<text x="{label_x}" y="{yy}" text-anchor="end" fill="{MUTED}" font-size="11" font-weight="700" font-family="Inter,Arial">{lbl}</text>')
xsplit=starts[2]+6*cw-1
# Mark the /22 boundary after six bits of octet 3.
a.append(f'<line x1="{xsplit:.1f}" y1="158" x2="{xsplit:.1f}" y2="218" stroke="{NAVY}" stroke-width="2.5" stroke-dasharray="3 3"/>')
a.append(f'<text x="{xsplit:.1f}" y="139" text-anchor="middle" fill="{NAVY}" font-size="13" font-weight="700" font-family="Inter,Arial">/22 boundary</text>')
a.append(f'<text x="60" y="307" fill="{NAVY}" font-size="18" font-weight="700" font-family="Inter,Arial">Only the last 2 bits of octet 3 can change</text>')
a.append(f'<text x="60" y="333" fill="{MUTED}" font-size="14" font-family="Inter,Arial">Third octet = 000000xx (binary) = 0, 1, 2, or 3 (decimal). Final octet = 00000000 through 11111111.</text>')
for i in range(4):
 x=60+i*254
 active=i==1
 fill='#e5f5f1' if active else '#f1f5fa';stroke=TEAL if active else LINE
 a.append(f'<rect x="{x}" y="363" width="237" height="112" rx="12" fill="{fill}" stroke="{stroke}" stroke-width="{2 if active else 1}"/>')
 a.append(f'<text x="{x+15}" y="390" fill="{INK}" font-size="14" font-family="monospace">000000{i:02b}</text>')
 a.append(f'<text x="{x+15}" y="421" fill="{NAVY}" font-size="24" font-weight="700" font-family="Inter,Arial">10.0.{i}.x</text>')
 a.append(f'<text x="{x+15}" y="448" fill="{TEAL if active else MUTED}" font-size="13" font-family="Inter,Arial">{("Laptop: 10.0.1.254" if active else "256 addresses")}</text>')
a.append(f'<text x="550" y="519" text-anchor="middle" fill="{MUTED}" font-size="14" font-family="Inter,Arial">10 host bits = 2<tspan font-size="10" dy="-7">10</tspan><tspan dy="7"> = 1,024 total addresses | Network 10.0.0.0 | Broadcast 10.0.3.255</tspan></text>')
save('02-subnet.svg',a)
# Dots vs. prefix line: the octet grouping and the mask grouping are independent.
a=canvas('Two different groupings of the same 32 bits','The dots are fixed by the notation. The /22 line is set by the mask. They do not have to agree.',1100,520)
left=150; cw=27; ch=40; top=186; GREY='#8fa2b8'
bits=''.join(f'{v:08b}' for v in (10,0,1,254))
def bx(i): return left+i*cw
a.append(f'<line x1="{left}" y1="118" x2="{left+22}" y2="118" stroke="{NAVY}" stroke-width="3"/><text x="{left+30}" y="122" font-family="Inter,Arial" font-size="14" fill="{INK}">Octet dot: always after bits 8, 16, 24</text>')
a.append(f'<line x1="{left+340}" y1="118" x2="{left+362}" y2="118" stroke="{ORANGE}" stroke-width="3" stroke-dasharray="5 4"/><text x="{left+370}" y="122" font-family="Inter,Arial" font-size="14" fill="{INK}">/22 line: after bit 22, set by the subnet mask</text>')
for i,b in enumerate(bits):
 clr=TEAL if i<22 else '#e6a044'
 a.append(f'<rect x="{bx(i)+1}" y="{top}" width="{cw-2}" height="{ch}" rx="4" fill="{clr}"/>')
 a.append(f'<text x="{bx(i)+cw/2}" y="{top+27}" text-anchor="middle" font-size="17" font-weight="700" fill="white" font-family="monospace">{b}</text>')
for n in (1,8,16,22,24,32):
 a.append(f'<text x="{bx(n-1)+cw/2}" y="{top-10}" text-anchor="middle" font-size="11" fill="{MUTED}" font-family="Inter,Arial">bit {n}</text>')
a.append(f'<text x="{left-14}" y="{top+26}" text-anchor="end" font-size="12" font-weight="700" fill="{MUTED}" font-family="Inter,Arial">10.0.1.254</text>')
# fixed octet dots
for n in (8,16,24):
 x=bx(n)
 a.append(f'<line x1="{x}" y1="{top-30}" x2="{x}" y2="{top+ch+74}" stroke="{NAVY}" stroke-width="3"/>')
 a.append(f'<circle cx="{x}" cy="{top-36}" r="4" fill="{NAVY}"/>')
# the /22 line
x22=bx(22)
a.append(f'<line x1="{x22}" y1="{top-30}" x2="{x22}" y2="{top+ch+134}" stroke="{ORANGE}" stroke-width="3" stroke-dasharray="5 4"/>')
a.append(f'<text x="{x22}" y="{top-40}" text-anchor="middle" font-size="12" font-weight="700" fill="{ORANGE}" font-family="Inter,Arial">/22</text>')
def bracket(x0,x1,y,color,label,sub=None):
 a.append(f'<path d="M {x0+3} {y-8} L {x0+3} {y} L {x1-3} {y} L {x1-3} {y-8}" stroke="{color}" stroke-width="2" fill="none"/>')
 a.append(f'<text x="{(x0+x1)/2}" y="{y+20}" text-anchor="middle" font-size="15" font-weight="700" fill="{color}" font-family="Inter,Arial">{escape(label)}</text>')
 if sub:a.append(f'<text x="{(x0+x1)/2}" y="{y+37}" text-anchor="middle" font-size="12" fill="{MUTED}" font-family="Inter,Arial">{escape(sub)}</text>')
def rowlabel(y,text):
 a.append(f'<text x="{left-14}" y="{y}" text-anchor="end" font-size="12" font-weight="700" fill="{MUTED}" font-family="Inter,Arial">{escape(text)}</text>')
# row 1: how it is written
y1=top+ch+22
rowlabel(y1+14,'WRITTEN AS')
for k,v in enumerate((10,0,1,254)):
 bracket(bx(8*k),bx(8*k+8),y1,NAVY,str(v),'8 bits')
# row 2: how the /22 mask reads it
y2=y1+72
rowlabel(y2+14,'READ BY /22')
bracket(bx(0),bx(22),y2,TEAL,'network: 22 bits','fixed on this network (10.0.0.x, x = 0..3)')
bracket(bx(22),bx(32),y2,'#c97f12','host: 10 bits','varies per device (0..1023; this one is 510)')
# row 3: /24 for comparison
y3=y2+72
rowlabel(y3+14,'IF IT WERE /24')
bracket(bx(0),bx(24),y3,GREY,'network: 24 bits','line lands exactly on the third dot')
bracket(bx(24),bx(32),y3,GREY,'host: 8 bits','only then is "3 octets + 1 octet" true')
a.append(f'<text x="550" y="{y3+66}" text-anchor="middle" fill="{MUTED}" font-size="14" font-family="Inter,Arial">The dots never move. The prefix line can land anywhere, including inside an octet.</text>')
save('04-dots-vs-prefix.svg',a)
a=canvas('Troubleshooting | Discover, verify, connect','A successful TCP connection is evidence of an open port, not proof that MQTT authorization will succeed.',1000,360)
steps=[('1. Inspect','ip -4 addr, ip route'),('2. Scan','nmap TCP 1883'),('3. Verify','mosquitto_sub'),('4. Connect','MQTT Explorer')]
for i,(title,detail) in enumerate(steps):
 x=52+i*239;rect(a,x,145,210,98,title,[detail],TEAL if i==3 else BLUE)
 if i<3:path(a,f'M {x+212} 190 L {x+234} 190')
a.append(f'<text x="500" y="304" text-anchor="middle" font-size="15" fill="{MUTED}" font-family="Inter,Arial">Known working example: 10.0.1.173:1883 (observed October 13, 2026)</text>')
save('03-workflow.svg',a)
print('generated',*[str(p) for p in P.glob('*.svg')],sep='\n')
