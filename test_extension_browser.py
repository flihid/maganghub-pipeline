"""Synthetic integration test on localhost with a temporary extension copy."""
import json
import tempfile
import time
import unittest
import shutil
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

EXT=Path(__file__).parent.joinpath('scraper_extension').resolve()
FIXTURE='''<!doctype html><html><body><main>
<input role="combobox"><article data-testid="tweet">
<a href="/synthetic_fixture/status/1000000000000000001"><time datetime="2026-09-10T01:00:00Z">fixture</time></a>
<div data-testid="tweetText" lang="in">Teks sintetis <img alt="😭"> bukan hasil penelitian.</div>
<button aria-label="0 Replies. Reply"></button><button aria-label="1 Like. Like"></button>
</article><div style="height:2000px"></div></main><script>
document.querySelector('input').value=new URLSearchParams(location.search).get('q')||'';
let added=false;addEventListener('scroll',()=>{if(added)return;added=true;
const a=document.querySelector('article').cloneNode(true);
a.querySelector('a').href='/synthetic_fixture/status/1000000000000000002';
a.querySelector('[data-testid="tweetText"]').textContent='Post kedua sintetis untuk pengujian.';
document.querySelector('main').appendChild(a);});
</script></body></html>'''


class BrowserExtensionTest(unittest.TestCase):
    def test_save_scroll_quota_and_restart(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                body=FIXTURE.encode('utf-8'); self.send_response(200)
                self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(body)))
                self.end_headers();self.wfile.write(body)
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        with tempfile.TemporaryDirectory() as test_root, sync_playwright() as p:
            ext=Path(test_root)/'extension';shutil.copytree(EXT,ext)
            manifest=json.loads((ext/'manifest.json').read_text(encoding='utf-8'))
            manifest['host_permissions']=['http://127.0.0.1/*']
            manifest['content_scripts'][0]['matches']=['http://127.0.0.1/*']
            (ext/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
            core=(ext/'core.js').read_text(encoding='utf-8').replace('https://x.com/search?',f'http://127.0.0.1:{server.server_port}/search?')
            (ext/'core.js').write_text(core,encoding='utf-8')
            profile=str(Path(test_root)/'profile')
            def launch():
                ctx=p.chromium.launch_persistent_context(profile,headless=True,channel='chromium',args=[
                    '--disable-extensions-except='+str(ext),'--load-extension='+str(ext)])
                ctx.set_default_timeout(5000)
                worker=ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event('serviceworker')
                return ctx,worker
            ctx,worker=launch()
            config=worker.evaluate('structuredClone(MagangHubCore.defaults)')
            config.update(phases=[{'name':'fase2_seleksi','since':'2026-09-10','until':'2026-09-11'}],
                          pilotPerPhase=2,maxPerDay=2,maxRaw=10,idleRounds=2,scrollDelayMs=5000)
            panel=ctx.new_page();panel.goto(worker.url.rsplit('/',1)[0]+'/panel.html')
            started=panel.evaluate('(config)=>chrome.runtime.sendMessage({type:"START",mode:"pilot",config})',config)
            self.assertTrue(started['ok'],started)
            def wait_count(page,count):
                deadline=time.monotonic()+30
                while time.monotonic()<deadline:
                    state=page.evaluate('chrome.runtime.sendMessage({type:"STATUS"})')['state']
                    if state.get('total')==count:return state
                    page.wait_for_timeout(250)
                self.fail(state)
            wait_count(panel,1)
            panel.evaluate('chrome.runtime.sendMessage({type:"STOP"})')
            exported=panel.evaluate('chrome.runtime.sendMessage({type:"EXPORT"})')['export']
            self.assertEqual(len(exported['posts']),1)
            self.assertIn('😭',exported['posts'][0]['text'])
            self.assertTrue(all(r['post_lang']=='in' for r in exported['posts']))
            ctx.close()
            ctx,worker=launch();panel=ctx.new_page();panel.goto(worker.url.rsplit('/',1)[0]+'/panel.html')
            exported=panel.evaluate('chrome.runtime.sendMessage({type:"EXPORT"})')['export']
            self.assertEqual(len(exported['posts']),1)
            panel.evaluate('chrome.runtime.sendMessage({type:"RESUME"})')
            wait_count(panel,2)
            exported=panel.evaluate('chrome.runtime.sendMessage({type:"EXPORT"})')['export']
            self.assertEqual(len(exported['posts']),2)
            self.assertEqual(exported['state']['counts']['fase2_seleksi'],2)
            panel.evaluate('chrome.runtime.sendMessage({type:"STOP"})')
            panel.evaluate('chrome.runtime.sendMessage({type:"RESUME"})')
            status=panel.evaluate('chrome.runtime.sendMessage({type:"STATUS"})')['state']
            self.assertEqual(status['status'],'job_list_finished')
            self.assertEqual(status['total'],2)
            ctx.close()


if __name__=='__main__':unittest.main()
