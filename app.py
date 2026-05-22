import streamlit as st
import requests
from datetime import datetime, timedelta
import streamlit.components.v1 as components

# --- CONFIGURAÇÕES DO SUPABASE ---
SUPABASE_URL = "https://hxkeahtcsmmehucmndhk.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh4a2VhaHRjc21tZWh1Y21uZGhrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk0NTA5ODgsImV4cCI6MjA5NTAyNjk4OH0.62RDcA4bWJA-0Ie3DWFnaFC4lWvoOTDgCWagmOJ2X34"

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

def buscar_dados(tabela, custom_headers=None):
    headers = custom_headers if custom_headers else HEADERS
    res = requisicao_supabase("GET", f"rest/v1/{tabela}?select=*", custom_headers=headers)
    return res.json() if res and res.status_code == 200 else []

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
                
                # CORREÇÃO CRÍTICA: Autentica a chamada de busca do perfil usando o token recém-criado
                h_auth_login = {**HEADERS, "Authorization": f"Bearer {token}"}
                perfil = buscar_dados(f"perfis?id_usuario=eq.{uid}", custom_headers=h_auth_login)
                
                if perfil and isinstance(perfil, list) and len(perfil) > 0:
                    nome_salvo = perfil[0].get("nome_participante", "")
                    if nome_salvo and nome_salvo.strip() != "":
                        st.session_state.nome_usuario = nome_salvo
                st.rerun()
            else: 
                st.error("Acesso negado. Verifique as suas credenciais.")
    with aba_c:
        nu = st.text_input("Novo E-mail")
        ns = st.text_input("Nova Senha (mín. 6 dígitos)", type="password")
        if st.button("Registrar"):
            if cadastrar_usuario(nu, ns): 
                st.success("Conta criada com sucesso! Mude para a aba 'Entrar' para acessar.")
            else: 
                st.error("Erro ao registrar. O usuário pode já existir ou a senha é curta.")

