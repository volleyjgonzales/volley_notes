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
path(a,'M 230 251 L 230 304 L 383 304','Connect + subscribe',270,288)
path(a,'M 810 251 L 810 310 L 643 310','Publish / subscribe',749,288)
save('01-topology.svg',a)
a=canvas('IPv4 subnet | Why /22 starts at 10.0.0.0','10.0.1.254/22 has mask 255.255.252.0; /22 covers four consecutive /24 ranges.',1000,340)
for i in range(4):
 x=54+i*235; active=i==1
 a.append(f'<rect x="{x}" y="130" width="217" height="135" rx="13" fill="{("#e3f5f2" if active else "#edf2f8")}" stroke="{(TEAL if active else LINE)}" stroke-width="{(3 if active else 1)}"/>')
 a.append(f'<text x="{x+17}" y="170" fill="{INK}" font-family="Inter,Arial" font-size="22" font-weight="700">10.0.{i}.x</text><text x="{x+17}" y="200" fill="{MUTED}" font-family="Inter,Arial" font-size="14">256 addresses</text>')
 if active:a.append(f'<text x="{x+17}" y="238" fill="{TEAL}" font-family="Inter,Arial" font-size="14" font-weight="700">Laptop: .254</text>')
a.append(f'<text x="500" y="296" text-anchor="middle" fill="{MUTED}" font-size="14" font-family="Inter,Arial">Full /22 range: 10.0.0.0 - 10.0.3.255 | 1,024 total addresses</text>')
save('02-subnet.svg',a)
a=canvas('Troubleshooting | Discover, verify, connect','A successful TCP connection is evidence of an open port, not proof that MQTT authorization will succeed.',1000,360)
steps=[('1. Inspect','ip -4 addr, ip route'),('2. Scan','nmap TCP 1883'),('3. Verify','mosquitto_sub'),('4. Connect','MQTT Explorer')]
for i,(title,detail) in enumerate(steps):
 x=52+i*239;rect(a,x,145,210,98,title,[detail],TEAL if i==3 else BLUE)
 if i<3:path(a,f'M {x+212} 190 L {x+234} 190')
a.append(f'<text x="500" y="304" text-anchor="middle" font-size="15" fill="{MUTED}" font-family="Inter,Arial">Known working example: 10.0.1.173:1883 (observed October 13, 2026)</text>')
save('03-workflow.svg',a)
print('generated',*[str(p) for p in P.glob('*.svg')],sep='\n')
