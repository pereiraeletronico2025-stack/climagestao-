import re, py_compile, sys, os

# ========== TEMPLATES (arquivos separados, sem confusao) ==========
os.makedirs("templates/financeiro", exist_ok=True)
os.makedirs("templates/funcionarios", exist_ok=True)

caixa_html = """<!DOCTYPE html>
<html lang="pt-br"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Caixa Diario</title><link rel="stylesheet" href="/static/style.css">
<style>
body{margin:0;padding:20px;background:#f4f6f9;font-family:Segoe UI,sans-serif}
.c{max-width:1000px;margin:0 auto;background:#fff;border-radius:12px;padding:24px;box-shadow:0 4px 15px rgba(0,0,0,.06)}
.bar{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:16px;padding-bottom:12px;border-bottom:2px solid #eee}
a.btn,button{display:inline-block;padding:10px 16px;border-radius:8px;border:0;color:#fff;font-weight:600;text-decoration:none;cursor:pointer}
.g{background:#6c757d}.b{background:#00a8ff}.d{background:#dc3545;padding:6px 10px}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px}
@media(max-width:700px){.cards{grid-template-columns:1fr}}
.card{border:1px solid #e2e8f0;border-radius:10px;padding:16px}
.t{font-size:.85em;color:#666}.v{font-size:1.35em;font-weight:700;margin-top:6px}
label{display:block;margin:8px 0 4px;font-weight:600;font-size:.9em}
input,select{width:100%;padding:10px;border:1px solid #cbd5e0;border-radius:8px;box-sizing:border-box}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
@media(max-width:700px){.grid{grid-template-columns:1fr}}
table{width:100%;border-collapse:collapse;margin-top:12px}th,td{padding:10px;border-bottom:1px solid #eee;text-align:left;font-size:.9em}
th{background:#f8f9fa}.alert{padding:12px;margin-bottom:12px;border-radius:8px;background:#d1e7dd}
</style></head><body><div class="c">
<div class="bar">
<a class="btn g" href="/painel">Painel</a>
<h2 style="margin:0">Caixa Diario</h2>
<a class="btn g" href="/faturamento">Faturamento</a>
</div>
{% with messages = get_flashed_messages(with_categories=true) %}
{% if messages %}{% for cat,msg in messages %}<div class="alert">{{ msg }}</div>{% endfor %}{% endif %}
{% endwith %}
<div class="cards">
<div class="card"><div class="t">Entradas</div><div class="v" style="color:#2e7d32">R$ {{ '%.2f'|format(total_entradas|default(0)) }}</div></div>
<div class="card"><div class="t">Saidas</div><div class="v" style="color:#c62828">R$ {{ '%.2f'|format(total_saidas|default(0)) }}</div></div>
<div class="card"><div class="t">Saldo do Dia</div><div class="v" style="color:#0d47a1">R$ {{ '%.2f'|format(saldo_dia|default(saldo|default(0))) }}</div></div>
</div>
<div class="card" style="margin-bottom:16px">
<h3 style="margin-top:0">Novo Lancamento</h3>
<form method="POST" action="/caixa">
<div class="grid">
<div><label>Data</label><input type="date" name="data" value="{{ data_selecionada|default('') }}"></div>
<div><label>Tipo</label><select name="tipo"><option value="Entrada">Entrada</option><option value="Saida">Saida</option></select></div>
<div><label>Categoria</label><input name="categoria" value="Geral"></div>
<div><label>Descricao</label><input name="descricao" required></div>
<div><label>Valor</label><input type="number" step="0.01" name="valor" required></div>
<div><label>Pagamento</label><select name="forma_pagamento"><option>Dinheiro</option><option>PIX</option><option>Cartao</option><option>Transferencia</option></select></div>
</div>
<button class="btn b" style="margin-top:12px" type="submit">Salvar</button>
</form>
</div>
<form method="GET" action="/caixa" style="margin-bottom:10px;display:flex;gap:8px;align-items:end;flex-wrap:wrap">
<div><label>Filtrar data</label><input type="date" name="data" value="{{ data_selecionada|default('') }}"></div>
<button class="btn g" type="submit">Filtrar</button>
</form>
<table>
<thead><tr><th>Data</th><th>Tipo</th><th>Descricao</th><th>Valor</th><th>Pgto</th><th></th></tr></thead>
<tbody>
{% if lancamentos %}
{% for l in lancamentos %}
<tr>
<td>{{ l.data }}</td><td>{{ l.tipo }}</td><td>{{ l.descricao }}</td>
<td><b>R$ {{ '%.2f'|format(l.valor or 0) }}</b></td><td>{{ l.forma_pagamento or '-' }}</td>
<td><a class="btn d" href="/caixa/excluir/{{ l.id }}" onclick="return confirm('Excluir?')">Excluir</a></td>
</tr>
{% endfor %}
{% else %}
<tr><td colspan="6" style="text-align:center;color:#888;padding:28px">Nenhum lancamento neste dia.</td></tr>
{% endif %}
</tbody></table>
</div></body></html>
"""
open("templates/financeiro/caixa.html","w",encoding="utf-8").write(caixa_html)

