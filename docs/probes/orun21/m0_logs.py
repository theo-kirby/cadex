"""orun21 M0, the log pass: where an Ouroboros iteration's wall time goes.

    python3 m0_logs.py <repo>/.ouroboros/runs/<run> ...   [--json]

Reads each run's transcripts/*.json (stream-json, one per role session) and
splits every session's wall time into model time, foreground tool time by
kind (build, train, judge, test, memory), and the time a session sat idle
until a background task of that kind finished. Background tasks are also timed
start to end on their own (``bgtask:*``); they overlap the foreground and are
not added to it. "model" is an upper bound: an idle gap with no finished task
to blame lands there. Kinds come from regexes on the command text.
"""
import json, re, sys, collections, datetime as dt, glob, os

KINDS = [
    ('memory', r'ouroboros mem|governor'),
    ('test', r'pytest|test-engine'),
    ('judge', r'judge|evaluat|cadex_eval|fidelity|score|summaris'),
    ('train', r'cadex_train|launch\.sh|train\.sh|turn\.sh|curriculum|train_bench|\btrain|seed\s?\d|progress\.json|sweep'),
    ('build', r'cadex\b.*\b(script|build|render|hero|export|smoke|look|clearance|params|check|bundle|film)\b|FreeCADCmd|build-engine|stage-engine|a2_bundle|training_model|\bbuild|\bhero|render'),
    ('git', r'^\s*(cd [^;&]+(&&|;)\s*)?git '),
]
WAIT = r'^\s*(cd [^;&]+(&&|;)\s*)?(until|while)\b|sleep \d|^(Wait|Block until)'
def kind(cmd):
    pre = 'waitloop-' if re.search(WAIT, cmd) else ''
    for k, rx in KINDS:
        if re.search(rx, cmd, re.I):
            return pre + k
    return pre + 'other'

def ts(s):
    return dt.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()

def session(path):
    ev = []
    for line in open(path, errors='replace'):
        try:
            ev.append(json.loads(line))
        except ValueError:
            pass
    out = collections.Counter()
    uses = {}          # tool_use_id -> (t_start, kind)
    bg = {}            # task_id -> (t_start, kind)
    tokens = collections.Counter()
    times = [ts(e['timestamp']) for e in ev if 'timestamp' in e]
    if not times:
        return None
    t0, t1 = min(times), max(times)
    last_t, last_waiting, done_kind = t0, False, None
    reads = collections.Counter()
    for e in ev:
        t = ts(e['timestamp']) if 'timestamp' in e else None
        if e['type'] == 'assistant':
            m = e['message']
            # model time: since the last timestamped event, unless the last
            # assistant turn ended with no tool call (then it is a wait)
            if t is not None:
                gap = t - last_t
                if last_waiting and done_kind:
                    out['wait:' + done_kind] += gap
                else:
                    out['model'] += gap
                last_t, done_kind = t, None
            has_tool = False
            for c in m.get('content', []):
                if c.get('type') == 'tool_use':
                    has_tool = True
                    name = c['name']
                    inp = c.get('input', {})
                    if name == 'Bash':
                        k = 'bg_launch' if inp.get('run_in_background') else kind(inp.get('command', ''))
                    elif name in ('Monitor', 'TaskOutput'):
                        k = 'monitor_call'
                    elif name in ('Agent', 'Task', 'Workflow'):
                        k = 'subagent'
                    else:
                        k = 'tool:' + name
                    uses[c['id']] = (t, k)
            last_waiting = not has_tool and not uses
        elif e['type'] == 'user' and t is not None:
            for c in e['message'].get('content', []) if isinstance(e['message'].get('content'), list) else []:
                if c.get('type') == 'tool_result' and c['tool_use_id'] in uses:
                    t_s, k = uses.pop(c['tool_use_id'])
                    if t_s is not None:
                        out[k] += t - t_s
                    body = c.get('content')
                    n = len(json.dumps(body)) if body is not None else 0
                    reads[k] += n
            last_t = t
        elif e['type'] == 'system' and e.get('subtype') == 'task_started':
            bg[e['task_id']] = (last_t, kind(e.get('description', '')))
        elif e['type'] == 'system' and e.get('subtype') == 'task_updated':
            p = e.get('patch', {})
            if p.get('end_time') and e['task_id'] in bg:
                t_s, k = bg.pop(e['task_id'])
                out['bgtask:' + k] += p['end_time'] / 1000 - t_s
                done_kind = done_kind or k
        elif e['type'] == 'rate_limit_event':
            info = e.get('rate_limit_info', {})
            if info.get('status') != 'allowed':
                out['rate_limited_events'] += 1
        elif e['type'] == 'result':
            u = e.get('usage', {})
            for key in ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'output_tokens'):
                tokens[key] += u.get(key, 0)
            tokens['turns'] += e.get('num_turns', 0)
            tokens['api_s'] += e.get('duration_api_ms', 0) / 1000
            tokens['cost'] += e.get('total_cost_usd', 0)
    out['wall'] = t1 - t0
    return out, tokens, reads

def main(run_dirs):
    grand = collections.defaultdict(collections.Counter)
    for rd in run_dirs:
        run = os.path.basename(rd.rstrip('/'))
        for f in sorted(glob.glob(os.path.join(rd, 'transcripts', '*.json'))):
            role = re.sub(r'^\d+-', '', os.path.basename(f))[:-5]
            r = session(f)
            if not r:
                continue
            out, tokens, reads = r
            g = grand[(run, role)]
            g['sessions'] += 1
            g.update(out)
            g.update({'tok_' + k: v for k, v in tokens.items()})
            g.update({'chars_' + k: v for k, v in reads.items()})
    if '--json' in flags:
        json.dump({f'{a}/{b}': dict(v) for (a, b), v in grand.items()}, sys.stdout, indent=1, default=float)
        return
    cats = ['model', 'build', 'train', 'judge', 'test', 'memory', 'other']

    def cat(key):
        if key.startswith('bgtask:') or key == 'rate_limited_events':
            return None
        return next((c for c in cats[1:] if c in key), 'model' if key == 'model' else 'other')

    print('| run/role | sessions | wall h | ' + ' | '.join(cats) + ' |')
    print('|---' * (len(cats) + 3) + '|')
    for (run, role), v in grand.items():
        row = collections.Counter()
        for key, value in v.items():
            if not key.startswith(('chars_', 'tok_')) and key not in ('sessions', 'wall') and cat(key):
                row[cat(key)] += value
        print(f"| {run}/{role} | {v['sessions']} | {v['wall'] / 3600:.2f} | "
              + ' | '.join(f"{row[c] / 3600:.2f} ({100 * row[c] / v['wall']:.0f}%)" for c in cats) + ' |')

if __name__ == '__main__':
    flags = [a for a in sys.argv[1:] if a.startswith('--')]
    main([a for a in sys.argv[1:] if not a.startswith('--')])
