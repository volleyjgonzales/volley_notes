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
# Bit-level /22 explanation: 32 columns in four octets.
a=canvas('IPv4 address anatomy | 10.0.1.254/22','22 network bits stay fixed; 10 host bits vary across 1,024 addresses.',1100,560)
left=60; cw=29.2; space=13; gap=1.6
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
a.append(f'<text x="52" y="239" fill="{MUTED}" font-size="11" font-family="Inter,Arial">MASK</text>')
a.append(f'<text x="52" y="269" fill="{MUTED}" font-size="11" font-family="Inter,Arial">DEC</text>')
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
a.append(f'<text x="550" y="519" text-anchor="middle" fill="{MUTED}" font-size="14" font-family="Inter,Arial">10 host bits = 2^10 = 1,024 total addresses | Network 10.0.0.0 | Broadcast 10.0.3.255</text>')
save('02-subnet.svg',a)
a=canvas('Troubleshooting | Discover, verify, connect','A successful TCP connection is evidence of an open port, not proof that MQTT authorization will succeed.',1000,360)
steps=[('1. Inspect','ip -4 addr, ip route'),('2. Scan','nmap TCP 1883'),('3. Verify','mosquitto_sub'),('4. Connect','MQTT Explorer')]
for i,(title,detail) in enumerate(steps):
 x=52+i*239;rect(a,x,145,210,98,title,[detail],TEAL if i==3 else BLUE)
 if i<3:path(a,f'M {x+212} 190 L {x+234} 190')
a.append(f'<text x="500" y="304" text-anchor="middle" font-size="15" fill="{MUTED}" font-family="Inter,Arial">Known working example: 10.0.1.173:1883 (observed October 13, 2026)</text>')
save('03-workflow.svg',a)
print('generated',*[str(p) for p in P.glob('*.svg')],sep='\n')
