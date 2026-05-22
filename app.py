import streamlit as st
import requests
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# --- CONFIGURAÇÕES DO SUPABASE ---
SUPABASE_URL = "https://hxkeahtcsmmehucmndhk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInZiI6Imh4a2VhaHRjc21tZWh1Y21uZGhrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk0NTA5ODgsImV4cCI6MjA5NTAyNjk4OH0.62RDcA4bWJA-0Ie3DWFnaFC4lWvoOTDgCWagmOJ2X34"

# SUBSTITUA PELO SEU E-MAIL DE ADMINISTRADOR:
EMAIL_ADMIN = "felipegpinheiro@hotmail.com" 

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

st.set_page_config(page_title="Super Bolão Copa 2026", page_icon="🏆", layout="wide")

# --- FUNÇÕES DE BANCO DE DADOS (API) ---
def requisicao_supabase(metodo, endpoint, json_data=None, params=None, custom_headers=None):
    url = f"{SUPABASE_URL}/{endpoint}"
    headers = custom_headers if custom_headers else HEADERS
    try:
        if metodo == "GET": return requests.get(url, headers=headers, params=params)
        if metodo == "POST": return requests.post(url, headers=headers, json=json_data)
        if metodo == "PATCH": return requests.patch(url, headers=headers, json=json_data)
    except Exception:
        return None

def fazer_login(email, password):
    res = requisicao_supabase("POST", "auth/v1/token?grant_type=password", json_data={"email": email, "password": password})
    return (res.json()["access_token"], res.json()["user"]["id"]) if res and res.status_code == 200 else (None, None)

def cadastrar_usuario(email, password):
    res = requisicao_supabase("POST", "auth/v1/signup", json_data={"email": email, "password": password})
    return res is not None and res.status_code in [200, 201]

def buscar_dados(tabela):
    res = requisicao_supabase("GET", f"rest/v1/{tabela}?select=*")
    return res.json() if res and res.status_code == 200 else []

# --- MOTOR DE CÁLCULO DE PONTUAÇÃO ---
def calcular_pontos(gols_p_a, gols_p_b, gols_r_a, gols_r_b):
    if gols_r_a is None or gols_r_b is None: return 0
    if gols_p_a == gols_r_a and gols_p_b == gols_r_b: return 5
    vencedor_palpite = "A" if gols_p_a > gols_p_b else "B" if gols_p_b > gols_p_a else "Empate"
    vencedor_real = "A" if gols_r_a > gols_r_b else "B" if gols_r_b > gols_r_a else "Empate"
    if vencedor_palpite == vencedor_real: return 3
    if gols_p_a == gols_r_a or gols_p_b == gols_r_b: return 1
    return 0

if "logado" not in st.session_state:
    st.session_state.update({"logado": False, "token": None, "user_id": None, "email": ""})

# --- INTERFACE DE LOGIN ---
if not st.session_state.logado:
    st.title("⚽ Launchpad - Bolão da Empresa")
    aba_l, aba_c = st.tabs(["Entrar", "Criar Conta"])
    with aba_l:
        u = st.text_input("E-mail corporativo")
        s = st.text_input("Senha", type="password")
        if st.button("Acessar Painel"):
            token, uid = fazer_login(u, s)
            if token:
                st.session_state.update({"logado": True, "token": token, "user_id": uid, "email": u})
                st.rerun()
            else: st.error("Acesso negado. Verifique as suas credenciais.")
    with aba_c:
        nu = st.text_input("Novo E-mail")
        ns = st.text_input("Nova Senha (mín. 6 dígitos)", type="password")
        if st.button("Registrar"):
            if cadastrar_usuario(nu, ns): st.success("Conta criada! Mude para a aba 'Entrar'.")
            else: st.error("Erro ao registrar usuário.")

