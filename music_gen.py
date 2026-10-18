import numpy as np, json, sys
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile
SR=44100
R=sys.argv[1]; INFO=json.load(open(f"r{R}_info.json"))
DUR=INFO["dur"]+0.0; N=int(SR*DUR); BEAT=0.45; BAR=BEAT*4
rng=np.random.default_rng(100+int(R))
def t_(n): return np.arange(n) / SR
def idx(t): return int(round(t * SR))
def note(n): return 440.0 * 2 ** ((n - 69) / 12)        # midi -> Hz
def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], 'band', fs=SR, output='sos'), x)

def add(sig, t, gain=1.0, pan=0.0, side=None):
    i = idx(t)
    if i >= N: return
    sig = sig[: N - i] * gain
    gl = np.cos((pan + 1) * np.pi / 4); gr = np.sin((pan + 1) * np.pi / 4)
    if side is None:
        L[i:i + len(sig)] += sig * gl * 1.414 / 2 * 2 ** .5
        R[i:i + len(sig)] += sig * gr * 1.414 / 2 * 2 ** .5
    else:
        side.append((i, sig, gl, gr))

# ---------- instruments ----------
def kick():
    n = int(.42 * SR); tt = t_(n)
    f = 46 + 110 * np.exp(-tt * 38)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-tt * 7.5)
    click = hp(rng.standard_normal(n), 2500) * np.exp(-tt * 260) * .35
    return np.tanh((body + click) * 1.6) * .68

def clap():
    n = int(.35 * SR); tt = t_(n)
    nz = bp(rng.standard_normal(n), 900, 5200)
    env = np.zeros(n)
    for k, o in enumerate([0, .011, .022, .034]):
        s = idx(o); env[s:] += np.exp(-(tt[: n - s]) * (90 if k < 3 else 16))
    return nz * env * .8

def hat(open_=False):
    n = int((.32 if open_ else .07) * SR); tt = t_(n)
    nz = hp(rng.standard_normal(n), 7500, 4)
    return nz * np.exp(-tt * (11 if open_ else 70)) * (.32 if open_ else .26)

