# -*- coding: utf-8 -*-
import os
import sqlite3
import json
import urllib.request
import urllib.parse
import threading
import time
from datetime import datetime, date, timedelta
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "climagestao_secret_key_2025_safe_hvac")
DB_NAME = os.environ.get("DB_PATH", "app.db")

def get_db():
    conn = sqlite3.connect(DB_NAME, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS Configuracao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_empresa TEXT, slogan TEXT, documento TEXT, telefone TEXT,
        email TEXT, endereco TEXT, site TEXT, logo TEXT,
        cor_principal TEXT, cor_secundaria TEXT, cor_destaque TEXT,
        mensagem_recibo TEXT, valor_mei_padrao REAL, aliquota_simples_padrao REAL,
        mensagem_manutencao TEXT, foto_alerta TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS Usuario (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_completo TEXT, empresa TEXT, email TEXT UNIQUE, telefone TEXT,
        senha_hash TEXT, is_admin INTEGER DEFAULT 0, assinatura_ativa INTEGER DEFAULT 1,
        data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP, ultimo_acesso TIMESTAMP,
        token_reset TEXT, token_expira TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS TelegramConfig (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bot_token TEXT, chat_id TEXT, notificar_agendamentos INTEGER DEFAULT 1,
        notificar_caixa INTEGER DEFAULT 1, ativo INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS Cliente (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT, email TEXT, tipo TEXT, documento TEXT, telefone TEXT,
        endereco TEXT, observacoes TEXT, data_visita_inicial TEXT,
        data_retorno_programado TEXT, forma_pagamento TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS Aparelho (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER, marca TEXT, modelo TEXT, capacidade_btu TEXT,
        voltagem TEXT, local_instalado TEXT, data_instalacao TEXT, observacoes TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS Funcionario (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT, email TEXT, telefone TEXT, cargo TEXT,
        salario_base REAL, comissao_percentual REAL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS Produto (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_barras TEXT, nome TEXT, descricao TEXT, unidade TEXT,
        preco_custo REAL, preco_venda REAL, quantidade_estoque INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS Caixa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT, tipo TEXT, categoria TEXT, descricao TEXT,
        valor REAL, forma_pagamento TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS Imposto (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo_imposto TEXT, mes_referencia TEXT, valor REAL, data_vencimento TEXT,
        codigo_barras TEXT, status TEXT, descricao TEXT, data_pagamento TEXT, tipo TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS AgendamentoOnline (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_cliente TEXT, telefone TEXT, endereco TEXT, bairro TEXT,
        tipo_servico TEXT, tipo_aparelho TEXT, data_sugerida DATE, periodo TEXT,
        observacao TEXT, status TEXT, data_solicitacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        valor REAL, forma_pagamento TEXT, status_pagamento TEXT, status_servico TEXT,
        vencimento TEXT, funcionario_id INTEGER, observacao_interna TEXT, documento TEXT,
        etapa_fluxo INTEGER DEFAULT 1, foto_antes TEXT, foto_depois TEXT,
        assinatura_cliente TEXT, data_aprovacao TIMESTAMP, data_conclusao TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS Disponibilidade (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data DATE, periodo TEXT, status TEXT, vagas INTEGER, agendados INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS CatServico (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT, valor_padrao REAL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS CatEquipamento (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS Orcamento (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER, cliente_nome TEXT, telefone TEXT, equipamento TEXT,
        servico TEXT, valor_mo REAL, valor_pecas REAL, valor_total REAL,
        garantia TEXT, data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS VideoCurso (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT, descricao TEXT, url_video TEXT, categoria TEXT,
        ordem INTEGER, ativo INTEGER DEFAULT 1, data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS ChecklistTipo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT, icone TEXT, descricao TEXT
    )''')

    cfg = c.execute("SELECT * FROM Configuracao WHERE id=1").fetchone()
    if not cfg:
        c.execute('''INSERT INTO Configuracao (id, nome_empresa, slogan, cor_principal, valor_mei_padrao, aliquota_simples_padrao)
                     VALUES (1, 'ClimaGestao Climatizacao', 'Especialistas em Ar Condicionado', '#0d6efd', 75.0, 6.0)''')

    admin = c.execute("SELECT * FROM Usuario WHERE email='admin@climagestao.com'").fetchone()
    if not admin:
        pwd_hash = generate_password_hash("admin123")
        c.execute('''INSERT INTO Usuario (nome_completo, empresa, email, senha_hash, is_admin, assinatura_ativa)
                     VALUES ('Administrador ClimaGestao', 'ClimaGestao Matriz', 'admin@climagestao.com', ?, 1, 1)''', (pwd_hash,))

    tg_row = c.execute("SELECT * FROM TelegramConfig WHERE id=1").fetchone()
    if not tg_row:
        c.execute("INSERT INTO TelegramConfig (id, ativo, notificar_agendamentos, notificar_caixa) VALUES (1, 0, 1, 1)")

    if c.execute("SELECT COUNT(*) FROM CatServico").fetchone()[0] == 0:
        c.executemany("INSERT INTO CatServico (nome, valor_padrao) VALUES (?, ?)", [
            ('Higienizacao Completa', 180.0),
            ('Instalacao Split 9k-12k', 450.0),
            ('Instalacao Split 18k-24k', 600.0),
            ('Carga de Gas R410A', 220.0),
            ('Manutencao Preventiva', 150.0)
        ])

    if c.execute("SELECT COUNT(*) FROM CatEquipamento").fetchone()[0] == 0:
        c.executemany("INSERT INTO CatEquipamento (nome) VALUES (?)", [
            ('Split Hi-Wall 9.000 BTU',),
            ('Split Hi-Wall 12.000 BTU',),
            ('Split Hi-Wall 18.000 BTU',),
            ('Split Inverter 12.000 BTU',),
            ('Split Piso Teto 36.000 BTU',)
        ])

    conn.commit()
    conn.close()

init_db()

@app.context_processor
def inject_globals():
    conn = get_db()
    config = conn.execute("SELECT * FROM Configuracao WHERE id=1").fetchone()
    conn.close()
    return dict(config=config or {}, now=datetime.now())

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash("Por favor, faca login para acessar.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session or not session.get('is_admin'):
            flash("Acesso restrito ao administrador.", "danger")
            return redirect(url_for('painel'))
        return f(*args, **kwargs)
    return decorated_function

_last_update_id = 0
_user_states = {}


def tg_get_config():
    try:
        conn = get_db()
        row = conn.execute("SELECT * FROM TelegramConfig WHERE id=1").fetchone()
        conn.close()
        if row:
            return {
                'id': row['id'],
                'token': row['bot_token'] or '',
                'bot_token': row['bot_token'] or '',
                'chat_id': row['chat_id'] or '',
                'notificar_agendamentos': row['notificar_agendamentos'],
                'notificar_caixa': row['notificar_caixa'],
                'ativo': row['ativo']
            }
    except Exception:
        pass
    return {'id': 1, 'token': '', 'bot_token': '', 'chat_id': '', 'notificar_agendamentos': 1, 'notificar_caixa': 1, 'ativo': 0}

def enviar_msg_telegram(mensagem, chat_id_dest=None):
    cfg = tg_get_config()
    token = cfg.get('token')
    chat_id = chat_id_dest or cfg.get('chat_id')
    if not token or not chat_id:
        return False, "Token ou Chat ID nao configurados."
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = urllib.parse.urlencode({
            'chat_id': str(chat_id).strip(),
            'text': mensagem,
            'parse_mode': 'HTML'
        }).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return (True, "Mensagem enviada com sucesso!") if data.get('ok') else (False, data.get('description', 'Erro Telegram'))
    except Exception as e:
        return False, str(e)

def _telegram_bot_loop():
    global _last_update_id, _user_states
    while True:
        try:
            cfg = tg_get_config()
            token = cfg.get('token') or ''
            if not token or not cfg.get('ativo'):
                time.sleep(5)
                continue

            url = f"https://api.telegram.org/bot{token}/getUpdates?offset={_last_update_id + 1}&timeout=10"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            try:
                resp = urllib.request.urlopen(req, timeout=15)
                data = json.loads(resp.read().decode('utf-8'))
            except Exception:
                time.sleep(5)
                continue

            if not (data.get('ok') and data.get('result')):
                time.sleep(1)
                continue

            for update in data['result']:
                _last_update_id = update['update_id']
                msg = update.get('message') or {}
                text = (msg.get('text') or '').strip()
                from_id = str((msg.get('chat') or {}).get('id') or '')
                if not text or not from_id:
                    continue

                def menu_txt():
                    m = " <b>CLIMAGESTÃO  TELEGRAM INTERATIVO</b> \n\n"
                    m += "Digite o número da opção desejada:\n"
                    m += "<b>1</b>  Caixa de Hoje\n"
                    m += "<b>2</b>  Próximos Agendamentos\n"
                    m += "<b>3</b>  Resumo do Mês\n"
                    m += "<b>4</b>  Ajuda / Instruções\n"
                    m += "<b>5</b>  Buscar Cliente\n"
                    m += "<b>6</b>  Ver este Menu\n"
                    m += "<b>7</b>  Cadastrar Cliente (Passo a Passo) \n"
                    m += "<b>8</b>  Agendar Serviço (Passo a Passo) \n"
                    m += "<b>9</b>  Orçamento Rápido (Passo a Passo) \n\n"
                    m += "<i>Atalhos Rápidos de Caixa:</i>\n"
                    m += " <code>e 150 Higienizacao</code>\n"
                    m += " <code>s 45 Gas R410</code>\n"
                    m += " <code>c Carlos</code>\n\n"
                    m += " <i>Durante qualquer cadastro, digite <b>sair</b> ou <b>cancelar</b> para retornar.</i>"
                    return m

                cmd = text.lower().strip()

                # Verificação de Cancelamento Global das Máquinas de Estado
                if cmd in ['sair', 'cancelar', 'cancel', 'exit'] and from_id in _user_states:
                    del _user_states[from_id]
                    enviar_msg_telegram(" Ação cancelada com sucesso! Retornando ao início.\n\n" + menu_txt(), from_id)
                    continue

                # Máquina de Estados Interativa (Step-by-Step)
                if from_id in _user_states:
                    state = _user_states[from_id]
                    action = state['action']
                    step = state['step']
                    s_data = state['data']
                    conn = get_db()

                    try:
                        # --- CONVERSA DE CADASTRO DE CLIENTE ---
                        if action == 'cadastrar_cliente':
                            if step == 0:  # Recebe Nome
                                s_data['nome'] = text
                                state['step'] = 1
                                enviar_msg_telegram(" Digite o <b>Telefone</b> do cliente:\n\n<i>(Ou digite <b>x</b> para pular, ou <b>pular</b> para salvar agora com o nome atual)</i>", from_id)
                            
                            elif step == 1:  # Recebe Telefone
                                if cmd in ['pular', 'p']:
                                    s_data['telefone'] = ""
                                    s_data['endereco'] = ""
                                    conn.execute("INSERT INTO Cliente (nome, telefone, endereco, tipo) VALUES (?, ?, ?, 'PF')", (s_data['nome'], s_data['telefone'], s_data['endereco']))
                                    conn.commit()
                                    enviar_msg_telegram(f" <b>CLIENTE SALVO!</b>\n\n Nome: {s_data['nome']}\n\nDigite <b>6</b> para o menu.", from_id)
                                    del _user_states[from_id]
                                else:
                                    s_data['telefone'] = "" if cmd == 'x' else text
                                    state['step'] = 2
                                    enviar_msg_telegram(" Digite o <b>Endereço</b> completo:\n\n<i>(Ou digite <b>x</b> para pular, ou <b>pular</b> para salvar agora)</i>", from_id)
                            
                            elif step == 2:  # Recebe Endereço
                                s_data['endereco'] = "" if cmd in ['x', 'pular', 'p'] else text
                                conn.execute("INSERT INTO Cliente (nome, telefone, endereco, tipo) VALUES (?, ?, ?, 'PF')", (s_data['nome'], s_data['telefone'], s_data['endereco']))
                                conn.commit()
                                enviar_msg_telegram(f" <b>CLIENTE SALVO COM SUCESSO!</b>\n\n Nome: <b>{s_data['nome']}</b>\n Tel: {s_data['telefone'] or '-'}\n End: {s_data['endereco'] or '-'}\n\nDigite <b>6</b> para retornar.", from_id)
                                del _user_states[from_id]

                        # --- CONVERSA DE AGENDAMENTO ---
                        elif action == 'agendar_servico':
                            if step == 0:  # Recebe Nome do Cliente
                                s_data['nome'] = text
                                state['step'] = 1
                                enviar_msg_telegram(" Qual o <b>Serviço</b> a ser realizado? (Ex: Higienização, Instalação):\n\n<i>(Ou digite <b>pular</b> para salvar como 'Serviço Geral')</i>", from_id)
                            
                            elif step == 1:  # Recebe Serviço
                                if cmd in ['pular', 'p']:
                                    s_data['servico'] = "Serviço Geral"
                                    s_data['turno'] = "Manhã"
                                    s_data['data'] = date.today().isoformat()
                                    conn.execute("INSERT INTO AgendamentoOnline (nome_cliente, tipo_servico, periodo, data_sugerida, status, etapa_fluxo) VALUES (?, ?, ?, ?, 'Pendente', 1)", (s_data['nome'], s_data['servico'], s_data['turno'], s_data['data']))
                                    conn.commit()
                                    enviar_msg_telegram(f" <b>AGENDAMENTO SALVO!</b>\n\n Cliente: {s_data['nome']}\n Serviço: {s_data['servico']}\n\nDigite <b>6</b> para retornar.", from_id)
                                    del _user_states[from_id]
                                else:
                                    s_data['servico'] = text
                                    state['step'] = 2
                                    enviar_msg_telegram(" Digite o <b>Turno</b> (Manhã / Tarde):\n\n<i>(Ou digite <b>x</b> para 'Manhã', ou <b>pular</b> para salvar agora)</i>", from_id)
                            
                            elif step == 2:  # Recebe Turno
                                if cmd in ['pular', 'p']:
                                    s_data['turno'] = "Manhã"
                                    s_data['data'] = date.today().isoformat()
                                    conn.execute("INSERT INTO AgendamentoOnline (nome_cliente, tipo_servico, periodo, data_sugerida, status, etapa_fluxo) VALUES (?, ?, ?, ?, 'Pendente', 1)", (s_data['nome'], s_data['servico'], s_data['turno'], s_data['data']))
                                    conn.commit()
                                    enviar_msg_telegram(f" <b>AGENDAMENTO SALVO!</b>\n\n Cliente: {s_data['nome']}\n Serviço: {s_data['servico']}\n\nDigite <b>6</b> para retornar.", from_id)
                                    del _user_states[from_id]
                                else:
                                    s_data['turno'] = "Manhã" if cmd == 'x' else text
                                    state['step'] = 3
                                    enviar_msg_telegram(" Digite a <b>Data</b> (DD/MM/YYYY):\n\n<i>(Ou digite <b>x</b> ou <b>pular</b> para agendar para HOJE)</i>", from_id)
                            
                            elif step == 3:  # Recebe Data
                                if cmd in ['x', 'pular', 'p']:
                                    s_data['data'] = date.today().isoformat()
                                    d_br = date.today().strftime('%d/%m/%Y')
                                else:
                                    try:
                                        from datetime import datetime
                                        s_data['data'] = datetime.strptime(text, "%d/%m/%Y").strftime("%Y-%m-%d")
                                        d_br = text
                                    except Exception:
                                        s_data['data'] = date.today().isoformat()
                                        d_br = date.today().strftime('%d/%m/%Y')

                                conn.execute("INSERT INTO AgendamentoOnline (nome_cliente, tipo_servico, periodo, data_sugerida, status, etapa_fluxo) VALUES (?, ?, ?, ?, 'Pendente', 1)", (s_data['nome'], s_data['servico'], s_data['turno'], s_data['data']))
                                conn.commit()
                                enviar_msg_telegram(f" <b>SERVIÇO AGENDADO!</b>\n\n Cliente: <b>{s_data['nome']}</b>\n Serviço: {s_data['servico']}\n Turno: {s_data['turno']}\n Data: {d_br}\n\nDigite <b>6</b> para retornar.", from_id)
                                del _user_states[from_id]

                        # --- CONVERSA DE ORÇAMENTO RÁPIDO ---
                        elif action == 'orcamento_rapido':
                            if step == 0:  # Recebe Nome
                                s_data['nome'] = text
                                state['step'] = 1
                                enviar_msg_telegram(" Digite o <b>Equipamento</b> (Ex: Split 12000 BTU Inverter):\n\n<i>(Ou digite <b>pular</b> para pular as próximas etapas)</i>", from_id)
                            
                            elif step == 1:  # Recebe Equipamento
                                if cmd in ['pular', 'p']:
                                    s_data['equipamento'] = "Ar Condicionado"
                                    s_data['servico'] = "Manutenção"
                                    s_data['mo'] = 0.0
                                    s_data['pecas'] = 0.0
                                    v_tot = 0.0
                                    conn.execute("INSERT INTO Orcamento (cliente_nome, equipamento, servico, valor_mo, valor_pecas, valor_total, garantia) VALUES (?, ?, ?, ?, ?, ?, '90 dias')", (s_data['nome'], s_data['equipamento'], s_data['servico'], s_data['mo'], s_data['pecas'], v_tot))
                                    conn.commit()
                                    msg_z = f"Olá {s_data['nome']}! Segue seu orçamento ClimaGestão:\n Equipamento: {s_data['equipamento']}\n Serviço: {s_data['servico']}\n Total: R$ 0,00"
                                    z_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(msg_z)}"
                                    enviar_msg_telegram(f" <b>ORÇAMENTO CONCLUÍDO!</b>\n\nTotal: R$ 0,00\n\n <a href='{z_url}'>Enviar via WhatsApp</a>", from_id)
                                    del _user_states[from_id]
                                else:
                                    s_data['equipamento'] = text
                                    state['step'] = 2
                                    enviar_msg_telegram(" Digite o <b>Serviço</b> a ser orçado (Ex: Higienização Completa):", from_id)
                            
                            elif step == 2:  # Recebe Serviço
                                s_data['servico'] = text
                                state['step'] = 3
                                enviar_msg_telegram(" Digite o valor da <b>Mão de Obra</b> (Ex: 150 ou pular para R$ 0,00):\n\n<i>(Ou digite <b>x</b> para pular)</i>", from_id)
                            
                            elif step == 3:  # Recebe Mão de Obra
                                try:
                                    s_data['mo'] = 0.0 if cmd in ['x', 'pular', 'p'] else float(text.replace(',', '.'))
                                except ValueError:
                                    s_data['mo'] = 0.0
                                state['step'] = 4
                                enviar_msg_telegram(" Digite o valor de <b>Peças / Materiais</b> (Ex: 80 ou pular para R$ 0,00):\n\n<i>(Ou digite <b>x</b> para pular)</i>", from_id)
                            
                            elif step == 4:  # Recebe Peças
                                try:
                                    s_data['pecas'] = 0.0 if cmd in ['x', 'pular', 'p'] else float(text.replace(',', '.'))
                                except ValueError:
                                    s_data['pecas'] = 0.0
                                v_total = s_data['mo'] + s_data['pecas']
                                
                                conn.execute("INSERT INTO Orcamento (cliente_nome, equipamento, servico, valor_mo, valor_pecas, valor_total, garantia) VALUES (?, ?, ?, ?, ?, ?, '90 dias')", (s_data['nome'], s_data['equipamento'], s_data['servico'], s_data['mo'], s_data['pecas'], v_total))
                                conn.commit()

                                msg_zap = f"Olá {s_data['nome']}! Segue seu orçamento ClimaGestão:\n Equipamento: {s_data['equipamento']}\n Serviço: {s_data['servico']}\n Total: R$ {v_total:,.2f}\n Garantia: 90 dias"
                                zap_url = f"https://api.whatsapp.com/send?text={urllib.parse.quote(msg_zap)}"

                                txt = (f" <b>ORÇAMENTO RÁPIDO GERADO!</b>\n\n"
                                       f" Cliente: <b>{s_data['nome']}</b>\n"
                                       f" Equipamento: {s_data['equipamento']}\n"
                                       f" Serviço: {s_data['servico']}\n"
                                       f" Mão de Obra: R$ {s_data['mo']:,.2f}\n"
                                       f" Peças: R$ {s_data['pecas']:,.2f}\n"
                                       f" Total: <b>R$ {v_total:,.2f}</b>\n\n"
                                       f" <a href='{zap_url}'>Clique para enviar via WhatsApp</a>\n\n"
                                       f"Digite <b>6</b> para retornar.")
                                enviar_msg_telegram(txt, from_id)
                                del _user_states[from_id]

                    except Exception as ex:
                        enviar_msg_telegram(f" Erro ao processar: {ex}", from_id)
                    finally:
                        conn.close()
                    continue

                # --- FLUXO NORMAL DE COMANDOS (SE NÃO TIVER EM ESTADO DE CADASTRO) ---
                conn = get_db()
                try:
                    if cmd in ['/start', '/menu', 'menu', '6', 'ajuda', 'help', '/help']:
                        enviar_msg_telegram(menu_txt(), from_id)

                    elif cmd in ['1', 'caixa', 'saldo']:
                        hoje = date.today().isoformat()
                        rows = conn.execute("SELECT tipo, valor FROM Caixa WHERE data = ?", (hoje,)).fetchall()
                        ent = sum(r['valor'] for r in rows if r['tipo'] == 'Entrada')
                        sai = sum(r['valor'] for r in rows if r['tipo'] == 'Saida')
                        bal = ent - sai
                        txt = (f" <b>CAIXA DE HOJE ({date.today().strftime('%d/%m/%Y')})</b>\n\n"
                               f" Entradas: <b>R$ {ent:,.2f}</b>\n"
                               f" Saídas: <b>R$ {sai:,.2f}</b>\n"
                               f" Saldo: <b>R$ {bal:,.2f}</b>\n\n"
                               f"Digite <b>6</b> para o menu.")
                        enviar_msg_telegram(txt, from_id)

                    elif cmd in ['2', 'agendamentos', 'agenda']:
                        hoje = date.today().isoformat()
                        agends = conn.execute(
                            "SELECT nome_cliente, tipo_servico, periodo FROM AgendamentoOnline WHERE data_sugerida >= ? ORDER BY data_sugerida ASC LIMIT 5",
                            (hoje,)
                        ).fetchall()
                        if agends:
                            txt = " <b>PRÓXIMOS AGENDAMENTOS</b>\n\n"
                            for a in agends:
                                txt += f" <b>{a['nome_cliente']}</b>\n  Serviço: {a['tipo_servico'] or 'Serviço'}\n  Turno: {a['periodo'] or 'A definir'}\n\n"
                            txt += "Digite <b>6</b> para o menu."
                        else:
                            txt = " Nenhum agendamento futuro encontrado.\n\nDigite <b>6</b> para o menu."
                        enviar_msg_telegram(txt, from_id)

                    elif cmd in ['3', 'resumo', 'faturamento']:
                        mes_atual = date.today().strftime('%Y-%m')
                        rows = conn.execute("SELECT tipo, valor FROM Caixa WHERE data LIKE ?", (f"{mes_atual}%",)).fetchall()
                        ent = sum(r['valor'] for r in rows if r['tipo'] == 'Entrada')
                        sai = sum(r['valor'] for r in rows if r['tipo'] == 'Saida')
                        lucro = ent - sai
                        txt = (f" <b>RESUMO DO MÊS ({date.today().strftime('%m/%Y')})</b>\n\n"
                               f" Entradas: <b>R$ {ent:,.2f}</b>\n"
                               f" Saídas: <b>R$ {sai:,.2f}</b>\n"
                               f" Resultado Líquido: <b>R$ {lucro:,.2f}</b>\n\n"
                               f"Digite <b>6</b> para o menu.")
                        enviar_msg_telegram(txt, from_id)

                    elif cmd in ['4']:
                        txt = (" <b>INSTRUÇÕES DO TELEGRAM INTERATIVO</b>\n\n"
                               " <b>Lançar Entrada Direta:</b>\n"
                               "<code>e VALOR DESCRICAO</code>\n"
                               "Exemplo: <code>e 150 Higienização Split</code>\n\n"
                               " <b>Lançar Saída Direta:</b>\n"
                               "<code>s VALOR DESCRICAO</code>\n"
                               "Exemplo: <code>s 45 Gás R410</code>\n\n"
                               " <b>Buscar Cliente:</b>\n"
                               "<code>c NOME</code>\n"
                               "Exemplo: <code>c Carlos</code>\n\n"
                               " <b>Cadastros Passo a Passo:</b>\n"
                               "Basta digitar <b>7</b> (Clientes), <b>8</b> (Agendamento) ou <b>9</b> (Orçamento) e o bot fará as perguntas uma a uma no seu chat.")
                        enviar_msg_telegram(txt, from_id)

                    elif cmd in ['5']:
                        enviar_msg_telegram(" Digite <b>c</b> seguido do nome do cliente.\nExemplo: <code>c Roberto</code>", from_id)

                    # INICIALIZAÇÃO DOS ESTADOS INTERATIVOS PELOS NÚMEROS DO MENU
                    elif cmd in ['7', 'nc']:
                        _user_states[from_id] = {
                            'action': 'cadastrar_cliente',
                            'step': 0,
                            'data': {}
                        }
                        enviar_msg_telegram(" <b>CADASTRAR NOVO CLIENTE</b>\n\nDigite o <b>Nome</b> completo do cliente:", from_id)

                    elif cmd in ['8', 'ag']:
                        _user_states[from_id] = {
                            'action': 'agendar_servico',
                            'step': 0,
                            'data': {}
                        }
                        enviar_msg_telegram(" <b>AGENDAR NOVO SERVIÇO</b>\n\nDigite o <b>Nome</b> do cliente para o agendamento:", from_id)

                    elif cmd in ['9', 'or']:
                        _user_states[from_id] = {
                            'action': 'orcamento_rapido',
                            'step': 0,
                            'data': {}
                        }
                        enviar_msg_telegram(" <b>ORÇAMENTO RÁPIDO</b>\n\nDigite o <b>Nome</b> do cliente:", from_id)

                    # ATALHOS RÁPIDOS DE CAIXA DE UMA LINHA SÓ (Legado mantido para velocidade)
                    elif cmd.startswith('e ') or cmd.startswith('entrada '):
                        partes = text.split(' ', 2)
                        if len(partes) >= 3:
                            val_str = partes[1].replace(',', '.').replace('R$', '').strip()
                            val = float(val_str)
                            desc = partes[2].strip()
                            hoje = date.today().isoformat()
                            conn.execute("INSERT INTO Caixa (data, tipo, categoria, descricao, valor, forma_pagamento) VALUES (?, 'Entrada', 'Servico', ?, ?, 'Telegram')", (hoje, desc, val))
                            conn.commit()
                            enviar_msg_telegram(f" <b>ENTRADA REGISTRADA!</b>\n\n Valor: <b>R$ {val:,.2f}</b>\n Descricao: {desc}\n Data: {date.today().strftime('%d/%m/%Y')}", from_id)
                        else:
                            enviar_msg_telegram(" Formato: <code>e VALOR DESCRICAO</code>", from_id)

                    elif cmd.startswith('s ') or cmd.startswith('saida ') or cmd.startswith('saída '):
                        partes = text.split(' ', 2)
                        if len(partes) >= 3:
                            val_str = partes[1].replace(',', '.').replace('R$', '').strip()
                            val = float(val_str)
                            desc = partes[2].strip()
                            hoje = date.today().isoformat()
                            conn.execute("INSERT INTO Caixa (data, tipo, categoria, descricao, valor, forma_pagamento) VALUES (?, 'Saida', 'Despesa', ?, ?, 'Telegram')", (hoje, desc, val))
                            conn.commit()
                            enviar_msg_telegram(f" <b>SAIDA REGISTRADA!</b>\n\n Valor: <b>R$ {val:,.2f}</b>\n Descricao: {desc}\n Data: {date.today().strftime('%d/%m/%Y')}", from_id)
                        else:
                            enviar_msg_telegram(" Formato: <code>s VALOR DESCRICAO</code>", from_id)

                    elif cmd.startswith('c ') or cmd.startswith('cliente '):
                        termo = text.split(' ', 1)[1].strip()
                        rows = conn.execute("SELECT nome, telefone, endereco, documento FROM Cliente WHERE nome LIKE ? OR telefone LIKE ? LIMIT 3", (f"%{termo}%", f"%{termo}%")).fetchall()
                        if not rows:
                            rows = conn.execute("SELECT nome_cliente, telefone, endereco, COALESCE(documento,'') FROM AgendamentoOnline WHERE nome_cliente LIKE ? OR telefone LIKE ? LIMIT 3", (f"%{termo}%", f"%{termo}%")).fetchall()
                        if rows:
                            rtxt = " <b>CLIENTE(S) ENCONTRADO(S)</b>\n\n"
                            for r in rows:
                                rtxt += f"<b>{r[0]}</b>\n Tel: {r[1] or '-'}\n End: {r[2] or '-'}\n Doc: {r[3] or '-'}\n\n"
                            rtxt += "Digite <b>6</b> para o menu."
                            enviar_msg_telegram(rtxt, from_id)
                        else:
                            enviar_msg_telegram(f" Nenhum cliente encontrado para: <i>{termo}</i>\n\nDigite <b>6</b> para o menu.", from_id)

                    else:
                        enviar_msg_telegram(" Comando não reconhecido.\n\n" + menu_txt(), from_id)

                except Exception as ex:
                    try:
                        enviar_msg_telegram(f" Erro no comando: {ex}", from_id)
                    except Exception:
                        pass
                finally:
                    conn.close()

        except Exception:
            time.sleep(3)

@app.route('/')
def index():
    if 'usuario_id' in session:
        return redirect(url_for('painel'))
    return render_template('auth/landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'usuario_id' in session:
        return redirect(url_for('painel'))
    erro = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        conn = get_db()
        user = conn.execute("SELECT * FROM Usuario WHERE email = ?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user['senha_hash'], senha):
            session['usuario_id'] = user['id']
            session['usuario_nome'] = user['nome_completo']
            session['usuario_email'] = user['email']
            session['empresa'] = user['empresa']
            session['is_admin'] = bool(user['is_admin'])
            conn = get_db()
            conn.execute("UPDATE Usuario SET ultimo_acesso = CURRENT_TIMESTAMP WHERE id = ?", (user['id'],))
            conn.commit()
            conn.close()
            flash("Bem-vindo ao ClimaGestao!", "success")
            return redirect(url_for('painel'))
        else:
            erro = "E-mail ou senha incorretos."
    return render_template('auth/login.html', erro=erro, msg=None)

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form.get('nome_completo', '').strip()
        empresa = request.form.get('empresa', '').strip()
        email = request.form.get('email', '').strip().lower()
        telefone = request.form.get('telefone', '').strip()
        senha = request.form.get('senha', '')
        if not (nome and email and senha):
            flash("Preencha todos os campos obrigatorios.", "danger")
            return render_template('auth/cadastro.html')
        conn = get_db()
        existente = conn.execute("SELECT id FROM Usuario WHERE email = ?", (email,)).fetchone()
        if existente:
            conn.close()
            flash("Este e-mail ja esta cadastrado. Faca login.", "warning")
            return redirect(url_for('login'))
        pwd_hash = generate_password_hash(senha)
        conn.execute(
            "INSERT INTO Usuario (nome_completo, empresa, email, telefone, senha_hash, is_admin, assinatura_ativa) VALUES (?, ?, ?, ?, ?, 0, 1)",
            (nome, empresa, email, telefone, pwd_hash)
        )
        conn.commit()
        conn.close()
        flash("Conta criada com sucesso! Faca login para comecar.", "success")
        return redirect(url_for('login'))
    return render_template('auth/cadastro.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Sessao encerrada.", "info")
    return redirect(url_for('login'))

@app.route('/esqueci-senha', methods=['GET', 'POST'])
def esqueci_senha():
    if request.method == 'POST':
        flash("Se o e-mail estiver cadastrado, as instrucoes foram enviadas.", "info")
        return redirect(url_for('login'))
    return render_template('auth/esqueci_senha.html')

@app.route('/painel')
@login_required
def painel():
    conn = get_db()
    hoje = date.today().isoformat()
    mes_atual = date.today().strftime('%Y-%m')

    # Função auxiliar para contagens seguras
    def count_tbl(tbl, where=""):
        try:
            sql = f"SELECT COUNT(*) FROM {tbl}" + (f" WHERE {where}" if where else "")
            return conn.execute(sql).fetchone()[0]
        except Exception:
            return 0

    # Contadores Gerais
    total_clientes = count_tbl("Cliente")
    total_servicos = count_tbl("AgendamentoOnline")
    total_produtos = count_tbl("Produto")
    total_funcionarios = count_tbl("Funcionario")
    total_aparelhos = count_tbl("Aparelho")
    total_notas = count_tbl("NotaFiscal")
    total_pontos_hoje = count_tbl("Ponto", f"data = '{hoje}'")
    total_alertas = count_tbl("AlertaRetorno", "status = 'Pendente'")

    # Impostos (Pendentes, Pagos e Totais)
    try:
        row_imp_pend = conn.execute("SELECT SUM(valor) FROM Imposto WHERE status != 'Pago'").fetchone()
        total_impostos_pendentes = float(row_imp_pend[0] or 0.0)
        row_imp_pago = conn.execute("SELECT SUM(valor) FROM Imposto WHERE status = 'Pago'").fetchone()
        total_impostos_pagos = float(row_imp_pago[0] or 0.0)
    except Exception:
        total_impostos_pendentes = 0.0
        total_impostos_pagos = 0.0
    total_impostos = total_impostos_pendentes + total_impostos_pagos

    # Caixa Hoje
    try:
        rows_hoje = conn.execute("SELECT tipo, valor FROM Caixa WHERE data = ?", (hoje,)).fetchall()
        entradas_hoje = sum(r['valor'] for r in rows_hoje if r['tipo'] == 'Entrada')
        saidas_hoje = sum(r['valor'] for r in rows_hoje if r['tipo'] == 'Saida')
    except Exception:
        entradas_hoje, saidas_hoje = 0.0, 0.0
    saldo_hoje = entradas_hoje - saidas_hoje

    # Caixa Mês Atual
    try:
        rows_mes = conn.execute("SELECT tipo, valor FROM Caixa WHERE data LIKE ?", (f"{mes_atual}%",)).fetchall()
        faturamento_mes = sum(r['valor'] for r in rows_mes if r['tipo'] == 'Entrada')
        despesas_mes = sum(r['valor'] for r in rows_mes if r['tipo'] == 'Saida')
    except Exception:
        faturamento_mes, despesas_mes = 0.0, 0.0
    lucro_mes = faturamento_mes - despesas_mes

    # Caixa Acumulado Total
    try:
        rows_total = conn.execute("SELECT tipo, valor FROM Caixa").fetchall()
        faturamento_total = sum(r['valor'] for r in rows_total if r['tipo'] == 'Entrada')
        despesas_total = sum(r['valor'] for r in rows_total if r['tipo'] == 'Saida')
    except Exception:
        faturamento_total, despesas_total = 0.0, 0.0
    saldo_total = faturamento_total - despesas_total
    lucro_total = saldo_total

    # Pendente a Receber (OS / Agendamentos)
    try:
        rows_pend = conn.execute("SELECT valor FROM AgendamentoOnline WHERE status_pagamento != 'Pago' OR status_pagamento IS NULL").fetchall()
        total_receber = sum(r['valor'] or 0 for r in rows_pend)
    except Exception:
        total_receber = 0.0
    total_a_receber = total_receber

    # Listas auxiliares
    try:
        alertas = conn.execute("SELECT * FROM AlertaRetorno WHERE status = 'Pendente' ORDER BY id DESC LIMIT 5").fetchall()
    except Exception:
        alertas = []
    try:
        proximos_servicos = conn.execute("SELECT * FROM AgendamentoOnline WHERE data_sugerida >= ? ORDER BY data_sugerida ASC LIMIT 6", (hoje,)).fetchall()
    except Exception:
        proximos_servicos = []
    try:
        ultimos_servicos = conn.execute("SELECT * FROM AgendamentoOnline ORDER BY id DESC LIMIT 5").fetchall()
    except Exception:
        ultimos_servicos = []
    try:
        ultimos_lancamentos = conn.execute("SELECT * FROM Caixa ORDER BY id DESC LIMIT 5").fetchall()
    except Exception:
        ultimos_lancamentos = []

    conn.close()

    contexto = {
        'total_clientes': total_clientes,
        'total_aparelhos': total_aparelhos,
        'total_servicos': total_servicos,
        'total_produtos': total_produtos,
        'total_funcionarios': total_funcionarios,
        'total_notas': total_notas,
        'total_pontos_hoje': total_pontos_hoje,
        'total_alertas': total_alertas,
        'total_impostos_pendentes': total_impostos_pendentes,
        'total_impostos_pagos': total_impostos_pagos,
        'total_impostos': total_impostos,
        'entradas_hoje': entradas_hoje,
        'saidas_hoje': saidas_hoje,
        'saldo_hoje': saldo_hoje,
        'faturamento_mes': faturamento_mes,
        'despesas_mes': despesas_mes,
        'lucro_mes': lucro_mes,
        'faturamento_total': faturamento_total,
        'despesas_total': despesas_total,
        'saldo_total': saldo_total,
        'lucro_total': lucro_total,
        'total_receber': total_receber,
        'total_a_receber': total_a_receber,
        'alertas': alertas,
        'proximos_servicos': proximos_servicos,
        'ultimos_servicos': ultimos_servicos,
        'ultimos_lancamentos': ultimos_lancamentos,
        'session': session
    }

    return render_template('dashboard.html', **contexto)
@app.route('/fluxo')
@login_required
def fluxo_esteira():
    conn = get_db()
    e1 = conn.execute("SELECT * FROM AgendamentoOnline WHERE etapa_fluxo = 1 OR etapa_fluxo IS NULL ORDER BY id DESC").fetchall()
    e2 = conn.execute("SELECT * FROM AgendamentoOnline WHERE etapa_fluxo = 2 ORDER BY id DESC").fetchall()
    e3 = conn.execute("SELECT * FROM AgendamentoOnline WHERE etapa_fluxo = 3 ORDER BY id DESC").fetchall()
    e4 = conn.execute("SELECT * FROM AgendamentoOnline WHERE etapa_fluxo = 4 ORDER BY id DESC").fetchall()
    e5 = conn.execute("SELECT * FROM AgendamentoOnline WHERE etapa_fluxo = 5 ORDER BY id DESC").fetchall()
    conn.close()
    return render_template('fluxo/esteira.html', e1=e1, e2=e2, e3=e3, e4=e4, e5=e5)

@app.route('/fluxo/avancar/<int:id>/<int:etapa>')
@login_required
def fluxo_avancar(id, etapa):
    conn = get_db()
    agend = conn.execute("SELECT * FROM AgendamentoOnline WHERE id = ?", (id,)).fetchone()
    if agend:
        conn.execute("UPDATE AgendamentoOnline SET etapa_fluxo = ? WHERE id = ?", (etapa, id))
        if etapa == 5:
            conn.execute("UPDATE AgendamentoOnline SET status_servico = 'Concluido', data_conclusao = CURRENT_TIMESTAMP WHERE id = ?", (id,))
        conn.commit()
    conn.close()
    return redirect(url_for('fluxo_esteira'))

@app.route('/fluxo/executar/<int:id>', methods=['GET', 'POST'])
@login_required
def fluxo_executar(id):
    conn = get_db()
    agend = conn.execute("SELECT * FROM AgendamentoOnline WHERE id = ?", (id,)).fetchone()
    if request.method == 'POST':
        foto_antes = request.form.get('foto_antes', '')
        foto_depois = request.form.get('foto_depois', '')
        assinatura = request.form.get('assinatura_cliente', '')
        obs = request.form.get('observacao_interna', '')
        conn.execute('''UPDATE AgendamentoOnline SET 
            foto_antes = COALESCE(NULLIF(?, ''), foto_antes),
            foto_depois = COALESCE(NULLIF(?, ''), foto_depois),
            assinatura_cliente = COALESCE(NULLIF(?, ''), assinatura_cliente),
            observacao_interna = ?, etapa_fluxo = 4 WHERE id = ?''',
            (foto_antes, foto_depois, assinatura, obs, id)
        )
        conn.commit()
        conn.close()
        flash("Servico atualizado com sucesso!", "success")
        return redirect(url_for('fluxo_esteira'))
    conn.close()
    return render_template('fluxo/executar_servico.html', a=agend)

@app.route('/agendar', methods=['GET', 'POST'])
def agendar_publico():
    if request.method == 'POST':
        nome = request.form.get('nome_cliente', '').strip()
        telefone = request.form.get('telefone', '').strip()
        endereco = request.form.get('endereco', '').strip()
        bairro = request.form.get('bairro', '').strip()
        tipo_servico = request.form.get('tipo_servico', '')
        tipo_aparelho = request.form.get('tipo_aparelho', '')
        data_sugerida = request.form.get('data_sugerida', '')
        periodo = request.form.get('periodo', 'Manha')
        observacao = request.form.get('observacao', '')

        conn = get_db()
        conn.execute('''INSERT INTO AgendamentoOnline (
            nome_cliente, telefone, endereco, bairro, tipo_servico, tipo_aparelho,
            data_sugerida, periodo, observacao, status, etapa_fluxo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pendente', 1)''',
        (nome, telefone, endereco, bairro, tipo_servico, tipo_aparelho, data_sugerida, periodo, observacao))
        conn.commit()
        conn.close()

        cfg = tg_get_config()
        if cfg.get('ativo') and cfg.get('notificar_agendamentos'):
            msg_tg = f"NOVO AGENDAMENTO ONLINE!\n\nCliente: {nome}\nTel: {telefone}\nEnd: {endereco} ({bairro})\nServico: {tipo_servico} - {tipo_aparelho}\nData: {data_sugerida} ({periodo})"
            enviar_msg_telegram(msg_tg)

        return render_template('publico/sucesso.html', nome=nome, data=data_sugerida, periodo=periodo)

    conn = get_db()
    slots = conn.execute("SELECT * FROM Disponibilidade WHERE data >= date('now') ORDER BY data ASC").fetchall()
    conn.close()
    return render_template('publico/agendar.html', slots=slots)

@app.route('/agendamentos')
@app.route('/agendamentos-online')
@app.route('/agendamento-online')
@app.route('/agendamentos_online')
@app.route('/agenda')
@login_required
def lista_agendamentos():
    conn = get_db()
    agendamentos = conn.execute("SELECT * FROM AgendamentoOnline ORDER BY id DESC").fetchall()
    conn.close()
    if os.path.exists("templates/publico/lista_agendamentos.html"):
        return render_template('publico/lista_agendamentos.html', agendamentos=agendamentos, a=agendamentos)
    return render_template('lista_agendamentos.html', agendamentos=agendamentos, a=agendamentos)

@app.route('/agendamento/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_agendamento(id):
    conn = get_db()
    if request.method == 'POST':
        nome = request.form.get('nome_cliente')
        telefone = request.form.get('telefone')
        endereco = request.form.get('endereco')
        tipo_servico = request.form.get('tipo_servico')
        valor = float(request.form.get('valor', 0) or 0)
        status_pagamento = request.form.get('status_pagamento', 'Pendente')
        status = request.form.get('status', 'Pendente')
        conn.execute('''UPDATE AgendamentoOnline SET 
            nome_cliente = ?, telefone = ?, endereco = ?, tipo_servico = ?, valor = ?,
            status_pagamento = ?, status = ? WHERE id = ?''',
            (nome, telefone, endereco, tipo_servico, valor, status_pagamento, status, id)
        )
        if status_pagamento == 'Pago':
            hoje = date.today().isoformat()
            conn.execute(
                "INSERT INTO Caixa (data, tipo, categoria, descricao, valor, forma_pagamento) VALUES (?, 'Entrada', 'Servico', ?, ?, 'OS')",
                (hoje, f"Recebimento OS #{id} - {nome}", valor)
            )
        conn.commit()
        conn.close()
        flash("Agendamento atualizado com sucesso!", "success")
        return redirect(url_for('fluxo_esteira'))

    agend = conn.execute("SELECT * FROM AgendamentoOnline WHERE id = ?", (id,)).fetchone()
    conn.close()
    return render_template('publico/editar_agendamento.html', a=agend)

@app.route('/agendamento/excluir/<int:id>')
@login_required
def excluir_agendamento(id):
    conn = get_db()
    conn.execute("DELETE FROM AgendamentoOnline WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("Agendamento removido.", "info")
    return redirect(url_for('fluxo_esteira'))

@app.route('/ficha-cliente/<int:id>')
@login_required
def ficha_cliente(id):
    conn = get_db()
    agend = conn.execute("SELECT * FROM AgendamentoOnline WHERE id = ?", (id,)).fetchone()
    conn.close()
    return render_template('publico/ficha_cliente.html', a=agend)

@app.route('/disponibilidade', methods=['GET', 'POST'])
@login_required
def disponibilidade():
    conn = get_db()
    if request.method == 'POST':
        data_disp = request.form.get('data')
        periodo = request.form.get('periodo')
        vagas = int(request.form.get('vagas', 1) or 1)
        conn.execute("INSERT INTO Disponibilidade (data, periodo, status, vagas, agendados) VALUES (?, ?, 'Livre', ?, 0)",
                     (data_disp, periodo, vagas))
        conn.commit()
        flash("Vaga adicionada!", "success")
    slots = conn.execute("SELECT * FROM Disponibilidade ORDER BY data DESC").fetchall()
    conn.close()
    return render_template('publico/disponibilidade.html', slots=slots)


@app.route('/impostos', methods=['GET', 'POST'])
@login_required
def impostos():
    mes = request.args.get('mes', date.today().strftime('%Y-%m'))
    conn = get_db()
    if request.method == 'POST':
        tipo = request.form.get('tipo', 'MEI (DAS)')
        mes_ref = request.form.get('mes_referencia', mes)
        valor = float(request.form.get('valor', 0) or 0)
        venc = request.form.get('data_vencimento', '')
        cod = request.form.get('codigo_barras', '')
        status = request.form.get('status', 'Pendente')
        desc = request.form.get('descricao', '')
        conn.execute(
            "INSERT INTO Imposto (tipo, tipo_imposto, mes_referencia, valor, data_vencimento, codigo_barras, status, descricao) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (tipo, tipo, mes_ref, valor, venc, cod, status, desc)
        )
        conn.commit()
        flash("Imposto registrado!", "success")
        return redirect(url_for('impostos', mes=mes_ref))

    cfg = conn.execute("SELECT * FROM Configuracao WHERE id=1").fetchone()
    impostos_lista = conn.execute("SELECT * FROM Imposto WHERE mes_referencia = ? ORDER BY id DESC", (mes,)).fetchall()
    rows_caixa = conn.execute("SELECT valor FROM Caixa WHERE tipo='Entrada' AND data LIKE ?", (f"{mes}%",)).fetchall()
    fat_num = sum(r['valor'] for r in rows_caixa)
    mei_num = cfg['valor_mei_padrao'] if (cfg and cfg['valor_mei_padrao']) else 75.0
    pago_val = sum(i['valor'] for i in impostos_lista if i['status'] == 'Pago')
    pend_val = sum(i['valor'] for i in impostos_lista if i['status'] != 'Pago')
    conn.close()
    return render_template(
        'impostos/impostos.html',
        impostos=impostos_lista,
        mes=mes,
        fat_num=fat_num,
        mei_num=mei_num,
        pago_txt=f"R$ {pago_val:,.2f}",
        pend_txt=f"R$ {pend_val:,.2f}"
    )

@app.route('/impostos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_imposto(id):
    conn = get_db()
    if request.method == 'POST':
        tipo = request.form.get('tipo')
        mes_ref = request.form.get('mes_referencia')
        valor = float(request.form.get('valor', 0) or 0)
        venc = request.form.get('data_vencimento')
        cod = request.form.get('codigo_barras')
        status = request.form.get('status')
        desc = request.form.get('descricao')
        conn.execute('''UPDATE Imposto SET 
            tipo = ?, tipo_imposto = ?, mes_referencia = ?, valor = ?, data_vencimento = ?,
            codigo_barras = ?, status = ?, descricao = ? WHERE id = ?''',
            (tipo, tipo, mes_ref, valor, venc, cod, status, desc, id)
        )
        conn.commit()
        conn.close()
        flash("Imposto atualizado!", "success")
        return redirect(url_for('impostos', mes=mes_ref))
    imp = conn.execute("SELECT * FROM Imposto WHERE id = ?", (id,)).fetchone()
    conn.close()
    return render_template('impostos/editar_imposto.html', imp=imp, t=imp)

@app.route('/impostos/excluir/<int:id>')
@login_required
def excluir_imposto(id):
    mes = request.args.get('mes', date.today().strftime('%Y-%m'))
    conn = get_db()
    conn.execute("DELETE FROM Imposto WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("Imposto removido.", "info")
    return redirect(url_for('impostos', mes=mes))

@app.route('/orcamento-rapido', methods=['GET', 'POST'])
@login_required
def orcamento_rapido():
    conn = get_db()
    reenviar_zap = None
    if request.method == 'POST':
        c_nome = request.form.get('cliente_nome', '').strip()
        tel = request.form.get('telefone', '').strip()
        equip = request.form.get('equipamento', '')
        serv = request.form.get('servico', '')
        v_mo = float(request.form.get('valor_mo', 0) or 0)
        v_pecas = float(request.form.get('valor_pecas', 0) or 0)
        garantia = request.form.get('garantia', '90 dias')
        v_total = v_mo + v_pecas
        conn.execute('''INSERT INTO Orcamento (
            cliente_nome, telefone, equipamento, servico, valor_mo, valor_pecas, valor_total, garantia
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (c_nome, tel, equip, serv, v_mo, v_pecas, v_total, garantia))
        conn.commit()
        clean_tel = tel.replace('(','').replace(')','').replace('-','').replace(' ','')
        msg_zap = f"Ola {c_nome}! Segue seu orcamento ClimaGestao:\nEquipamento: {equip}\nServico: {serv}\nTotal: R$ {v_total:,.2f}\nGarantia: {garantia}"
        reenviar_zap = f"https://api.whatsapp.com/send?phone=55{clean_tel}&text={urllib.parse.quote(msg_zap)}"

    c = conn.execute("SELECT * FROM Cliente ORDER BY nome ASC").fetchall()
    e = conn.execute("SELECT * FROM CatEquipamento ORDER BY nome ASC").fetchall()
    s = conn.execute("SELECT * FROM CatServico ORDER BY nome ASC").fetchall()
    o = conn.execute("SELECT * FROM Orcamento ORDER BY id DESC LIMIT 20").fetchall()
    conn.close()
    return render_template('servicos/orcamento_rapido.html', c=c, e=e, s=s, o=o, reenviar_zap=reenviar_zap)

@app.route('/orcamento/config', methods=['GET', 'POST'])
@app.route('/orcamentos/config', methods=['GET', 'POST'])
@app.route('/config_orcamento', methods=['GET', 'POST'])
@app.route('/catalogos', methods=['GET', 'POST'])
@login_required
def config_orcamento():
    conn = get_db()
    if request.method == 'POST':
        tipo = request.form.get('tipo_cadastro') or request.form.get('tipo')
        nome = request.form.get('nome') or request.form.get('nome_servico') or request.form.get('nome_equipamento')
        
        if not tipo and request.form.get('valor_padrao'):
            tipo = 'servico'
        elif not tipo:
            tipo = 'equipamento'

        if nome:
            if tipo == 'servico':
                val_str = request.form.get('valor_padrao') or request.form.get('preco_base') or '0'
                try: val = float(str(val_str).replace(',', '.'))
                except ValueError: val = 0.0
                conn.execute("INSERT INTO CatServico (nome, valor_padrao) VALUES (?, ?)", (nome.strip(), val))
                flash(f"Serviço '{nome}' cadastrado com sucesso!", "success")
            else:
                conn.execute("INSERT INTO CatEquipamento (nome) VALUES (?)", (nome.strip(),))
                flash(f"Equipamento '{nome}' cadastrado com sucesso!", "success")
            conn.commit()

    s = conn.execute("SELECT * FROM CatServico ORDER BY nome ASC").fetchall()
    a = conn.execute("SELECT * FROM CatEquipamento ORDER BY nome ASC").fetchall()
    conn.close()
    return render_template('servicos/config_orcamento.html', s=s, a=a)

@app.route('/orcamento/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_orcamento(id):
    conn = get_db()
    if request.method == 'POST':
        c_nome = request.form.get('cliente_nome')
        tel = request.form.get('telefone')
        equip = request.form.get('equipamento')
        serv = request.form.get('servico')
        v_mo = float(request.form.get('valor_mo', 0) or 0)
        v_pecas = float(request.form.get('valor_pecas', 0) or 0)
        garantia = request.form.get('garantia')
        v_total = v_mo + v_pecas
        conn.execute('''UPDATE Orcamento SET 
            cliente_nome = ?, telefone = ?, equipamento = ?, servico = ?, valor_mo = ?,
            valor_pecas = ?, valor_total = ?, garantia = ? WHERE id = ?''',
            (c_nome, tel, equip, serv, v_mo, v_pecas, v_total, garantia, id)
        )
        conn.commit()
        conn.close()
        flash("Orcamento atualizado!", "success")
        return redirect(url_for('orcamento_rapido'))
    o = conn.execute("SELECT * FROM Orcamento WHERE id = ?", (id,)).fetchone()
    conn.close()
    return render_template('servicos/editar_orcamento.html', o=o)

@app.route('/catalogos')
@login_required
def catalogos():
    return redirect(url_for('config_orcamento'))

@app.route('/clientes')
@app.route('/cliente')
@app.route('/lista_clientes')
@login_required
def lista_clientes():
    conn = get_db()
    clientes = conn.execute("SELECT * FROM Cliente ORDER BY nome ASC").fetchall()
    conn.close()
    return render_template('cliente/lista_clientes.html', clientes=clientes)

@app.route('/cliente/novo', methods=['GET', 'POST'])
@app.route('/cliente/cadastrar', methods=['GET', 'POST'])
@app.route('/clientes/novo', methods=['GET', 'POST'])
@app.route('/clientes/cadastrar', methods=['GET', 'POST'])
@app.route('/cadastrar_cliente', methods=['GET', 'POST'])
@app.route('/cadastrar-cliente', methods=['GET', 'POST'])
@login_required
def cadastrar_cliente():
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        tipo = request.form.get('tipo', 'PF')
        doc = request.form.get('documento')
        tel = request.form.get('telefone')
        end = request.form.get('endereco')
        obs = request.form.get('observacoes')
        conn = get_db()
        conn.execute("INSERT INTO Cliente (nome, email, tipo, documento, telefone, endereco, observacoes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (nome, email, tipo, doc, tel, end, obs))
        conn.commit()
        conn.close()
        flash("Cliente cadastrado com sucesso!", "success")
        return redirect(url_for('lista_clientes'))
    
    # Renderiza o template correto de acordo com a pasta
    if os.path.exists("templates/cliente/cadastrar_cliente.html"):
        return render_template('cliente/cadastrar_cliente.html')
    return render_template('cadastrar_cliente.html')

@app.route('/cliente/editar/<int:id>', methods=['GET', 'POST'])
@app.route('/cliente/editar/<id>', methods=['GET', 'POST'])
@app.route('/cliente/editar', methods=['GET', 'POST'])
@app.route('/clientes/editar/<int:id>', methods=['GET', 'POST'])
@app.route('/clientes/editar/<id>', methods=['GET', 'POST'])
@app.route('/clientes/editar', methods=['GET', 'POST'])
@app.route('/editar_cliente/<int:id>', methods=['GET', 'POST'])
@app.route('/editar_cliente/<id>', methods=['GET', 'POST'])
@app.route('/editar_cliente', methods=['GET', 'POST'])
@app.route('/editar-cliente/<int:id>', methods=['GET', 'POST'])
@app.route('/editar-cliente/<id>', methods=['GET', 'POST'])
@app.route('/editar-cliente', methods=['GET', 'POST'])
@app.route('/cadastrar_cliente/<int:id>', methods=['GET', 'POST'])
@app.route('/cliente/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_cliente(id=None):
    if id is None:
        id = request.args.get('id') or request.form.get('id') or request.args.get('cliente_id')
    
    try:
        id = int(str(id).strip())
    except (ValueError, TypeError):
        id = None

    if not id:
        flash("ID do cliente inválido ou não especificado.", "warning")
        return redirect(url_for('lista_clientes'))

    conn = get_db()
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        tipo = request.form.get('tipo', 'PF')
        doc = request.form.get('documento')
        tel = request.form.get('telefone')
        end = request.form.get('endereco')
        obs = request.form.get('observacoes')
        conn.execute("UPDATE Cliente SET nome=?, email=?, tipo=?, documento=?, telefone=?, endereco=?, observacoes=? WHERE id=?",
                     (nome, email, tipo, doc, tel, end, obs, id))
        conn.commit()
        conn.close()
        flash("Cliente atualizado com sucesso!", "success")
        return redirect(url_for('lista_clientes'))

    cliente = conn.execute("SELECT * FROM Cliente WHERE id = ?", (id,)).fetchone()
    conn.close()

    if not cliente:
        flash("Cliente não encontrado.", "danger")
        return redirect(url_for('lista_clientes'))

    # Tenta carregar o template existente
    for tpl in ['cliente/editar_cliente.html', 'editar_cliente.html', 'cliente/cadastrar_cliente.html', 'cadastrar_cliente.html']:
        if os.path.exists(os.path.join("templates", tpl)):
            return render_template(tpl, cliente=cliente, c=cliente)

    return "Template de edição não encontrado.", 500
    return render_template('editar_cliente.html', cliente=cliente, c=cliente)

@app.route('/cliente/excluir/<id>', methods=['GET', 'POST'])
@app.route('/cliente/excluir/<int:id>', methods=['GET', 'POST'])
@app.route('/cliente/excluir', methods=['GET', 'POST'])
@app.route('/excluir_cliente/<id>', methods=['GET', 'POST'])
@app.route('/excluir_cliente/<int:id>', methods=['GET', 'POST'])
@app.route('/excluir_cliente', methods=['GET', 'POST'])
@app.route('/clientes/excluir/<id>', methods=['GET', 'POST'])
@app.route('/clientes/excluir/<int:id>', methods=['GET', 'POST'])
@app.route('/clientes/excluir', methods=['GET', 'POST'])
@login_required
def excluir_cliente(id=None):
    if id is None:
        id = request.args.get('id') or request.form.get('id') or request.args.get('cliente_id')
    
    try:
        id_num = int(str(id).strip())
    except Exception:
        id_num = None

    if id_num:
        conn = get_db()
        conn.execute("DELETE FROM Cliente WHERE id = ?", (id_num,))
        conn.commit()
        conn.close()
        flash("Cliente excluído com sucesso!", "info")
    else:
        flash("Não foi possível identificar o cliente para exclusão.", "warning")

    return redirect(url_for('lista_clientes'))

@app.route('/aparelhos')
@login_required
def lista_aparelhos():
    conn = get_db()
    aparelhos = conn.execute('''SELECT a.*, c.nome as cliente_nome 
                                FROM Aparelho a 
                                LEFT JOIN Cliente c ON a.cliente_id = c.id 
                                ORDER BY a.id DESC''').fetchall()
    conn.close()
    return render_template('aparelhos/lista_aparelhos.html', aparelhos=aparelhos)

@app.route('/aparelho/novo', methods=['GET', 'POST'])
@app.route('/cadastrar_aparelho', methods=['GET', 'POST'])
@app.route('/aparelhos/novo', methods=['GET', 'POST'])
@login_required
def cadastrar_aparelho():
    conn = get_db()
    if request.method == 'POST':
        c_id = request.form.get('cliente_id')
        marca = request.form.get('marca')
        modelo = request.form.get('modelo')
        btu = request.form.get('capacidade_btu')
        volt = request.form.get('voltagem')
        loc = request.form.get('local_instalado')
        conn.execute("INSERT INTO Aparelho (cliente_id, marca, modelo, capacidade_btu, voltagem, local_instalado) VALUES (?, ?, ?, ?, ?, ?)",
                     (c_id, marca, modelo, btu, volt, loc))
        conn.commit()
        conn.close()
        flash("Aparelho registrado!", "success")
        return redirect(url_for('lista_aparelhos'))
    clientes = conn.execute("SELECT id, nome FROM Cliente ORDER BY nome ASC").fetchall()
    conn.close()
    return render_template('aparelhos/cadastrar_aparelho.html', clientes=clientes)

@app.route('/produtos')
@login_required
def lista_produtos():
    conn = get_db()
    produtos = conn.execute("SELECT * FROM Produto ORDER BY nome ASC").fetchall()
    conn.close()
    return render_template('produtos/lista_produtos.html', produtos=produtos)

@app.route('/produto/novo', methods=['GET', 'POST'])
@app.route('/cadastrar_produto', methods=['GET', 'POST'])
@app.route('/produtos/novo', methods=['GET', 'POST'])
@login_required
def cadastrar_produto():
    if request.method == 'POST':
        nome = request.form.get('nome')
        cod = request.form.get('codigo_barras')
        un = request.form.get('unidade', 'UN')
        pc = float(request.form.get('preco_custo', 0) or 0)
        pv = float(request.form.get('preco_venda', 0) or 0)
        qtd = int(request.form.get('quantidade_estoque', 0) or 0)
        conn = get_db()
        conn.execute("INSERT INTO Produto (codigo_barras, nome, unidade, preco_custo, preco_venda, quantidade_estoque) VALUES (?, ?, ?, ?, ?, ?)",
                     (cod, nome, un, pc, pv, qtd))
        conn.commit()
        conn.close()
        flash("Produto cadastrado com sucesso!", "success")
        return redirect(url_for('lista_produtos'))
    return render_template('produtos/cadastrar_produto.html')


@app.route('/notas')
@login_required
def lista_notas():
    conn = get_db()
    notas = []
    if conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='NotaFiscal'").fetchone():
        notas = conn.execute("SELECT * FROM NotaFiscal ORDER BY id DESC").fetchall()
    conn.close()
    return render_template('notas/notas.html', notas=notas)

@app.route('/ferramentas')
@login_required
def central_ferramentas():
    return render_template('ferramentas/central.html')

@app.route('/checklists')
@app.route('/checklist')
@app.route('/checklists/tipos')
@login_required
def lista_checklists():
    conn = get_db()
    tipos = conn.execute("SELECT * FROM ChecklistTipo ORDER BY id ASC").fetchall()
    
    # Se não existirem tipos padrão, cria os principais (Instalação, Higienização, Preventiva)
    if not tipos:
        conn.executemany("INSERT INTO ChecklistTipo (nome, icone, descricao) VALUES (?, ?, ?)", [
            ('Higienização Completa', '', 'Checklist padrão para higienização e limpeza de split'),
            ('Instalação Padrão', '', 'Checklist de instalação, vácuo e teste de estanqueidade'),
            ('Manutenção Preventiva / PMOC', '', 'Verificação periódica de filtros, drenos e pressões')
        ])
        conn.commit()
        tipos = conn.execute("SELECT * FROM ChecklistTipo ORDER BY id ASC").fetchall()

    conn.close()
    if os.path.exists("templates/checklists/tipos.html"):
        return render_template('checklists/tipos.html', tipos=tipos, t=tipos)
    elif os.path.exists("templates/checklists/lista_checklists.html"):
        return render_template('checklists/lista_checklists.html', tipos=tipos, t=tipos)
    return render_template('checklists/tipos.html', tipos=tipos)

@app.route('/checklists/itens/<int:id>')
@app.route('/checklist/itens/<int:id>')
@app.route('/checklists/<int:id>/itens')
@login_required
def checklist_itens(id):
    conn = get_db()
    tipo = conn.execute("SELECT * FROM ChecklistTipo WHERE id = ?", (id,)).fetchone()
    itens = []
    if conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ChecklistItem'").fetchone():
        itens = conn.execute("SELECT * FROM ChecklistItem WHERE tipo_id = ? ORDER BY ordem ASC, id ASC", (id,)).fetchall()
        
        # Se não houver itens cadastrados, cria itens recomendados para o tipo
        if not itens:
            itens_padrao = [
                (id, "Disjuntor e fiação elétrica adequados", 1),
                (id, "Teste de estanqueidade / Pressurização com Nitrogênio", 2),
                (id, "Vácuo realizado abaixo de 500 microns", 3),
                (id, "Carga de fluido refrigerante por balança / superaquecimento", 4),
                (id, "Teste de dreno e caimento da tubulação", 5),
                (id, "Higienização da serpentina e turbina", 6),
                (id, "Medição de temperatura de insuflamento e retorno", 7)
            ]
            conn.executemany("INSERT INTO ChecklistItem (tipo_id, descricao, ordem) VALUES (?, ?, ?)", itens_padrao)
            conn.commit()
            itens = conn.execute("SELECT * FROM ChecklistItem WHERE tipo_id = ? ORDER BY ordem ASC, id ASC", (id,)).fetchall()

    conn.close()
    if os.path.exists("templates/checklists/itens.html"):
        return render_template('checklists/itens.html', tipo=tipo, itens=itens, t=tipo, i=itens)
    return redirect(url_for('lista_checklists'))

@app.route('/checklists/novo', methods=['GET', 'POST'])
@app.route('/checklist/novo', methods=['GET', 'POST'])
@login_required
def novo_checklist():
    conn = get_db()
    if request.method == 'POST':
        nome = request.form.get('nome')
        icone = request.form.get('icone', '')
        desc = request.form.get('descricao', '')
        conn.execute("INSERT INTO ChecklistTipo (nome, icone, descricao) VALUES (?, ?, ?)", (nome, icone, desc))
        conn.commit()
        conn.close()
        flash("Novo modelo de Checklist criado!", "success")
        return redirect(url_for('lista_checklists'))
    conn.close()
    if os.path.exists("templates/checklists/novo_checklist.html"):
        return render_template('checklists/novo_checklist.html')
    return redirect(url_for('lista_checklists'))

@app.route('/videos')
@app.route('/videos-cursos')
@app.route('/videos_cursos')
@login_required
def videos_cursos():
    conn = get_db()
    videos = conn.execute("SELECT * FROM VideoCurso WHERE ativo=1 ORDER BY ordem ASC").fetchall()
    conn.close()
    return render_template('videos_cursos.html', videos=videos)

@app.route('/configuracoes', methods=['GET', 'POST'])
@login_required
def configuracoes():
    conn = get_db()
    if request.method == 'POST':
        nome = request.form.get('nome_empresa')
        slogan = request.form.get('slogan')
        doc = request.form.get('documento')
        tel = request.form.get('telefone')
        email = request.form.get('email')
        cor = request.form.get('cor_principal')
        mei = float(request.form.get('valor_mei_padrao', 75.0) or 75.0)
        conn.execute('''UPDATE Configuracao SET 
            nome_empresa = ?, slogan = ?, documento = ?, telefone = ?, email = ?,
            cor_principal = ?, valor_mei_padrao = ? WHERE id = 1''',
            (nome, slogan, doc, tel, email, cor, mei)
        )
        conn.commit()
        flash("Configuracoes atualizadas!", "success")
    cfg = conn.execute("SELECT * FROM Configuracao WHERE id=1").fetchone()
    conn.close()
    return render_template('configuracoes.html', config=cfg)

@app.route('/telegram', methods=['GET', 'POST'])
@login_required
def telegram_config_view():
    conn = get_db()
    if request.method == 'POST':
        bot_token = request.form.get('bot_token', '').strip()
        chat_id = request.form.get('chat_id', '').strip()
        notif_agend = 1 if request.form.get('notificar_agendamentos') else 0
        notif_caixa = 1 if request.form.get('notificar_caixa') else 0
        ativo = 1 if request.form.get('ativo') else 0
        conn.execute('''UPDATE TelegramConfig SET 
            bot_token = ?, chat_id = ?, notificar_agendamentos = ?,
            notificar_caixa = ?, ativo = ? WHERE id = 1''',
            (bot_token, chat_id, notif_agend, notif_caixa, ativo)
        )
        conn.commit()
        flash("Configuracoes do Telegram salvas!", "success")
    tg = conn.execute("SELECT * FROM TelegramConfig WHERE id=1").fetchone()
    conn.close()
    return render_template('telegram.html', tg=tg)

@app.route('/telegram/testar')
@login_required
def telegram_testar():
    ok, msg = enviar_msg_telegram("Teste de Conexao ClimaGestao!\nO bot esta ativo e pronto para operar.")
    if ok:
        flash("Mensagem de teste enviada com sucesso ao seu Telegram!", "success")
    else:
        flash(f"Falha ao enviar mensagem de teste: {msg}", "danger")
    return redirect(url_for('telegram_config_view'))

@app.route('/admin')
@admin_required
def painel_admin():
    conn = get_db()
    usuarios = conn.execute("SELECT * FROM Usuario ORDER BY id DESC").fetchall()
    conn.close()
    return render_template('admin/painel_admin.html', usuarios=usuarios)

def _iniciar_telegram_background():
    t = threading.Thread(target=_telegram_bot_loop, daemon=True)
    t.start()
    print("[Telegram] Bot iniciado em segundo plano com sucesso.")

@app.route('/catalogo/servico/editar/<int:id>', methods=['POST'])
@app.route('/catalogo/servico/editar/<id>', methods=['POST'])
@login_required
def editar_cat_servico(id):
    try: id = int(id)
    except: return redirect(url_for('config_orcamento'))
    nome = request.form.get('nome', '').strip()
    try: val = float(str(request.form.get('valor_padrao', 0)).replace(',', '.'))
    except: val = 0.0
    conn = get_db()
    conn.execute("UPDATE CatServico SET nome=?, valor_padrao=? WHERE id=?", (nome, val, id))
    conn.commit()
    conn.close()
    flash("Serviço atualizado!", "success")
    return redirect(url_for('config_orcamento'))

@app.route('/catalogo/servico/excluir/<int:id>')
@app.route('/catalogo/servico/excluir/<id>')
@login_required
def excluir_cat_servico(id):
    try: id = int(id)
    except: return redirect(url_for('config_orcamento'))
    conn = get_db()
    conn.execute("DELETE FROM CatServico WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Serviço excluído!", "info")
    return redirect(url_for('config_orcamento'))

@app.route('/catalogo/equipamento/editar/<int:id>', methods=['POST'])
@app.route('/catalogo/equipamento/editar/<id>', methods=['POST'])
@login_required
def editar_cat_equipamento(id):
    try: id = int(id)
    except: return redirect(url_for('config_orcamento'))
    nome = request.form.get('nome', '').strip()
    conn = get_db()
    conn.execute("UPDATE CatEquipamento SET nome=? WHERE id=?", (nome, id))
    conn.commit()
    conn.close()
    flash("Equipamento atualizado!", "success")
    return redirect(url_for('config_orcamento'))

@app.route('/catalogo/equipamento/excluir/<int:id>')
@app.route('/catalogo/equipamento/excluir/<id>')
@login_required
def excluir_cat_equipamento(id):
    try: id = int(id)
    except: return redirect(url_for('config_orcamento'))
    conn = get_db()
    conn.execute("DELETE FROM CatEquipamento WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Equipamento excluído!", "info")
    return redirect(url_for('config_orcamento'))


# === OS / SERVICOS (bloco unico, endpoints explicitos) ===


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


@app.route('/alertas')
@app.route('/alertas-retorno')
@app.route('/alertas_retorno')
@login_required
def alertas_retorno():
    conn = get_db()
    alertas = []
    if conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='AlertaRetorno'").fetchone():
        alertas = conn.execute("SELECT * FROM AlertaRetorno ORDER BY id DESC").fetchall()
    conn.close()
    if os.path.exists("templates/servicos/alertas_retorno.html"):
        return render_template('servicos/alertas_retorno.html', alertas=alertas)
    return render_template('alertas_retorno.html', alertas=alertas)

@app.route('/servicos')
@app.route('/servico')
@app.route('/lista_servicos')
@app.route('/os')
@login_required
def lista_servicos():
    conn = get_db()
    servicos = conn.execute("SELECT * FROM AgendamentoOnline ORDER BY id DESC").fetchall()
    conn.close()
    return render_template('servicos/lista_servicos.html', servicos=servicos)

@app.route('/servico/novo', methods=['GET', 'POST'])
@app.route('/servicos/novo', methods=['GET', 'POST'])
@app.route('/cadastrar_servico', methods=['GET', 'POST'])
@app.route('/cadastrar-servico', methods=['GET', 'POST'])
@app.route('/nova-os', methods=['GET', 'POST'])
@login_required
def cadastrar_servico():
    conn = get_db()
    if request.method == 'POST':
        c_id = request.form.get('cliente_id')
        sel = (request.form.get('tipo_servico') or '').strip()
        livre = (request.form.get('tipo_servico_livre') or '').strip()
        tipo_s = sel or livre or 'Serviço Geral'
        desc = request.form.get('descricao', '')
        equip = request.form.get('equipamento', '')
        try:
            preco = float(request.form.get('preco', 0) or 0)
        except Exception:
            preco = 0.0
        data_s = request.form.get('data_servico') or date.today().isoformat()
        nome_cli, tel, end = 'Cliente', '', ''
        if c_id:
            row = conn.execute("SELECT nome, telefone, endereco FROM Cliente WHERE id=?", (c_id,)).fetchone()
            if row:
                nome_cli = row['nome']
                tel = row['telefone'] or ''
                end = row['endereco'] or ''
        conn.execute("""INSERT INTO AgendamentoOnline (
            nome_cliente, telefone, endereco, tipo_servico, tipo_aparelho,
            data_sugerida, valor, status, status_servico, etapa_fluxo, observacao
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Pendente', 'Pendente', 1, ?)""",
        (nome_cli, tel, end, tipo_s, equip, data_s, preco, desc))
        conn.commit()
        conn.close()
        flash("Nova OS cadastrada com sucesso!", "success")
        return redirect(url_for('lista_servicos'))
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
    return render_template('servicos/cadastrar_servico.html', clientes=clientes, aparelhos=aparelhos, cat_servicos=cat_servicos)


def _ensure_func_ponto_schema(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS Funcionario (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT, telefone TEXT, cargo TEXT, salario_base REAL, comissao_percentual REAL, foto_base64 TEXT)")
    # adiciona coluna foto se tabela antiga nao tiver
    cols = [r[1] for r in conn.execute("PRAGMA table_info(Funcionario)").fetchall()]
    if 'foto_base64' not in cols:
        try:
            conn.execute("ALTER TABLE Funcionario ADD COLUMN foto_base64 TEXT")
        except Exception:
            pass
    conn.execute("CREATE TABLE IF NOT EXISTS Ponto (id INTEGER PRIMARY KEY AUTOINCREMENT, funcionario_id INTEGER, data TEXT, hora_entrada TEXT, hora_saida TEXT, total_horas REAL, horas_extras REAL, foto_base64 TEXT)")
    cols_p = [r[1] for r in conn.execute("PRAGMA table_info(Ponto)").fetchall()]
    if 'foto_base64' not in cols_p:
        try:
            conn.execute("ALTER TABLE Ponto ADD COLUMN foto_base64 TEXT")
        except Exception:
            pass
    conn.commit()

@app.route('/funcionarios')
@app.route('/funcionario')
@login_required
def lista_funcionarios():
    conn = get_db()
    _ensure_func_ponto_schema(conn)
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
    _ensure_func_ponto_schema(conn)
    if request.method == 'POST':
        nome = (request.form.get('nome') or '').strip()
        email = request.form.get('email') or ''
        telefone = request.form.get('telefone') or ''
        cargo = request.form.get('cargo') or ''
        foto = request.form.get('foto_base64') or ''
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
            "INSERT INTO Funcionario (nome, email, telefone, cargo, salario_base, comissao_percentual, foto_base64) VALUES (?,?,?,?,?,?,?)",
            (nome, email, telefone, cargo, salario, comissao, foto if foto.startswith('data:image') else None)
        )
        conn.commit()
        conn.close()
        flash('Funcionario cadastrado' + (' com foto facial!' if foto else '!'), 'success')
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
    _ensure_func_ponto_schema(conn)
    if request.method == 'POST':
        nome = (request.form.get('nome') or '').strip()
        email = request.form.get('email') or ''
        telefone = request.form.get('telefone') or ''
        cargo = request.form.get('cargo') or ''
        foto = request.form.get('foto_base64') or ''
        try:
            salario = float(request.form.get('salario_base', 0) or 0)
        except Exception:
            salario = 0.0
        try:
            comissao = float(request.form.get('comissao_percentual', 0) or 0)
        except Exception:
            comissao = 0.0
        if foto.startswith('data:image'):
            conn.execute(
                "UPDATE Funcionario SET nome=?, email=?, telefone=?, cargo=?, salario_base=?, comissao_percentual=?, foto_base64=? WHERE id=?",
                (nome, email, telefone, cargo, salario, comissao, foto, id)
            )
        else:
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
    _ensure_func_ponto_schema(conn)
    if request.method == 'POST':
        func_id = request.form.get('funcionario_id')
        tipo_reg = request.form.get('tipo', 'Entrada')
        foto_ponto = request.form.get('foto_ponto') or ''
        modo = request.form.get('modo') or 'manual'
        hoje = date.today().isoformat()
        agora = datetime.now().strftime('%H:%M:%S')
        if not func_id:
            flash('Selecione ou reconheca o funcionario.', 'warning')
        else:
            nome = ''
            rowf = conn.execute("SELECT nome FROM Funcionario WHERE id=?", (func_id,)).fetchone()
            if rowf:
                nome = rowf['nome']
            if tipo_reg == 'Entrada':
                conn.execute(
                    "INSERT INTO Ponto (funcionario_id, data, hora_entrada, foto_base64) VALUES (?,?,?,?)",
                    (func_id, hoje, agora, foto_ponto if foto_ponto.startswith('data:image') else None)
                )
                conn.commit()
                tag = ' (facial)' if modo == 'facial' else ''
                flash('ENTRADA de ' + (nome or 'funcionario') + ' as ' + agora + tag, 'success')
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
                    if foto_ponto.startswith('data:image'):
                        conn.execute("UPDATE Ponto SET hora_saida=?, total_horas=?, foto_base64=? WHERE id=?", (agora, total, foto_ponto, row['id']))
                    else:
                        conn.execute("UPDATE Ponto SET hora_saida=?, total_horas=? WHERE id=?", (agora, total, row['id']))
                else:
                    conn.execute(
                        "INSERT INTO Ponto (funcionario_id, data, hora_saida, foto_base64) VALUES (?,?,?,?)",
                        (func_id, hoje, agora, foto_ponto if foto_ponto.startswith('data:image') else None)
                    )
                conn.commit()
                tag = ' (facial)' if modo == 'facial' else ''
                flash('SAIDA de ' + (nome or 'funcionario') + ' as ' + agora + tag, 'success')

    try:
        pontos = conn.execute(
            "SELECT p.*, f.nome as funcionario_nome FROM Ponto p LEFT JOIN Funcionario f ON p.funcionario_id=f.id ORDER BY p.id DESC LIMIT 50"
        ).fetchall()
    except Exception:
        pontos = []
    funcionarios = conn.execute("SELECT * FROM Funcionario ORDER BY nome ASC").fetchall()
    conn.close()
    return render_template('funcionarios/bater_ponto.html', pontos=pontos, funcionarios=funcionarios)


if __name__ == '__main__':
    try:
        _iniciar_telegram_background()
    except Exception as e:
        print(f"[Telegram] Aviso ao iniciar bot: {e}")

    print("=" * 60)
    print(" ClimaGestao iniciado com sucesso!")
    print(" URL Local:   http://127.0.0.1:5001")
    print(" Painel:      http://127.0.0.1:5001/painel")
    print("=" * 60)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)), debug=True)

