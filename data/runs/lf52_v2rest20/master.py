"""When the game is back: probe ACTION5, then replay levels 1-5."""
import subprocess,re,json,sys
def st():
    o=subprocess.run(['./act','status'],capture_output=True,text=True).stdout
    m=re.search(r'score=(\d+)/\d+ level=(\d+) attempt=(\d+) state=(\w+) actions=(\d+)',o)
    return m.groups() if m else o.strip()
def board():
    o=subprocess.run(['./act','board'],capture_output=True,text=True).stdout
    return [l for l in o.splitlines() if len(l)==64]
def do(plan,*acts):
    r=subprocess.run(['./act','do','--plan',plan]+list(acts),capture_output=True,text=True)
    return (r.stdout+r.stderr).strip()
print('status',st())
b0=board()
out=do('probe: ACTION5 has never been played in this run - find out what it does before replaying','ACTION5')
print('ACTION5 ->',out.splitlines()[0] if out else '(ok)')
b1=board()
print('board changed by ACTION5:',b0!=b1)
if b0!=b1:
    print(do('ACTION5 changed the board - reset level 1 so the recorded replay stays valid','RESET'))
import replay
