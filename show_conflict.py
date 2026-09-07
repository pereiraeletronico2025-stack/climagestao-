import re, py_compile, sys

with open("app.py", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

print(f"Total linhas: {len(lines)}")
print("\n===== LINHAS 1320-1500 =====")
for i in range(1319, min(1500, len(lines))):
    print(f"{i+1:4d}|{lines[i].rstrip()}")

print("\n===== TODAS as defs + rotas proximas de notas/servico/os =====")
for i, l in enumerate(lines):
    if re.search(r"def (lista_notas|lista_servicos|cadastrar_servico)\b", l) or \
       re.search(r"@app\.route\(['\"]/(os|notas|servico)", l):
        # contexto
        a = max(0, i-3)
        b = min(len(lines), i+8)
        print(f"\n--- em torno da linha {i+1} ---")
        for j in range(a, b):
            print(f"{j+1:4d}|{lines[j].rstrip()}")
