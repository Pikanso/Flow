// Cinematic controls share the sentence player state in app.js.
const timeline = $('timeline'), stage = $('stage');
const shortTime = value => {value=Number.isFinite(value)?Math.floor(value):0;return `${String(Math.floor(value/60)).padStart(2,'0')}:${String(value%60).padStart(2,'0')}`;};
function updateTimeline(){
  const duration=video.duration;
  timeline.disabled=!Number.isFinite(duration);
  timeline.max=Number.isFinite(duration)?duration:1;
  timeline.value=video.currentTime || 0;
  const percent=Number.isFinite(duration)?video.currentTime/duration*100:0;
  timeline.style.background=`linear-gradient(to right,#e50914 ${percent}%,#55555d ${percent}%)`;
  $('timecode').textContent=`${shortTime(video.currentTime)} / ${shortTime(duration)}`;
}
video.addEventListener('loadedmetadata',updateTimeline);
video.addEventListener('timeupdate',updateTimeline);
video.addEventListener('emptied',updateTimeline);
video.addEventListener('play',()=>stage.classList.add('is-playing'));
video.addEventListener('pause',()=>stage.classList.remove('is-playing'));
function updatePlaybackButton(){
  const paused=video.paused;
  $('mediaToggle').innerHTML=paused?'<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="m7 4 14 8-14 8Z"/></svg>':'<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M6 4h4v16H6zm8 0h4v16h-4z"/></svg>';
  $('mediaToggle').setAttribute('aria-label',paused?'播放':'暂停');
}
video.addEventListener('play',updatePlaybackButton); video.addEventListener('pause',updatePlaybackButton);
video.addEventListener('emptied',updatePlaybackButton);
$('mediaToggle').onclick=togglePlayback;
$('mediaRate').onchange=()=>{$('rate').value=$('mediaRate').value;video.playbackRate=Number($('mediaRate').value);};
timeline.addEventListener('input',()=>{stop();video.currentTime=Number(timeline.value);updateTimeline();});
$('volume').addEventListener('input',()=>{video.volume=Number($('volume').value);video.muted=video.volume===0;updateVolume();});
function updateVolume(){
  const muted=video.muted||video.volume===0;
  $('mute').innerHTML=`<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M11 4 6 8H2v8h4l5 4V4Z"/>${muted?'<path d="m16 9 6 6m0-6-6 6"/>':'<path d="M15 8a6 6 0 0 1 0 8m3-11a10 10 0 0 1 0 14"/>'}</svg>`;
  $('mute').setAttribute('aria-label',muted?'取消静音':'静音');$('mute').title=muted?'取消静音':'静音';
}
$('mute').onclick=()=>{video.muted=!video.muted;updateVolume();};
$('fullscreen').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await stage.parentElement.requestFullscreen();}catch(e){status('全屏暂不可用，可以最大化软件窗口。');}};
function updateFullscreen(){
  $('fullscreen').innerHTML='<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M3 9V3h6m6 0h6v6m0 6v6h-6m-6 0H3v-6"/></svg>';
  $('fullscreen').setAttribute('aria-label',document.fullscreenElement?'退出全屏':'全屏');
}
document.addEventListener('fullscreenchange',updateFullscreen);
updateTimeline();updateVolume();updateFullscreen();updatePlaybackButton();
const settingsDialog=$('settingsDialog');
$('settingsButton').onclick=()=>settingsDialog.showModal();
$('openImport').onclick=()=>settingsDialog.showModal();
$('closeSettings').onclick=()=>settingsDialog.close();
$('finishImport').onclick=()=>settingsDialog.close();
settingsDialog.addEventListener('click',event=>{if(event.target===settingsDialog){const bounds=settingsDialog.getBoundingClientRect();if(event.clientX<bounds.left||event.clientX>bounds.right||event.clientY<bounds.top||event.clientY>bounds.bottom)settingsDialog.close();}});
