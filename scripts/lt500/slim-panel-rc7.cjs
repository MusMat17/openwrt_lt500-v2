const fs=require('fs'),acorn=require('acorn'),scope=require('eslint-scope'),postcss=require('postcss'),selectors=require('postcss-selector-parser'),{JSDOM}=require('jsdom');
let source=fs.readFileSync(process.argv[2],'utf8'),original=source;
function once(s,a,b){if(s.split(a).length!==2)throw Error('Expected one marker: '+a.slice(0,70));return s.replace(a,b);}
function walk(n,cb){if(!n||typeof n!=='object')return;if(n.type)cb(n);for(const v of Object.values(n)){if(Array.isArray(v))v.forEach(x=>walk(x,cb));else if(v&&typeof v==='object')walk(v,cb);}}
const ast=s=>acorn.parse(s,{ecmaVersion:2022,ranges:true});
function edit(s,es){es.sort((a,b)=>a[0]-b[0]||b[1]-a[1]);const keep=[];for(const e of es){const p=keep.at(-1);if(p&&e[0]>=p[0]&&e[1]<=p[1])continue;if(p&&e[0]<p[1])throw Error('Overlap');keep.push(e);}for(const[a,b,t]of keep.reverse())s=s.slice(0,a)+t+s.slice(b);return s;}
function payload(path,fn){const m="cat > '"+path+"' << 'ZM_INSTALLER_EOF'\n",a=source.indexOf(m);if(a<0)throw Error(path);const b=a+m.length,e=source.indexOf('\nZM_INSTALLER_EOF',b),old=source.slice(b,e),fresh=fn(old);source=source.slice(0,b)+fresh+source.slice(e);console.log(path,Buffer.byteLength(old),'->',Buffer.byteLength(fresh));}
payload('/www/zm/app.js',s=>{
 const old=s,removed=new Set(),a=s.indexOf('var mqDark = '),b=s.indexOf('var ROUTES = ',a),c=s.indexOf('var LOOK_PV = ',b),d=s.indexOf('var NAV_LOCK = ',c);
 if([a,b,c,d].some(x=>x<0))throw Error('Appearance boundaries');
 for(const n of ast(s).body[0].expression.callee.body.body)if((n.start>=a&&n.end<=b)||(n.start>=c&&n.end<=d)){if(n.type==='FunctionDeclaration')removed.add(n.id.name);if(n.type==='VariableDeclaration')for(const x of n.declarations)if(x.id.type==='Identifier')removed.add(x.id.name);}
 s=s.slice(0,c)+s.slice(d);s=s.slice(0,a)+s.slice(b);
 s=s.replace(/^.*id: 'look', title:.*\n/gm,'').replace('look: 1, ','');
 s=s.replace(/^.*(?:var themeBtn =|^\s*themeBtn,|var mxRain =|var mxMsg =|^\s*mxRain,|^\s*mxMsg,|loginEl.zmMxStop =|if \(el.zmMxStop\)|mxMsg.textContent =|zmw-mx-title|zmw-mx-sub|zmw-orbs|zmw-grid-bg|zmw-login-theme).*\n/gm,'');
 s=s.replace(/^.*card.classList.remove\('zmw-shake'\).*\n/gm,'');
 for(const n of ['K_THEME','K_ANIM','K_ANIMFOR','K_LOOK'])s=s.replace(new RegExp(', '+n+" = '[^']*'"),'').replace(' && k !== '+n,'');
 let es=[];walk(ast(s),n=>{if(n.type==='FunctionDeclaration'&&n.id.name==='matrixRain'){removed.add('matrixRain');es.push([n.start,n.end,'']);}});s=edit(s,es);
 function mentions(n){let yes=false;walk(n,x=>{if(x.type==='Identifier'&&removed.has(x.name))yes=true;});return yes;}
 es=[];walk(ast(s),n=>{if(n.type==='IfStatement'&&mentions(n.test))es.push([n.start,n.end,'']);if(n.type==='ExpressionStatement'){const e=n.expression;if(e.type==='CallExpression'&&e.callee.type==='Identifier'&&removed.has(e.callee.name))es.push([n.start,n.end,'']);if(e.type==='AssignmentExpression'&&e.left.type==='Identifier'&&removed.has(e.left.name))es.push([n.start,n.end,'']);}});s=edit(s,es);
 const p=s.indexOf('if (!sid) { showLogin(); return; }'),st=s.indexOf('\t\treturn Promise.all([',p),en=s.indexOf('\n\t}).catch(function (e)',st);if(st<0||en<0)throw Error('Theme ACL block');s=s.slice(0,st)+'\t\tstartApp();'+s.slice(en);
 s=once(s,"root = document.getElementById('zmw-root');","root = document.getElementById('zmw-root');\n\tdocument.documentElement.setAttribute('data-theme', 'light');").replace(/behavior: 'smooth'/g,"behavior: 'auto'");
 function globals(t){return new Set(scope.analyze(ast(t),{ecmaVersion:2022}).globalScope.through.map(r=>r.identifier.name));}
 const prev=globals(old),missing=[...globals(s)].filter(x=>!prev.has(x));if(missing.length)throw Error('Remaining appearance references: '+missing.join(','));
 if(/themeSync|lookSync|ZMFX|function dustStart|function matrixRain|fonts\.google|toggleTheme|lookPage\(/.test(s))throw Error('Appearance remains');return s;
});
const dropClass=/^(?:zmw-(?:theme|bg-|bgo|dust|mx-|orbs|grid-bg)|zm-lk(?:-|$)|zm-theme-dark$|zm-bg-only$|zm-look)/;
for(const path of ['/www/zm/app.css','/www/luci-static/resources/view/zapret-manager/style.css'])payload(path,s=>{
 const tree=postcss.parse(s);tree.walkAtRules(a=>{if(/keyframes/i.test(a.name)||a.name==='font-face'||(a.name==='import'&&/fonts|google/i.test(a.params))||(a.name==='media'&&/prefers-color-scheme|prefers-reduced-motion/.test(a.params)))a.remove();});
 tree.walkDecls(d=>{if(/^(?:-webkit-)?(?:animation|transition)(?:-|$)/.test(d.prop)||/backdrop-filter/.test(d.prop))d.remove();if(d.prop==='scroll-behavior')d.value='auto';if(d.prop==='--font')d.value='system-ui, -apple-system, "Segoe UI", sans-serif';if(d.prop==='--mono')d.value='ui-monospace, Consolas, monospace';});
 tree.walkRules(r=>{if(!r.selector)return;r.selector=selectors(root=>root.each(sel=>{let drop=false;sel.walkClasses(c=>{if(dropClass.test(c.value))drop=true;});sel.walkAttributes(a=>{if(/^data-(?:theme|zm-(?:look|font|tint|motion|anim|bg))/.test(a.attribute)){if(a.attribute==='data-theme'&&a.value==='light')a.remove();else drop=true;}});if(drop)sel.remove();})).processSync(r.selector);if(!r.selector.trim()||!r.nodes.length)r.remove();});
 let changed=true;while(changed){changed=false;tree.walkAtRules(a=>{if(a.nodes&&!a.nodes.length){a.remove();changed=true;}});tree.walkRules(r=>{if(!r.nodes.length){r.remove();changed=true;}});}tree.walkComments(c=>c.remove());return tree.toString();
});
payload('/www/zm-webui.html',html=>{const dom=new JSDOM(html),d=dom.window.document;d.querySelectorAll('script:not([src]),style,link[href*="fonts.googleapis"],link[href*="fonts.gstatic"]').forEach(x=>x.remove());d.documentElement.setAttribute('data-theme','light');const s=dom.serialize();dom.window.close();return s;});
const ts=source.indexOf('ui_theme_set() {\n'),te=source.indexOf('UI_NAV_FILE=',ts);if(ts<0||te<0)throw Error('Theme backend markers');source=source.slice(0,ts)+source.slice(te);source=source.split('\n').filter(x=>!/\bui_(?:theme|look)_set\b/.test(x)).join('\n');
const old=source.match(/^_st_warp_on\(\) \{[\s\S]*?^\}/m);if(!old)throw Error('WARP detection marker');source=once(source,old[0],fs.readFileSync(__dirname+'/rc7-warp-on.sh','utf8').trim());
fs.writeFileSync(process.argv[3],source);console.log('Total panel bytes removed:',Buffer.byteLength(original)-Buffer.byteLength(source));
