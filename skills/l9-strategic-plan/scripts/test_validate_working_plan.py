#!/usr/bin/env python3
import io,json,tempfile,zipfile,subprocess,sys
from pathlib import Path
from validate_working_plan import read_zip,check_graph

def pack(path, files):
    with zipfile.ZipFile(path,'w') as z:
        for k,v in files.items():z.writestr('plan/'+k,v)

def test():
    with tempfile.TemporaryDirectory() as t:
        d=Path(t);good=d/'good.zip';bad=d/'bad.zip';g=json.dumps({'nodes':[{'id':'a'},{'id':'b'}],'edges':[{'source':'a','target':'b','relation':'requires'}]})
        pack(good,{'graph.json':g,'README.md':'working'})
        assert len(read_zip(good))==2
        assert check_graph(read_zip(good),'graph.json','nodes','edges','id','source','target','relation',{'requires'})['edges']==1
        pack(bad,{'graph.json':json.dumps({'nodes':[{'id':'a'}],'edges':[{'source':'a','target':'missing','relation':'requires'}]})})
        try:check_graph(read_zip(bad),'graph.json','nodes','edges','id','source','target','relation',{'requires'});raise AssertionError('dangling edge passed')
        except ValueError as e:assert 'dangling' in str(e)
        pack(bad,{'../escape':'unsafe'})
        try:read_zip(bad);raise AssertionError('traversal passed')
        except ValueError as e:assert 'unsafe' in str(e)
        pack(bad,{'graph.json':g})
        proc=subprocess.run([sys.executable,str(Path(__file__).with_name('validate_working_plan.py')),str(bad),'--predecessor',str(good)],capture_output=True,text=True)
        assert proc.returncode==1 and 'undocumented' in proc.stdout
        print('PASS 5 structural tests including negative controls')
if __name__=='__main__':test()
