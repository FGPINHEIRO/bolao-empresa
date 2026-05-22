import streamlit as st
import requests
from datetime import datetime, timedelta
import streamlit.components.v1 as components
import time
import json

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

def cadastrar_usuario(email, password, nome_completo):
    payload = {
        "email": email,
        "password": password,
        "options": {
            "data": {
                "full_name": nome_completo.strip()
            }
        }
    }
    res = requisicao_supabase("POST", "auth/v1/signup", json_data=payload)
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

# --- COMPONENTE DE PERSISTÊNCIA (LOCALSTORAGE) ---
# Esse código injeta um JS invisível para salvar e ler a sessão direto no navegador do usuário
def gerenciar_persistenca_sessao():
    js_script = """
    <script>
        const enviarParaStreamlit = (dados) => {
            window.parent.postMessage({type: 'streamlit:setComponentValue', value: dados}, '*');
        };
        
        window.addEventListener('message', (e) => {
            if (e.data.type === 'gravar_sessao') {
                localStorage.setItem('bolao_session', JSON.stringify(e.data.payload));
            } else if (e.data.type === 'limpar_sessao') {
                localStorage.removeItem('bolao_session');
            }
        });

        // Tenta recuperar a sessão ao carregar a página
        setTimeout(() => {
            const sessaoSalva = localStorage.getItem('bolao_session');
            if (sessaoSalva) {
                enviarParaStreamlit(JSON.parse(sessaoSalva));
            } else {
                enviarParaStreamlit({vazio: true});
            }
        }, 300);
    </script>
    """
    dados_navegador = components.html(js_script, height=0, width=0)
    return dados_navegador

# Inicialização padrão da sessão interna do Streamlit
if "logado" not in st.session_state:
    st.session_state.update({"logado": False, "token": None, "user_id": None, "email": "", "nome_usuario": ""})

# Executa o componente invisível na abertura/refresh da página
dados_recuperados = gerenciar_persistenca_sessao()

# Se o Streamlit detectou que existiam dados salvos no navegador e a sessão do state atual está deslogada, restaura!
if not st.session_state.logado and dados_recuperados and not getattr(dados_recuperados, 'vazio', False):
    try:
        # Dependendo da versão do Streamlit, tratamos o retorno do componente de forma segura
        if isinstance(dados_recuperados, dict) and "token" in dados_recuperados:
            st.session_state.update({
                "logado": True,
                "token": dados_recuperados["token"],
                "user_id": dados_recuperados["user_id"],
                "email": dados_recuperados["email"],
                "nome_usuario": dados_recuperados["nome_usuario"]
            })
            st.rerun()
    except:
        pass

# --- INTERFACE DE LOGIN / CADASTRO ---
if not st.session_state.logado:
    st.title("⚽ Launchpad - Bolão da Empresa")
    aba_l, aba_c = st.tabs(["Entrar", "Criar Conta"])
    with aba_l:
        u = st.text_input("E-mail corporativo")
        s = st.text_input("Senha", type="password")
        if st.button("Acessar Painel"):
            token, uid = fazer_login(u, s)
            if token:
                h_auth_login = {**HEADERS, "Authorization": f"Bearer {token}"}
                perfil = buscar_dados(f"perfis?id_usuario=eq.{uid}", custom_headers=h_auth_login)
                nome_usr = perfil[0].get("nome_participante", "Usuário") if perfil and isinstance(perfil, list) and len(perfil) > 0 else "Usuário"
                
                # Guarda no State do Streamlit
                st.session_state.update({"logado": True, "token": token, "user_id": uid, "email": u, "nome_usuario": nome_usr})
                
                # MODIFICAÇÃO: Dispara comando para o JavaScript salvar os dados no LocalStorage do Navegador
                payload_local = {"token": token, "user_id": uid, "email": u, "nome_usuario": nome_usr}
                st.components.v1.html(f"<script>window.parent.postMessage({{type: 'gravar_sessao', payload: {json.dumps(payload_local)}}}, '*');</script>", height=0, width=0)
                
                time.sleep(0.2)
                st.rerun()
            else: 
                st.error("Acesso negado. Certifique-se de que o e-mail foi verificado ou se os dados estão corretos.")
    with aba_c:
        nu = st.text_input("Novo E-mail")
        nnome = st.text_input("Nome e Sobrenome Completo")
        ns = st.text_input("Nova Senha (mín. 6 dígitos)", type="password")
        if st.button("Registrar Conta"):
            if not nu or not nnome or not ns:
                st.error("Por favor, preencha todos os campos.")
            elif len(nnome.strip()) < 3:
                st.error("Insira um nome válido com no mínimo 3 caracteres.")
            else:
                if cadastrar_usuario(nu, ns, nnome): 
                    st.success("Conta criada com sucesso! Mude para a aba 'Entrar' para acessar.")
                else: 
                    st.error("Erro ao registrar. O usuário pode já existir ou a senha é muito curta.")

