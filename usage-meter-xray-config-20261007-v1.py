"""幂等添加仅回环 StatsService；不修改任何 clients 或 Reality 参数。"""
import copy

def add_stats(config, port):
    if type(port) is not int or not 1024<=port<=65535:raise ValueError('invalid port')
    cfg=copy.deepcopy(config)
    original_clients=[copy.deepcopy(i.get('settings',{}).get('clients')) for i in cfg.get('inbounds',[])]
    if cfg.get('api') and cfg['api'].get('tag')!='usage-meter-api':
        raise ValueError('existing api requires explicit compatibility review')
    cfg.setdefault('stats',{})
    levels=cfg.setdefault('policy',{}).setdefault('levels',{})
    used={'0'}
    for inbound in cfg.get('inbounds',[]):
        for client in inbound.get('settings',{}).get('clients',[]) or []:used.add(str(client.get('level',0)))
    for level in used:
        levels.setdefault(level,{})['statsUserUplink']=True
        levels[level]['statsUserDownlink']=True
    cfg['api']={'tag':'usage-meter-api','services':['StatsService']}
    entries=[i for i in cfg.setdefault('inbounds',[]) if i.get('tag')=='usage-meter-api-in']
    desired={'tag':'usage-meter-api-in','listen':'127.0.0.1','port':port,'protocol':'dokodemo-door','settings':{'address':'127.0.0.1'}}
    if entries:
        if len(entries)!=1 or entries[0]!=desired:raise ValueError('api inbound conflict')
    else:
        if any(i.get('port')==port for i in cfg['inbounds']):raise ValueError('port conflict')
        cfg['inbounds'].append(desired)
    rule={'type':'field','inboundTag':['usage-meter-api-in'],'outboundTag':'usage-meter-api'}
    rules=cfg.setdefault('routing',{}).setdefault('rules',[])
    if rule not in rules:rules.insert(0,rule)
    assert original_clients==[i.get('settings',{}).get('clients') for i in cfg['inbounds'][:len(original_clients)]]
    return cfg
