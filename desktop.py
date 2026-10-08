"""Windows desktop entry point, including a packaged-runtime integration check."""
import ctypes
import json
import logging
import os
import sys
import threading
import time
import traceback
import urllib.request
from pathlib import Path
from http.server import ThreadingHTTPServer

import webview
import server

DATA = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'Gengju'
DATA.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=str(DATA / 'desktop.log'), level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s', encoding='utf-8')


class NativeAPI:
    def __init__(self):
        self._window = None

    def save_subtitles(self, text, name):
        paths = self._window.create_file_dialog(webview.FileDialog.SAVE,
                                               save_filename=Path(name).name,
                                               file_types=('SRT subtitles (*.srt)',))
        if not paths:
            return {'saved': False}
        path = Path(paths[0]).with_suffix('.srt')
        path.write_text(text, encoding='utf-8')
        return {'saved': True, 'path': str(path)}


def main():
    checking = '--self-test' in sys.argv
    report_path = Path(sys.argv[sys.argv.index('--self-test')+1]).resolve() if checking else None
    # Each window owns its service; it stops when the desktop app exits.
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
    base_url = f'http://127.0.0.1:{httpd.server_port}'
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    bridge = NativeAPI()
    window = webview.create_window('Flow', base_url, js_api=bridge,
                                   width=1240, height=900, min_size=(900,650),
                                   background_color='#0b0b0d', text_select=True,
                                   hidden=False)
    bridge._window = window

    def check_runtime():
        report = {'ok': False}
        try:
            logging.info('Self-test: waiting for window load')
            if not window.events.loaded.wait(30):
                raise RuntimeError('桌面窗口加载超时')
            logging.info('Self-test: evaluating window title')
            report['title'] = window.evaluate_js('document.title')
            logging.info('Self-test: title %s', report['title'])
            assert report['title'] == 'Flow', report
            # Exercise decoding, automatic speech recognition and the packaged model without a network download.
            sample = server.ROOT / 'sample.mp4'
            request = urllib.request.Request(base_url+'/api/transcribe', data=sample.read_bytes(),
                                              headers={'Content-Type':'application/octet-stream', 'Origin':base_url})
            job_id = json.load(urllib.request.urlopen(request, timeout=30))['id']
            deadline = time.monotonic()+180
            while time.monotonic() < deadline:
                job = json.load(urllib.request.urlopen(base_url+'/api/jobs/'+job_id))
                if job['status'] != 'running':
                    break
                time.sleep(.25)
            assert job['status'] == 'done', job
            assert len(job['sentences']) == 4, job
            assert job['progress'] == 100, job
            report['sentences'] = job['sentences']
            # Load a sample through the same file-input handler used by the user.
            import base64
            encoded = base64.b64encode(sample.read_bytes()).decode('ascii')
            js = """(() => {
              const bytes = Uint8Array.from(atob(ENCODED), c => c.charCodeAt(0));
              const transfer = new DataTransfer(); transfer.items.add(new File([bytes], 'sample.mp4', {type:'video/mp4'}));
              const input = document.getElementById('videoFile'); input.files = transfer.files; input.dispatchEvent(new Event('change'));
              sentences = SENTENCES; current = 1; render(); document.getElementById('loop').checked = false;
              return document.getElementById('count').textContent;
            })()""".replace('ENCODED',json.dumps(encoded)).replace('SENTENCES',json.dumps(job['sentences']))
            report['count'] = window.evaluate_js(js)
            deadline = time.monotonic()+15
            while time.monotonic()<deadline:
                if window.evaluate_js('Number.isFinite(document.getElementById("video").duration)'):
                    break
                time.sleep(.1)
            assert window.evaluate_js('Number.isFinite(document.getElementById("video").duration)'), 'MP4 decoding failed'
            layout = window.evaluate_js("""(() => {
              const stage = document.getElementById('stage'), caption = document.getElementById('caption');
              const play = document.getElementById('play');
              return {text:caption.textContent, outsideVideo:!stage.contains(caption),
                stageBottom:stage.getBoundingClientRect().bottom, captionTop:caption.getBoundingClientRect().top,
                captionBottom:caption.getBoundingClientRect().bottom, playTop:play.getBoundingClientRect().top,
                playBottom:play.getBoundingClientRect().bottom, height:innerHeight,
                pageHeight:document.documentElement.scrollHeight};
            })()""")
            assert layout['text'] == job['sentences'][1]['text'], layout
            assert layout['outsideVideo'] and layout['stageBottom'] <= layout['captionTop'] and layout['captionBottom'] <= layout['playTop'], layout
            assert layout['playBottom'] <= layout['height'] and layout['pageHeight'] <= layout['height']+1, layout
            report['layout'] = layout
            window.evaluate_js("document.getElementById('play').click(); 'started'")
            time.sleep(.7)
            before = window.evaluate_js('document.getElementById("video").currentTime')
            window.evaluate_js("document.getElementById('play').click(); 'replayed'")
            time.sleep(.15)
            after = window.evaluate_js('document.getElementById("video").currentTime')
            assert after < before and abs(after-job['sentences'][1]['start']) < .45, (before,after)
            report['replay'] = {'before':before,'after':after}
            window.evaluate_js("document.getElementById('settingsButton').click(); 'opened'")
            assert window.evaluate_js('document.getElementById("settingsDialog").open'), 'Settings did not open'
            window.evaluate_js("document.getElementById('closeSettings').click(); 'closed'")
            assert not window.evaluate_js('document.getElementById("settingsDialog").open'), 'Settings did not close'
            time.sleep(4)
            state = window.evaluate_js("({paused:document.getElementById('video').paused,time:document.getElementById('video').currentTime,status:document.getElementById('status').textContent})")
            report['playback'] = state
            assert state['paused'] and abs(state['time']-job['sentences'][1]['end']) < .1, state
            window.evaluate_js("document.getElementById('mediaToggle').click(); 'started'")
            time.sleep(.5)
            window.evaluate_js("document.getElementById('mediaToggle').click(); 'paused'")
            paused_at = window.evaluate_js('document.getElementById("video").currentTime')
            time.sleep(.25)
            assert window.evaluate_js('document.getElementById("video").paused'), 'Pause control failed'
            assert abs(window.evaluate_js('document.getElementById("video").currentTime')-paused_at) < .05
            window.evaluate_js("document.getElementById('mediaToggle').click(); 'resumed'")
            time.sleep(.2)
            resumed_at = window.evaluate_js('document.getElementById("video").currentTime')
            assert resumed_at > paused_at, (paused_at, resumed_at)
            window.evaluate_js("document.getElementById('mediaRate').value='0.5';document.getElementById('mediaRate').dispatchEvent(new Event('change')); 'slowed'")
            assert window.evaluate_js('document.getElementById("video").playbackRate') == .5
            assert window.evaluate_js('document.getElementById("rate").value') == '0.5'
            window.evaluate_js("document.getElementById('rate').value='1.5';document.getElementById('rate').dispatchEvent(new Event('change')); stop(); 'sped up'")
            assert window.evaluate_js('document.getElementById("video").playbackRate') == 1.5
            assert window.evaluate_js('document.getElementById("mediaRate").value') == '1.5'
            report['mediaControls'] = {'pausedAt':paused_at,'resumedAt':resumed_at,'speedSync':True}
            window.evaluate_js("document.getElementById('settingsButton').click();document.getElementById('auto').click(); 'generating'")
            assert window.evaluate_js('document.getElementById("settingsDialog").contains(document.getElementById("videoFile"))'), 'Import is outside settings'
            deadline = time.monotonic()+60
            while time.monotonic()<deadline:
                if window.evaluate_js('!document.getElementById("auto").disabled'):
                    break
                time.sleep(.25)
            progress = window.evaluate_js("({value:document.getElementById('progressBar').value,label:document.getElementById('progressLabel').textContent,visible:!document.getElementById('recognitionProgress').hidden,count:document.getElementById('count').textContent})")
            assert progress['visible'] and progress['value'] == 100 and progress['count'] == '4 句', progress
            report['generationPanel'] = progress
            window.evaluate_js("document.getElementById('finishImport').click(); 'finished'")
            assert not window.evaluate_js('document.getElementById("settingsDialog").open'), 'Finish did not close panel'
            report['ok'] = True
        except Exception:
            report['error'] = traceback.format_exc()
        finally:
            report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            window.destroy()

    try:
        webview.start(check_runtime if checking else None, gui='edgechromium',
                      storage_path=str(DATA / 'WebView'), private_mode=False,
                      icon=str(server.ROOT / 'app.ico'))
    finally:
        httpd.shutdown()
        httpd.server_close()
    if checking and not json.loads(report_path.read_text(encoding='utf-8'))['ok']:
        raise SystemExit(1)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        logging.exception('Desktop startup failed')
        ctypes.windll.user32.MessageBoxW(None,
            'Flow 启动失败。详情见 %LOCALAPPDATA%\\Gengju\\desktop.log。\n请确认已安装 Microsoft Edge WebView2 Runtime。',
            'Flow', 0x10)
        raise