# --- SISTEMA APÓS LOGIN ---
else:
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

    # --- BARRA LATERAL ---
    st.sidebar.markdown(f"**Usuário:** {st.session_state.nome_usuario}")
    
    # MODIFICAÇÃO: O botão de Log Out agora apaga explicitamente a chave do localStorage do navegador
    if st.sidebar.button("Log Out"):
        st.components.v1.html("<script>window.parent.postMessage({type: 'limpar_sessao'}, '*');</script>", height=0, width=0)
        st.session_state.update({"logado": False, "token": None, "user_id": None, "email": "", "nome_usuario": ""})
        time.sleep(0.2)
        st.rerun()

    abas = ["Jogos e Palpites", "Jogos e Resultados", "Palpites da Competição", "Ranking Geral", "Ver Palpites Alheios"]
    if is_admin: abas.append("⚙️ Painel do Admin")
    
    abas_gui = st.tabs(abas)

    # --- ABA 1: JOGOS E PALPITES ---
    with abas_gui[0]:
        st.header("🎯 Palpites dos Jogos")
        palpites = buscar_dados(f"palpites?id_usuario=eq.{st.session_state.user_id}")
        
        palpites_dict = {}
        for p in palpites:
            if "id_jogo" in p and p["id_jogo"] is not None:
                palpites_dict[int(p["id_jogo"])] = p

        jogos_validos = []
        for x in jogos_banco:
            try:
                d_l = x["data_hora"].replace("Z", "").split("+")[0].split(".")[0]
                jogos_validos.append((datetime.fromisoformat(d_l), x))
            except: pass

        for data_j, j in sorted(jogos_validos, key=lambda val: val[0]):
            id_jogo_int = int(j["id"])
            data_trava_jogo = data_j - timedelta(minutes=30)
            bloqueado = agora > data_trava_jogo
            
            p_salvo = palpites_dict.get(id_jogo_int, None)
            gols_a_inicial = int(p_salvo["gols_time_a"]) if p_salvo else 0
            gols_b_inicial = int(p_salvo["gols_time_b"]) if p_salvo else 0
            
            txt_tempo = "🔒 Inscrições Encerradas" if bloqueado else "⏳ Palpites Abertos"
            cor_tempo = "#64748B" if bloqueado else "#10B981"

            with st.container():
                col_info1, col_info2 = st.columns([2, 1])
                with col_info1: st.markdown(f"**Fase:** {j['fase']} | 📅 {data_j.strftime('%d/%m/%Y às %H:%M')}")
                with col_info2: st.markdown(f"<p style='text-align:right; font-weight:bold; color:{cor_tempo}; margin:0;'>{txt_tempo}</p>", unsafe_allow_html=True)
                
                col1, col2, col3, col4 = st.columns([3, 1, 3, 2])
                with col1: g_a = st.number_input(f"{j['time_a']}", min_value=0, value=gols_a_inicial, disabled=bloqueado, key=f"inp_a_{id_jogo_int}")
                with col2: st.markdown("<p style='text-align:center;font-size:24px;margin-top:20px;'>X</p>", unsafe_allow_html=True)
                with col3: g_b = st.number_input(f"{j['time_b']}", min_value=0, value=gols_b_inicial, disabled=bloqueado, key=f"inp_b_{id_jogo_int}")
                with col4:
                    if j.get("gols_real_a") is not None and str(j["gols_real_a"]).strip() != "":
                        st.metric("Resultado Oficial", f"{j['gols_real_a']} x {j['gols_real_b']}")
                    elif bloqueado: st.info("🔒 Bloqueado")
                    else:
                        if st.button("Salvar Palpite", key=f"save_{id_jogo_int}"):
                            h_auth = {**HEADERS, "Authorization": f"Bearer {st.session_state.token}", "Prefer": "resolution=merge-duplicates"}
                            payload_palpite = {"id_usuario": st.session_state.user_id, "id_jogo": id_jogo_int, "gols_time_a": int(g_a), "gols_time_b": int(g_b)}
                            resposta = requisicao_supabase("POST", "rest/v1/palpites", json_data=payload_palpite, custom_headers=h_auth)
                            if resposta and resposta.status_code in [200, 201]:
                                st.toast("⚽ Palpite salvo no sistema!")
                                time.sleep(0.4)
                                st.rerun()
                            else:
                                st.error(f"Erro ao salvar no banco. Código: {resposta.status_code if resposta else 'Sem Conexão'}")
                            
                if p_salvo:
                    st.markdown(f"ℹ️ *Palpite atual válido no sistema:* **{p_salvo['gols_time_a']} x {p_salvo['gols_time_b']}**")
                else:
                    st.markdown("ℹ️ *Você ainda não enviou palpites para este confronto.*")
                st.markdown("---")

    # --- ABA 2: JOGOS E RESULTADOS (TABELA OFICIAL) ---
    with abas_gui[1]:
        st.header("📋 Tabela de Jogos e Placares Oficiais")
        st.write("Abaixo você confere o andamento das partidas e o impacto direto na sua pontuação.")
        
        palpites_usuario_res = buscar_dados(f"palpites?id_usuario=eq.{st.session_state.user_id}")
        palpites_res_dict = {int(p["id_jogo"]): p for p in \
                             palpites_usuario_res if p.get("id_jogo") is not None}
        
        jogos_processados = []
        for x in jogos_banco:
            try:
                d_l = x["data_hora"].replace("Z", "").split("+")[0].split(".")[0]
                jogos_processados.append((datetime.fromisoformat(d_l), x))
            except: pass
            
        for data_j, j in sorted(jogos_processados, key=lambda val: val[0]):
            id_j = int(j["id"])
            tem_placar_oficial = j.get("gols_real_a") is not None and j.get("gols_real_b") is not None and str(j["gols_real_a"]).strip() != "" and str(j["gols_real_b"]).strip() != ""
            palpite_efetuado = palpites_res_dict.get(id_j, None)
            
            with st.container():
                c_fase, c_status = st.columns([3, 1])
                with c_fase: st.markdown(f"**{j['fase']}** — 📅 {data_j.strftime('%d/%m/%Y às %H:%M')}")
                with c_status:
                    if tem_placar_oficial:
                        st.markdown("<p style='color:#38BDF8; font-weight:bold; margin:0; text-align:right;'>✓ Encerrado / Computado</p>", unsafe_allow_html=True)
                    else:
                        st.markdown("<p style='color:#94A3B8; font-style:italic; margin:0; text-align:right;'>Aguardando Placar</p>", unsafe_allow_html=True)
                
                col_timeA, col_placar, col_timeB, col_pontos = st.columns([3, 2, 3, 3])
                
                with col_timeA:
                    st.markdown(f"<h3 style='text-align:right; margin:0;'>{j['time_a']}</h3>", unsafe_allow_html=True)
                
                with col_placar:
                    if tem_placar_oficial:
                        st.markdown(f"<h2 style='text-align:center; margin:0; color:#10B981;'>{j['gols_real_a']} - {j['gols_real_b']}</h2>", unsafe_allow_html=True)
                    else:
                        st.markdown("<h4 style='text-align:center; margin:0; color:#64748B;'>Em breve</h4>", unsafe_allow_html=True)
                        
                with col_timeB:
                    st.markdown(f"<h3 style='text-align:left; margin:0;'>{j['time_b']}</h3>", unsafe_allow_html=True)
                    
                with col_pontos:
                    if palpite_efetuado:
                        txt_seu_chute = f"Seu palpite: **{palpite_efetuado['gols_time_a']} x {palpite_efetuado['gols_time_b']}**"
                        if tem_placar_oficial:
                            pts_ganhos = calcular_pontos(int(palpite_efetuado['gols_time_a']), int(palpite_efetuado['gols_time_b']), int(j['gols_real_a']), int(j['gols_real_b']))
                            if pts_ganhos == 5:
                                st.success(f"{txt_seu_chute} (+5 pts 🔥 Placar Cheio!)")
                            elif pts_ganhos == 3:
                                st.info(f"{txt_seu_chute} (+3 pts 🎯 Acertou Vencedor)")
                            elif pts_ganhos == 1:
                                st.warning(f"{txt_seu_chute} (+1 pt ⚽ Acertou Gols de 1 Time)")
                            else:
                                st.error(f"{txt_seu_chute} (+0 pts ❌ Errou)")
                        else:
                            st.markdown(f"<p style='margin:5px 0 0 0; color:#94A3B8;'>{txt_seu_chute}</p>", unsafe_allow_html=True)
                    else:
                        st.markdown("<p style='margin:5px 0 0 0; color:#EF4444; font-style:italic;'>Você não enviou palpite para este jogo.</p>", unsafe_allow_html=True)
                st.markdown("---")

    # --- ABA 3: PALPITES DA COMPETIÇÃO ---
    with abas_gui[2]:
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

    # --- ABA 4: RANKING GENERATIVO E DINÂMICO ---
    with abas_gui[3]:
        st.header("📊 Classificação da Empresa")
        
        # Função interna para garantir comparação numérica
        def converter_int(valor):
            try: return int(valor)
            except: return -1

        todos_palpites = buscar_dados("palpites")
        todos_perfis = buscar_dados("perfis")
        res_comp = buscar_dados("resultados_competicao")
        r_c = res_comp[0] if res_comp else {}
        todos_palpites_comp = buscar_dados("palpites_competicao")

        mapa_nomes = {p["id_usuario"]: p.get("nome_participante", "Anônimo") for p in todos_perfis if p.get("nome_participante")}
        pontos_usuarios = {p["id_usuario"]: 0 for p in todos_perfis if p.get("id_usuario")}
        
        for p in todos_palpites:
            uid = p["id_usuario"]
            jogo = next((j for j in jogos_banco if j["id"] == p["id_jogo"]), None)
            
            # Verificação estrita de resultado oficial
            if jogo and jogo.get("gols_real_a") is not None and jogo.get("gols_real_b") is not None:
                # Converte tudo para int antes de comparar
                palp_a = converter_int(p["gols_time_a"])
                palp_b = converter_int(p["gols_time_b"])
                real_a = converter_int(jogo["gols_real_a"])
                real_b = converter_int(jogo["gols_real_b"])
                
                # Só calcula se o resultado oficial for válido (>= 0)
                if real_a >= 0 and real_b >= 0:
                    pts = calcular_pontos(palp_a, palp_b, real_a, real_b)
                    pontos_usuarios[uid] = pontos_usuarios.get(uid, 0) + pts

        # Adiciona bônus da competição
        for pc in todos_palpites_comp:
            uid = pc["id_usuario"]
            if uid in pontos_usuarios:
                if r_c.get("campeon") and pc["campeon"] == r_c["campeon"]: pontos_usuarios[uid] += 50
                if r_c.get("vice") and pc["vice"] == r_c["vice"]: pontos_usuarios[uid] += 25
                if r_c.get("artilheiro") and pc["artilheiro"] == r_c["artilheiro"]: pontos_usuarios[uid] += 25
                if r_c.get("melhor_jogador") and pc["melhor_jogador"] == r_c["melhor_jogador"]: pontos_usuarios[uid] += 25

        # Exibição do ranking
        ranking_ordenado = sorted(pontos_usuarios.items(), key=lambda item: item[1], reverse=True)
        if ranking_ordenado:
            for pos, (u_id, total_pts) in enumerate(ranking_ordenado, start=1):
                nome_exibir = mapa_nomes.get(u_id, f"Usuário {u_id[:5]}")
                st.write(f"### 🥇 {pos}º: {nome_exibir} — **{total_pts} pontos**")
        else: 
            st.info("Nenhum ponto computado até o momento.")

    # --- ABA 5: VER PALPITES ALHEIOS ---
    with abas_gui[4]:
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

    # --- ABA 6: PAINEL DO ADMINISTRADOR ---
    if is_admin:
        with abas_gui[5]:
            st.header("⚙️ Controle Geral do Administrador")
            sub_admin_1, sub_admin_2 = st.tabs(["👥 Usuários Cadastrados", "⚽ Cadastrar Jogos & Placar"])
            
            with sub_admin_1:
                st.subheader("Gerenciamento de Pendências da Empresa")
                todos_palpites_banco = buscar_dados("palpites")
                todos_perfis_banco = buscar_dados("perfis")
                total_jogos = len(jogos_banco)
                
                st.metric("Total de Jogos Oficiais Cadastrados", total_jogos)
                usuarios_validos = [u for u in todos_perfis_banco if u.get("nome_participante") and len(str(u["nome_participante"]).strip()) > 0]
                
                if not usuarios_validos:
                    st.info("Nenhum usuário ativo registrou o nome no sistema até agora.")
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
                        if res_add and res_add.status_code in [200, 201]: 
                            st.success("Jogo cadastrado com sucesso!")
                            st.rerun()

                st.subheader("2. Imputar Resultados Reais / Prévias")
                opcoes_admin_jogos = [f"{jg['id']} | {jg['time_a']} x {jg['time_b']}" for jg in jogos_banco]
                if opcoes_admin_jogos:
                    id_j_res = st.selectbox("Escolha o jogo para atualizar o placar definitivo ou simulação:", opcoes_admin_jogos, key="sb_admin_res")
                    if id_j_res:
                        id_real = int(id_j_res.split(" | ")[0])
                        jogo_selecionado = next(jg for jg in jogos_banco if jg["id"] == id_real)
                        g_real_a_inicial = int(jogo_selecionado["gols_real_a"]) if jogo_selecionado.get("gols_real_a") is not None else 0
                        g_real_b_inicial = int(jogo_selecionado["gols_real_b"]) if jogo_selecionado.get("gols_real_b") is not None else 0

                        res_a = st.number_input("Gols do Time A", min_value=0, step=1, value=g_real_a_inicial, key="res_a")
                        res_b = st.number_input("Gols do Time B", min_value=0, step=1, value=g_real_b_inicial, key="res_b")
                        
                        if st.button("Gravar Placar Oficial / Atualizar Ranking"):
                            requisicao_supabase("PATCH", f"rest/v1/jogos?id=eq.{id_real}", json_data={"gols_real_a": int(res_a), "gols_real_b": int(res_b)})
                            st.success("Placar updated! O ranking foi recalculado.")
                            time.sleep(0.4)
                            st.rerun()
