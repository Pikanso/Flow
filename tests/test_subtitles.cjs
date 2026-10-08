const vm = require('node:vm');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const nodes = new Map();
function element(){return {value:'',textContent:'',disabled:false,checked:false,classList:{toggle(){}},append(){},replaceChildren(){},querySelector(){return null},addEventListener(){},pause(){},scrollIntoView(){}};}
const context = vm.createContext({document:{getElementById(id){if(!nodes.has(id))nodes.set(id,element());return nodes.get(id);},createElement:element,addEventListener(){}},requestAnimationFrame(){},setTimeout,clearTimeout,URL,Blob,console});
vm.runInContext(fs.readFileSync('web/app.js','utf8'),context);
const parse = text => JSON.parse(JSON.stringify(vm.runInContext(`parseSubtitles(${JSON.stringify(text)})`,context)));
assert.deepEqual(parse('1\n00:00:01,200 --> 00:00:03,500\nHello.\n\n2\n00:00:04,000 --> 00:00:05,000\nGood morning.'),[{start:1.2,end:3.5,text:'Hello.'},{start:4,end:5,text:'Good morning.'}]);
assert.deepEqual(parse('WEBVTT\n\n00:01.500 --> 00:03.000 align:start\n<b>Hello</b> there.'),[{start:1.5,end:3,text:'Hello there.'}]);
assert.deepEqual(parse('1\n00:00:05,000 --> 00:00:01,000\nInvalid'),[]);
assert.equal(vm.runInContext('stamp(59.9996)',context),'00:01:00,000');
console.log('Subtitle parsing and timestamp tests passed.');
