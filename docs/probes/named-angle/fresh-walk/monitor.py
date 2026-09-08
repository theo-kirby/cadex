import os, signal, subprocess, sys, time
start=time.monotonic()
p=subprocess.Popen(sys.argv[1:], start_new_session=True)
peak=0
while p.poll() is None:
    rows=[list(map(int,line.split())) for line in subprocess.check_output(['ps','-axo','pid=,ppid=,rss='],text=True).splitlines()]
    ids={p.pid}
    for _ in range(12):
        ids.update(pid for pid,ppid,rss in rows if ppid in ids)
    rss=sum(rss for pid,ppid,rss in rows if pid in ids)*1024
    peak=max(peak,rss)
    if rss>2.9e9 or time.monotonic()-start>850:
        os.killpg(p.pid,signal.SIGTERM)
        raise SystemExit('Resource cutoff')
    time.sleep(.2)
print(f'Monitor: exit={p.returncode} seconds={time.monotonic()-start:.2f} peak_RSS_bytes={peak}',file=sys.stderr)
sys.exit(p.returncode)
