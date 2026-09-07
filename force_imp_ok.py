import os, re, glob

print("=== GRAVACAO FORCADA IMPOSTOS ===")
base = os.getcwd()
tpl_dir = os.path.join(base, "templates", "impostos")
os.makedirs(tpl_dir, exist_ok=True)
tpl_path = os.path.join(tpl_dir, "impostos.html")
app_path = os.path.join(base, "app.py")

# Apaga qualquer impostos.html em pastas erradas
for p in glob.glob(os.path.join(base, "**", "impostos.html"), recursive=True):
    print("Encontrado:", p)

html = r'''<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Simulador de Impostos</title>
<link rel="stylesheet" href="/static/style.css">
<style>
.sim-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:14px 0}
.sim-card{background:#fff;border-radius:10px;padding:14px;border-left:5px solid #00A6FF;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.sim-card.green{border-color:#10b981}.sim-card.red{border-color:#ef4444}
.sim-card.blue{border-color:#3b82f6}.sim-card.orange{border-color:#f59e0b}
.sim-card small{color:#64748b;font-size:.72rem;font-weight:700;text-transform:uppercase}
.sim-card h2{margin:6px 0 0;font-size:1.35rem}
.trib{display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:10px 0;border-bottom:1px solid #e2e8f0}
.trib input[type=number]{width:88px;padding:6px;border:1px solid #cbd5e1;border-radius:6px}
.badge-v{background:#e0f2fe;color:#0369a1;padding:4px 10px;border-radius:6px;font-weight:700;font-size:.85rem;min-width:100px;text-align:center}
.banner{background:#e0f2fe;border:1px solid #00A6FF;color:#0369a1;padding:12px;border-radius:8px;margin-bottom:14px;font-weight:bold}
</style>
</head>
<body>
<div class="hvac-container" style="max-width:1100px;">
  <header class="hvac-header">
    <a href="/painel" class="btn-back">Painel</a>
    <h2>Simulador de Impostos sobre Faturamento</h2>
  </header>

  <div class="banner">NOVA TELA ATIVA  escolha o tributo, altere a % e simule o imposto sobre o faturamento.</div>

  <div class="card-tech" style="margin-bottom:14px;">
    <form method="GET" style="display:flex;gap:10px;flex-wrap:wrap;align-items:end;">
      <div class="form-group">
        <label>Mes (base do Caixa)</label>
        <input type="month" name="mes" class="input-hvac" value="{{ mes }}">
      </div>
      <button class="btn-primary-hvac" style="width:auto;" type="submit">Carregar faturamento do mes</button>
    </form>
  </div>

  <div class="card-tech" style="margin-bottom:16px;">
    <h3 style="margin-top:0;color:#00A6FF;">1) Base e regime</h3>
    <div class="form-grid">
      <div class="form-group">
        <label>Faturamento para simulacao (R$)</label>
        <input type="number" step="0.01" id="fat" class="input-hvac" value="{{ fat_num }}" oninput="calc()">
      </div>
      <div class="form-group">
        <label>Escolha o tributo / regime</label>
        <select id="regime" class="input-hvac" onchange="setRegime()">
          <option value="mei">MEI (valor fixo)</option>
          <option value="simples6" selected>Simples Nacional ~6% (servicos)</option>
          <option value="simples4">Simples ~4,5% + ISS 2%</option>
          <option value="simples15">Simples Anexo V ~15,5%</option>
          <option value="presumido">Lucro Presumido (pacote)</option>
          <option value="custom">Personalizado (voce marca)</option>
        </select>
      </div>
    </div>

    <h3 style="color:#00A6FF;">2) Tributos (ligue e altere a %)</h3>
    <div id="box"></div>

    <div class="sim-grid">
      <div class="sim-card green"><small>Faturamento</small><h2 id="o1">R$ 0,00</h2></div>
      <div class="sim-card orange"><small>Carga media</small><h2 id="o2">0%</h2></div>
      <div class="sim-card red"><small>Total impostos</small><h2 id="o3">R$ 0,00</h2></div>
      <div class="sim-card blue"><small>Liquido</small><h2 id="o4">R$ 0,00</h2></div>
    </div>

    <button type="button" class="btn-primary-hvac" style="width:auto;margin-top:8px;" onclick="preencherGuia()">Usar total no formulario de guia abaixo</button>
  </div>

  <div class="card-tech" style="margin-bottom:16px;">
    <h3 style="margin-top:0;">3) Salvar guia no mes {{ mes }}</h3>
    <form method="POST" class="form-grid">
      <input type="hidden" name="acao" value="add">
      <input type="hidden" name="mes" value="{{ mes }}">
      <div class="form-group" style="grid-column:span 2;">
        <label>Descricao</label>
        <input class="input-hvac" name="descricao" id="d" required placeholder="Ex: DAS Simples">
      </div>
      <div class="form-group">
        <label>Valor (R$)</label>
        <input class="input-hvac" type="number" step="0.01" name="valor" id="v" value="0" required>
      </div>
      <div class="form-group">
        <label>Vencimento</label>
        <input class="input-hvac" type="date" name="venc">
      </div>
      <div class="form-group">
        <label>Tipo</label>
        <select class="input-hvac" name="tipo" id="t">
          <option>Simples</option><option>MEI</option><option>ISS</option>
          <option>PIS/COFINS</option><option>IRPJ/CSLL</option><option>Outro</option>
        </select>
      </div>
      <div class="form-group">
        <label>Status</label>
        <select class="input-hvac" name="status"><option>Pendente</option><option>Pago</option></select>
      </div>
      <button class="btn-primary-hvac" style="width:auto;" type="submit">Salvar lancamento</button>
    </form>
  </div>

  <div class="card-tech">
    <h3 style="margin-top:0;">Lancamentos {{ mes }}  Pendente R$ {{ pend_txt }} | Pago R$ {{ pago_txt }}</h3>
    <table class="tech-table">
      <thead><tr><th>Descricao</th><th>Tipo</th><th>Valor</th><th>Venc</th><th>Status</th><th>Acao</th></tr></thead>
      <tbody>
      {% for i in impostos %}
        <tr>
          <td>{{ i.descricao }}</td>
          <td>{{ i.tipo }}</td>
          <td>R$ {{ i.valor_txt }}</td>
          <td>{{ i.vencimento }}</td>
          <td>{{ i.status }}</td>
          <td>
            {% if i.status != 'Pago' %}
            <form method="POST" style="display:inline">
              <input type="hidden" name="acao" value="pagar">
              <input type="hidden" name="id" value="{{ i.id }}">
              <input type="hidden" name="mes" value="{{ mes }}">
              <button class="status-badge badge-success" style="border:0;cursor:pointer" type="submit">Marcar pago</button>
            </form>
            {% endif %}
          </td>
        </tr>
      {% else %}
        <tr><td colspan="6" style="text-align:center;color:#888;padding:16px;">Nenhum lancamento.</td></tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
</div>

<script>
var MEI = {{ mei_num }};
var T = [
  {id:'mei', n:'MEI (fixo mensal)', p:0, f:MEI, tipo:'MEI', on:0},
  {id:'das', n:'DAS Simples Nacional', p:6, f:0, tipo:'Simples', on:1},
  {id:'iss', n:'ISS', p:2, f:0, tipo:'ISS', on:0},
  {id:'pis', n:'PIS', p:0.65, f:0, tipo:'PIS/COFINS', on:0},
  {id:'cofins', n:'COFINS', p:3, f:0, tipo:'PIS/COFINS', on:0},
  {id:'irpj', n:'IRPJ (presumido approx)', p:4.8, f:0, tipo:'IRPJ/CSLL', on:0},
  {id:'csll', n:'CSLL (presumido approx)', p:2.88, f:0, tipo:'IRPJ/CSLL', on:0},
  {id:'out', n:'Outro / extra', p:0, f:0, tipo:'Outro', on:0}
];
function m(n){n=+n||0;return n.toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2});}
function draw(){
  var h='';
  T.forEach(function(t,i){
    h+='<div class="trib">'+
      '<input type="checkbox" '+(t.on?'checked':'')+' onchange="T['+i+'].on=this.checked?1:0;calc()">'+
      '<div style="flex:1;min-width:180px"><b>'+t.n+'</b><br><small style="color:#64748b">'+t.tipo+'</small></div>'+
      '<span>% <input type="number" step="0.01" value="'+t.p+'" onchange="T['+i+'].p=parseFloat(this.value)||0;calc()"></span>'+
      '<span>Fixo <input type="number" step="0.01" value="'+t.f+'" onchange="T['+i+'].f=parseFloat(this.value)||0;calc()"></span>'+
      '<span class="badge-v" id="r'+t.id+'">R$ 0,00</span></div>';
  });
  document.getElementById('box').innerHTML=h; calc();
}
function setRegime(){
  var r=document.getElementById('regime').value;
  T.forEach(function(t){t.on=0});
  function on(id,p){var t=T.find(function(x){return x.id===id}); if(!t)return; t.on=1; if(p!=null)t.p=p;}
  if(r==='mei') on('mei');
  if(r==='simples6') on('das',6);
  if(r==='simples4'){ on('das',4.5); on('iss',2); }
  if(r==='simples15') on('das',15.5);
  if(r==='presumido'){ on('iss',3); on('pis'); on('cofins'); on('irpj'); on('csll'); }
  draw();
}
function calc(){
  var fat=parseFloat(document.getElementById('fat').value)||0, tot=0;
  T.forEach(function(t){
    var v=t.on? (fat*(t.p/100)+(t.f||0)) : 0; tot+=v;
    var el=document.getElementById('r'+t.id); if(el) el.innerText='R$ '+m(v);
  });
  var liq=fat-tot, pc=fat>0?(tot/fat*100):0;
  document.getElementById('o1').innerText='R$ '+m(fat);
  document.getElementById('o2').innerText=m(pc)+'%';
  document.getElementById('o3').innerText='R$ '+m(tot);
  document.getElementById('o4').innerText='R$ '+m(liq);
  window._tot=tot;
}
function preencherGuia(){
  calc();
  var reg=document.getElementById('regime').selectedOptions[0].text;
  document.getElementById('d').value='Simulacao - '+reg;
  document.getElementById('v').value=(window._tot||0).toFixed(2);
  alert('Valor R$ '+m(window._tot||0)+' preenchido. Clique em Salvar lancamento.');
  document.getElementById('v').scrollIntoView({behavior:'smooth'});
}
window.onload=function(){ setRegime(); };
</script>
</body>
</html>
'''

