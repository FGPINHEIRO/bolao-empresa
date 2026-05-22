import streamlit as st
import requests
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES DO SUPABASE ---
SUPABASE_URL = "https://hxkeahtcsmmehucmndhk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh4a2VhaHRjc21tZWh1Y21uZGhrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk0NTA5ODgsImV4cCI6MjA5NTAyNjk4OH0.62RDcA4bWJA-0Ie3DWFnaFC4lWvoOTDgCWagmOJ2X34"

# CONFIGURADO COM O SEU E-MAIL REAL PARA ACESSO ADMIN:
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
    if metodo == "GET": return requests.get(url, headers=headers, params=params)
    if metodo == "POST": return requests.post(url, headers=headers, json=json_data)
    if metodo == "PATCH": return requests.patch(url, headers=headers, json=json_data)

def fazer_login(email, password):
    res = requisicao_supabase("POST", "auth/v1/token?grant_type=password", json_data={"email": email, "password": password})
    return (res.json()["access_token"], res.json()["user"]["id"]) if res.status_code == 200 else (None, None)

def cadastrar_usuario(email, password):
    return requisicao_supabase("POST", "auth/v1/signup", json_data={"email": email, "password": password}).status_code == 200

def buscar_dados(tabela):
    res = requisicao_supabase("GET", f"rest/v1/{tabela}?select=*")
    return res.json() if res.status_code == 200 else []

def buscar_usuarios():
    res = requisicao_supabase("GET", "rest/v1/palpites?select=id_usuario")
    if res.status_code == 200:
        return list(set([p["id_usuario"] for p in res.json()]))
    return []

# --- MOTOR DE CÁLCULO DE PONTUAÇÃO ---
def calcular_pontos(gols_p_a, gols_p_b, gols_r_a, gols_r_b):
    if gols_r_a is None or gols_r_b is None:
        return 0
    # 1. Acerto em cheio do placar (5 pontos)
    if gols_p_a == gols_r_a and gols_p_b == gols_r_b:
        return 5
    
    vencedor_palpite = "A" if gols_p_a > gols_p_b else "B" if gols_p_b > gols_p_a else "Empate"
    vencedor_real = "A" if gols_r_a > gols_r_b else "B" if gols_r_b > gols_r_a else "Empate"
    
    # 2. Acerto do ganhador ou do empate (3 pontos)
    if vencedor_palpite == vencedor_real:
        return 3
    # 3. Acerto do placar de apenas um dos times (1 ponto)
    if gols_p_a == gols_r_a or gols_p_b == gols_r_b:
        return 1
    return 0

# --- CONTROLE DE SESSÃO ---
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
            else: st.error("Acesso negado.")
    with aba_c:
        nu = st.text_input("Novo E-mail")
        ns = st.text_input("Nova Senha (mín. 6 dígitos)", type="password")
        if st.button("Registrar"):
            if cadastrar_usuario(nu, ns): st.success("Sucesso! Faça login.")
            else: st.error("Incapaz de registrar usuário.")