fat_html = """<!DOCTYPE html>
<html lang="pt-br"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Faturamento</title><link rel="stylesheet" href="/static/style.css">
<style>
body{margin:0;padding:20px;background:#f4f6f9;font-family:Segoe UI,sans-serif}
.c{max-width:1000px;margin:0 auto;background:#fff;border-radius:12px;padding:24px}
.bar{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:16px;padding-bottom:12px;border-bottom:2px solid #eee}
a.btn{display:inline-block;padding:10px 16px;border-radius:8px;color:#fff;text-decoration:none;font-weight:600;background:#6c757d}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px}
@media(max-width:700px){.cards{grid-template-columns:1fr}}
.card{border:1px solid #e2e8f0;border-radius:10px;padding:16px}
.t{font-size:.85em;color:#666}.v{font-size:1.35em;font-weight:700;margin-top:6px}
table{width:100%;border-collapse:collapse}th,td{padding:10px;border-bottom:1px solid #eee;text-align:left;font-size:.9em}
th{background:#f8f9fa}
</style></head><body><div class="c">
<div class="bar"><a class="btn" href="/painel">Painel</a><h2 style="margin:0">Faturamento {{ mes|default('') }}</h2><a class="btn" href="/caixa">Caixa</a></div>
<div class="cards">
<div class="card"><div class="t">Entradas</div><div class="v" style="color:#2e7d32">R$ {{ '%.2f'|format(total_entradas|default(0)) }}</div></div>
<div class="card"><div class="t">Saidas</div><div class="v" style="color:#c62828">R$ {{ '%.2f'|format(total_saidas|default(0)) }}</div></div>
<div class="card"><div class="t">Resultado</div><div class="v" style="color:#0d47a1">R$ {{ '%.2f'|format((total_entradas|default(0))-(total_saidas|default(0))) }}</div></div>
</div>
<table><thead><tr><th>Data</th><th>Tipo</th><th>Descricao</th><th>Valor</th></tr></thead><tbody>
{% if lancamentos %}
{% for l in lancamentos %}
<tr><td>{{ l.data }}</td><td>{{ l.tipo }}</td><td>{{ l.descricao }}</td><td>R$ {{ '%.2f'|format(l.valor or 0) }}</td></tr>
{% endfor %}
{% else %}
<tr><td colspan="4" style="text-align:center;color:#888;padding:28px">Sem movimentacoes neste mes.</td></tr>
{% endif %}
</tbody></table></div></body></html>
"""
open("templates/financeiro/faturamento.html","w",encoding="utf-8").write(fat_html)

