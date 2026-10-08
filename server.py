r"""Local sentence-loop video player. Run with .venv\Scripts\python server.py."""
import json
import logging
import os
import re
import tempfile
import sys
import threading
import uuid
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODEL_CACHE = (Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'Gengju' / 'models'
               if getattr(sys, 'frozen', False) else ROOT / '.models')
# Use ordinary HTTPS downloads; avoids Xet transfer stalls on some Windows networks.
os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING', '1')
os.environ.setdefault('HF_HUB_DOWNLOAD_TIMEOUT', '60')
JOBS = {}
LOCK = threading.Lock()
MODEL = None
MODEL_LOCK = threading.Lock()


def sentence_chunks(segments):
    """Group timestamped words at punctuation, long pauses, or a length limit."""
    result, words = [], []

    def flush():
        if words:
            result.append(dict(start=round(words[0].start, 3),
                               end=round(words[-1].end, 3),
                               text=''.join(w.word for w in words).strip()))
            words.clear()

    for segment in segments:
        for word in segment.words or []:
            if words and word.start - words[-1].end > 0.8:
                flush()
            words.append(word)
            if re.search(r'[.!?]["\u201d\u2019]*$', word.word.strip()) or len(words) >= 30:
                flush()
    flush()
    return result


def transcribe(job_id, path):
    global MODEL
    try:
        with MODEL_LOCK:
            JOBS[job_id].update(message='正在加载英文识别模型…', progress=None)
            if MODEL is None:
                from faster_whisper import WhisperModel
                model_source = str(ROOT / 'model') if (ROOT / 'model' / 'model.bin').exists() else 'base.en'
                MODEL = WhisperModel(model_source, device='cpu', compute_type='int8',
                                     download_root=str(MODEL_CACHE))
            JOBS[job_id]['message'] = '正在识别英文并生成句子时间戳…'
            segments, info = MODEL.transcribe(path, language='en', word_timestamps=True,
                                              vad_filter=True, beam_size=5)
            collected = []
            for segment in segments:
                collected.append(segment)
                JOBS[job_id].update(message=f'正在识别：{segment.end:.0f} / {info.duration:.0f} 秒',
                                    progress=min(99, round(segment.end / max(info.duration, .001) * 100)))
            JOBS[job_id].update(status='done', sentences=sentence_chunks(collected), message='识别完成', progress=100)
    except Exception as exc:
        JOBS[job_id].update(status='error', message=f'识别失败：{exc}')
    finally:
        Path(path).unlink(missing_ok=True)
        LOCK.release()


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        logging.getLogger('gengju.http').info(format, *args)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'web'), **kwargs)

    def json_response(self, value, status=200):
        body = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/api/health':
            return self.json_response({'app': 'Flow'})
        if self.path.startswith('/api/jobs/'):
            job = JOBS.get(self.path.rsplit('/', 1)[-1])
            return self.json_response(job or {'message': '任务不存在'}, 200 if job else 404)
        return super().do_GET()

    def do_POST(self):
        if self.path != '/api/transcribe':
            return self.json_response({'message': '不存在的接口'}, 404)
        port = self.server.server_port
        if self.headers.get('Origin') not in (None, f'http://127.0.0.1:{port}', f'http://localhost:{port}'):
            return self.json_response({'message': '仅允许本地页面请求'}, 403)
        length = int(self.headers.get('Content-Length', '0'))
        if length <= 0 or length > 2 * 1024**3:
            return self.json_response({'message': '请选择小于 2 GB 的视频'}, 400)
        if not LOCK.acquire(blocking=False):
            return self.json_response({'message': '已有视频正在识别，请稍后重试'}, 409)
        path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.media') as f:
                path = f.name
                remaining = length
                while remaining:
                    chunk = self.rfile.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ValueError('上传中断')
                    f.write(chunk)
                    remaining -= len(chunk)
            job_id = uuid.uuid4().hex
            JOBS[job_id] = {'status': 'running', 'message': '视频已接收，准备识别…', 'progress': None}
            threading.Thread(target=transcribe, args=(job_id, path), daemon=True).start()
            return self.json_response({'id': job_id}, 202)
        except Exception as exc:
            if path:
                Path(path).unlink(missing_ok=True)
            LOCK.release()
            return self.json_response({'message': str(exc)}, 400)


if __name__ == '__main__':
    os.chdir(ROOT)
    print('Flow · http://127.0.0.1:8765', flush=True)
    httpd = ThreadingHTTPServer(('127.0.0.1', 8765), Handler)
    if '--open' in sys.argv:
        webbrowser.open('http://127.0.0.1:8765')
    httpd.serve_forever()
