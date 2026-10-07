from style import *
import os, csv, collections
HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,"..","05-structures")+"/"; PV="/tmp/"
def go(fig,name): save(fig, OUT+name+".svg", PV+name+".png")

# 1. LowPassFilter: step response and effective cutoff
fc=1.0
fig,axs=plt.subplots(1,2,figsize=(11.5,4.2))
ax=axs[0]; tt=np.linspace(0,1.2,500); ax.plot(tt,1-np.exp(-2*np.pi*fc*tt),color="black",lw=1.2,label="continuous RC: 1 − e^(−2π f_c t)")
for dt,col in [(0.01,C["s1"]),(0.1,C["s2"]),(0.3,C["hl"])]:
    a=2*np.pi*fc*dt/(1+2*np.pi*fc*dt); y=0; T=[0];Y=[0]
    for k in range(int(1.2/dt)): y=a*1+(1-a)*y; T.append((k+1)*dt); Y.append(y)
    ax.step(T,Y,where="post",color=col,label=f"LowPassFilter, dt = {dt} s (α = {a:.3f})")
ax.set_xlabel("t [s]"); ax.set_ylabel("output"); ax.set_title("Step response, f_c = 1 Hz"); ax.legend(fontsize=8,loc="lower right"); ax.grid(alpha=.3)
ax=axs[1]; x=np.logspace(-3,0,300)  # f_c*dt
w=2*np.pi*x; a=w/(1+w)
cosw=1-a**2/(2*(1-a)); ok=(cosw>=-1)
feff=np.where(ok,np.arccos(np.clip(cosw,-1,1))/(2*np.pi*x),np.nan)  # effective -3 dB frequency / f_c
ax.semilogx(x,feff,color=C["s1"],lw=2,label="effective −3 dB frequency / nominal f_c")
ax.semilogx(x,a/(1-np.exp(-w)),color=C["s2"],lw=2,ls="--",label="α used / α exact (1 − e^(−2π f_c dt))")
ax.axhline(1,color=C["aux"],lw=.8,ls=":"); ax.set_xlabel("f_c · dt  (cutoff × sample period)"); ax.set_ylim(0,1.6)
ax.set_title("Discretization error grows with f_c · dt"); ax.legend(fontsize=8,loc="lower left"); ax.grid(alpha=.3,which="both")
fig.tight_layout(); go(fig,"lowpass_response")

# 2. OnlineMeanVariance drift (data from structures_omv_drift.cpp, which runs the real class)
d=collections.defaultdict(list)
for r in csv.DictReader(open(os.path.join(HERE,"data","structures_omv_drift.csv"))):
    d[(r["type"],float(r["offset"]))].append((int(r["i"]),float(r["exact"]),float(r["online"])))
fig,ax=plt.subplots(figsize=(9.5,4.8))
for (k,off),col in zip([("float",1000.0),("float",0.0),("double",1000.0)],[C["hl"],C["s2"],C["s1"]]):
    v=d[(k,off)]; i=np.array([a for a,_,_ in v]); e=np.array([abs(o-x)/x for _,x,o in v])
    ax.semilogy(i,np.maximum(e,1e-12),color=col,lw=1.6,label=f"OnlineMeanVariance<{k},100>, data = {off:g} + N(0, 0.01²)")
ax.axhline(0.01,color=C["aux"],ls=":",lw=.8); ax.text(1.0e4,0.013,"1 % error",fontsize=8,color=C["aux"])
ax.set_xlabel("number of samples pushed"); ax.set_ylabel("relative error of variance")
ax.set_title("Sliding-window Welford: accumulated rounding error (window N = 100)"); ax.legend(fontsize=8,loc="upper left",bbox_to_anchor=(0,-0.2),ncol=1); ax.grid(alpha=.3,which="both")
ax.set_ylim(1e-12,10); fig.tight_layout(); go(fig,"omv_drift")

# 3. Debouncer timeline (example from debouncer.hpp, 3 trues / 2 falses)
raw=[1,1,0,1,0,1,1,1,0,1,0,1,0,1,0,0,1,0,1,0,1,1,1,1,0,1]
st=False; cnt=0; init=0; F=[]; CERT=[]; CNT=[]
for r in raw:
    if init<3: init+=1
    if r==st: cnt=0
    else:
        cnt+=1
        if r and cnt>=3: st=True; cnt=0
        elif (not r) and cnt>=2: st=False; cnt=0
    F.append(int(st)); CERT.append(init>=3); CNT.append(cnt)
k=np.arange(1,len(raw)+1)
fig,ax=plt.subplots(figsize=(11,3.2))
ax.step(k,np.array(raw)+2.4,where="mid",color=C["aux"],lw=1.5); ax.text(0.2,2.9,"raw",ha="right",fontsize=9)
ax.step(k,np.array(F)+.9,where="mid",color=C["s1"],lw=2.2); ax.text(0.2,1.4,"filtered",ha="right",fontsize=9)
for i,(c,cert) in enumerate(zip(CNT,CERT)):
    ax.text(k[i],.35,str(c),ha="center",fontsize=8,color=C["s2"])
    ax.plot(k[i],-.15,"s",ms=6,color=C["pt"] if cert else "white",mec=C["pt"])
ax.text(0.2,.35,"count",ha="right",fontsize=9,color=C["s2"]); ax.text(0.2,-.15,"IsCertain",ha="right",va="center",fontsize=9,color=C["pt"])
ax.set_yticks([]); ax.set_xticks(k); ax.set_xlim(-2.2,len(raw)+.8); ax.set_ylim(-.5,3.7); ax.set_xlabel("reading number")
for s in ("left","right","top"): ax.spines[s].set_visible(False)
ax.set_title("Debouncer(3, 2): 3 consecutive trues to switch on, 2 consecutive falses to switch off",loc="left")
go(fig,"debouncer_timeline")
print("ok")