# --- SISTEMA LOGADO ---
else:
    is_admin = st.session_state.email == EMAIL_ADMIN
    
    abas = ["Jogos e Palpites", "Palpites da Competição", "Ranking Geral", "Ver Palpites Alheios"]
    if is_admin:
        abas.append("⚙️ Painel do Admin")
        
    abas_gui = st.tabs(abas)
    agora = datetime.utcnow()

    # --- ABA 1: JOGOS E PALPITES ---
    with abas_gui[0]:
        st.header("🎯 Palpites dos Jogos")
        jogos = buscar_dados("jogos")
        palpites = buscar_dados(f"palpites?id_usuario=eq.{st.session_state.user_id}")
        palpites_dict = {p["id_jogo"]: p for p in palpites}

        for j in sorted(jogos, key=lambda x: x["data_hora"]):
            # Tratamento da data para remover qualquer informação oculta de fuso horário (limpa o Z ou o +00)
            data_limpa = j["data_hora"].replace("Z", "").split("+")[0]
            data_j = datetime.fromisoformat(data_limpa)
            
            # Agora a comparação funciona perfeitamente (ambas são naive)
            bloqueado = agora > (data_j - timedelta(minutes=30))
            
            p_salvo = palpites_dict.get(j["id"], {"gols_time_a": 0, "gols_time_b": 0})
            
            with st.container():
                st.markdown(f"**Fase:** {j['fase']} | 📅 {data_j.strftime('%d/%m/%Y às %H:%M')} UTC")
                col1, col2, col3, col4 = st.columns([3, 1, 3, 2])
                with col1: g_a = st.number_input(f"{j['time_a']}", min_value=0, value=int(p_salvo["gols_time_a"]), disabled=bloqueado, key=f"inp_a_{j['id']}")
                with col2: st.markdown("<p style='text-align:center;font-size:24px;margin-top:20px;'>X</p>", unsafe_allow_html=True)
                with col3: g_b = st.number_input(f"{j['time_b']}", min_value=0, value=int(p_salvo["gols_time_b"]), disabled=bloqueado, key=f"inp_b_{j['id']}")
                with col4:
                    if j["gols_real_a"] is not None:
                        st.metric("Resultado Real", f"{j['gols_real_a']} x {j['gols_real_b']}")
                    elif bloqueado:
                        st.info("🔒 Bloqueado")
                    else:
                        if st.button("Salvar", key=f"save_{j['id']}"):
                            headers_auth = {**HEADERS, "Authorization": f"Bearer {st.session_state.token}", "Prefer": "resolution=merge-duplicates"}
                            payload = {"id_usuario": st.session_state.user_id, "id_jogo": j["id"], "gols_time_a": g_a, "gols_time_b": g_b}
                            requisicao_supabase("POST", "rest/v1/palpites", json_data=payload, custom_headers=headers_auth)
                            st.toast("Palpite computado!")
                st.markdown("---")

    # --- ABA 2: PALPITES DA COMPETIÇÃO ---
    with abas_gui[1]:
        st.header("🏆 Palpites de Longo Prazo")
        primeiro_jogo_copa = datetime(2026, 6, 11, 16, 0) 
        competicao_bloqueada = agora > primeiro_jogo_copa

        p_comp = buscar_dados(f"palpites_competicao?id_usuario=eq.{st.session_state.user_id}")
        p_c_atual = p_comp[0] if p_comp else {"campeon": "", "vice": "", "artilheiro": "", "melhor_jogador": ""}

        st.write("Dê os seus palpites definitivos até o primeiro jogo do torneio começar!")
        
        c_camp = st.text_input("Quem será o Campeão? (50 pts)", value=p_c_atual["campeon"], disabled=competicao_bloqueada)
        c_vice = st.text_input("Quem será o Vice-Campeão? (25 pts)", value=p_c_atual["vice"], disabled=competicao_bloqueada)
        c_art = st.text_input("Quem será o Artilheiro? (25 pts)", value=p_c_atual["artilheiro"], disabled=competicao_bloqueada)
        c_melhor = st.text_input("Quem será o Melhor Jogador? (25 pts)", value=p_c_atual["melhor_jogador"], disabled=competicao_bloqueada)

        if not competicao_bloqueada:
            if st.button("Gravar Palpites Especiais"):
                h_auth = {**HEADERS, "Authorization": f"Bearer {st.session_state.token}", "Prefer": "resolution=merge-duplicates"}
                payload = {"id_usuario": st.session_state.user_id, "campeon": c_camp, "vice": c_vice, "artilheiro": c_art, "melhor_jogador": c_melhor}
                requisicao_supabase("POST", "rest/v1/palpites_competicao", json_data=payload, custom_headers=h_auth)
                st.success("Palpites de competição atualizados!")
        else:
            st.warning("🔒 O torneio já iniciou. Palpites de competição trancados.")

    # --- ABA 3: RANKING EM TEMPO REAL ---
    with abas_gui[2]:
        st.header("📊 Classificação da Empresa")
        todos_jogos = buscar_dados("jogos")
        todos_palpites = buscar_dados("palpites")
        todos_palpites_comp = buscar_dados("palpites_competicao")
        res_comp = buscar_dados("resultados_competicao")
        r_c = res_comp[0] if res_comp else {}

        pontos_usuarios = {}

        # Processar pontos por jogo
        for p in todos_palpites:
            uid = p["id_usuario"]
            jogo = next((j for j in todos_jogos if j["id"] == p["id_jogo"]), None)
            if jogo and jogo["gols_real_a"] is not None:
                pts = calcular_pontos(p["gols_time_a"], p["gols_time_b"], jogo["gols_real_a"], jogo["gols_real_b"])
                pontos_usuarios[uid] = pontos_usuarios.get(uid, 0) + pts

        # Processar pontos especiais da competição
        for pc in todos_palpites_comp:
            uid = pc["id_usuario"]
            if r_c.get("campeon") and pc["campeon"] == r_c["campeon"]: pontos_usuarios[uid] = pontos_usuarios.get(uid, 0) + 50
            if r_c.get("vice") and pc["vice"] == r_c["vice"]: pontos_usuarios[uid] = pontos_usuarios.get(uid, 0) + 25
            if r_c.get("artilheiro") and pc["artilheiro"] == r_c["artilheiro"]: pontos_usuarios[uid] = pontos_usuarios.get(uid, 0) + 25
            if r_c.get("melhor_jogador") and pc["melhor_jogador"] == r_c["melhor_jogador"]: pontos_usuarios[uid] = pontos_usuarios.get(uid, 0) + 25

        ranking_ordenado = sorted(pontos_usuarios.items(), key=lambda item: item[1], reverse=True)
        
        if ranking_ordenado:
            for posicao, (u_id, total_pts) in enumerate(ranking_ordenado, start=1):
                st.subheader(f"🥇 {posicao}º Lugar: ID Usuário {u_id[:8]}... — {total_pts} Pontos")
        else:
            st.info("Nenhum ponto computado até o momento.")

    # --- ABA 4: VER PALPITES ALHEIOS ---
    with abas_gui[3]:
        st.header("👀 Espiar Palpites Concluídos")
        st.write("Os palpites de outros usuários só ficam visíveis quando faltarem menos de 30 minutos para o jogo começar.")
        
        jogos_disponiveis = buscar_dados("jogos")
        lista_opcoes_jogos = [f"{j['id']} | {j['time_a']} x {j['time_b']}" for j in jogos_disponiveis]
        escolha_jogo = st.selectbox("Selecione a partida para auditar:", lista_opcoes_jogos)

        if escolha_jogo:
            id_j_sel = int(escolha_jogo.split(" | ")[0])
            j_sel = next(j for j in jogos_disponiveis if j["id"] == id_j_sel)
            
            # Correção de fuso horário também na aba de espiar
            data_limpa_sel = j_sel["data_hora"].replace("Z", "").split("+")[0]
            data_j_sel = datetime.fromisoformat(data_limpa_sel)
            
            if agora > (data_j_sel - timedelta(minutes=30)):
                palpites_desse_jogo = buscar_dados(f"palpites?id_jogo=eq.{id_j_sel}")
                for plp in palpites_desse_jogo:
                    st.text(f"Usuário {plp['id_usuario'][:8]}... chutou: {j_sel['time_a']} {plp['gols_time_a']} x {plp['gols_time_b']} {j_sel['time_b']}")
            else:
                st.error("🔒 Segredo! Os palpites desta partida só serão revelados 30 minutos antes do início do jogo.")

    # --- ABA 5: PAINEL DO ADMINISTRADOR ---
    if is_admin:
        with abas_gui[4]:
            st.header("⚙️ Controle Geral do Administrador")
            
            st.subheader("1. Inserir Confronto de Mata-Mata (Fases Finais)")
            with st.form("novos_confrontos"):
                fase_selecionada = st.selectbox("Fase", ["Oitavas de Final", "Quartas de Final", "Semifinal", "Terceiro Lugar", "Grande Final"])
                t_a = st.text_input("Seleção A")
                t_b = st.text_input("Seleção B")
                d_h = st.text_input("Data/Hora no padrão (AAAA-MM-DD HH:MM:SS)", value="2026-06-27 15:00:00")
                if st.form_submit_button("Lançar Novo Jogo no Sistema"):
                    payload = {"time_a": t_a, "time_b": t_b, "data_hora": f"{d_h}+00", "fase": fase_selecionada}
                    requisicao_supabase("POST", "rest/v1/jogos", json_data=payload)
                    st.success("Novo confronto disponibilizado para palpites!")

            st.subheader("2. Imputar Resultados Reais dos Jogos")
            jogos_cadastrados = buscar_dados("jogos")
            id_j_res = st.selectbox("Escolha o jogo para atualizar o placar definitivo:", [f"{jg['id']} | {jg['time_a']} x {jg['time_b']}" for jg in jogos_cadastrados])
            if id_j_res:
                id_real = int(id_j_res.split(" | ")[0])
                res_a = st.number_input("Gols do Time A", min_value=0, step=1, key="res_a")
                res_b = st.number_input("Gols do Time B", min_value=0, step=1, key="res_b")
                if st.button("Gravar Placar Oficial"):
                    requisicao_supabase("PATCH", f"rest/v1/jogos?id=eq.{id_real}", json_data={"gols_real_a": res_a, "gols_real_b": res_b})
                    st.success("Placar oficial gravado! Ranking recalculado automaticamente.")

            st.subheader("3. Imputar Resultados Finais da Competição")
            r_c_dados = buscar_dados("resultados_competicao")
            rc_atual = r_c_dados[0] if r_c_dados else {"campeon": "", "vice": "", "artilheiro": "", "melhor_jogador": ""}
            
            f_camp = st.text_input("Campeão Oficial", value=rc_atual.get("campeon", ""))
            f_vice = st.text_input("Vice Oficial", value=rc_atual.get("vice", ""))
            f_art = st.text_input("Artilheiro Oficial", value=rc_atual.get("artilheiro", ""))
            f_melhor = st.text_input("Melhor Jogador Oficial", value=rc_atual.get("melhor_jogador", ""))
            
            if st.button("Encerrar Prêmiações da Copa"):
                payload = {"campeon": f_camp, "vice": f_vice, "artilheiro": f_art, "melhor_jogador": f_melhor}
                requisicao_supabase("PATCH", "rest/v1/resultados_competicao?id=eq.1", json_data=payload)
                st.success("Resultados oficiais salvos com sucesso!")
