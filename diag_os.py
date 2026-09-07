import os, re, py_compile, traceback

print("=" * 60)
print("DIAGNOSTICO COMPLETO")
print("=" * 60)

# 1. Tamanho e se compila
print(f"\n[1] app.py existe: {os.path.exists('app.py')} | bytes: {os.path.getsize('app.py') if os.path.exists('app.py') else 0}")
try:
    py_compile.compile("app.py", doraise=True)
    print("[1] app.py COMPILA OK")
except Exception as e:
    print("[1] ERRO DE SINTAXE no app.py:")
    print(e)

# 2. Procura def cadastrar_servico e rotas
with open("app.py", "r", encoding="utf-8", errors="ignore") as f:
    src = f.read()

print(f"\n[2] 'def cadastrar_servico' aparece {src.count('def cadastrar_servico')} vez(es)")
print(f"[2] '/servico/novo' aparece {src.count('/servico/novo')} vez(es)")
print(f"[2] 'def lista_servicos' aparece {src.count('def lista_servicos')} vez(es)")

# Mostra contexto ao redor de cadastrar_servico
for m in re.finditer(r"def cadastrar_servico", src):
    start = max(0, m.start() - 400)
    end = min(len(src), m.end() + 200)
    print("\n--- trecho def cadastrar_servico ---")
    print(src[start:end][:600])
    print("--- fim trecho ---")

# 3. Importa o app e lista rotas reais
print("\n[3] Importando app e listando rotas com 'servico' ou 'os'...")
try:
    # evita iniciar telegram/thread se possível
    import sys
    # limpa cache
    if "app" in sys.modules:
        del sys.modules["app"]
    import app as app_mod
    flask_app = getattr(app_mod, "app", None)
    if flask_app is None:
        print("[3] ERRO: módulo app não tem atributo 'app' (Flask)")
    else:
        regras = sorted([str(r) for r in flask_app.url_map.iter_rules()])
        print(f"[3] Total de rotas: {len(regras)}")
        hits = [r for r in regras if "servico" in r.lower() or r.endswith("/os") or "nova" in r.lower() or "cadastrar" in r.lower()]
        if not hits:
            print("[3] NENHUMA rota de servico/os encontrada no url_map!")
        else:
            for r in hits:
                print("   ", r)
        # testa match
        with flask_app.test_request_context("/servico/novo"):
            adapter = flask_app.url_map.bind("127.0.0.1")
            try:
                endpoint, args = adapter.match("/servico/novo", method="GET")
                print(f"[3] MATCH /servico/novo -> endpoint={endpoint} args={args}")
            except Exception as ex:
                print(f"[3] NÃO DEU MATCH /servico/novo: {ex}")
except Exception as e:
    print("[3] FALHA ao importar app:")
    traceback.print_exc()

# 4. Links no template
print("\n[4] Links no template lista_servicos:")
for p in ["templates/servicos/lista_servicos.html", "templates/lista_servicos.html"]:
    if os.path.exists(p):
        t = open(p, encoding="utf-8", errors="ignore").read()
        for h in re.findall(r'href=["\']([^"\']+)["\']', t):
            print(f"   {p}: {h}")

print("\n[5] Template cadastrar_servico existe?", os.path.exists("templates/servicos/cadastrar_servico.html"))
print("=" * 60)