# --- SISTEMA LOGADO ---
else:
    # Solicita o nome se a coluna estiver em branco no perfil público ou na sessão
    if not st.session_state.nome_usuario:
        st.title("👋 Bem-vindo ao Super Bolão!")
        st.subheader("Para continuar, defina o nome que aparecerá no Ranking Geral da empresa:")
        nome_digitado = st.text_input("Seu Nome e Sobrenome:")
        
        if st.button("Salvar Perfil e Entrar"):
            if len(nome_digitado.strip()) < 3:
                st.error("Por favor, digite um nome válido com no mínimo 3 letras.")
            else:
                nome_limpo = nome_digitado.strip()
                h_auth = {**HEADERS, "Authorization": f"Bearer {st.session_state.token}"}
                
                # Atualiza o perfil na tabela com o cabeçalho autenticado
                requisicao_supabase("PATCH", f"rest/v1/perfis?id_usuario=eq.{st.session_state.user_id}", json_data={"nome_participante": nome_limpo}, custom_headers=h_auth)
                
                st.session_state.nome_usuario = nome_limpo
                st.success("Nome salvo com sucesso!")
                st.rerun()
        st.stop()

    is_admin = st.session_state.email == EMAIL_ADMIN
    agora = datetime.utcnow()
    jogos_banco = buscar_dados("jogos")
    
    # --- CRONÔMETRO SUPERIOR ---
    proximas_travas = []
    for j in jogos_banco:
        if not j.get("data_hora"): continue
        try:
            d_limpa = j["data_hora"].replace("Z", "").split("+")[0].split(".")[0]
            d_trava = datetime.fromisoformat(d_limpa) - timedelta(minutes=30)
            if d_trava > agora: proximas_travas.append(d_trava)
        except: pass
            
    if proximas_travas:
        iso_alvo = min(proximas_travas).strftime("%Y-%m-%dT%H:%M:%SZ")
        js_relogio = f"""
        <div style="background-color: #1E293B; border-radius: 10px; padding: 12px; text-align: center; font-family: sans-serif; color: #F8FAFC; border: 1px solid #334155;">
            <span style="font-size: 14px; text-transform: uppercase; letter-spacing: 1px; color: #94A3B8; font-weight: bold;">⏱️ Tempo restante para o fechamento dos próximos palpites:</span>
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
                    document.getElementById("countdown").innerHTML = "PALPITES DA RODADA ENCERRADOS!";
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
        st.markdown("<div style='background-color:#1E293B; padding:15px; text-align:center; border-radius:10px; color:#EF4444; font-weight:bold;'>🔒 Inscrições de palpites encerradas!</div>", unsafe_allow_html=True)

    abas = ["Jogos e Palpites", "Palpites da Competição", "Ranking Geral", "Ver Palpites Alheios"]
    if is_admin: abas.append("⚙️ Painel do Admin")
    abas_gui = st.tabs(abas)

    # --- ABA 1: JOGOS E PALPITES ---
    with abas_gui[0]:
        st.header("🎯 Palpites dos Jogos")
        palpites = buscar_dados(f"palpites?id_usuario=eq.{st.session_state.user_id}")
        palpites_dict = {p["id_jogo"]: p for p in palpites}

        jogos_validos = []
        for x in jogos_banco:
            try:
                d_l = x["data_hora"].replace("Z", "").split("+")[0].split(".")[0]
                jogos_validos.append((datetime.fromisoformat(d_l), x))
            except: pass

        for data_j, j in sorted(jogos_validos, key=lambda val: val[0]):
            data_trava_jogo = data_j - timedelta(minutes=30)
            bloqueado = agora > data_trava_jogo
            p_salvo = palpites_dict.get(j["id"], {"gols_time_a": 0, "gols_time_b": 0})
            
            txt_tempo = "🔒 Inscrições Encerradas" if bloqueado else "⏳ Palpites Abertos"
            cor_tempo = "#64748B" if bloqueado else "#10B981"

            with st.container():
                col_info1, col_info2 = st.columns([2, 1])
                with col_info1: st.markdown(f"**Fase:** {j['fase']} | 📅 {data_j.strftime('%d/%m/%Y às %H:%M')}")
                with col_info2: st.markdown(f"<p style='text-align:right; font-weight:bold; color:{cor_tempo}; margin:0;'>{txt_tempo}</p>", unsafe_allow_html=True)
                
                col1, col2, col3, col4 = st.columns([3, 1, 3, 2])
                with col1: g_a = st.number_input(f"{j['time_a']}", min_value=0, value=int(p_salvo["gols_time_a"]), disabled=bloqueado, key=f"inp_a_{j['id']}")
                with col2: st.markdown("<p style='text-align:center;font-size:24px;margin-top:20px;'>X</p>", unsafe_allow_html=True)
                with col3: g_b = st.number_input(f"{j['time_b']}", min_value=0, value=int(p_salvo["gols_time_b"]), disabled=bloqueado, key=f"inp_b_{j['id']}")
                with col4:
                    if j.get("gols_real_a") is not None:
                        st.metric("Resultado Real", f"{j['gols_real_a']} x {j['gols_real_b']}")
                    elif bloqueado: st.info("🔒 Bloqueado")
                    else:
                        if st.button("Salvar", key=f"save_{j['id']}"):
                            h_auth = {**HEADERS, "Authorization": f"Bearer {st.session_state.token}", "Prefer": "resolution=merge-duplicates"}
                            requisicao_supabase("POST", "rest/v1/palpites", json_data={"id_usuario": st.session_state.user_id, "id_jogo": j["id"], "gols_time_a": g_a, "gols_time_b": g_b}, custom_headers=h_auth)
                            st.toast("Palpite computado!")
                st.markdown("---")

    # --- ABA 2: PALPITES DA COMPETIÇÃO ---
    with abas_gui[1]:
        st.header("🏆 Palpites de Longo Prazo")
        primeiro_jogo_copa = datetime(2026, 6, 11, 16, 0) 
        competicao_bloqueada = agora > primeiro_jogo_copa

        p_comp = buscar_dados(f"palpites_competicao?id_usuario=eq.{st.session_state.user_id}")
        p_c_atual = p_comp[0] if p_comp else {"campeon": "", "vice": "", "artilheiro": "", "melhor_jogador": ""}

        paises_set = {jg["time_a"] for jg in jogos_banco if jg.get("time_a")}.union({jg["time_b"] for jg in jogos_banco if jg.get("time_b")})
        lista_paises = sorted(list(paises_set))

        if lista_paises:
            idx_camp = lista_paises.index(p_c_atual["campeon"]) if p_c_atual["campeon"] in lista_paises else 0
            idx_vice = lista_paises.index(p_c_atual["vice"]) if p_c_atual["vice"] in lista_paises else 0
            c_camp = st.selectbox("Quem será o Campeão? (50 pts)", options=lista_paises, index=idx_camp, disabled=competicao_bloqueada)
            c_vice = st.selectbox("Quem será o Vice-Campeão? (25 pts)", options=lista_paises, index=idx_vice, disabled=competicao_bloqueada)
        else:
            c_camp = st.text_input("Quem será o Campeão? (50 pts)", value=p_c_atual["campeon"], disabled=competicao_bloqueada)
            c_vice = st.text_input("Quem será o Vice-Campeão? (25 pts)", value=p_c_atual["vice"], disabled=competicao_bloqueada)

        c_art = st.text_input("Quem será o Artilheiro? (25 pts)", value=p_c_atual["artilheiro"], disabled=competicao_bloqueada)
        c_melhor = st.text_input("Quem será o Melhor Jogador? (25 pts)", value=p_c_atual["melhor_jogador"], disabled=competicao_bloqueada)

        if not competicao_bloqueada:
            if st.button("Gravar Palpites Especiais"):
                h_auth = {**HEADERS, "Authorization": f"Bearer {st.session_state.token}", "Prefer": "resolution=merge-duplicates"}
                requisicao_supabase("POST", "rest/v1/palpites_competicao", json_data={"id_usuario": st.session_state.user_id, "campeon": c_camp, "vice": c_vice, "artilheiro": c_art, "melhor_jogador": c_melhor, "nome_participante": st.session_state.nome_usuario}, custom_headers=h_auth)
                st.success("Palpites salvos!")
        else: st.warning("🔒 Torneio iniciado. Palpites trancados.")

    # --- ABA 3: RANKING ---
    with abas_gui[2]:
        st.header("📊 Classificação da Empresa")
        todos_palpites = buscar_dados("palpites")
        todos_perfis = buscar_dados("perfis")
        res_comp = buscar_dados("resultados_competicao")
        r_c = res_comp[0] if res_comp else {}
        todos_palpites_comp = buscar_dados("palpites_competicao")

        mapa_nomes = {p["id_usuario"]: p.get("nome_participante", "Anônimo") for p in todos_perfis if p.get("nome_participante")}

        pontos_usuarios = {}
        for p in todos_palpites:
            uid = p["id_usuario"]
            jogo = next((j for j in jogos_banco if j["id"] == p["id_jogo"]), None)
            if jogo and jogo.get("gols_real_a") is not None:
                pontos_usuarios[uid] = pontos_usuarios.get(uid, 0) + calcular_pontos(p["gols_time_a"], p["gols_time_b"], jogo["gols_real_a"], jogo["gols_real_b"])

        for pc in todos_palpites_comp:
            uid = pc["id_usuario"]
            if r_c.get("campeon") and pc["campeon"] == r_c["campeon"]: pontos_usuarios[uid] = pontos_usuarios.get(uid, 0) + 50
            if r_c.get("vice") and pc["vice"] == r_c["vice"]: pontos_usuarios[uid] = pontos_usuarios.get(uid, 0) + 25
            if r_c.get("artilheiro") and pc["artilheiro"] == r_c["artilheiro"]: pontos_usuarios[uid] = pontos_usuarios.get(uid, 0) + 25
            if r_c.get("melhor_jogador") and pc["melhor_jogador"] == r_c["melhor_jogador"]: pontos_usuarios[uid] = pontos_usuarios.get(uid, 0) + 25

        ranking_ordenado = sorted(pontos_usuarios.items(), key=lambda item: item[1], reverse=True)
        if ranking_ordenado:
            for pos, (u_id, total_pts) in enumerate(ranking_ordenado, start=1):
                st.subheader(f"🥇 {pos}º Lugar: {mapa_nomes.get(u_id, f'Usuário {u_id[:5]}')} — {total_pts} Pontos")
        else: st.info("Nenhum ponto computado até o momento.")

    # --- ABA 4: VER PALPITES ALHEIOS ---
    with abas_gui[3]:
        st.header("👀 Espiar Palpites Concluídos")
        lista_opcoes_jogos = [f"{j['id']} | {j['time_a']} x {j['time_b']}" for j in jogos_banco]
        if lista_opcoes_jogos:
            escolha_jogo = st.selectbox("Selecione a partida para auditar:", lista_opcoes_jogos)
            if escolha_jogo:
                id_j_sel = int(escolha_jogo.split(" | ")[0])
                j_sel = next(j for j in jogos_banco if j["id"] == id_j_sel)
                try:
                    data_j_sel = datetime.fromisoformat(j_sel["data_hora"].replace("Z", "").split("+")[0].split(".")[0])
                    if agora > (data_j_sel - timedelta(minutes=30)):
                        palpites_desse_jogo = buscar_dados(f"palpites?id_jogo=eq.{id_j_sel}")
                        todos_perfis_audit = buscar_dados("perfis")
                        mapa_audit = {p["id_usuario"]: p.get("nome_participante", "Anônimo") for p in todos_perfis_audit}
                        for plp in palpites_desse_jogo:
                            st.text(f"👤 {mapa_audit.get(plp['id_usuario'], 'Anônimo')} chutou: {j_sel['time_a']} {plp['gols_time_a']} x {plp['gols_time_b']} {j_sel['time_b']}")
                    else: st.error("🔒 Segredo! Liberado apenas 30 minutos antes do jogo.")
                except: st.error("Erro ao processar data.")

    # --- ABA 5: PAINEL DO ADMINISTRADOR ---
    if is_admin:
        with abas_gui[4]:
            st.header("⚙️ Controle Geral do Administrador")
            sub_admin_1, sub_admin_2 = st.tabs(["👥 Usuários Cadastrados", "⚽ Cadastrar Jogos & Placar"])
            
            with sub_admin_1:
                st.subheader("Gerenciamento de Usuários Ativos (Mapeados via SQL)")
                todos_palpites_banco = buscar_dados("palpites")
                todos_perfis_banco = buscar_dados("perfis")
                total_jogos = len(jogos_banco)
                
                st.metric("Total de Jogos Cadastrados", total_jogos)
                
                usuarios_validos = [u for u in todos_perfis_banco if u.get("nome_participante") and len(str(u["nome_participante"]).strip()) > 0]
                
                if not usuarios_validos:
                    st.info("Nenhum usuário ativo salvou o nome de perfil no sistema até agora.")
                else:
                    for usr in usuarios_validos:
                        nome_p = usr["nome_participante"]
                        uid_p = usr["id_usuario"]
                        email_p = usr["email"]
                        
                        palpites_feitos = len([p for p in todos_palpites_banco if p["id_usuario"] == uid_p])
                        faltam = max(0, total_jogos - palpites_feitos)
                        cor_borda = "#10B981" if faltam == 0 else "#EF4444"
                        
                        st.markdown(f"""
                        <div style="padding:12px; background-color:#1E293B; border-radius:6px; margin-bottom:10px; border-left: 6px solid {cor_borda};">
                            <span style="font-size:16px; font-weight:bold; color:#F8FAFC;">👤 {nome_p} ({email_p})</span> <br>
                            📊 Progresso: Palpites Feitos: <strong>{palpites_feitos} / {total_jogos}</strong> | 🚨 Restantes: <strong style='color:{cor_borda}'>{faltam}</strong>
                        </div>
                        """, unsafe_allow_html=True)
            
            with sub_admin_2:
                st.subheader("1. Inserir Confronto")
                with st.form("novos_confrontos"):
                    fase_sel = st.selectbox("Fase", ["Fase de Grupos", "Oitavas de Final", "Quartas de Final", "Semifinal", "Grande Final"])
                    t_a, t_b = st.text_input("Seleção A"), st.text_input("Seleção B")
                    d_h = st.text_input("Data/Hora (AAAA-MM-DD HH:MM:SS)", value="2026-06-11 16:00:00")
                    if st.form_submit_button("Lançar Novo Jogo"):
                        res_add = requisicao_supabase("POST", "rest/v1/jogos", json_data={"time_a": t_a, "time_b": t_b, "data_hora": f"{d_h}+00", "fase": fase_sel})
                        if res_add and res_add.status_code in [200, 201]: st.rerun()