# grava template
with open(tpl_path, "w", encoding="utf-8", newline="\n") as f:
    f.write(html)

# valida template
with open(tpl_path, "r", encoding="utf-8") as f:
    t = f.read()
assert "NOVA TELA ATIVA" in t, "FALHA ao gravar template"
assert "config.valor_mei_padrao" not in t, "Template ainda tem format perigoso"
print("[OK] Template OK:", tpl_path)

# ---- app.py ----
with open(app_path, "r", encoding="utf-8") as f:
    code = f.read()
if code.startswith("\ufeff"):
    code = code.lstrip("\ufeff")

# remove TODOS os blocos de rota que mencionam impostos
parts = re.split(r"(?=\n@app\.route|\nif __name__)", "\n" + code)
head = parts[0]
kept = []
removed = 0
for b in parts[1:]:
    if "/impostos" in b or "gerenciar_impostos" in b or "impostos_simulador" in b:
        removed += 1
        print("Removido bloco impostos #", removed)
        continue
    kept.append(b)
code = head + "".join(kept)

rota = r'''
@app.route('/impostos', methods=['GET', 'POST'])
def impostos_simulador_final():
    from datetime import datetime
    from flask import make_response
    config = get_config() or {}
    conn = get_db()

    def P(v, d=0.0):
        try:
            if v is None: return float(d)
            if isinstance(v, (int, float)): return float(v)
            s = str(v).strip().replace('R$', '').replace(' ', '')
            if ',' in s and '.' in s: s = s.replace('.', '').replace(',', '.')
            elif ',' in s: s = s.replace(',', '.')
            return float(s)
        except Exception:
            return float(d)

    def M(v):
        return f"{P(v):.2f}"

    try:
        conn.execute('''CREATE TABLE IF NOT EXISTS Imposto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mes_referencia TEXT, descricao TEXT, valor REAL DEFAULT 0,
            status TEXT DEFAULT 'Pendente', data_vencimento TEXT, data_pagamento TEXT, tipo TEXT DEFAULT 'Simples'
        )''')
        conn.commit()
    except Exception:
        pass

    mes = request.args.get('mes') or request.form.get('mes') or datetime.now().strftime('%Y-%m')

    if request.method == 'POST':
        acao = request.form.get('acao', 'add')
        if acao == 'add':
            try:
                conn.execute(
                    'INSERT INTO Imposto (mes_referencia, descricao, valor, status, data_vencimento, tipo) VALUES (?,?,?,?,?,?)',
                    (mes, request.form.get('descricao') or 'Imposto', P(request.form.get('valor')),
                     request.form.get('status') or 'Pendente', request.form.get('venc') or '',
                     request.form.get('tipo') or 'Simples')
                )
                conn.commit()
            except Exception:
                pass
        elif acao == 'pagar':
            try:
                iid = request.form.get('id')
                conn.execute("UPDATE Imposto SET status='Pago', data_pagamento=date('now') WHERE id=?", (iid,))
                row = conn.execute('SELECT descricao, valor FROM Imposto WHERE id=?', (iid,)).fetchone()
                if row:
                    conn.execute(
                        "INSERT INTO Caixa (descricao, valor, tipo, categoria, data) VALUES (?,?, 'Saida', 'Imposto', CURRENT_TIMESTAMP)",
                        (f"Imposto: {row[0]}", P(row[1]))
                    )
                conn.commit()
            except Exception:
                pass
        conn.close()
        return redirect('/impostos?mes=' + mes)

    try:
        fat = conn.execute(
            "SELECT COALESCE(SUM(valor),0) FROM Caixa WHERE tipo='Entrada' AND strftime('%Y-%m', data)=?",
            (mes,)
        ).fetchone()
        faturamento = P(fat[0] if fat else 0)
    except Exception:
        faturamento = 0.0

    mei = 75.90
    try:
        if isinstance(config, dict):
            mei = P(config.get('valor_mei_padrao'), 75.90)
    except Exception:
        pass

    try:
        rows = conn.execute(
            'SELECT id, descricao, valor, status, data_vencimento, data_pagamento, tipo FROM Imposto WHERE mes_referencia=? ORDER BY id DESC',
            (mes,)
        ).fetchall()
    except Exception:
        rows = []

    impostos, pend, pago = [], 0.0, 0.0
    for r in rows:
        val = P(r[2]); st = r[3] or 'Pendente'
        impostos.append({
            'id': r[0], 'descricao': r[1], 'valor_txt': M(val), 'status': st,
            'vencimento': r[4] or '-', 'pagamento': r[5] or '', 'tipo': r[6] or 'Simples'
        })
        if st == 'Pago': pago += val
        else: pend += val
    conn.close()

    out = render_template(
        'impostos/impostos.html',
        config=config, mes=mes,
        fat_num=f"{faturamento:.2f}",
        pend_txt=M(pend), pago_txt=M(pago),
        mei_num=f"{mei:.2f}",
        impostos=impostos,
    )
    resp = make_response(out)
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp
'''

if "if __name__" in code:
    a, b = code.split("if __name__", 1)
    code = a.rstrip() + "\n" + rota + "\n\nif __name__" + b
else:
    code = code.rstrip() + "\n" + rota

with open(app_path, "w", encoding="utf-8", newline="\n") as f:
    f.write(code)

with open(app_path, "r", encoding="utf-8") as f:
    ac = f.read()
assert "impostos_simulador_final" in ac
assert "gerenciar_impostos_definitivo" not in ac
print("[OK] app.py: impostos_simulador_final presente")
print("[OK] app.py: gerenciar_impostos_definitivo removido")
print("[OK] Rotas /impostos:", ac.count("'/impostos'") + ac.count('"/impostos"'))

# teste import
import importlib.util
spec = importlib.util.spec_from_file_location("app_check", app_path)
# nao importa flask app completo se der conflito - so confere sintaxe
import py_compile
py_compile.compile(app_path, doraise=True)
print("[OK] app.py compila sem SyntaxError")
print("=== SUCESSO ===")
print("Rode: python app.py")
print("Abra: http://127.0.0.1:5001/impostos")
print("Ctrl+F5  deve ver faixa: NOVA TELA ATIVA")