open("templates/funcionarios/lista_funcionarios.html","w",encoding="utf-8").write("""<!DOCTYPE html>
<html lang="pt-br"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Funcionarios</title><link rel="stylesheet" href="/static/style.css">
<style>
body{margin:0;padding:20px;background:#f4f6f9;font-family:Segoe UI,sans-serif}
.c{max-width:1000px;margin:0 auto;background:#fff;border-radius:12px;padding:24px}
.bar{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:16px;align-items:center}
a.btn{display:inline-block;padding:10px 16px;border-radius:8px;color:#fff;text-decoration:none;font-weight:600}
.g{background:#6c757d}.v{background:#28a745}.e{background:#ff9800;padding:6px 10px}.d{background:#dc3545;padding:6px 10px}
table{width:100%;border-collapse:collapse}th,td{padding:12px;border-bottom:1px solid #eee;text-align:left}
th{background:#f8f9fa}.empty{text-align:center;padding:40px;color:#888}
.alert{padding:12px;margin-bottom:12px;border-radius:8px;background:#d1e7dd}
</style></head><body><div class="c">
<div class="bar"><a class="btn g" href="/painel">Painel</a><h2 style="margin:0">Funcionarios</h2><a class="btn v" href="/funcionario/novo">+ Novo Funcionario</a></div>
{% with messages = get_flashed_messages(with_categories=true) %}{% if messages %}{% for c,m in messages %}<div class="alert">{{ m }}</div>{% endfor %}{% endif %}{% endwith %}
<table><thead><tr><th>ID</th><th>Nome</th><th>Telefone</th><th>Cargo</th><th>Salario</th><th>Acoes</th></tr></thead><tbody>
{% if funcionarios %}
{% for f in funcionarios %}
<tr>
<td>#{{ f.id }}</td><td><b>{{ f.nome }}</b></td><td>{{ f.telefone or '-' }}</td><td>{{ f.cargo or '-' }}</td>
<td>R$ {{ '%.2f'|format(f.salario_base or 0) }}</td>
<td><a class="btn e" href="/funcionario/editar/{{ f.id }}">Editar</a>
<a class="btn d" href="/funcionario/excluir/{{ f.id }}" onclick="return confirm('Apagar?')">Excluir</a></td>
</tr>
{% endfor %}
{% else %}
<tr><td colspan="6" class="empty">Nenhum funcionario.<br><br><a class="btn v" href="/funcionario/novo">Cadastrar</a></td></tr>
{% endif %}
</tbody></table></div></body></html>
""")

open("templates/funcionarios/cadastrar_funcionario.html","w",encoding="utf-8").write("""<!DOCTYPE html>
<html lang="pt-br"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Novo Funcionario</title><link rel="stylesheet" href="/static/style.css">
<style>
body{margin:0;padding:20px;background:#f4f6f9;font-family:Segoe UI,sans-serif}
.box{max-width:640px;margin:0 auto;background:#fff;border-radius:12px;padding:28px}
label{display:block;margin:12px 0 6px;font-weight:600}
input{width:100%;padding:11px;border:1px solid #cbd5e0;border-radius:8px;box-sizing:border-box}
a.btn,button{display:inline-block;padding:12px 18px;border-radius:8px;border:0;color:#fff;font-weight:600;text-decoration:none;cursor:pointer}
.g{background:#6c757d}.v{background:#28a745;width:100%;margin-top:16px}
</style></head><body><div class="box">
<a class="btn g" href="/funcionarios">Voltar</a>
<h2>Novo Funcionario</h2>
<form method="POST" action="/funcionario/novo">
<label>Nome *</label><input name="nome" required>
<label>Email</label><input name="email" type="email">
<label>Telefone</label><input name="telefone">
<label>Cargo</label><input name="cargo">
<label>Salario Base</label><input name="salario_base" type="number" step="0.01" value="0">
<label>Comissao %</label><input name="comissao_percentual" type="number" step="0.01" value="0">
<button class="v" type="submit">Salvar</button>
</form></div></body></html>
""")

