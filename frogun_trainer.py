#!/usr/bin/env python3
# frogun trainer
# made this bc i died 47 times on the same boss and gave up. fuck this shit
#
# uses scanmem to find the health and then keeps rewriting the value
# needs root bc it reads the game memory

import argparse
import os
import re
import select
import shutil
import signal
import struct
import subprocess
import sys
import time

# scanmem prompt looks like "123> " or just "> "
PROMPT_RE = re.compile(rb"\d*> $")
MATCHES_RE = re.compile(r"we currently have (\d+) matches")
# "list" line: [ 0] 7f2a7432d43c, 34 +      3eb743c,  misc, 5, [I32 I16 I8 ]
LIST_RE = re.compile(r"^\[\s*(\d+)\]\s+([0-9a-f]+),.*?,\s*\S+,\s*(-?\d+),\s*\[([^\]]*)\]")


def acha_pid(nome):
    # steam spawns like 3 processes with Frogun in the name (reaper, bwrap...)
    # so check the actual exe or you grab the wrong one. wasted half an hour on this
    for p in os.listdir("/proc"):
        if not p.isdigit():
            continue
        try:
            exe = os.readlink(f"/proc/{p}/exe")
        except OSError:
            continue
        if os.path.basename(exe) == nome:
            return int(p)
    return None


class ScanMem:
    def __init__(self, pid):
        self.proc = subprocess.Popen(
            ["scanmem", "-p", str(pid)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.le_ate_prompt()

    def le_ate_prompt(self, timeout=300):
        # cant use readline bc the prompt has no \n at the end. another 20 minutes on this bullshit
        buf = b""
        fd = self.proc.stdout.fileno()
        limite = time.monotonic() + timeout
        while not PROMPT_RE.search(buf):
            falta = limite - time.monotonic()
            if falta <= 0:
                raise TimeoutError("scanmem travou??")
            ok, _, _ = select.select([fd], [], [], falta)
            if not ok:
                continue
            pedaco = os.read(fd, 65536)
            if not pedaco:
                raise RuntimeError("scanmem morreu do nada:\n" + buf.decode(errors="replace"))
            buf += pedaco
        # print(buf)
        return buf.decode(errors="replace")

    def cmd(self, c):
        self.proc.stdin.write(c.encode() + b"\n")
        self.proc.stdin.flush()
        return self.le_ate_prompt()

    def scan(self, val):
        out = self.cmd(str(val))
        achou = MATCHES_RE.findall(out)
        return int(achou[-1]) if achou else None

    def lista(self):
        res = []
        for linha in self.cmd("list").splitlines():
            m = LIST_RE.match(linha.strip())
            if m:
                res.append({
                    "id": int(m.group(1)),
                    "addr": int(m.group(2), 16),
                    "value": int(m.group(3)),
                    "types": m.group(4).split(),
                })
        return res

    def fecha(self):
        if self.proc.poll() is None:
            try:
                self.proc.stdin.write(b"exit\n")
                self.proc.stdin.flush()
                self.proc.wait(timeout=3)
            except Exception:
                self.proc.kill()


def pergunta_num(txt):
    while True:
        r = input(txt).strip()
        try:
            return int(r)
        except ValueError:
            print("  numero, porra")


def escreve(pid, addr, v):
    with open(f"/proc/{pid}/mem", "r+b", buffering=0) as f:
        f.seek(addr)
        f.write(struct.pack("<i", v))


def le(pid, addr):
    with open(f"/proc/{pid}/mem", "rb", buffering=0) as f:
        f.seek(addr)
        return struct.unpack("<i", f.read(4))[0]


def acha_vida(pid, max_matches):
    sm = ScanMem(pid)
    try:
        vida = pergunta_num("quantos coracoes vc tem agora? ")
        print("procurando... (a primeira demora)")
        qtd = sm.scan(vida)
        print(f"  {qtd} enderecos")

        while qtd is None or qtd > max_matches:
            if qtd == 0:
                print("nao sobrou nada. vc digitou errado ou mudou a vida antes da hora. roda de novo")
                return []
            print("\ntoma um dano (ou pega coracao) e me fala o numero novo")
            vida = pergunta_num("e agora? ")
            qtd = sm.scan(vida)
            print(f"  sobraram {qtd}")

        # health is int32. the ones that are only I8/I16 are garbage
        candidatos = [m for m in sm.lista() if "I32" in m["types"]]
        # TODO: sometimes 2-3 addresses are left, could test them one by one instead of writing to all
        return candidatos
    finally:
        sm.fecha()


def main():
    ap = argparse.ArgumentParser(description="hack de vida infinita no frogun pq esse jogo é dificil pra caralho")
    ap.add_argument("--process", default="Frogun", help="nome do executavel (padrao: Frogun)")
    ap.add_argument("--interval", type=float, default=0.2, help="de quanto em quanto tempo regrava a vida (padrao 0.2s)")
    ap.add_argument("--max-matches", type=int, default=5, help="filtra ate sobrar isso (padrao 5)")
    args = ap.parse_args()

    if os.geteuid() != 0:
        print("precisa de root, abrindo com sudo...")
        os.execvp("sudo", ["sudo", sys.executable, os.path.abspath(__file__)] + sys.argv[1:])

    if not shutil.which("scanmem"):
        sys.exit("cade o scanmem? sudo dnf install scanmem (ou apt)")

    pid = acha_pid(args.process)
    if pid is None:
        sys.exit("nao achei o jogo. abre ele e entra numa fase antes")
    print(f"achei o jogo, pid {pid}\n")

    enderecos = acha_vida(pid, args.max_matches)
    if not enderecos:
        sys.exit("nao achei a vida :(")

    qnt_vida = pergunta_num("\nquer travar em quantos coracoes? ")
    for e in enderecos:
        escreve(pid, e["addr"], qnt_vida)
    print(f"escrevi {qnt_vida} em {len(enderecos)} endereco(s), olha se mudou ai")
    if input("mudou? [S/n] ").strip().lower() in ("n", "nao", "não"):
        sys.exit("ixi. roda de novo e muda a vida mais vezes")

    parar = False

    def sai(*_):
        nonlocal parar
        parar = True

    signal.signal(signal.SIGINT, sai)
    signal.signal(signal.SIGTERM, sai)
    while not parar:
        try:
            for e in enderecos:
                if le(pid, e["addr"]) != qnt_vida:
                    escreve(pid, e["addr"], qnt_vida)
        except OSError:
            print("fecghando processo")
            break
        time.sleep(args.interval)
    print("desligado")


if __name__ == "__main__":
    main()
