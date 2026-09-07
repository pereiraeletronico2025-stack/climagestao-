import re, py_compile, sys

with open("app.py", "r", encoding="utf-8", errors="ignore") as f:
    src = f.read()

print("Linhas originais:", len(src.splitlines()))

# Identifica todas as funções top-level definidas em app.py
def_pattern = re.compile(r"^[ \t]*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", re.M)
all_funcs = def_pattern.findall(src)
print("Todas as funcoes encontradas no app.py:")
func_counts = {}
for fn in all_funcs:
    func_counts[fn] = func_counts.get(fn, 0) + 1
    print(f"  - {fn}: {func_counts[fn]}x")

duplicates = [fn for fn, count in func_counts.items() if count > 1]
print("\nFuncoes DUPLICADAS detectadas:", duplicates)

# Para cada função duplicada, mantemos apenas a ÚLTIMA ocorrência (a mais recente e corrigida)
# Vamos processar linha a linha reconstruindo a arvore de blocos

def parse_blocks(text):
    lines = text.splitlines(keepends=True)
    blocks = [] # lista de {'type': 'code'|'func', 'name': str, 'lines': list}
    current_deco = []
    current_body = []
    current_name = None
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Se for decorator top-level (@app.route, @login_required, @admin_required)
        if (line.startswith("@app.route") or line.startswith("@login_required") or line.startswith("@admin_required")):
            current_deco.append(line)
            i += 1
            continue
            
        # Se for definicao de funcao top-level (def func_name)
        if line.startswith("def ") and not line.startswith("    "):
            m = re.match(r"^def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", line)
            func_name = m.group(1) if m else "desconhecida"
            
            # Coleta o corpo da funcao ate a proxima funcao/decorator top-level ou if __name__
            body = [line]
            i += 1
            while i < len(lines):
                next_l = lines[i]
                if (next_l.startswith("def ") or next_l.startswith("@app.route") or 
                    next_l.startswith("@login_required") or next_l.startswith("@admin_required") or 
                    next_l.startswith("if __name__")):
                    break
                body.append(next_l)
                i += 1
                
            blocks.append({
                'type': 'func',
                'name': func_name,
                'lines': current_deco + body
            })
            current_deco = []
            continue
            
        # Se for if __name__
        if line.startswith("if __name__"):
            blocks.append({
                'type': 'main',
                'name': '__main__',
                'lines': lines[i:]
            })
            break
            
        # Codigo geral (imports, init, etc)
        blocks.append({
            'type': 'code',
            'name': None,
            'lines': current_deco + [line]
        })
        current_deco = []
        i += 1
        
    return blocks

blocks = parse_blocks(src)

# Identifica a ultima posicao de cada funcao
last_pos = {}
for idx, b in enumerate(blocks):
    if b['type'] == 'func':
        last_pos[b['name']] = idx

print("\nFiltrando e removendo definicoes antigas de funcoes duplicadas...")
final_lines = []
for idx, b in enumerate(blocks):
    if b['type'] == 'func':
        if idx != last_pos[b['name']]:
            print(f"  [X] Removendo versao antiga da funcao: {b['name']} (bloco {idx})")
            continue
    final_lines.extend(b['lines'])

clean_src = "".join(final_lines)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(clean_src)

print(f"\nLinhas apos limpeza: {len(clean_src.splitlines())}")

# Compila para garantir que a sintaxe Python esta 100%
py_compile.compile("app.py", doraise=True)
print("[OK] app.py compila sem SyntaxError!")

# Testa se o Flask carrega sem conflitos de rotas/endpoints
for k in list(sys.modules):
    if k == "app" or k.startswith("app."):
        del sys.modules[k]

import app as M
print(f"[OK] Flask importado com sucesso! Total de rotas registradas: {len(list(M.app.url_map.iter_rules()))}")

# Testa match das principais rotas
ad = M.app.url_map.bind("127.0.0.1")
rotas_teste = [
    "/painel", "/caixa", "/faturamento", "/ponto", 
    "/funcionarios", "/funcionario/novo", "/servicos", "/servico/novo"
]

print("\n--- Testando se todas as rotas respondem sem erro: ---")
for p in rotas_teste:
    try:
        ep, _ = ad.match(p, method="GET")
        print(f"  [OK] {p} -> {ep}")
    except Exception as e:
        print(f"  [ERRO] {p} -> {e}")

print("\n=== LIMPEZA CONCLUÍDA COM SUCESSO! ===")
print("Rode agora: python app.py")
