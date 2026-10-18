import asyncio
from playwright.async_api import async_playwright
names={1:'reel-avaliacoes-num-toque',2:'reel-3-erros-google',3:'reel-antes-depois-site',4:'reel-um-cartao-para-cada-rede'}
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':1080,'height':1920})
        for k,n in names.items():
            await pg.goto(f'file:///tmp/claude-0/-home-claude/1cf4490a-d3ff-512d-adb5-79ff9d56e2a2/scratchpad/reels/cover{k}.html')
            await pg.evaluate("document.fonts.ready"); await pg.evaluate("Promise.all([...document.images].map(i=>i.decode().catch(()=>0)))")
            await pg.screenshot(path=f'out/capa-{n}.png')
        await b.close()
asyncio.run(main())
