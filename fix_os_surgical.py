import re, py_compile, sys, os

with open("app.py", "r", encoding="utf-8", errors="ignore") as f:
    src = f.read()
    lines = src.splitlines(keepends=True)

# Estrategia: reescrever o arquivo em "secoes" por def, e
# 1) achar def lista_notas e garantir que so tem rotas /notas
# 2) remover qualquer def lista_servicos e cadastrar_servico
# 3) anexar bloco limpo no final

def split_into_chunks(lines):
    """Divide o arquivo em: preamble + lista de (decorators_lines, def_line, body_lines)"""
    chunks = []
    i = 0
    n = len(lines)
    # preamble ate primeira @app.route ou def no nivel do modulo apos app =
    # melhor: varrer linearmente
    pending_deco = []
    preamble = []
    mode = "pre"
    while i < n:
        line = lines[i]
        stripped = line.lstrip()
        # decorator de rota ou login
        if stripped.startswith("@app.route") or stripped.startswith("@login_required") or stripped.startswith("@admin_required"):
            if mode == "pre":
                mode = "body"
            pending_deco.append(line)
            i += 1
            continue
        if stripped.startswith("def ") and not line.startswith(" ") and not line.startswith("\t"):
            # top-level def
            m = re.match(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", stripped)
            name = m.group(1) if m else "?"
            def_line = line
            i += 1
            body = []
            while i < n:
                l2 = lines[i]
                s2 = l2.lstrip()
                # proxima top-level def ou top-level @app.route ou if __name__
                if (l2.startswith("def ") or (l2.startswith("@") and not l2.startswith(" @"))) and not l2.startswith(" ") and not l2.startswith("\t"):
                    break
                if l2.startswith("if __name__"):
                    break
                # tambem break se linha top-level @app.route
                if re.match(r"^@app\.route", l2) or re.match(r"^@login_required", l2) or re.match(r"^@admin_required", l2):
                    break
                if re.match(r"^def ", l2):
                    break
                body.append(l2)
                i += 1
            chunks.append({
                "deco": pending_deco[:],
                "name": name,
                "def_line": def_line,
                "body": body,
            })
            pending_deco = []
            mode = "body"
            continue
        if line.startswith("if __name__"):
            # resto
            rest = lines[i:]
            return preamble, chunks, pending_deco, rest
        if mode == "pre":
            preamble.append(line)
        else:
            # codigo top-level solto (ex: _last_update_id = 0) - joga no preamble se ainda nao teve def, senao anexa ao body anterior
            if chunks:
                chunks[-1]["body"].append(line)
            else:
                preamble.append(line)
        i += 1
    return preamble, chunks, pending_deco, []

preamble, chunks, pending, rest = split_into_chunks(lines)
print(f"Chunks (funcoes top-level): {len(chunks)}")
for c in chunks:
    routes = [d.strip() for d in c["deco"] if "@app.route" in d]
    if c["name"] in ("lista_notas", "lista_servicos", "cadastrar_servico") or any("/os" in d or "/servico" in d or "/notas" in d for d in routes):
        print(f"  * {c['name']}: routes={routes[:8]}")

# Filtra: remove lista_servicos e cadastrar_servico por completo
# Para lista_notas: limpa decorators que nao sejam /notas
new_chunks = []
for c in chunks:
    if c["name"] in ("lista_servicos", "cadastrar_servico"):
        print(f"  REMOVENDO funcao {c['name']}")
        continue
    if c["name"] == "lista_notas":
        # mantem so rotas de notas
        new_deco = []
        for d in c["deco"]:
            if "@app.route" in d:
                if "/nota" in d.lower() or "notas" in d:
                    new_deco.append(d)
                else:
                    print(f"  Limpando decorator estranho de lista_notas: {d.strip()}")
            else:
                new_deco.append(d)
        if not any("@app.route" in d for d in new_deco):
            new_deco = ["@app.route('/notas')\n", "@login_required\n"]
        c["deco"] = new_deco
    # remove decorator /os ou /servico de QUALQUER outra funcao que nao seja a nossa nova
    cleaned = []
    for d in c["deco"]:
        if "@app.route" in d and re.search(r"['\"]/(os|servico|servicos|lista_servicos|cadastrar_servico|cadastrar-servico|nova-os|nova_os)['\"]", d):
            if c["name"] not in ("lista_servicos", "cadastrar_servico"):
                print(f"  Removendo rota {d.strip()} de {c['name']}")
                continue
        cleaned.append(d)
    c["deco"] = cleaned
    new_chunks.append(c)

# Garante templates
os.makedirs("templates/servicos", exist_ok=True)
if not os.path.exists("templates/servicos/lista_servicos.html"):
    open("templates/servicos/lista_servicos.html","w",encoding="utf-8").write(
        "<html><body><h1>OS</h1><a href='/servico/novo'>Nova OS</a></body></html>"
    )
if not os.path.exists("templates/servicos/cadastrar_servico.html"):
    open("templates/servicos/cadastrar_servico.html","w",encoding="utf-8").write(
        "<html><body><h1>Nova OS</h1><form method='post'><button>Salvar</button></form></body></html>"
    )

# Bloco novo OS
os_block = '''
@app.route("/servicos")
@app.route("/servico")
@app.route("/lista_servicos")
@app.route("/os")
@login_required
def lista_servicos():
    conn = get_db()
    servicos = conn.execute("SELECT * FROM AgendamentoOnline ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("servicos/lista_servicos.html", servicos=servicos)

@app.route("/servico/novo", methods=["GET", "POST"])
@app.route("/servicos/novo", methods=["GET", "POST"])
@app.route("/cadastrar_servico", methods=["GET", "POST"])
@app.route("/cadastrar-servico", methods=["GET", "POST"])
@app.route("/nova-os", methods=["GET", "POST"])
@app.route("/nova_os", methods=["GET", "POST"])
@login_required
def cadastrar_servico():
    conn = get_db()
    if request.method == "POST":
        c_id = request.form.get("cliente_id")
        sel = (request.form.get("tipo_servico") or "").strip()
        livre = (request.form.get("tipo_servico_livre") or "").strip()
        tipo_s = sel or livre or "Servico Geral"
        desc = request.form.get("descricao", "")
        equip = request.form.get("equipamento", "")
        try:
            preco = float(request.form.get("preco", 0) or 0)
        except Exception:
            preco = 0.0
        data_s = request.form.get("data_servico") or date.today().isoformat()
        nome_cli, tel, end = "Cliente", "", ""
        if c_id:
            row = conn.execute("SELECT nome, telefone, endereco FROM Cliente WHERE id=?", (c_id,)).fetchone()
            if row:
                nome_cli = row["nome"]
                tel = row["telefone"] or ""
                end = row["endereco"] or ""
        conn.execute(
            """INSERT INTO AgendamentoOnline (
                nome_cliente, telefone, endereco, tipo_servico, tipo_aparelho,
                data_sugerida, valor, status, status_servico, etapa_fluxo, observacao
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Pendente', 'Pendente', 1, ?)""",
            (nome_cli, tel, end, tipo_s, equip, data_s, preco, desc),
        )
        conn.commit()
        conn.close()
        flash("Nova OS cadastrada com sucesso!", "success")
        return redirect(url_for("lista_servicos"))
    clientes = conn.execute("SELECT id, nome, telefone FROM Cliente ORDER BY nome ASC").fetchall()
    try:
        aparelhos = conn.execute("SELECT * FROM CatEquipamento ORDER BY nome ASC").fetchall()
    except Exception:
        aparelhos = []
    try:
        cat_servicos = conn.execute("SELECT * FROM CatServico ORDER BY nome ASC").fetchall()
    except Exception:
        cat_servicos = []
    conn.close()
    return render_template(
        "servicos/cadastrar_servico.html",
        clientes=clientes,
        aparelhos=aparelhos,
        cat_servicos=cat_servicos,
    )

'''

# Reconstroi arquivo
out = []
out.extend(preamble)
for c in new_chunks:
    out.extend(c["deco"])
    out.append(c["def_line"] if c["def_line"].endswith("\n") else c["def_line"] + "\n")
    out.extend(c["body"])

# pending decorators soltos - descarta se forem de servico
for d in pending:
    if "/servico" in d or "/os" in d:
        print("Descartando decorator solto:", d.strip())
        continue
    out.append(d)

# Insere bloco OS antes de if __name__
rest_text = "".join(rest) if rest else ""
if "if __name__" in rest_text:
    idx = rest_text.find("if __name__")
    rest_text = rest_text[:idx] + os_block + "\n" + rest_text[idx:]
elif rest_text.strip():
    rest_text = os_block + "\n" + rest_text
else:
    # if __name__ pode ter ficado no body de alguma func - procura no out
    joined = "".join(out)
    if "if __name__" in joined:
        # reescreve out
        joined = joined.replace("if __name__", os_block + "\nif __name__", 1)
        out = [joined]
        rest_text = ""
    else:
        rest_text = os_block + "\n\nif __name__ == '__main__':\n    app.run(host='0.0.0.0', port=5001, debug=True)\n"

final = "".join(out) + rest_text
# evita duplicar bloco se ja rodou
while final.count("def lista_servicos") > 1:
    # remove primeira ocorrencia do bloco antigo ja limpo - keep last
    first = final.find("def lista_servicos")
    # find start of decorators before it
    start = final.rfind("@app.route", 0, first)
    if start == -1:
        break
    second = final.find("def lista_servicos", first + 1)
    # remove from start to just before second's decorators - complex; simpler break
    break

with open("app.py", "w", encoding="utf-8") as f:
    f.write(final)

print("Arquivo gravado, validando...")
try:
    py_compile.compile("app.py", doraise=True)
    print("COMPILA OK")
except Exception as e:
    print("ERRO COMPILACAO:", e)
    sys.exit(1)

# Import test
for k in list(sys.modules):
    if k == "app" or k.startswith("app."):
        del sys.modules[k]
try:
    import app as app_mod
    print("IMPORT OK, rotas:", len(list(app_mod.app.url_map.iter_rules())))
    ad = app_mod.app.url_map.bind("127.0.0.1")
    for p in ["/servico/novo", "/servicos", "/os", "/notas", "/painel"]:
        try:
            ep, _ = ad.match(p, method="GET")
            print(f"  OK {p} -> {ep}")
        except Exception as ex:
            print(f"  XX {p} -> {ex}")
except Exception as e:
    print("IMPORT FAIL:", e)
    # mostra linhas ao redor do erro se AssertionError
    import traceback
    traceback.print_exc()
    # dump linha 1370
    ls = open("app.py", encoding="utf-8").read().splitlines()
    for i in range(max(0,1360), min(len(ls), 1400)):
        print(f"{i+1}|{ls[i]}")
    sys.exit(1)

print("=== SUCESSO: python app.py ===")
