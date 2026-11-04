from pathlib import Path
from html.parser import HTMLParser
from html import unescape
import re,json,hashlib
import sys
ROOT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[2]
def flat(d,p=''):
 return {k:v for n,v in d.items() for k,v in (flat(v,p+n+'.').items() if isinstance(v,dict) else [(p+n,v)])}
def norm(v):return re.sub(r'\s+',' ',unescape(v)).strip()
base=flat(json.loads((ROOT/'static/i18n/pt-BR.json').read_text()));known={}
for k,v in base.items():known.setdefault(norm(v),k)
TECHNICAL={'API','CSV','XLSX','PDF','PNG','JPEG','JPG','QR Code','CNPJ','CPF','CA','CE','BRL','EPI Controle','EPI Control','WhatsApp','Microsoft','Google','Facebook','Apple','Android','iOS','Start','Business','Corporate','Individual','Enterprise','QR','HTML','JSON','HTTP','URL','UTC','LTDA','CNAE','UF','CEP','XML','Pix','PIX','A4','A5','UTF-8','P','M','G','GG','XG','XXG','EXG','XS','S','L','XL','XXL'}
class Scan(HTMLParser):
 def __init__(self,src,name):
  super().__init__(convert_charrefs=False);self.src=src;self.name=name;self.offsets=[0];self.stack=[];self.nodes=[];self.records=[]
  for m in re.finditer('\n',src):self.offsets.append(m.end())
 def position(self):line,col=self.getpos();return self.offsets[line-1]+col
 def handle_starttag(self,tag,attrs):
  start=self.position();raw=self.get_starttag_text();d=dict(attrs);n={'tag':tag,'attrs':d,'start':start,'end':start+len(raw),'text':[],'parent':self.stack[-1] if self.stack else None}
  self.nodes.append(n)
  if not any(x['tag'] in ['script','style'] for x in self.stack):
   for attr in ['placeholder','title','aria-label','alt']:
    text=norm(d.get(attr) or '')
    if text and re.search(r'[A-Za-zÀ-ÿ]',text) and 'data-i18n-'+attr not in d:
     self.records.append({'kind':'attribute','attribute':attr,'text':text,'node':n})
  if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:self.stack.append(n)
 def handle_startendtag(self,tag,attrs):self.handle_starttag(tag,attrs);self.handle_endtag(tag)
 def handle_endtag(self,tag):
  for i in range(len(self.stack)-1,-1,-1):
   if self.stack[i]['tag']==tag:self.stack=self.stack[:i];break
 def handle_data(self,data):
  if not self.stack or any(x['tag'] in ['script','style','textarea','code','pre'] or 'data-i18n-html' in x['attrs'] for x in self.stack):return
  parent=self.stack[-1]
  if 'data-i18n' in parent['attrs']:return
  start=self.position();text=norm(data)
  if not text or not re.search(r'[A-Za-zÀ-ÿ]',text):return
  rec={'kind':'text','text':text,'node':parent,'start':start,'end':start+len(data)};parent['text'].append(rec);self.records.append(rec)
 def handle_entityref(self,name):pass
 def handle_charref(self,name):pass
 def export(self):
  out=[]
  for r in self.records:
   n=r.pop('node');text=r['text']
   if text in TECHNICAL or re.fullmatch(r'(?:https?://|www\.)\S+|[\w.+-]+@[\w.-]+\.[a-z]{2,}|[\d\s.,/%+×x-]+',text):continue
   r.update(file=self.name,tag=n['tag'],tag_start=n['start'],tag_end=n['end'],parent_texts=len(n['text']),line=self.src.count('\n',0,n['start'])+1,existing=known.get(text))
   if not r['existing']:
    slug=re.sub('[^a-z0-9]+','_',__import__('unicodedata').normalize('NFKD',text).encode('ascii','ignore').decode().lower()).strip('_')[:75]
    domain=Path(self.name).stem.lstrip('_').replace('-','_');r['key']='ui.'+domain+'.'+slug+'_'+hashlib.sha256(text.encode()).hexdigest()[:6]
   else:r['key']=r['existing']
   out.append(r)
  return out
def collect(root=ROOT):
 records=[]
 for p in sorted((root/'static').rglob('*.html')):
  if p.name in ('index.html','_layout.html'):continue
  scanner=Scan(p.read_text(),p.relative_to(root).as_posix());scanner.feed(scanner.src);records+=scanner.export()
 return records

if __name__=='__main__':
 print(json.dumps(collect(),ensure_ascii=True,indent=2))
