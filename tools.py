import ast, operator

OPS={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,ast.Mod:operator.mod,ast.USub:operator.neg,ast.UAdd:operator.pos}
def calculator(expression):
 def calc(n):
  if isinstance(n,ast.Constant) and type(n.value) in (int,float): return n.value
  if isinstance(n,ast.BinOp) and type(n.op) in OPS: return OPS[type(n.op)](calc(n.left),calc(n.right))
  if isinstance(n,ast.UnaryOp) and type(n.op) in OPS: return OPS[type(n.op)](calc(n.operand))
  raise ValueError('Unsupported expression')
 if len(expression)>200: raise ValueError('Expression too long')
 return calc(ast.parse(expression,mode='eval').body)

def spec(name,description,properties,required): return {'type':'function','function':{'name':name,'description':description,'parameters':{'type':'object','properties':properties,'required':required,'additionalProperties':False}}}
TOOLS=[spec('calculator','计算算术表达式',{'expression':{'type':'string'}},['expression']),spec('search','搜索模拟资料，结果不代表实时网络',{'query':{'type':'string'}},['query']),spec('todo','仅管理用户明确要求执行或记录的待办任务，不是保存姓名、偏好等对话记忆的工具。',{'action':{'type':'string','enum':['add','list','complete']},'text':{'type':'string'},'id':{'type':'integer'}},['action'])]


class Registry:
 def __init__(self): self.entries={}
 def register(self, definition, handler):
  name=definition['function']['name']
  if name in self.entries: raise ValueError('Tool already registered')
  self.entries[name]=(definition,handler)
 def definitions(self): return [entry[0] for entry in self.entries.values()]
 def execute(self,name,sid,args):
  if name not in self.entries: raise ValueError('Unknown tool')
  if not isinstance(args,dict): raise ValueError('Arguments must be an object')
  definition,handler=self.entries[name]; schema=definition['function']['parameters']; props=schema.get('properties',{})
  if any(k not in args for k in schema.get('required',[])): raise ValueError('Missing required argument')
  if schema.get('additionalProperties') is False and any(k not in props for k in args): raise ValueError('Unexpected argument')
  types={'string':str,'integer':int,'number':(int,float),'boolean':bool,'object':dict,'array':list}
  for k,v in args.items():
   rule=props.get(k,{}); kind=rule.get('type')
   if kind in types and (not isinstance(v,types[kind]) or (kind in ('integer','number') and isinstance(v,bool))): raise ValueError('Invalid argument type: '+k)
   if 'enum' in rule and v not in rule['enum']: raise ValueError('Invalid argument value: '+k)
  return handler(sid,**args)

def default_registry(store):
 registry=Registry()
 registry.register(TOOLS[0],lambda sid,expression: calculator(expression))
 registry.register(TOOLS[1],lambda sid,query: {'mock':True,'query':query,'results':['模拟搜索结果：请使用真实搜索服务获取最新信息。']})
 def todo_handler(sid,**args):
  action=args.get('action')
  required={'add':{'action','text'},'list':{'action'},'complete':{'action','id'}}
  if action not in required or set(args)!=required[action]: raise ValueError('Invalid arguments for todo action')
  if action=='add' and not args['text'].strip(): raise ValueError('Todo text must not be empty')
  if action=='complete' and args['id']<1: raise ValueError('Todo id must be positive')
  return store.todo(sid,**args)
 registry.register(TOOLS[2],todo_handler)
 return registry

