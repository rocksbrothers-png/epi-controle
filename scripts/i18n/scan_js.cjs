const fs=require('fs'),path=require('path'),acorn=require('acorn');
const root=process.argv[2],out=[];
function files(p){return fs.readdirSync(p,{withFileTypes:true}).flatMap(e=>e.isDirectory()?(e.name==='test'?[]:files(path.join(p,e.name))):e.name.endsWith('.js')?[path.join(p,e.name)]:[]);}
for(const file of files(path.join(root,'static'))){
 const src=fs.readFileSync(file,'utf8');let ast;try{ast=acorn.parse(src,{ecmaVersion:'latest',sourceType:'script',locations:true});}catch(e){out.push({file,error:String(e)});continue;}
 function translatedAncestor(anc) {
 return anc.some(x=> {
  if(x.type==='CallExpression')return /(?:\btr|\bt|trEpi|_tr|translate|tEpi|bindText|textFor|attributeFor|format)$/.test(src.slice(x.callee.start,x.callee.end));
  if(x.type==='LogicalExpression'&&['??','||'].includes(x.operator))return /(?:trEpi|bindText|textFor|attributeFor)\s*\?\.\s*\(/.test(src.slice(x.left.start,x.left.end));
  return false;
 });
}
function visit(n,anc=[]){if(!n||typeof n!=='object')return;const p=anc.at(-1);const binding=[...anc].reverse().find(x=>x.type==='VariableDeclarator'&&x.id.type==='Identifier')?.id.name||'';if(n.type==='Literal'&&typeof n.value==='string'&&/[A-Za-zÀ-ÿ]/.test(n.value)){
 const call=[...anc].reverse().find(x=>x.type==='CallExpression'||x.type==='NewExpression');const callName=call?(['Identifier','MemberExpression'].includes(call.callee.type)?src.slice(call.callee.start,call.callee.end).slice(0,100):call.callee.type):'';
 const translated=translatedAncestor(anc);
 out.push({file:path.relative(root,file),start:n.start,end:n.end,line:n.loc.start.line,kind:'string',binding,isPropertyKey:p?.type==='Property'&&p.key===n,assignmentProperty:(()=>{const a=[...anc].reverse().find(x=>x.type==='AssignmentExpression');return a?.left.type==='MemberExpression'?a.left.property.name:'';})(),callFirstArg:call?.arguments[0]?.value,value:n.value,call:callName,parent:p?.type,property:p?.type==='Property'?(p.key.name||p.key.value):'',propertyStart:p?.type==='Property'?p.start:null,propertyEnd:p?.type==='Property'?p.end:null,functionDepth:anc.filter(x=>['FunctionDeclaration','FunctionExpression','ArrowFunctionExpression'].includes(x.type)).length,translated,context:src.slice(Math.max(0,n.start-60),Math.min(src.length,n.end+40)).replace(/\n/g,' ')});
 }
 if(n.type==='TemplateLiteral')out.push({file:path.relative(root,file),start:n.start,end:n.end,line:n.loc.start.line,kind:'template',binding,value:src.slice(n.start,n.end),parent:p?.type,property:p?.type==='Property'?(p.key.name||p.key.value):'',call:(()=>{const c=[...anc].reverse().find(x=>x.type==='CallExpression'||x.type==='NewExpression');return c?src.slice(c.callee.start,c.callee.end).slice(0,90):'';})(),translated:translatedAncestor(anc),context:src.slice(Math.max(0,n.start-60),n.start).replace(/\n/g,' '),quasis:n.quasis.map(x=>({start:x.start,end:x.end,value:x.value.cooked})),expressions:n.expressions.map(x=>{const a=x.type==='CallExpression'&&x.callee.type==='Identifier'&&['esc','escapeHtml','escapeAttribute'].includes(x.callee.name)&&x.arguments.length===1?x.arguments[0]:x;return {start:x.start,end:x.end,value:src.slice(x.start,x.end),textStart:a.start,textEnd:a.end,textValue:src.slice(a.start,a.end)};})});
 for(const[k,v]of Object.entries(n)){if(k==='loc')continue;if(Array.isArray(v))v.forEach(x=>{if(x?.type)visit(x,[...anc,n]);});else if(v?.type)visit(v,[...anc,n]);}
 }visit(ast);
}
fs.writeFileSync(process.argv[3],JSON.stringify(out,null,2));
