const $ = id => document.getElementById(id);
const video = $('video');
let sentences = [], current = -1, file = null, blobURL = null;
let practising = false, timer = null, generation = 0, mediaGeneration = 0;
const status = message => $('status').textContent = message;
const seconds = text => text.trim().replace(',', '.').split(':').reduce((n, x) => n * 60 + Number(x), 0);
const stamp = n => { const ms = Math.round(n * 1000); return `${String(Math.floor(ms / 3600000)).padStart(2,'0')}:${String(Math.floor(ms / 60000) % 60).padStart(2,'0')}:${String(Math.floor(ms / 1000) % 60).padStart(2,'0')},${String(ms % 1000).padStart(3,'0')}`; };

function validate(items) {
  if (!Array.isArray(items)) throw new Error('字幕数据必须是句子数组');
  return items.map(s => ({start:Number(s.start), end:Number(s.end), text:String(s.text || '').trim()}))
    .filter(s => Number.isFinite(s.start) && Number.isFinite(s.end) && s.start >= 0 && s.end > s.start)
    .sort((a,b) => a.start - b.start);
}
function parseSubtitles(text) {
  const items = [];
  for (const block of text.replace(/\r/g, '').split(/\n\s*\n/)) {
    const lines = block.split('\n');
    const i = lines.findIndex(line => line.includes('-->'));
    if (i < 0) continue;
    const match = lines[i].match(/([\d:. ,]+)\s*-->\s*([\d:.,]+)/);
    if (!match) continue;
    items.push({start:seconds(match[1]), end:seconds(match[2]), text:lines.slice(i+1).join(' ').replace(/<[^>]*>/g,'').trim()});
  }
  return validate(items);
}
function stop() {
  practising = false; generation++; clearTimeout(timer); timer = null;
  video.pause(); $('play').textContent = '↻ 重播';
}
function render() {
  $('count').textContent = `${sentences.length} 句`;
  $('list').replaceChildren();
  if (!sentences.length) {
    const empty = document.createElement('div'); empty.className = 'list-empty';
    empty.textContent = '导入字幕或自动识别后，点击任意一句开始跟读。'; $('list').append(empty);
  }
  sentences.forEach((s,i) => {
    const button = document.createElement('button');
    button.className = 'sentence' + (i === current ? ' active' : '');
    const number = document.createElement('span'); number.className = 'sentence-number'; number.textContent = String(i+1).padStart(2,'0');
    const small = document.createElement('small'); small.textContent = `${stamp(s.start).slice(3)} — ${stamp(s.end).slice(3)}`;
    const text = document.createElement('span'); text.className = 'sentence-copy'; text.textContent = s.text || '（手动添加的句子）';
    button.append(number,small,text); button.onclick = () => select(i,true); $('list').append(button);
  });
  const s = sentences[current];
  $('caption').textContent = s ? s.text || '（无字幕）' : '';
  $('editText').value = s?.text || ''; $('start').value = s?.start ?? ''; $('end').value = s?.end ?? '';
  for (const id of ['prev','next','save','split','merge','delete','export']) $(id).disabled = !s;
  $('play').disabled = !file; $('mediaToggle').disabled = !file;
  $('prev').disabled = current <= 0; $('next').disabled = current >= sentences.length-1;
  $('merge').disabled = !s || current >= sentences.length-1;
  const list = $('list'), active = list.querySelector('.active');
  if (active) {
    const row = active.getBoundingClientRect(), bounds = list.getBoundingClientRect();
    if (row.top < bounds.top) list.scrollTop -= bounds.top - row.top;
    else if (row.bottom > bounds.bottom) list.scrollTop += row.bottom - bounds.bottom;
  }
}
async function togglePlayback() {
  if (!file) return;
  if (!video.paused || timer) { stop(); return; }
  const s = sentences[current];
  if (s && (video.currentTime < s.start || video.currentTime >= s.end - .025)) { await playSentence(); return; }
  practising = !!s; generation++; clearTimeout(timer); timer=null;
  try { video.playbackRate=Number($('rate').value); await video.play(); }
  catch(e) { stop(); status(`无法播放：${e.message}`); }
}
function showRecognitionProgress(value, message) {
  $('recognitionProgress').hidden=false;
  $('progressLabel').textContent=message;
  if (Number.isFinite(value)) { $('progressBar').value=value; $('progressPercent').textContent=`${value}%`; }
  else { $('progressBar').removeAttribute('value'); $('progressPercent').textContent='处理中'; }
}
function select(index, autoplay=false) {
  stop(); if (index < 0 || index >= sentences.length) return;
  current = index; render();
  if (file) video.currentTime = Math.min(sentences[index].start, video.duration || Infinity);
  if (autoplay) playSentence();
}
async function playSentence() {
  stop(); const s = sentences[current];
  if (!file) { status('请先导入视频。'); return; }
  if (!Number.isFinite(video.duration)) { status('视频尚未加载完成，或格式不受浏览器支持。'); return; }
  if (!s) {
    try {video.currentTime=0;video.playbackRate=Number($('rate').value);await video.play();status('正在播放视频；生成句子后可逐句跟读。');}
    catch(e){status(`无法播放：${e.message}`);}
    return;
  }
  if (s.start >= video.duration) { status('本句起点超出视频长度，请检查字幕是否与视频匹配。'); return; }
  practising = true; const token = generation;
  status('正在播放本句…');
  try {
    // Wait for the seek before resuming, so the previous frame cannot trigger the end boundary.
    if (Math.abs(video.currentTime - s.start) > .015) {
      await new Promise((resolve,reject) => {
        const timeout = setTimeout(() => { cleanup(); reject(new Error('视频定位超时')); }, 5000);
        function cleanup(){clearTimeout(timeout);video.removeEventListener('seeked',done);}
        function done(){cleanup();resolve();}
        video.addEventListener('seeked',done,{once:true}); video.currentTime = s.start;
      });
    }
    if (!practising || token !== generation) return;
    video.playbackRate = Number($('rate').value); await video.play();
  } catch(e) { if (token === generation) {stop();status(`无法播放：${e.message}`);} }
}
function boundary() {
  const s = sentences[current];
  if (practising && s && !video.paused && video.currentTime >= Math.min(s.end,video.duration) - .025) {
    video.pause();
    video.currentTime = Math.min(s.end,video.duration);
    if (!$('loop').checked) {stop();status('本句播放完成。');}
    else {
      const gap = $('gap').value === 'sentence' ? (s.end-s.start)/video.playbackRate : Number($('gap').value);
      status(gap ? `留白 ${gap.toFixed(1)} 秒，轮到你跟读…` : '循环播放本句…');
      const token = generation;
      timer = setTimeout(() => {if (practising && generation === token) {status('正在循环本句…');playSentence();}},gap*1000);
    }
  }
  requestAnimationFrame(boundary);
}
video.addEventListener('ended', () => {
  if (practising && !timer) {
    if ($('loop').checked) {
      const s = sentences[current]; const gap = $('gap').value === 'sentence' ? (s.end-s.start)/video.playbackRate : Number($('gap').value);
      const token = generation; timer = setTimeout(() => {if(practising && token===generation) playSentence();},gap*1000);
    } else stop();
  }
});
video.addEventListener('error',()=>status('浏览器无法播放这个视频格式。请使用 MP4（H.264）或 WebM。'));
$('videoFile').onchange = () => {
  const selected = $('videoFile').files[0]; if (!selected) return;
  stop(); mediaGeneration++; sentences=[];current=-1;file=selected;
  if(blobURL) URL.revokeObjectURL(blobURL); blobURL=URL.createObjectURL(file);video.src=blobURL;
  $('empty').hidden=true; $('filename').textContent=file.name; $('importFilename').textContent=file.name; $('auto').disabled=false;
  $('recognitionProgress').hidden=true; $('finishImport').disabled=false; $('finishImport').textContent='返回播放器';
  status('视频已导入。点击“生成英文字幕 / 分句”，或导入已有字幕。'); render();
  $('videoFile').value='';
};
$('subtitleFile').onchange = async () => {
  const selected = $('subtitleFile').files[0];if(!selected)return;
  try {
    const text = await selected.text();
    const items = selected.name.toLowerCase().endsWith('.json') ? validate(JSON.parse(text)) : parseSubtitles(text);
    if(!items.length)throw new Error('没有找到有效时间戳；支持 SRT、VTT 或本工具导出的 JSON');
    stop();sentences=items;current=0;render();select(0);status(`已导入 ${items.length} 个字幕片段；跨句或半句可手动拆分、合并。`);
    showRecognitionProgress(100,`字幕已导入 · ${items.length} 句`); $('finishImport').textContent='完成，开始学习';
  } catch(e){status(`导入失败：${e.message}`);}
  $('subtitleFile').value='';
};
$('auto').onclick = async () => {
  if(!file)return; const originalFile=file, version=mediaGeneration; $('auto').disabled=true;
  stop(); $('videoFile').disabled=true; $('subtitleFile').disabled=true; $('finishImport').disabled=true;
  try {
    showRecognitionProgress(null,'正在准备视频…');
    status('正在将视频交给本机识别程序…');
    const response=await fetch('/api/transcribe',{method:'POST',body:originalFile});const data=await response.json();
    if(!response.ok)throw new Error(data.message);
    while(true){
      await new Promise(resolve=>setTimeout(resolve,1500));
      const r=await fetch(`/api/jobs/${data.id}`); const job=await r.json();
      if(version!==mediaGeneration)return;
      status(job.message);
      showRecognitionProgress(job.progress,job.message);
      if(!r.ok || job.status==='error')throw new Error(job.message);
      if(job.status==='done'){
        stop();sentences=validate(job.sentences);current=sentences.length?0:-1;render();
        if(current>=0)select(0);
        status(sentences.length?`已生成 ${sentences.length} 句。可逐句循环，也可以调整字幕和边界。`:'没有识别到英文语音；可导入字幕或手动添加句子。');break;
      }
    }
    showRecognitionProgress(100,sentences.length?`生成完成 · ${sentences.length} 句`:'识别完成 · 未找到英文语音');
    $('finishImport').textContent=sentences.length?'完成，开始学习':'返回播放器';
  }catch(e){if(version===mediaGeneration){status(`${e.message}。仍可导入字幕或手动分句。`);$('progressLabel').textContent='生成失败，请重试';$('progressPercent').textContent='';$('progressBar').value=0;}}
  finally{if(version===mediaGeneration){$('auto').disabled=false;$('videoFile').disabled=false;$('subtitleFile').disabled=false;$('finishImport').disabled=false;}}
};
$('play').onclick=playSentence;
$('prev').onclick=()=>select(current-1,true);$('next').onclick=()=>select(current+1,true);
$('rate').onchange=()=>{video.playbackRate=Number($('rate').value);$('mediaRate').value=$('rate').value;};
$('hide').onchange=()=>$('caption').classList.toggle('hidden',$('hide').checked);
$('markStart').onclick=()=>$('start').value=video.currentTime.toFixed(2);
$('markEnd').onclick=()=>$('end').value=video.currentTime.toFixed(2);
function editValues(){
  const start=Number($('start').value),end=Number($('end').value);
  if(!$('start').value || !$('end').value || !Number.isFinite(start)||!Number.isFinite(end)||start<0||end<=start || (Number.isFinite(video.duration)&&end>video.duration+.05))throw new Error('请输入有效起止时间：终点大于起点，并在视频长度内。');
  return {start,end,text:$('editText').value.trim()};
}
$('save').onclick=()=>{try{const s=editValues();stop();sentences[current]=s;render();status('本句已保存。');}catch(e){status(e.message);}};
$('add').onclick=()=>{try{const s=editValues();stop();sentences.push(s);sentences.sort((a,b)=>a.start-b.start);current=sentences.indexOf(s);render();status('新句子已添加。');}catch(e){status(e.message);}};
$('split').onclick=()=>{const s=sentences[current],t=video.currentTime;if(!s||t<=s.start+.05||t>=s.end-.05){status('请把播放位置移到当前句内部，再拆句。');return;}stop();sentences.splice(current,1,{...s,end:t},{start:t,end:s.end,text:''});render();status('已拆为两句，请分别编辑文字。');};
$('merge').onclick=()=>{if(current<0||current>=sentences.length-1)return;stop();const a=sentences[current],b=sentences[current+1];sentences.splice(current,2,{start:Math.min(a.start,b.start),end:Math.max(a.end,b.end),text:`${a.text} ${b.text}`.trim()});render();};
$('delete').onclick=()=>{if(current<0)return;stop();sentences.splice(current,1);current=Math.min(current,sentences.length-1);render();};
$('export').onclick=async()=>{
  const text=sentences.map((s,i)=>`${i+1}\n${stamp(s.start)} --> ${stamp(s.end)}\n${s.text}\n`).join('\n');
  if (window.pywebview?.api) {
    try {
      const result = await window.pywebview.api.save_subtitles(text,(file?.name.replace(/\.[^.]+$/,'')||'跟读字幕')+'.srt');
      status(result.saved ? `字幕已保存：${result.path}` : '已取消保存字幕。');
    } catch (e) {status(`字幕保存失败：${e.message}`);}
    return;
  }
  const url=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=(file?.name.replace(/\.[^.]+$/,'')||'跟读字幕')+'.srt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);status('已导出 SRT 字幕。下次导入同一视频和字幕即可继续。');
};
document.addEventListener('keydown',e=>{if(['INPUT','TEXTAREA','SELECT','BUTTON','VIDEO'].includes(e.target.tagName))return;if(e.code==='Space'){e.preventDefault();togglePlayback();}else if(e.key==='ArrowLeft'){e.preventDefault();select(current-1,true);}else if(e.key==='ArrowRight'){e.preventDefault();select(current+1,true);}else if(e.key.toLowerCase()==='r')playSentence();});
render();requestAnimationFrame(boundary);
