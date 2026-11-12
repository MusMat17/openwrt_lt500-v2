const {JSDOM,VirtualConsole}=require('jsdom');
const fs=require('fs'),acorn=require('acorn'),scope=require('eslint-scope');
const source=fs.readFileSync(process.argv[2],'utf8'),original=fs.readFileSync(process.argv[3],'utf8');
const start="cat > '/www/zm/app.js' << 'ZM_INSTALLER_EOF'\n";
const extract=s=>s.split(start)[1].split('\nZM_INSTALLER_EOF')[0];
const app=extract(source);
function unresolved(s){return new Set(scope.analyze(acorn.parse(s,{ecmaVersion:2022,ranges:true}),{ecmaVersion:2022}).globalScope.through.map(r=>r.identifier.name));}
const before=unresolved(extract(original)); const added=[...unresolved(app)].filter(x=>!before.has(x));if(added.length)throw Error('New unresolved references: '+added);
async function test(auth){
 const errors=[],calls=[];const vc=new VirtualConsole();vc.on('jsdomError',e=>{if(!/navigation|Not implemented: window.scrollTo/.test(e.message))errors.push(e);});
 const dom=new JSDOM('<!doctype html><html><head></head><body><div id="zmw-root"></div></body></html>',{url:'http://192.168.1.1:7788/#look',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:vc});
 const w=dom.window;w.requestAnimationFrame=()=>0;w.cancelAnimationFrame=()=>{};w.scrollTo=()=>{};w.matchMedia=()=>({matches:false,addEventListener(){},addListener(){}});w.HTMLCanvasElement.prototype.getContext=()=>null;w.Audio=()=>{throw Error('Radio audio initialized');};
 w.fetch=async (url,options)=>{calls.push(url);let data={};if(url==='/ubus'){const q=JSON.parse(options.body);const method=q.params[2];data={jsonrpc:'2.0',id:q.id,result:[0,method==='access'?{access:true}:{}]};}return {ok:true,status:200,json:async()=>data,text:async()=>''};};
 if(auth)w.sessionStorage.setItem('zmw.sid','1'.repeat(32));
 w.eval(app);await new Promise(r=>setTimeout(r,250));
 if(auth&&!w.document.querySelector('.zmw-nav'))throw Error('Shell missing: '+w.document.body.textContent.slice(0,500));
 if(!auth&&!w.document.querySelector('input[type="password"]'))throw Error('Login missing');
 if(w.document.querySelector('[data-zm-radio],.zmw-radio,.zmw-nav-btn-radio')||calls.some(x=>/radio|hls/i.test(x)))throw Error('Radio resource requested');
 if(errors.length)throw errors[0];
 console.log(auth?'Authenticated shell and appearance settings rendered without radio':'Login rendered without radio');dom.window.close();
}
(async()=>{await test(false);await test(true);})().catch(e=>{console.error(e);process.exit(1)});