def saw(f, n, detune=0.0, maxf=6000):
    """band-limited sawtooth (additive), no aliasing"""
    tt = t_(n); f = f * (1 + detune); x = np.zeros(n)
    ph0 = rng.uniform(0, 2 * np.pi)
    for k in range(1, int(min(maxf, SR / 2.2) // f) + 1):
        x += ((-1) ** (k + 1)) * np.sin(2 * np.pi * k * f * tt + k * ph0) / k
    return x * (2 / np.pi)

def sq(f, n, maxf=6000):
    tt = t_(n); x = np.zeros(n)
    for k in range(1, int(min(maxf, SR / 2.2) // f) + 1, 2):
        x += np.sin(2 * np.pi * k * f * tt) / k
    return x * (4 / np.pi)

def bass(midi, length):
    n = int(length * SR); tt = t_(n)
    f = note(midi)
    x = saw(f, n, maxf=2500) * .6 + np.sin(2 * np.pi * f * tt) * .7
    x = lp(x, 900) * np.minimum(1, tt / .004) * np.exp(-tt * 3.5)
    return np.tanh(x * 1.4) * .4

def pad(midis, length):
    n = int(length * SR); tt = t_(n); x = np.zeros(n)
    for m in midis:
        for d in (-.012, -.005, 0, .006, .013):
            x += saw(note(m), n, d, maxf=4500)
    x = lp(x / (len(midis) * 5), 2600)
    env = np.minimum(1, tt / .05) * np.minimum(1, (length - tt) / .12)
    return x * env * .55

def pluck(midi, length=.22):
    n = int(length * SR); tt = t_(n); f = note(midi)
    x = (saw(f, n, maxf=9000) * .5 + sq(f, n, maxf=9000) * .25)
    cut = 1200 + 5200 * np.exp(-tt * 18)
    y = np.zeros(n); a = 0.0                       # time-varying one-pole lowpass
    for i in range(n):
        c = 1 - np.exp(-2 * np.pi * cut[i] / SR); a += c * (x[i] - a); y[i] = a
    return y * np.exp(-tt * 9) * .5

def riser(length):
    n = int(length * SR); tt = t_(n); p = tt / length
    nz = rng.standard_normal(n); out = np.zeros(n); seg = int(.02 * SR)
    for s in range(0, n, seg):                      # sweep a bandpass upward
        fc = 400 + 7000 * p[s] ** 2
        out[s:s + seg] = bp(nz[max(0, s - 2048):s + seg], fc * .7, min(fc * 1.4, 19000))[-len(out[s:s + seg]):]
    sweep = np.sin(2 * np.pi * np.cumsum(220 + 1600 * p ** 2) / SR) * .25
    return (out * .5 + sweep) * p ** 1.6

def whoosh(length=.45, up=True):
    n = int(length * SR); tt = t_(n); p = tt / length
    nz = rng.standard_normal(n); out = np.zeros(n); seg = int(.015 * SR)
    for s in range(0, n, seg):
        fc = (500 + 5000 * p[s]) if up else (5500 - 5000 * p[s])
        out[s:s + seg] = bp(nz[max(0, s - 2048):s + seg], fc * .6, min(fc * 1.6, 19000))[-len(out[s:s + seg]):]
    return out * np.sin(np.pi * p) ** 1.5 * .55

def impact():
    n = int(1.6 * SR); tt = t_(n)
    f = 30 + 70 * np.exp(-tt * 9)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 2.6)
    crash = hp(rng.standard_normal(n), 3000) * np.exp(-tt * 2.2) * .35
    return np.tanh(boom * 1.8) * .85 + crash

def ding():
    n = int(.9 * SR); tt = t_(n); x = np.zeros(n)
    for f, a, d in ((1318.5, 1, 5), (1975.5, .55, 6.5), (2637, .25, 9), (3950, .12, 12)):
        x += a * np.sin(2 * np.pi * f * tt) * np.exp(-tt * d)
    x2 = np.zeros(n); s = idx(.09)
    for f, a, d in ((1760, 1, 5), (2637, .5, 7)):
        x2[s:] += a * np.sin(2 * np.pi * f * tt[: n - s]) * np.exp(-tt[: n - s] * d)
    return (x * .5 + x2 * .55) * .3

def tap():
    n = int(.12 * SR); tt = t_(n)
    return (np.sin(2 * np.pi * 1900 * tt) * np.exp(-tt * 60) * .5 + hp(rng.standard_normal(n), 3000) * np.exp(-tt * 300) * .4) * .6

def pop():
    n = int(.16 * SR); tt = t_(n); f = 500 + 1400 * tt / .16
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 28) * .45



def tick():
    n=int(.09*SR); tt=t_(n); return np.sin(2*np.pi*2400*tt)*np.exp(-tt*55)*.35
def typing(length=1.2):
    n=int(length*SR); out=np.zeros(n)
    for k in range(int(length*14)):
        s=idx(k/14+rng.uniform(0,.02)); m=min(int(.03*SR),n-s)
        if m>0: out[s:s+m]+=hp(rng.standard_normal(m),2500)*np.exp(-t_(m)*160)*.25
    return out
def click():
    n=int(.06*SR); tt=t_(n); return hp(rng.standard_normal(n),1500)*np.exp(-tt*200)*.5
def buzz():
    n=int(.35*SR); tt=t_(n); return np.sign(np.sin(2*np.pi*110*tt))*.12*np.exp(-tt*6)*(np.sin(2*np.pi*14*tt)>0)
PROGS=[[([60,64,67],36),([57,60,64],33),([53,57,60],41),([55,59,62],43)],   # C Am F G
       [([62,65,69],38),([58,62,65],34),([53,57,60],41),([60,64,67],36)],   # Dm Bb F C
       [([64,67,71],40),([60,64,67],36),([55,59,62],43),([62,66,69],38)],   # Em C G D
       [([57,60,64],45),([53,57,60],41),([60,64,67],36),([55,59,62],43)]]   # Am F C G
prog=PROGS[INFO["prog"]]; REV=INFO["reveal"]
music=[]; Kk=kick(); C=clap(); H=hat(); HO=hat(True); kicks=[]
nbeats=int(np.ceil(DUR/BEAT))
for q in range(nbeats):
    tb=q*BEAT
    if tb>=DUR-.05: break
    full=tb>=REV-1e-6
    rel=(tb-REV) if full else tb+2*BEAT
    bar=int(np.floor(rel/BAR+1e-6)); qb=int(round((rel-bar*BAR)/BEAT))%4
    ch,root=prog[bar%4]
    if full or qb in (0,2): music.append((tb,Kk,1.0 if full else .7,0,False)); kicks.append(tb)
    if full and qb in (1,3): music.append((tb,C,.85,0,False))
    for e in range(4):
        th=tb+e*BEAT/4
        if e==2: music.append((th,HO if (full and qb==3) else H,.85,.25,False))
        elif full or e%2==0: music.append((th,H,.4 if e%2 else .55,-.2,False))
    for e in (0,2):
        music.append((tb+e*BEAT/4,bass(root+(12 if e==2 else 0),BEAT/2*.95),.8 if full else .5,0,True))
    if qb==0:
        L_=BAR if full else min(BAR,max(BEAT,REV-tb))
        music.append((tb,pad(ch,L_),.9 if full else .55,0,True))
        if full:
            arp=[ch[0]+12,ch[1]+12,ch[2]+12,ch[1]+24,ch[2]+12,ch[0]+24,ch[2]+12,ch[1]+12]
            for s_ in range(16):
                ts=tb+s_*BEAT/4
                if ts<DUR-.4: music.append((ts,pluck(arp[s_%8]),.7,.35 if s_%2 else -.35,True))
music.append((0,pad(prog[3][0],2*BEAT),.5,0,True))
for k in range(8): music.append((REV-BEAT*2+k*BEAT/4,C*(.22+.08*k),1,0,False))
DL=np.zeros(N);DR=np.zeros(N);ML=np.zeros(N);MR=np.zeros(N)
def put(t,sig,g,pan,dk):
    i=idx(t)
    if i>=N or i<0: return
    s=sig[:N-i]*g; gl=np.cos((pan+1)*np.pi/4)*2**.5; gr=np.sin((pan+1)*np.pi/4)*2**.5
    if dk: ML[i:i+len(s)]+=s*gl; MR[i:i+len(s)]+=s*gr
    else: DL[i:i+len(s)]+=s*gl; DR[i:i+len(s)]+=s*gr
for m in music: put(*m)
sc=np.ones(N)
for tk in kicks:
    i=idx(tk); n=min(int(BEAT*SR),N-i)
    if n<=0: continue
    sc[i:i+n]=np.minimum(sc[i:i+n],1-.55*np.exp(-t_(n)*9))
ML*=sc; MR*=sc
irn=int(1.4*SR); ti=t_(irn)
irL=lp(rng.standard_normal(irn)*np.exp(-ti*3.2),6000); irR=lp(rng.standard_normal(irn)*np.exp(-ti*3.2),6000)
irL/=np.sqrt((irL**2).sum()); irR/=np.sqrt((irR**2).sum())
L=hp(DL+ML+fftconvolve(ML,irL)[:N]*.25,32); R_=hp(DR+MR+fftconvolve(MR,irR)[:N]*.25,32)
FX={'impact':(impact,.55),'pop':(pop,.6),'whoosh':(lambda:whoosh(.45),.55),'tap':(tap,1.0),'ding':(ding,.8),'riser':(lambda:riser(.6),.8),
    'tick':(tick,.8),'type':(lambda:typing(1.2),.7),'click':(click,.8),'buzz':(buzz,.6)}
for i,(name,t) in enumerate(INFO["sfx"]):
    f,g=FX[name]; sig=f(); pan=(-.25 if i%2 else .25) if name in('pop','whoosh') else 0
    if name=='impact' and t<.05: g=.75
    j=idx(t)
    if j>=N: continue
    s=sig[:N-j]*g; gl=np.cos((pan+1)*np.pi/4)*2**.5; gr=np.sin((pan+1)*np.pi/4)*2**.5
    L[j:j+len(s)]+=s*gl; R_[j:j+len(s)]+=s*gr
fade=np.ones(N); fs=idx(DUR-1.0); fade[fs:]=np.linspace(1,0,N-fs)**1.5
L*=fade; R_*=fade
pk=max(np.abs(L).max(),np.abs(R_).max())
L=np.tanh(L/pk*1.25)*.9; R_=np.tanh(R_/pk*1.25)*.9
wavfile.write(f"r{R}_music.wav",SR,(np.stack([L,R_],1)*32767).astype(np.int16)); print('ok',R,DUR)
