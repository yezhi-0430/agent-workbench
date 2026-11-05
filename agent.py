import json, os, urllib.request, urllib.error, time

from storage import Store
from tools import Registry, TOOLS, calculator, default_registry, spec

def openrouter(messages,tools):
 key=os.environ.get('OPENROUTER_API_KEY')
 if not key: raise RuntimeError('请先设置 OPENROUTER_API_KEY')
 data={'model':os.environ.get('OPENROUTER_MODEL','openai/gpt-4o-mini'),'messages':messages}
 if tools: data['tools']=tools
 req=urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',json.dumps(data).encode(),{'Authorization':'Bearer '+key,'Content-Type':'application/json'})
 started=time.monotonic()
 for attempt in range(3):
  try:
   with urllib.request.urlopen(req,timeout=60) as r:
    payload=json.load(r); message=payload['choices'][0]['message']
    message['_trace']={'model':payload.get('model') or data['model'],'duration_ms':round((time.monotonic()-started)*1000),'retries':attempt}
    return message
  except urllib.error.HTTPError as e:
   if e.code not in (429,500,502,503,504) or attempt==2: raise
  except (urllib.error.URLError,TimeoutError,ConnectionError) as e:
   if attempt==2: raise
  time.sleep(0.5 * (2 ** attempt))


def repair_tool_history(messages):
 """Complete interrupted tool groups in the request, without rerunning side effects."""
 result=[]; pending=[]; repaired=0
 def flush():
  nonlocal repaired
  for tool_id in pending:
   result.append({'role':'tool','tool_call_id':tool_id,'content':json.dumps({'error':'Execution outcome unknown after interruption; check state before retrying.'})})
   repaired+=1
  pending.clear()
 for msg in messages:
  if msg.get('role')=='tool':
   tool_id=msg.get('tool_call_id')
   if tool_id in pending:
    result.append(msg); pending.remove(tool_id)
   continue
  flush(); result.append(msg)
  if msg.get('role')=='assistant': pending.extend(call['id'] for call in msg.get('tool_calls',[]) if call.get('id'))
 flush()
 return result,repaired

class Agent:
 def __init__(self,store,model=openrouter,max_steps=8,should_cancel=None,registry=None): self.store,self.model,self.max_steps,self.should_cancel,self.registry=store,model,max_steps,should_cancel or (lambda: False),registry if registry is not None else default_registry(store)
 def run(self,sid,text):
  self.store.add(sid,{'role':'user','content':text})
  if self.should_cancel():
   yield {'type':'error','content':'已停止。'}; return
  history=self.store.messages(sid)
  # A character budget is an approximation, not a tokenizer or model-window guarantee.
  starts=[i for i,m in enumerate(history) if m['role']=='user']
  cutoff=starts[-8] if len(starts)>8 else 0
  while cutoff < len(history) and len(json.dumps(history[cutoff:],ensure_ascii=False))>22000:
   candidates=[i for i in starts if i>cutoff]
   if not candidates:
    yield {'type':'error','content':'当前单轮对话过长，无法安全压缩，请缩短输入或工具结果。'}; return
   cutoff=candidates[0]
  if cutoff:
   previous,count=self.store.summary(sid)
   if cutoff>count:
    source=json.dumps(history[count:cutoff],ensure_ascii=False)
    working=previous
    try:
     for offset in range(0,len(source),10000):
      chunk=source[offset:offset+10000]
      summary_message=[{'role':'system','content':'将已有摘要和新增历史合并为简洁的中文摘要，保留用户目标、重要事实、约束、决定和未完成事项。仅输出摘要，不要编造。'}, {'role':'user','content':'已有摘要：'+working+'\n新增历史片段：'+chunk}]
      updated=self.model(summary_message,[]).get('content')
      if not isinstance(updated,str) or not updated.strip(): raise ValueError('empty summary')
      if len(updated.strip())>6000: raise ValueError('summary exceeds limit')
      working=updated.strip()
     previous=working; self.store.save_summary(sid,previous,cutoff)
     yield {'type':'context','content':previous,'count':cutoff}
    except Exception:
     yield {'type':'error','content':'上下文压缩失败，未丢弃旧记录，请稍后重试。'}; return
   history=[{'role':'system','content':'较早对话摘要（可能不完整）：\n'+previous}]+history[cutoff:]
  history,repaired=repair_tool_history(history)
  if repaired: yield {'type':'recovery','content':f'检测到 {repaired} 个中断的工具调用，执行结果未知；请先检查实际状态。','count':repaired}
  messages=[{'role':'system','content':'你是一个可靠的助手。根据需要使用工具，搜索是模拟的。只有用户明确要求记录或管理待办任务才使用 todo；姓名、偏好等普通对话记忆不是待办，应从上下文获取。待办通过工具读取，诚实报告错误。'}]+history
  for step in range(self.max_steps):
   if len(json.dumps(messages,ensure_ascii=False))>30000:
    yield {'type':'error','content':'工具结果或上下文过长，已停止本轮；请缩小查询范围后重试。'}; return
   try: response=self.model(messages,self.registry.definitions())
   except Exception as e:
    yield {'type':'error','content':str(e)}; return
   if self.should_cancel():
    yield {'type':'error','content':'已停止。'}; return
   if isinstance(response.get('_trace'),dict):
    yield {'type':'model','step':step+1,**response['_trace']}
   if self.should_cancel():
    yield {'type':'error','content':'已停止。'}; return
   calls=response.get('tool_calls') or []
   if not calls:
    answer=response.get('content') or '模型没有返回内容。'; self.store.add(sid,{'role':'assistant','content':answer}); yield {'type':'answer','content':answer}; return
   msg={'role':'assistant','content':response.get('content'),'tool_calls':calls}; self.store.add(sid,msg); messages.append(msg)
   for index,call in enumerate(calls):
    if self.should_cancel():
     for pending in calls[index:]:
      tool={'role':'tool','tool_call_id':pending['id'],'content':json.dumps({'error':'Cancelled'})}; self.store.add(sid,tool); messages.append(tool)
     yield {'type':'error','content':'已停止。'}; return
    f=call.get('function',{}); name=f.get('name',''); raw=f.get('arguments','{}')
    started=time.monotonic(); status='success'
    try:
     args=json.loads(raw)
     result=self.registry.execute(name,sid,args)
     output=json.dumps({'result':result},ensure_ascii=False)
    except Exception as e:
     status='error'; output=json.dumps({'error':str(e)},ensure_ascii=False)
    tool={'role':'tool','tool_call_id':call['id'],'content':output}; self.store.add(sid,tool); messages.append(tool)
    yield {'type':'tool','name':name,'arguments':raw,'content':output,'step':step+1,'status':status,'duration_ms':round((time.monotonic()-started)*1000)}
  yield {'type':'error','content':'已达到最大工具调用轮次。'}
