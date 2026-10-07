from style import *
import os
HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,"..","08-otel")+"/"; PV="/tmp/"
def go(fig,name): save(fig, OUT+name+".svg", PV+name+".png")
B=[0,5,10,25,50,75,100,250,500,750,1000,2500,5000,7500,10000]   # OTel SDK default boundaries
rng=np.random.default_rng(3)
x=rng.lognormal(mean=np.log(12),sigma=0.6,size=200000)          # illustrative latency [ms]
edges=[-np.inf]+B+[np.inf]
counts=np.array([((x>edges[i])&(x<=edges[i+1])).sum() for i in range(len(edges)-1)])
def q_interp(q):
    tgt=q*counts.sum(); c=np.cumsum(counts); i=np.searchsorted(c,tgt)
    lo=edges[i] if np.isfinite(edges[i]) else 0; hi=edges[i+1] if np.isfinite(edges[i+1]) else B[-1]
    prev=c[i-1] if i>0 else 0; return lo+(hi-lo)*(tgt-prev)/counts[i]
fig,axs=plt.subplots(1,2,figsize=(12,4.3),gridspec_kw=dict(width_ratios=[1.6,1]))
ax=axs[0]
ax.hist(x[x<120],bins=240,density=True,color=C["s1"],alpha=.35,label="illustrative latency distribution")
for b in B:
    if b<=120: ax.axvline(b,color=C["box"],lw=.8,ls=":")
for q,col in [(0.5,C["pt"]),(0.95,C["hl"])]:
    t=np.quantile(x,q); e=q_interp(q)
    ax.axvline(t,color=col,lw=2); ax.axvline(e,color=col,lw=2,ls="--")
    ax.text(t+1,ax.get_ylim()[1]*(.85 if q==.5 else .6),f"p{int(q*100)} true {t:.1f} ms\nfrom buckets {e:.1f} ms",color=col,fontsize=8.5)
ax.set_xlim(0,120); ax.set_xlabel("latency [ms]"); ax.set_yticks([])
ax.set_title("Default OTel buckets (dotted) and quantiles estimated from them",fontsize=10); ax.legend(fontsize=8,loc="upper right")
ax=axs[1]
lab=[f"≤{b:g}" for b in B]+[">10000"]
show=slice(0,9)
ax.bar(range(9),counts[show]/counts.sum(),color=C["s1"]); ax.set_xticks(range(9)); ax.set_xticklabels(lab[show],rotation=45,fontsize=8)
ax.set_ylabel("fraction of samples"); ax.set_title("Exported bucket counts (first 9 of 16)",fontsize=10)
ax.text(3.0,.36,"With HistogramBoundaries{.buckets = {}}\nthe histogram has ONE bucket:\nonly count, sum, min, max survive",fontsize=8,color=C["hl"],bbox=dict(fc="white",ec=C["hl"]))
fig.tight_layout(); go(fig,"histogram_buckets")

# Gauge sampling: observable gauge is read only at export instants
t=np.linspace(0,10,5001); sig=np.zeros_like(t)
for s,d,h in [(0.3,2.2,3),(2.8,0.35,9),(4.1,3.0,4),(5.55,0.25,12),(7.6,1.6,6),(9.2,0.4,10)]:
    sig[(t>=s)&(t<s+d)]=h
fig,ax=plt.subplots(figsize=(11,3.4))
ax.step(t,sig,where="post",color=C["s1"],lw=1.6,label="state the callback reads (e.g. active jobs)")
ts=np.arange(1,11); vs=[sig[np.searchsorted(t,k)-1] for k in ts]
ax.plot(ts,vs,"o",color=C["hl"],ms=8,label="values exported (callback runs once per export_interval = 1 s)")
ax.annotate("short spike never exported",xy=(5.65,12),xytext=(6.2,12.5),fontsize=8.5,color=C["hl"],arrowprops=dict(arrowstyle="->",color=C["hl"]))
ax.set_xlabel("time [s]"); ax.set_ylabel("value"); ax.grid(alpha=.3); ax.set_ylim(-.5,14.5); ax.legend(fontsize=8,loc="upper left")
ax.set_title("Observable gauges are sampled, not accumulated",loc="left")
go(fig,"gauge_sampling"); print("ok")