open("templates/funcionarios/editar_funcionario.html","w",encoding="utf-8").write("""<!DOCTYPE html>
<html lang="pt-br"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Editar Funcionario</title><link rel="stylesheet" href="/static/style.css">
<style>
body{margin:0;padding:20px;background:#f4f6f9;font-family:Segoe UI,sans-serif}
.box{max-width:640px;margin:0 auto;background:#fff;border-radius:12px;padding:28px}
label{display:block;margin:12px 0 6px;font-weight:600}
input{width:100%;padding:11px;border:1px solid #cbd5e0;border-radius:8px;box-sizing:border-box}
a.btn,button{display:inline-block;padding:12px 18px;border-radius:8px;border:0;color:#fff;font-weight:600;text-decoration:none;cursor:pointer}
.g{background:#6c757d}.v{background:#28a745;width:100%;margin-top:16px}
</style></head><body><div class="box">
<a class="btn g" href="/funcionarios">Voltar</a>
<h2>Editar Funcionario</h2>
<form method="POST">
<label>Nome *</label><input name="nome" value="{{ f.nome }}" required>
<label>Email</label><input name="email" value="{{ f.email or '' }}">
<label>Telefone</label><input name="telefone" value="{{ f.telefone or '' }}">
<label>Cargo</label><input name="cargo" value="{{ f.cargo or '' }}">
<label>Salario</label><input name="salario_base" type="number" step="0.01" value="{{ f.salario_base or 0 }}">
<label>Comissao %</label><input name="comissao_percentual" type="number" step="0.01" value="{{ f.comissao_percentual or 0 }}">
<button class="v" type="submit">Salvar</button>
</form></div></body></html>
""")

open("templates/funcionarios/bater_ponto.html","w",encoding="utf-8").write("""<!DOCTYPE html>
<html lang="pt-br"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ponto</title><link rel="stylesheet" href="/static/style.css">
<style>
body{margin:0;padding:20px;background:#f4f6f9;font-family:Segoe UI,sans-serif}
.c{max-width:900px;margin:0 auto;background:#fff;border-radius:12px;padding:24px}
.bar{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:16px;align-items:center}
a.btn,button{display:inline-block;padding:10px 16px;border-radius:8px;border:0;color:#fff;font-weight:600;text-decoration:none;cursor:pointer}
.g{background:#6c757d}.v{background:#28a745}
label{display:block;margin:10px 0 6px;font-weight:600}
select{width:100%;padding:11px;border:1px solid #cbd5e0;border-radius:8px;box-sizing:border-box}
.card{border:1px solid #e2e8f0;border-radius:10px;padding:16px;margin-bottom:16px}
table{width:100%;border-collapse:collapse}th,td{padding:10px;border-bottom:1px solid #eee;text-align:left;font-size:.9em}
th{background:#f8f9fa}.alert{padding:12px;margin-bottom:12px;border-radius:8px;background:#d1e7dd}
</style></head><body><div class="c">
<div class="bar"><a class="btn g" href="/painel">Painel</a><h2 style="margin:0">Ponto Facial</h2><a class="btn g" href="/funcionarios">Funcionarios</a></div>
{% with messages = get_flashed_messages(with_categories=true) %}{% if messages %}{% for c,m in messages %}<div class="alert">{{ m }}</div>{% endfor %}{% endif %}{% endwith %}
<div class="card">
<h3 style="margin-top:0">Bater Ponto</h3>
<form method="POST" action="/ponto">
<label>Funcionario</label>
<select name="funcionario_id" required>
<option value="">Selecione...</option>
{% for f in funcionarios %}<option value="{{ f.id }}">{{ f.nome }}</option>{% endfor %}
</select>
<label>Tipo</label>
<select name="tipo"><option value="Entrada">Entrada</option><option value="Saida">Saida</option></select>
<button class="btn v" style="margin-top:12px" type="submit">Registrar</button>
</form>
</div>
<table><thead><tr><th>Data</th><th>Funcionario</th><th>Entrada</th><th>Saida</th><th>Horas</th></tr></thead><tbody>
{% if pontos %}
{% for p in pontos %}
<tr>
<td>{{ p.data or '-' }}</td>
<td>{{ p.funcionario_nome or p.funcionario_id or '-' }}</td>
<td>{{ p.hora_entrada or '-' }}</td>
<td>{{ p.hora_saida or '-' }}</td>
<td>{{ p.total_horas or '-' }}</td>
</tr>
{% endfor %}
{% else %}
<tr><td colspan="5" style="text-align:center;color:#888;padding:28px">Nenhum ponto registrado.</td></tr>
{% endif %}
</tbody></table></div></body></html>
""")
print("[OK] templates")

# ========== PATCH app.py ==========
with open("app.py","r",encoding="utf-8",errors="ignore") as f:
    src = f.read()

# Patch funcao caixa: garantir saldo_dia no render_template
# Abordagem: substituir def caixa inteira se existir, senao anexar

