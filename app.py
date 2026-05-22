import streamlit as st
import requests
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES DO SUPABASE ---
SUPABASE_URL = "https://hxkeahtcsmmehucmndhk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInZiI6Imh4a2VhaHRjc21tZWh1Y21uZGhrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk0NTA5ODgsImV4cCI6MjA5NTAyNjk4OH0.62RDcA4bWJA-0Ie3DWFnaFC4lWvoOTDgCWagmOJ2X34"

# SEU E-MAIL DE ADMINISTRADOR:
EMAIL_ADMIN = "felipegpinheiro@hotmail.com" 

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

st.set_page_config(page_title="Super Bolão Copa 2026", page_icon="🏆", layout="wide")

# --- FUNÇÕES DE BANCO DE DADOS ---
def requisicao_supabase(metodo, endpoint, json_data=None, params=None, custom_headers=None):
    url = f"{SUPABASE_URL}/{endpoint}"
    headers = custom_headers if custom_headers else HEADERS
    try:
        if metodo == "GET": return requests.get(url, headers=headers, params=params)
        if metodo == "POST": return requests.post(url, headers=headers, json=json_data)
        if metodo == "PATCH": return requests.patch(url, headers=headers, json=json_data)
    except:
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

# --- MOTOR DE CÁLCULO ---
def calcular_pontos(gols_p_a, gols_p_b, gols_r_a, gols_r_b):
    if gols_r_a is None or gols_r_b is None: return 0
    if gols_p_a == gols_r_a and gols_p_b == gols_r_b: return 5
    vencedor_palpite = "A" if gols_p_a > gols_p_b else "B" if gols_p_b > gols_p_a else "Empate"
    vencedor_real = "A" if gols_r_a > gols_r_b else "B" if gols_r_b > gols_r_a else "Empate"
    if vencedor_palpite == vencedor_real: return 3
    if gols_p_a == gols_r_a or gols_p_b == gols_r_b: return 1
    return 0

if "logado" not in st.session_state:
    st.session_state.update({"logado": False, "token": None, "user_id": None, "email": "", "nome_usuario": ""})

# --- INTERFACE DE LOGIN ORIGINAL ---
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
                p_comp = buscar_dados(f"palpites_competicao?id_usuario=eq.{uid}")
                if p_comp and p_comp[0].get("nome_participante"):
                    st.session_state.nome_usuario = p_comp[0]["nome_participante"]
                st.rerun()
            else:
                st.error("Acesso negado. Certifique-se de que o e-mail foi confirmado ou desligue a checagem no Supabase.")
    with aba_c:
        nu = st.text_input("Novo E-mail")
        ns = st.text_input("Nova Senha (mín. 6 dígitos)", type="password")
        if st.button("Registrar"):
            if cadastrar_usuario(nu, ns): st.success("Conta criada! Vá para a aba 'Entrar'.")
            else: st.error("Erro ao registrar conta.")

