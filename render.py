import asyncio, sys, subprocess, json
from playwright.async_api import async_playwright
r=sys.argv[1]; mode=sys.argv[2]  # 'check' times... or 'video' out
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':1080,'height':1920})
        await pg.goto(f'file://'+__import__('os').path.dirname(__import__('os').path.abspath(__file__))+'/reels.html?r={r}')
        await pg.evaluate("document.fonts.ready"); await pg.evaluate("Promise.all([...document.images].map(i=>i.decode().catch(()=>0)))")
        info=await pg.evaluate("build()"); dur=await pg.evaluate("DUR")
        json.dump({'dur':dur,**info},open(f'r{r}_info.json','w'))
        if mode=='check':
            for t in sys.argv[3:]:
                await pg.evaluate(f"frame({t})"); await pg.screenshot(path=f'chk/r{r}_{t}.png')
        else:
            FPS=30; n=int(round(dur*FPS)); out=sys.argv[3]
            ff=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','image2pipe','-framerate',str(FPS),'-c:v','png','-i','-','-c:v','libx264','-preset','slow','-crf','17','-pix_fmt','yuv420p','-profile:v','high','-r',str(FPS),out],stdin=subprocess.PIPE)
            for i in range(n):
                await pg.evaluate(f"frame({i/FPS})"); ff.stdin.write(await pg.screenshot(type='png'))
            ff.stdin.close(); ff.wait(); print(r,'frames',n,ff.returncode)
        await b.close()
asyncio.run(main())