def remove_defs(src, names):
    for name in names:
        pat = re.compile(
            r"(?:^@app\.route\([^\n]*\)\s*\n)+"
            r"(?:^@login_required\s*\n)?"
            r"^def " + name + r"\s*\(.*?(?=^@app\.route|^def |^if __name__)",
            re.M | re.S
        )
        src, n = pat.subn("\n", src)
        print(f" remove {name}: {n}")
    return src

src = remove_defs(src, [
    "caixa","excluir_caixa","faturamento","relatorios",
    "lista_funcionarios","cadastrar_funcionario","editar_funcionario","excluir_funcionario",
    "ponto_eletronico"
])

# bloco novo - so aspas simples/duplas normais, CREATE com aspas simples triplas via concat
bloco = r'''

@app.route('/caixa', methods=['GET', 'POST'])
@app.route('/caixa-diario', methods=['GET', 'POST'])
@login_required
def caixa():
    conn = get_db()
    if request.method == 'POST':
        data_mov = request.form.get('data') or date.today().isoformat()
        tipo = request.form.get('tipo', 'Entrada')
        categoria = request.form.get('categoria', 'Geral')
        descricao = request.form.get('descricao', '')
        try:
            valor = float(request.form.get('valor', 0) or 0)
        except Exception:
            valor = 0.0
        forma = request.form.get('forma_pagamento', 'Dinheiro')
        conn.execute(
            "INSERT INTO Caixa (data, tipo, categoria, descricao, valor, forma_pagamento) VALUES (?,?,?,?,?,?)",
            (data_mov, tipo, categoria, descricao, valor, forma)
        )
        conn.commit()
        conn.close()
        flash('Movimentacao registrada!', 'success')
        return redirect(url_for('caixa', data=data_mov))
    data_selecionada = request.args.get('data') or date.today().isoformat()
    mes_selecionado = request.args.get('mes') or date.today().strftime('%Y-%m')
    try:
        lancamentos = conn.execute("SELECT * FROM Caixa WHERE data=? ORDER BY id DESC", (data_selecionada,)).fetchall()
    except Exception:
        lancamentos = []
    total_entradas = sum((l['valor'] or 0) for l in lancamentos if (l['tipo'] or '') == 'Entrada')
    total_saidas = sum((l['valor'] or 0) for l in lancamentos if (l['tipo'] or '') in ('Saida', 'Saida'))
    # aceita Saida sem acento e com
    total_saidas = sum((l['valor'] or 0) for l in lancamentos if str(l['tipo'] or '').startswith('Said'))
    saldo = total_entradas - total_saidas
    saldo_dia = saldo
    conn.close()
    return render_template(
        'financeiro/caixa.html',
        lancamentos=lancamentos,
        total_entradas=total_entradas,
        total_saidas=total_saidas,
        saldo=saldo,
        saldo_dia=saldo_dia,
        entradas_hoje=total_entradas,
        saidas_hoje=total_saidas,
        data_selecionada=data_selecionada,
        m=mes_selecionado,
        mes=mes_selecionado
    )

@app.route('/caixa/excluir/<int:id>')
@app.route('/caixa/excluir/<id>')
@login_required
def excluir_caixa(id):
    try:
        id = int(id)
    except Exception:
        return redirect(url_for('caixa'))
    conn = get_db()
    conn.execute("DELETE FROM Caixa WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash('Lancamento excluido.', 'info')
    return redirect(url_for('caixa'))

@app.route('/faturamento')
@app.route('/faturamento-mensal')
@login_required
def faturamento():
    conn = get_db()
    mes_atual = request.args.get('mes') or date.today().strftime('%Y-%m')
    try:
        lancamentos = conn.execute("SELECT * FROM Caixa WHERE data LIKE ? ORDER BY data ASC", (mes_atual + '%',)).fetchall()
    except Exception:
        lancamentos = []
    total_entradas = sum((l['valor'] or 0) for l in lancamentos if (l['tipo'] or '') == 'Entrada')
    total_saidas = sum((l['valor'] or 0) for l in lancamentos if str(l['tipo'] or '').startswith('Said'))
    conn.close()
    return render_template(
        'financeiro/faturamento.html',
        lancamentos=lancamentos,
        total_entradas=total_entradas,
        total_saidas=total_saidas,
        faturamento_mes=total_entradas,
        despesas_mes=total_saidas,
        lucro_mes=total_entradas - total_saidas,
        mes=mes_atual
    )

@app.route('/relatorios')
@login_required
def relatorios():
    if os.path.exists('templates/financeiro/relatorios.html'):
        return render_template('financeiro/relatorios.html')
    return redirect(url_for('faturamento'))

@app.route('/funcionarios')
@app.route('/funcionario')
@login_required
def lista_funcionarios():
    conn = get_db()
    conn.execute("CREATE TABLE IF NOT EXISTS Funcionario (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT, telefone TEXT, cargo TEXT, salario_base REAL, comissao_percentual REAL)")
    conn.commit()
    funcionarios = conn.execute("SELECT * FROM Funcionario ORDER BY nome ASC").fetchall()
    conn.close()
    return render_template('funcionarios/lista_funcionarios.html', funcionarios=funcionarios)

@app.route('/funcionario/novo', methods=['GET', 'POST'])
@app.route('/funcionarios/novo', methods=['GET', 'POST'])
@app.route('/cadastrar_funcionario', methods=['GET', 'POST'])
@app.route('/cadastrar-funcionario', methods=['GET', 'POST'])
@login_required
def cadastrar_funcionario():
    conn = get_db()
    conn.execute("CREATE TABLE IF NOT EXISTS Funcionario (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT, telefone TEXT, cargo TEXT, salario_base REAL, comissao_percentual REAL)")
    conn.commit()
    if request.method == 'POST':
        nome = (request.form.get('nome') or '').strip()
        email = request.form.get('email') or ''
        telefone = request.form.get('telefone') or ''
        cargo = request.form.get('cargo') or ''
        try:
            salario = float(request.form.get('salario_base', 0) or 0)
        except Exception:
            salario = 0.0
        try:
            comissao = float(request.form.get('comissao_percentual', 0) or 0)
        except Exception:
            comissao = 0.0
        if not nome:
            flash('Nome obrigatorio.', 'warning')
            conn.close()
            return render_template('funcionarios/cadastrar_funcionario.html')
        conn.execute(
            "INSERT INTO Funcionario (nome, email, telefone, cargo, salario_base, comissao_percentual) VALUES (?,?,?,?,?,?)",
            (nome, email, telefone, cargo, salario, comissao)
        )
        conn.commit()
        conn.close()
        flash('Funcionario cadastrado!', 'success')
        return redirect(url_for('lista_funcionarios'))
    conn.close()
    return render_template('funcionarios/cadastrar_funcionario.html')

@app.route('/funcionario/editar/<int:id>', methods=['GET', 'POST'])
@app.route('/funcionario/editar/<id>', methods=['GET', 'POST'])
@login_required
def editar_funcionario(id):
    try:
        id = int(id)
    except Exception:
        return redirect(url_for('lista_funcionarios'))
    conn = get_db()
    if request.method == 'POST':
        nome = (request.form.get('nome') or '').strip()
        email = request.form.get('email') or ''
        telefone = request.form.get('telefone') or ''
        cargo = request.form.get('cargo') or ''
        try:
            salario = float(request.form.get('salario_base', 0) or 0)
        except Exception:
            salario = 0.0
        try:
            comissao = float(request.form.get('comissao_percentual', 0) or 0)
        except Exception:
            comissao = 0.0
        conn.execute(
            "UPDATE Funcionario SET nome=?, email=?, telefone=?, cargo=?, salario_base=?, comissao_percentual=? WHERE id=?",
            (nome, email, telefone, cargo, salario, comissao, id)
        )
        conn.commit()
        conn.close()
        flash('Funcionario atualizado!', 'success')
        return redirect(url_for('lista_funcionarios'))
    frow = conn.execute("SELECT * FROM Funcionario WHERE id=?", (id,)).fetchone()
    conn.close()
    if not frow:
        flash('Nao encontrado.', 'warning')
        return redirect(url_for('lista_funcionarios'))
    return render_template('funcionarios/editar_funcionario.html', f=frow, funcionario=frow)

@app.route('/funcionario/excluir/<int:id>')
@app.route('/funcionario/excluir/<id>')
@login_required
def excluir_funcionario(id):
    try:
        id = int(id)
    except Exception:
        return redirect(url_for('lista_funcionarios'))
    conn = get_db()
    conn.execute("DELETE FROM Funcionario WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash('Funcionario removido.', 'info')
    return redirect(url_for('lista_funcionarios'))

@app.route('/ponto', methods=['GET', 'POST'])
@app.route('/ponto-facial', methods=['GET', 'POST'])
@app.route('/bater-ponto', methods=['GET', 'POST'])
@app.route('/bater_ponto', methods=['GET', 'POST'])
@app.route('/espelho-ponto', methods=['GET', 'POST'])
@login_required
def ponto_eletronico():
    conn = get_db()
    conn.execute("CREATE TABLE IF NOT EXISTS Funcionario (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT, telefone TEXT, cargo TEXT, salario_base REAL, comissao_percentual REAL)")
    conn.execute("CREATE TABLE IF NOT EXISTS Ponto (id INTEGER PRIMARY KEY AUTOINCREMENT, funcionario_id INTEGER, data TEXT, hora_entrada TEXT, hora_saida TEXT, total_horas REAL, horas_extras REAL, foto_base64 TEXT)")
    conn.commit()
    if request.method == 'POST':
        func_id = request.form.get('funcionario_id')
        tipo_reg = request.form.get('tipo', 'Entrada')
        hoje = date.today().isoformat()
        agora = datetime.now().strftime('%H:%M:%S')
        if not func_id:
            flash('Selecione o funcionario.', 'warning')
        elif tipo_reg == 'Entrada':
            conn.execute("INSERT INTO Ponto (funcionario_id, data, hora_entrada) VALUES (?,?,?)", (func_id, hoje, agora))
            conn.commit()
            flash('Entrada registrada as ' + agora, 'success')
        else:
            row = conn.execute(
                "SELECT id, hora_entrada FROM Ponto WHERE funcionario_id=? AND data=? AND (hora_saida IS NULL OR hora_saida='') ORDER BY id DESC LIMIT 1",
                (func_id, hoje)
            ).fetchone()
            total = None
            if row:
                try:
                    if row['hora_entrada']:
                        h1 = datetime.strptime(row['hora_entrada'], '%H:%M:%S')
                        h2 = datetime.strptime(agora, '%H:%M:%S')
                        total = round((h2 - h1).total_seconds() / 3600.0, 2)
                except Exception:
                    total = None
                conn.execute("UPDATE Ponto SET hora_saida=?, total_horas=? WHERE id=?", (agora, total, row['id']))
            else:
                conn.execute("INSERT INTO Ponto (funcionario_id, data, hora_saida) VALUES (?,?,?)", (func_id, hoje, agora))
            conn.commit()
            flash('Saida registrada as ' + agora, 'success')
    try:
        pontos = conn.execute(
            "SELECT p.*, f.nome as funcionario_nome FROM Ponto p LEFT JOIN Funcionario f ON p.funcionario_id=f.id ORDER BY p.id DESC LIMIT 50"
        ).fetchall()
    except Exception:
        pontos = []
    funcionarios = conn.execute("SELECT * FROM Funcionario ORDER BY nome ASC").fetchall()
    conn.close()
    return render_template('funcionarios/bater_ponto.html', pontos=pontos, funcionarios=funcionarios)

'''

if 'if __name__' in src:
    idx = src.rfind('if __name__')
    src = src[:idx] + bloco + '\n' + src[idx:]
else:
    src = src + bloco

src = re.sub(r'\n{5,}', '\n\n\n', src)
open('app.py','w',encoding='utf-8').write(src)
py_compile.compile('app.py', doraise=True)
print('[OK] compila')

for k in list(sys.modules):
    if k == 'app' or k.startswith('app.'):
        del sys.modules[k]
import app as M
ad = M.app.url_map.bind('127.0.0.1')
for p in ['/caixa','/faturamento','/ponto','/funcionarios','/funcionario/novo']:
    ep,_ = ad.match(p, method='GET')
    print('MATCH', p, '->', ep)
print('=== SUCESSO: python app.py ===')