# --- SISTEMA LOGADO ---
else:
    # SE NÃO TEM NOME, OBRIGA A CRIAR UM NOME ANTES DE VER O SITE
    if not st.session_state.nome_usuario:
        st.title("👋 Bem-vindo ao Bolão!")
        st.subheader("Por favor, indique o seu nome (como deseja aparecer no Ranking):")
        nome_digitado = st.text_input("Nome e Sobrenome:")
        if st.button("Salvar Nome e Entrar"):
            if len(nome_digitado.strip()) < 3:
                st.error("Digite um nome com pelo menos 3 letras.")
            else:
                h_auth = {**HEADERS, "Authorization": f"Bearer {st.session_state.token}", "Prefer": "resolution=merge-duplicates"}
                payload = {"id_usuario": st.session_state.user_id, "nome_participante": nome_digitado.strip()}
                requisicao_supabase("POST", "rest/v1/palpites_competicao", json_data=payload, custom_headers=h_auth)
                st.session_state.nome_usuario = nome_digitado.strip()
                st.success("Nome salvo!")
                st.rerun()
        st.stop()

    is_admin = st.session_state.email == EMAIL_ADMIN
    agora = datetime.utcnow()
    jogos_banco = buscar_dados("jogos")
    
    times_set = set()
    for jg in jogos_banco:
        if jg.get("time_a"): times_set.add(jg["time_a"])
        if jg.get("time_b"): times_set.add(jg["time_b"])
    lista_times = sorted(list(times_set))

    abas = ["Jogos e Palpites", "Palpites da Competição", "Ranking Geral", "Ver Palpites Alheios"]
    if is_admin: abas.append("⚙️ Painel do Admin")
    abas_gui = st.tabs(abas)

    # --- ABA 1: JOGOS ---
    with abas_gui[0]:
        st.header("🎯 Palpites dos Jogos")
        if not jogos_banco: st.info("Nenhum jogo cadastrado na base.")
        
        palpites = buscar_dados(f"palpites?id_usuario=eq.{st.session_state.user_id}")
        palpites_dict = {p["id_jogo"]: p for p in palpites}

        for j in sorted(jogos_banco, key=lambda x: x["data_hora"]):
            data_j = datetime.fromisoformat(j["data_hora"].replace("Z", "").split("+")[0])
            bloqueado = agora > (data_j - timedelta(minutes=30))
            p_salvo = palpites_dict.get(j["id"], {"gols_time_a": 0, "gols_time_b": 0})
            
            with st.container():
                st.markdown(f"**Fase:** {j['fase']} | 📅 {data_j.strftime('%d/%m/%Y às %H:%M')} UTC")
                col1, col2, col3, col4 = st.columns([3, 1, 3, 2])
                with col1: g_a = st.number_input(f"{j['time_a']}", min_value=0, value=int(p_salvo["gols_time_a"]), disabled=bloqueado, key=f"inp_a_{j['id']}")
                with col2: st.markdown("<p style='text-align:center;font-size:24px;margin-top:20px;'>X</p>", unsafe_allow_html=True)
                with col3: g_b = st.number_input(f"{j['time_b']}", min_value=0, value=int(p_salvo["gols_time_b"]), disabled=bloqueado, key=f"inp_b_{j['id']}")
                with col4:
                    if j["gols_real_a"] is not None: st.metric("Resultado Real", f"{j['gols_real_a']} x {j['gols_real_b']}")
                    elif bloqueado: st.info("🔒 Bloqueado")
                    else:
                        if st.button("Salvar", key=f"save_{j['id']}"):
                            headers_auth = {**HEADERS, "Authorization": f"Bearer {st.session_state.token}", "Prefer": "resolution=merge-duplicates"}
                            payload = {"id_usuario": st.session_state.user_id, "id_jogo": j["id"], "gols_time_a": g_a, "gols_time_b": g_b}
                            requisicao_supabase("POST", "rest/v1/palpites", json_data=payload, custom_headers=headers_auth)
                            st.toast("Palpite salvo!")
                st.markdown("---")

    # --- ABA 2: COMPETIÇÃO ---
    with abas_gui[1]:
        st.header("🏆 Palpites de Longo Prazo")
        competicao_bloqueada = agora > datetime(2026, 6, 11, 16, 0)

        p_comp = buscar_dados(f"palpites_competicao?id_usuario=eq.{st.session_state.user_id}")
        p_c_atual = p_comp[0] if p_comp else {"campeon": "", "vice": "", "artilheiro": "", "melhor_jogador": ""}

        if lista_times:
            idx_camp = lista_times.index(p_c_atual["campeon"]) if p_c_atual["campeon"] in lista_times else 0
            idx_vice = lista_times.index(p_c_atual["vice"]) if p_c_atual["vice"] in lista_times else 0
            c_camp = st.selectbox("Quem será o Campeão? (50 pts)", options=lista_times, index=idx_camp, disabled=competicao_bloqueada)
            c_vice = st.selectbox("Quem será o Vice-Campeão? (25 pts)", options=lista_times, index=idx_vice, disabled=competicao_bloqueada)
        else:
            c_camp = st.text_input("Quem será o Campeão? (50 pts)", value=p_c_atual["campeon"], disabled=competicao_bloqueada)
            c_vice = st.text_input("Quem será o Vice-Campeão? (25 pts)", value=p_c_atual["vice"], disabled=competicao_bloqueada)

        c_art = st.text_input("Quem será o Artilheiro? (25 pts)", value=p_c_atual["artilheiro"], disabled=competicao_bloqueada)
        c_melhor = st.text_input("Quem será o Melhor Jogador? (25 pts)", value=p_c_atual["melhor_jogador"], disabled=competicao_bloqueada)

        if not competicao_bloqueada:
            if st.button("Gravar Palpites Longo Prazo"):
                h_auth = {**HEADERS, "Authorization": f"Bearer {st.session_state.token}", "Prefer": "resolution=merge-duplicates"}
                payload = {"id_usuario": st.session_state.user_id, "campeon": c_camp, "vice": c_vice, "artilheiro": c_art, "melhor_jogador": c_melhor, "nome_participante": st.session_state.nome_usuario}
                requisicao_supabase("POST", "rest/v1/palpites_competicao", json_data=payload, custom_headers=h_auth)
                st.success("Palpites salvos!")

    # --- ABA 3: RANKING ---
    with abas_gui[2]:
        st.header("📊 Classificação")
        todos_palpites = buscar_dados("palpites")
        todos_palpites_comp = buscar_dados("palpites_competicao")
        res_comp = buscar_dados("resultados_competicao")
        r_c = res_comp[0] if res_comp else {}

        mapa_nomes = {p["id_usuario"]: p.get("nome_participante", "Sem nome") for p in todos_palpites_comp if p.get("nome_participante")}

        pontos_usuarios = {}
        for p in todos_palpites:
            uid = p["id_usuario"]
            jogo = next((j for j in jogos_banco if j["id"] == p["id_jogo"]), None)
            if jogo and jogo["gols_real_a"] is not None:
                pts = calcular_pontos(p["gols_time_a"], p["gols_time_b"], jogo["gols_real_a"], jogo["gols_real_b"])
                pontos_usuarios[uid] = pontos_usuarios.get(uid, 0) + pts

        ranking_ordenado = sorted(pontos_usuarios.items(), key=lambda item: item[1], reverse=True)
        for posicao, (u_id, total_pts) in enumerate(ranking_ordenado, start=1):
            st.subheader(f"🥇 {posicao}º Lugar: {mapa_nomes.get(u_id, u_id[:6])} — {total_pts} Pontos")

    # --- ABA 4: ESPIAR ---
    with abas_gui[3]:
        st.header("👀 Espiar Palpites")
        lista_opcoes_jogos = [f"{j['id']} | {j['time_a']} x {j['time_b']}" for j in jogos_banco]
        if lista_opcoes_jogos:
            escolha_jogo = st.selectbox("Selecione a partida:", lista_opcoes_jogos)
            id_j_sel = int(escolha_jogo.split(" | ")[0])
            j_sel = next(j for j in jogos_banco if j["id"] == id_j_sel)
            data_j_sel = datetime.fromisoformat(j_sel["data_hora"].replace("Z", "").split("+")[0])
            
            if agora > (data_j_sel - timedelta(minutes=30)):
                palpites_desse_jogo = buscar_dados(f"palpites?id_jogo=eq.{id_j_sel}")
                todos_comp = buscar_dados("palpites_competicao")
                mapa_audit = {p["id_usuario"]: p.get("nome_participante", "Sem Nome") for p in todos_comp}
                for plp in palpites_desse_jogo:
                    st.text(f"👤 {mapa_audit.get(plp['id_usuario'], 'Anónimo')} -> {j_sel['time_a']} {plp['gols_time_a']} x {plp['gols_time_b']} {j_sel['time_b']}")
            else:
                st.error("🔒 Palpites ocultos até 30 minutos antes do jogo!")

    # --- ABA 5: ADMIN ---
    if is_admin:
        with abas_gui[4]:
            st.header("⚙️ Painel do Admin")
            sub1, sub2 = st.tabs(["👥 Contas Criadas", "➕ Inserir/Resultados"])
            
            with sub1:
                st.subheader("Participantes Ativos e Pendências")
                todos_palpites_banco = buscar_dados("palpites")
                todos_usuarios_comp = buscar_dados("palpites_competicao")
                total_jogos = len(jogos_banco)
                
                for usr in todos_usuarios_comp:
                    nome_p = usr.get("nome_participante", "Nome não definido")
                    uid_p = usr["id_usuario"]
                    palpites_feitos = len([p for p in todos_palpites_banco if p["id_usuario"] == uid_p])
                    faltam = max(0, total_jogos - palpites_feitos)
                    
                    st.markdown(f"👤 **{nome_p}** | Feitos: {palpites_feitos} | **Faltam: {faltam}**")

            with sub2:
                with st.form("novojogodefin"):
                    fase = st.selectbox("Fase", ["Fase de Grupos", "Dezesseis-avos de Final", "Oitavas de Final", "Quartas de Final", "Semifinal", "Grande Final"])
                    ta = st.text_input("Time A")
                    tb = st.text_input("Time B")
                    dt = st.text_input("Data (AAAA-MM-DD HH:MM:SS)", value="2026-06-12 15:00:00")
                    if st.form_submit_button("Salvar Jogo"):
                        requisicao_supabase("POST", "rest/v1/jogos", json_data={"time_a": ta, "time_b": tb, "data_hora": f"{dt}+00", "fase": fase})
                        st.success("Jogo Inserido!")
                        st.rerun()