# --- SISTEMA LOGADO ---
else:
    is_admin = st.session_state.email == EMAIL_ADMIN
    agora = datetime.utcnow()
    
    # Coleta global de dados
    jogos_banco = buscar_dados("jogos")
    
    # Extrair lista única de seleções/times cadastrados na tabela de jogos
    times_disponiveis = set()
    for jg in jogos_banco:
        if jg.get("time_a"): times_disponiveis.add(jg["time_a"])
        if jg.get("time_b"): times_disponiveis.add(jg["time_b"])
    lista_times = sorted(list(times_disponiveis))
    
    # Fallback para o cronômetro funcionar caso o banco esteja vazio
    if not jogos_banco:
        jogos_para_relogio = [{"data_hora": "2026-06-11 19:00:00+00", "time_a": "México", "time_b": "EUA", "fase": "Grupos"}]
    else:
        jogos_para_relogio = jogos_banco
            
    st.title("🏆 Super Bolão Copa 2026")
    
    # Cronômetro de travas dinâmico
    proximas_travas = []
    for j in jogos_para_relogio:
        d_limpa = j["data_hora"].replace("Z", "").split("+")[0]
        try:
            d_trava = datetime.fromisoformat(d_limpa) - timedelta(minutes=30)
            if d_trava > agora: proximas_travas.append(d_trava)
        except: pass
            
    if proximas_travas:
        proxima_trava = min(proximas_travas)
        iso_alvo = proxima_trava.strftime("%Y-%m-%dT%H:%M:%SZ")
        js_relogio = f"""
        <div style="background-color: #1E293B; border-radius: 10px; padding: 12px; text-align: center; font-family: sans-serif; color: #F8FAFC; border: 1px solid #334155;">
            <span style="font-size: 14px; text-transform: uppercase; letter-spacing: 1px; color: #94A3B8; font-weight: bold;">⏱️ Tempo para fechamento dos próximos palpites:</span>
            <div id="countdown" style="font-size: 28px; font-weight: bold; color: #38BDF8; margin-top: 5px;">Calculando...</div>
        </div>
        <script>
            var targetDate = new Date("{iso_alvo}").getTime();
            var x = setInterval(function() {{
                var now = new Date().getTime();
                var nowUTC = now + (new Date().getTimezoneOffset() * 60000);
                var distance = targetDate - nowUTC;
                if (distance < 0) {{
                    clearInterval(x);
                    document.getElementById("countdown").innerHTML = "PALPITES ENCERRADOS!";
                    return;
                }}
                var days = Math.floor(distance / (1000 * 60 * 60 * 24));
                var hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                var seconds = Math.floor((distance % (1000 * 60)) / 1000);
                document.getElementById("countdown").innerHTML = (days > 0 ? days + "d " : "") + hours + "h " + minutes + "m " + seconds + "s";
            }}, 1000);
        </script>
        """
        components.html(js_relogio, height=95)
    else:
        st.markdown("<div style='background-color:#1E293B; padding:15px; text-align:center; border-radius:10px; color:#EF4444; font-weight:bold;'>🔒 Inscrições trancadas!</div>", unsafe_allow_html=True)

    abas = ["Jogos e Palpites", "Palpites da Competição", "Ranking Geral", "Ver Palpites Alheios"]
    if is_admin: abas.append("⚙️ Painel do Admin")
    abas_gui = st.tabs(abas)

    # --- ABA 1: JOGOS E PALPITES ---
    with abas_gui[0]:
        st.header("🎯 Palpites dos Jogos")
        if not jogos_banco:
            st.info("💡 A tabela de jogos está vazia no momento. Adicione jogos usando o painel administrativo.")
        
        palpites = buscar_dados(f"palpites?id_usuario=eq.{st.session_state.user_id}")
        palpites_dict = {p["id_jogo"]: p for p in palpites}

        for j in sorted(jogos_banco, key=lambda x: x["data_hora"]):
            data_limpa = j["data_hora"].replace("Z", "").split("+")[0]
            data_j = datetime.fromisoformat(data_limpa)
            bloqueado = agora > (data_j - timedelta(minutes=30))
            p_salvo = palpites_dict.get(j["id"], {"gols_time_a": 0, "gols_time_b": 0})
            
            with st.container():
                col_info1, col_info2 = st.columns([2, 1])
                with col_info1: st.markdown(f"**Fase:** {j['fase']} | 📅 {data_j.strftime('%d/%m/%Y às %H:%M')} UTC")
                with col_info2: st.markdown(f"<p style='text-align:right; font-weight:bold; color:{'#10B981' if not bloqueado else '#64748B'}; margin:0;'>{('⏳ Ativo' if not bloqueado else '🔒 Encerrado')}</p>", unsafe_allow_html=True)
                
                col1, col2, col3, col4 = st.columns([3, 1, 3, 2])
                with col1: g_a = st.number_input(f"{j['time_a']}", min_value=0, value=int(p_salvo["gols_time_a"]), disabled=bloqueado, key=f"inp_a_{j['id']}")
                with col2: st.markdown("<p style='text-align:center;font-size:24px;margin-top:20px;'>X</p>", unsafe_allow_html=True)
                with col3: g_b = st.number_input(f"{j['time_b']}", min_value=0, value=int(p_salvo["gols_time_b"]), disabled=bloqueado, key=f"inp_b_{j['id']}")
                with col4:
                    if j["gols_real_a"] is not None: st.metric("Resultado Real", f"{j['gols_real_a']} x {j['gols_real_b']}")
                    elif bloqueado: st.info("🔒 Trancado")
                    else:
                        if st.button("Salvar", key=f"save_{j['id']}"):
                            headers_auth = {**HEADERS, "Authorization": f"Bearer {st.session_state.token}", "Prefer": "resolution=merge-duplicates"}
                            payload = {"id_usuario": st.session_state.user_id, "id_jogo": j["id"], "gols_time_a": g_a, "gols_time_b": g_b}
                            requisicao_supabase("POST", "rest/v1/palpites", json_data=payload, custom_headers=headers_auth)
                            st.toast("Palpite gravado!")
                st.markdown("---")

    # --- ABA 2: PALPITES DA COMPETIÇÃO ---
    with abas_gui[1]:
        st.header("🏆 Palpites de Longo Prazo")
        primeiro_jogo_copa = datetime(2026, 6, 11, 16, 0) 
        competicao_bloqueada = agora > primeiro_jogo_copa

        p_comp = buscar_dados(f"palpites_competicao?id_usuario=eq.{st.session_state.user_id}")
        p_c_atual = p_comp[0] if p_comp else {"campeon": "", "vice": "", "artilheiro": "", "melhor_jogador": ""}

        st.write("Dê os seus palpites definitivos antes da abertura da Copa!")
        
        # MELHORIA: Caixas de seleção com base nas seleções reais cadastradas na tabela de jogos
        if lista_times:
            idx_camp = lista_times.index(p_c_atual["campeon"]) if p_c_atual["campeon"] in lista_times else 0
            idx_vice = lista_times.index(p_c_atual["vice"]) if p_c_atual["vice"] in lista_times else 0
            
            c_camp = st.selectbox("Quem será o Campeão? (50 pts)", options=lista_times, index=idx_camp, disabled=competicao_bloqueada)
            c_vice = st.selectbox("Quem será o Vice-Campeão? (25 pts)", options=lista_times, index=idx_vice, disabled=competicao_bloqueada)
        else:
            st.warning("⚠️ Cadastre jogos no painel para habilitar a escolha de seleções aqui.")
            c_camp = st.text_input("Quem será o Campeão? (50 pts)", value=p_c_atual["campeon"], disabled=competicao_bloqueada)
            c_vice = st.text_input("Quem será o Vice-Campeão? (25 pts)", value=p_c_atual["vice"], disabled=competicao_bloqueada)

        c_art = st.text_input("Quem será o Artilheiro? (25 pts)", value=p_c_atual["artilheiro"], disabled=competicao_bloqueada)
        c_melhor = st.text_input("Quem será o Melhor Jogador? (25 pts)", value=p_c_atual["melhor_jogador"], disabled=competicao_bloqueada)

        if not competicao_bloqueada:
            if st.button("Gravar Palpites Especiais"):
                h_auth = {**HEADERS, "Authorization": f"Bearer {st.session_state.token}", "Prefer": "resolution=merge-duplicates"}
                payload = {"id_usuario": st.session_state.user_id, "campeon": c_camp, "vice": c_vice, "artilheiro": c_art, "melhor_jogador": c_melhor}
                requisicao_supabase("POST", "rest/v1/palpites_competicao", json_data=payload, custom_headers=h_auth)
                st.success("Palpites especiais salvos!")
        else:
            st.warning("🔒 Torneio em andamento. Inscrições bloqueadas.")

    # --- ABA 3: RANKING EM TEMPO REAL ---
    with abas_gui[2]:
        st.header("📊 Classificação da Empresa")
        todos_palpites = buscar_dados("palpites")
        todos_palpites_comp = buscar_dados("palpites_competicao")
        res_comp = buscar_dados("resultados_competicao")
        r_c = res_comp[0] if res_comp else {}

        pontos_usuarios = {}
        for p in todos_palpites:
            uid = p["id_usuario"]
            jogo = next((j for j in jogos_banco if j["id"] == p["id_jogo"]), None)
            if jogo and jogo["gols_real_a"] is not None:
                pts = calcular_pontos(p["gols_time_a"], p["gols_time_b"], jogo["gols_real_a"], jogo["gols_real_b"])
                pontos_usuarios[uid] = pontos_usuarios.get(uid, 0) + pts

        for pc in todos_palpites_comp:
            uid = pc["id_usuario"]
            if r_c.get("campeon") and pc["campeon"] == r_c["campeon"]: pontos_usuarios[uid] = pontos_usuarios.get(uid, 0) + 50
            if r_c.get("vice") and pc["vice"] == r_c["vice"]: pontos_usuarios[uid] = pontos_usuarios.get(uid, 0) + 25
            if r_c.get("artilheiro") and pc["artilheiro"] == r_c["artilheiro"]: pontos_usuarios[uid] = pontos_usuarios.get(uid, 0) + 25
            if r_c.get("melhor_jogador") and pc["melhor_jogador"] == r_c["melhor_jogador"]: pontos_usuarios[uid] = pontos_usuarios.get(uid, 0) + 25

        ranking_ordenado = sorted(pontos_usuarios.items(), key=lambda item: item[1], reverse=True)
        if ranking_ordenado:
            for posicao, (u_id, total_pts) in enumerate(ranking_ordenado, start=1):
                st.subheader(f"🥇 {posicao}º Lugar: Usuário {u_id[:8]}... — {total_pts} Pontos")
        else:
            st.info("Nenhum ponto computado até o momento.")

    # --- ABA 4: VER PALPITES ALHEIOS ---
    with abas_gui[3]:
        st.header("👀 Espiar Palpites Concluídos")
        lista_opcoes_jogos = [f"{j['id']} | {j['time_a']} x {j['time_b']}" for j in jogos_banco]
        if lista_opcoes_jogos:
            escolha_jogo = st.selectbox("Selecione a partida para auditar:", lista_opcoes_jogos)
            if escolha_jogo:
                id_j_sel = int(escolha_jogo.split(" | ")[0])
                j_sel = next(j for j in jogos_banco if j["id"] == id_j_sel)
                data_limpa_sel = j_sel["data_hora"].replace("Z", "").split("+")[0]
                data_j_sel = datetime.fromisoformat(data_limpa_sel)
                
                if agora > (data_j_sel - timedelta(minutes=30)):
                    palpites_desse_jogo = buscar_dados(f"palpites?id_jogo=eq.{id_j_sel}")
                    for plp in palpites_desse_jogo:
                        st.text(f"Usuário {plp['id_usuario'][:8]}... chutou: {j_sel['time_a']} {plp['gols_time_a']} x {plp['gols_time_b']} {j_sel['time_b']}")
                else:
                    st.error("🔒 Palpites protegidos! Visíveis apenas 30 minutos antes do jogo.")
        else:
            st.info("Nenhum jogo disponível.")

    # --- ABA 5: PAINEL DO ADMINISTRADOR ---
    if is_admin:
        with abas_gui[4]:
            st.header("⚙️ Controle Geral do Administrador")
            
            # NOVIDADE: SUB-ABA DE AUDITORIA DE CONTAS CRIADAS
            sub_aba1, sub_aba2, sub_aba3, sub_aba4 = st.tabs([
                "👥 Contas & Pendências", 
                "➕ Inserir Jogos", 
                "📝 Resultados dos Jogos", 
                "🏆 Resultados da Copa"
            ])
            
            with sub_aba1:
                st.subheader("Usuários Registrados e Status de Palpites")
                todos_palpites_banco = buscar_dados("palpites")
                
                # Agrupar usuários únicos que já possuem alguma interação
                usuarios_unicos = list(set([p["id_usuario"] for p in todos_palpites_banco]))
                if st.session_state.user_id not in usuarios_unicos:
                    usuarios_unicos.append(st.session_state.user_id)
                
                total_jogos_cadastrados = len(jogos_banco)
                
                st.write(f"**Total de jogos na base:** {total_jogos_cadastrados}")
                
                dados_tabela_usuarios = []
                for idx, uid in enumerate(usuarios_unicos, start=1):
                    # Contar quantos jogos esse usuário específico já palpitou
                    palpites_do_usuario = len([p for p in todos_palpites_banco if p["id_usuario"] == uid])
                    faltam = max(0, total_jogos_cadastrados - p_do_usuario) if (total_jogos_cadastrados - palpites_do_usuario) > 0 else 0
                    
                    st.markdown(f"""
                    <div style="padding:10px; background-color:#1E293B; border-radius:5px; margin-bottom:8px; border-left: 5px solid {'#10B981' if faltam == 0 else '#EF4444'};">
                        <strong>👤 Participante {idx}:</strong> <code>{uid}</code> <br>
                        ✅ Palpites Feitos: <strong>{palpites_do_usuario}</strong> | 🚨 Palpites Restantes: <strong style="color:{'#10B981' if faltam == 0 else '#F87171'}">{faltam}</strong>
                    </div>
                    """, unsafe_allow_html=True)

            with sub_aba2:
                st.subheader("Inserir Confronto (Fase de Grupos ou Mata-Mata)")
                with st.form("novos_confrontos"):
                    fase_selecionada = st.selectbox("Fase", ["Fase de Grupos", "Dezesseis-avos de Final", "Oitavas de Final", "Quartas de Final", "Semifinal", "Terceiro Lugar", "Grande Final"])
                    t_a = st.text_input("Seleção A")
                    t_b = st.text_input("Seleção B")
                    d_h = st.text_input("Data/Hora no padrão (AAAA-MM-DD HH:MM:SS)", value="2026-06-11 16:00:00")
                    if st.form_submit_button("Lançar Novo Jogo no Sistema"):
                        payload = {"time_a": t_a, "time_b": t_b, "data_hora": f"{d_h}+00", "fase": fase_selecionada}
                        res_add = requisicao_supabase("POST", "rest/v1/jogos", json_data=payload)
                        if res_add and res_add.status_code in [200, 201]:
                            st.success("Jogo inserido com sucesso!")
                            st.rerun()
                        else: st.error("Erro ao salvar. Verifique o formato de data.")

            with sub_aba3:
                st.subheader("Imputar Resultados Reais")
                opcoes_admin_jogos = [f"{jg['id']} | {jg['time_a']} x {jg['time_b']}" for jg in jogos_banco]
                if opcoes_admin_jogos:
                    id_j_res = st.selectbox("Escolha o jogo para atualizar o placar definitivo:", opcoes_admin_jogos, key="sb_admin_res")
                    if id_j_res:
                        id_real = int(id_j_res.split(" | ")[0])
                        res_a = st.number_input("Gols do Time A", min_value=0, step=1, key="res_a")
                        res_b = st.number_input("Gols do Time B", min_value=0, step=1, key="res_b")
                        if st.button("Gravar Placar Oficial"):
                            requisicao_supabase("PATCH", f"rest/v1/jogos?id=eq.{id_real}", json_data={"gols_real_a": res_a, "gols_real_b": res_b})
                            st.success("Placar oficial gravado!")
                            st.rerun()
                else: st.info("Nenhum jogo cadastrado.")

            with sub_aba4:
                st.subheader("Imputar Resultados Finais da Competição")
                r_c_dados = buscar_dados("resultados_competicao")
                rc_atual = r_c_dados[0] if r_c_dados else {"campeon": "", "vice": "", "artilheiro": "", "melhor_jogador": ""}
                
                f_camp = st.text_input("Campeão Oficial", value=rc_atual.get("campeon", ""))
                f_vice = st.text_input("Vice Oficial", value=rc_atual.get("vice", ""))
                f_art = st.text_input("Artilheiro Oficial", value=rc_atual.get("artilheiro", ""))
                f_melhor = st.text_input("Melhor Jogador Oficial", value=rc_atual.get("melhor_jogador", ""))
                
                if st.button("Encerrar Prêmiações da Copa"):
                    payload = {"campeon": f_camp, "vice": f_vice, "artilheiro": f_art, "melhor_jogador": f_melhor}
                    requisicao_supabase("PATCH", "rest/v1/resultados_competicao?id=eq.1", json_data=payload)
                    st.success("Resultados oficiais salvos!")
