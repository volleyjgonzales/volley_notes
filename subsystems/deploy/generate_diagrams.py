"""Generate the reference SVG diagrams using Python's standard library."""
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).parent / 'diagrams'
OUT.mkdir(exist_ok=True)

def draw(name, title, subtitle, nodes, edges, width=1000, height=650):
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(title)}</title><desc id="desc">{escape(subtitle)}</desc>',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#52708a"/></marker></defs>',
        '<rect width="100%" height="100%" fill="#f5f8fc"/>',
        f'<text x="35" y="40" font-family="DejaVu Sans, sans-serif" font-size="24" font-weight="bold" fill="#173451">{escape(title)}</text>',
        f'<text x="35" y="68" font-family="DejaVu Sans, sans-serif" font-size="14" fill="#52708a">{escape(subtitle)}</text>']
    for points, label, lx, ly in edges:
        parts.append(f'<polyline points="{points}" fill="none" stroke="#52708a" stroke-width="2" marker-end="url(#arrow)"/>')
        if label:
            parts.append(f'<text x="{lx}" y="{ly}" font-family="DejaVu Sans, sans-serif" font-size="13" fill="#31546b">{escape(label)}</text>')
    for x,y,w,h,lines,kind in nodes:
        fill,stroke = ('#e0f5ef','#16836e') if kind=='output' else ('#ffffff','#8ca6bb')
        if kind=='missing': fill,stroke='#fff3db','#bc8418'
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
        for i,line in enumerate(lines):
            parts.append(f'<text x="{x+w/2}" y="{y+27+i*23}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="{16 if i==0 else 13}" font-weight="{"bold" if i==0 else "normal"}" fill="#173451">{escape(line)}</text>')
    parts.append('</svg>')
    (OUT/name).write_text('\n'.join(parts))

draw('artifact-flow.svg','Artifact build and delivery','The Mender bundle ships configuration and a CLI; application images are retrieved separately.',[
 (40,110,270,85,['swarmctl source + pyproject','uv / Poe → shiv build','Hatchling packages the Python code'],'normal'),
 (40,255,270,85,['bin/swarmctl','Executable Python zipapp','Requires a device Python interpreter'],'output'),
 (390,110,270,85,['Tracked swarm/ files','.env, manifest, YAML, templates','Service configuration files'],'normal'),
 (390,255,270,85,['Staged tree → normalized tar','Add bin/swarmctl','Metadata is a separate Mender input'],'normal'),
 (390,415,270,85,['Mender artifact','swarm-deploy-<version>.mender','Compatible: central-x86-64'],'output'),
 (40,550,280,75,['Hosted Mender','Stores the uploaded artifact'],'output'),
 (385,550,280,75,['Device /data/swarm','OS module extracts and drives CLI'],'missing'),
 (730,415,235,85,['Container registries','AWS / public registries','Referenced by Compose'],'output'),
 (730,550,235,75,['Docker Swarm tasks','Images fetched on swarm nodes'],'normal')],
 [('175,195 175,255','build',185,225),('310,295 390,295','copy',335,280),('525,195 525,255','copy',535,225),('525,340 525,415','wrap',535,380),('390,460 180,460 180,550','upload',225,447),('320,587 385,587','delivery',330,575),('665,587 730,587','deploy',675,575),('850,500 850,550','pull',860,528)],height=665)

draw('ci-pipeline.svg','CI job dependencies','Triggers: main/release pushes, matching release tags, and pull requests.',[
 (350,110,300,75,['builder-image','Build + push builder-<full SHA>'],'normal'),
 (100,255,300,75,['static-analysis','prek run --all-files'],'normal'),
 (600,255,300,75,['swarmctl','pytest → shiv → Actions artifact'],'normal'),
 (350,405,300,85,['mender-artifact','Needs builder + both checks','Build, upload to Mender, retain in CI'],'output'),
 (350,565,300,65,['github-release (tags only)','Attach CLI and .mender assets'],'output')],
 [('420,185 250,255','builder image',240,217),('580,185 750,255','builder image',610,217),('250,330 420,405','check passes',235,370),('750,330 580,405','CLI + tests pass',650,370),('500,185 500,405','direct dependency',510,365),('500,490 500,565','artifact ready',510,530),('900,295 950,295 950,600 650,600','CLI asset',825,583)],height=660)

draw('deployment-scope.svg','Stack ownership and placement','Example: two central managers share a swarm; east is the designated root.',[
 (35,110,285,100,['Root central: east','SWARM_ROOT=true','engine role=root','fq_site_name=garage-east'],'normal'),
 (365,110,285,100,['Central: west','SWARM_ROOT=false','fq_site_name=garage-west'],'normal'),
 (695,110,270,100,['Bay workers','device=bay-x86-64','fq_site_name and bay_id labels'],'normal'),
 (35,340,285,95,['site (one stack)','map / MQTT / OTEL / Prometheus','Placed on role=root'],'output'),
 (365,340,285,95,['global (one stack)','Fluentd task on every central','Root deploys it once'],'output'),
 (35,525,285,95,['app-east','Central + discovered east bays','Own stack-scoped overlay'],'output'),
 (695,525,270,95,['app-west','Central + discovered west bays','Own stack-scoped overlay'],'output')],
 [('120,210 120,340','root deploys',130,285),('310,195 340,195 340,300 500,300 500,340','root deploys',385,287),('80,210 15,210 15,570 35,570','east deploys',25,480),('650,170 675,170 675,570 695,570','west deploys',680,480),('460,340 460,235 280,235 280,210','task on east',325,250),('560,340 560,210','task on west',570,280),('260,525 800,450 800,210','east bay placement',540,473),('830,525 830,210','west bay placement',845,465)],height=650)

draw('release-lifecycle.svg','Device release lifecycle','CLI behavior shown; the external OS module and Mender state mapping are not supplied.',[
 (55,110,280,110,['Before install','live = previous release','staged = extracted new payload','last = older backup, if present'],'normal'),
 (55,295,280,95,['Remove owned stacks','Metadata + .pending in staged','Carry .env.local if not shipped'],'normal'),
 (400,295,280,95,['Swap release trees','Delete old last; live → last','staged → live; deploy automatic'],'output'),
 (55,500,280,90,['Commit','Remove live/.pending','Previous tree stays in last'],'output'),
 (655,500,290,115,['Rollback while pending','Remove owned stacks','failed live → staged; last → live','Clear marker; redeploy'],'output'),
 (655,110,290,100,['Interrupted between renames','live absent, last exists','recover(): last → live','Invoked by release rollback'],'missing')],
 [('195,220 195,295','install',205,253),('335,342 400,342','rename',343,283),('470,390 195,500','accept',255,448),('610,390 800,500','reject',735,440),('680,295 800,210','power cut window',705,257),('800,210 970,210 970,557 945,557','rollback recovery',815,435)],height=655)
