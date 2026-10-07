from style import *
import os
HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,"..","07-mqtt")+"/"; PV="/tmp/"
def go(fig,name): save(fig, OUT+name+".svg", PV+name+".png")
# Paho automatic reconnect: first retry after min interval, doubled on each failure, capped at max.
mn,mx=1.0,60.0
att=[]; t=0.0; iv=mn
while t<400: t+=iv; att.append(t); iv=min(2*iv,mx)
att=np.array(att)
T=np.linspace(0.01,330,4000)
delay=np.array([att[att>=x][0]-x for x in T])
fig,axs=plt.subplots(2,1,figsize=(10.5,5.6),sharex=True,gridspec_kw=dict(height_ratios=[1,2.2]))
ax=axs[0]
for a in att[att<330]: ax.axvline(a,color=C["s1"],lw=1)
ax.set_yticks([]); ax.set_title("Reconnect attempts after the connection is lost (min 1 s, doubling, max 60 s)",loc="left")
for a in att[:7]: ax.text(a,0.55,f"{a:g} s",rotation=90,fontsize=8,ha="right",va="center",color=C["s1"])
ax=axs[1]
ax.plot(T,delay,color=C["hl"],lw=1.4)
ax.set_xlabel("outage length: time from connection loss until the broker is reachable again [s]")
ax.set_ylabel("extra wait until the\nnext attempt [s]")
ax.set_title("Worst case: up to 60 s of extra downtime after the broker returns",loc="left")
ax.grid(alpha=.3); ax.set_ylim(0,65)
fig.tight_layout(); go(fig,"reconnect_backoff"); print("ok")
