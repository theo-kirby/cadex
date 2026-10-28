"""orun21 M0: every engine-opening `cadex` command an actor ran, timed.

    python3 m0_build_calls.py <repo>/.ouroboros/runs/<run> ...

Reads the actor transcripts (stream-json) like m0_logs.py and prints, per run
and per `cadex` subcommand, how many foreground calls ran and their wall time
(tool_use to tool_result), and the background ones from launch to the task's
end (marked `bg`): count, total, median, max. Each such call opens the
engine on the project, so its time includes the engine's restore of the
accepted revision before the command's own work.
"""
import collections, glob, json, os, re, statistics, sys

from m0_logs import ts

CMD = re.compile(r'(?:^|[\s/;&|(])cadex\s+(?:--?\S+\s+(?:\S+\s+)?)*?'
                 r'(script|params|export|render|hero|smoke|look|clearance|evaluate|train|walk|inventory|section|revision)\b')


def calls(path):
    uses, out, bg_use, bg = {}, [], {}, {}
    for line in open(path, errors='replace'):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        t = ts(e['timestamp']) if 'timestamp' in e else None
        if e.get('type') == 'assistant':
            for c in e['message'].get('content', []):
                if c.get('type') == 'tool_use' and c['name'] == 'Bash':
                    inp = c.get('input', {})
                    m = CMD.search(inp.get('command', ''))
                    if m and not inp.get('run_in_background'):
                        uses[c['id']] = (t, m.group(1))
                    elif m:
                        bg_use[c['id']] = (t, m.group(1) + ' bg')
        elif e.get('type') == 'user' and t is not None and isinstance(e['message'].get('content'), list):
            for c in e['message']['content']:
                if c.get('type') == 'tool_result' and c['tool_use_id'] in bg_use:
                    tid = re.search(r'background with ID: (\w+)', json.dumps(c.get('content')))
                    if tid:
                        bg[tid.group(1)] = bg_use.pop(c['tool_use_id'])
                if c.get('type') == 'tool_result' and c['tool_use_id'] in uses:
                    t0, sub = uses.pop(c['tool_use_id'])
                    if t0 is not None:
                        out.append((sub, t - t0))
        elif e.get('type') == 'system' and e.get('subtype') == 'task_updated':
            end = e.get('patch', {}).get('end_time')
            if end and e.get('task_id') in bg:
                t0, sub = bg.pop(e['task_id'])
                if t0 is not None:
                    out.append((sub, end / 1000 - t0))
    return out


def main(dirs):
    for rd in dirs:
        run = os.path.basename(rd.rstrip('/'))
        by = collections.defaultdict(list)
        for f in sorted(glob.glob(os.path.join(rd, 'transcripts', '*actor*.json'))):
            for sub, d in calls(f):
                by[sub].append(d)
        allc = [d for v in by.values() for d in v]
        print(f'## {run}: {len(allc)} calls, {sum(allc) / 3600:.2f} h')
        print('| subcommand | calls | total min | median s | max s |')
        print('|---|---|---|---|---|')
        for sub, v in sorted(by.items(), key=lambda kv: -sum(kv[1])):
            print(f'| {sub} | {len(v)} | {sum(v) / 60:.1f} | {statistics.median(v):.0f} | {max(v):.0f} |')


if __name__ == '__main__':
    main(sys.argv[1:])
