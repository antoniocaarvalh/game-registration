import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime
from contextlib import contextmanager

# comecei esse projeto só pra aprender streamlit, aí fui adicionando coisa
# e acabou virando isso aqui kkk

DB_PATH = "gametracker.db"


# contexmanager garante que a conexão fecha mesmo se der erro
# aprendi isso na aula de lab, muito útil pra não deixar conexão aberta à toa
@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT    NOT NULL,
                emoji      TEXT    DEFAULT '📁',
                color      TEXT    DEFAULT '#607D8B',
                created_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT    NOT NULL,
                platform      TEXT    NOT NULL,
                genre         TEXT    NOT NULL,
                status        TEXT    NOT NULL,
                rating        REAL,
                review        TEXT,
                start_date    TEXT,
                end_date      TEXT,
                hours         REAL DEFAULT 0,
                cover_url     TEXT,
                collection_id INTEGER,
                created_at    TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        # colunas que adicionei depois que já tinha dados salvos, não podia recriar o banco
        # o ALTER TABLE ignora se a coluna já existir, então tá safe
        for col, defn in [
            ("cover_url",     "TEXT"),
            ("collection_id", "INTEGER"),
        ]:
            try:
                conn.execute(f"ALTER TABLE games ADD COLUMN {col} {defn}")
            except sqlite3.OperationalError:
                pass


def get_setting(key: str, default: str = "") -> str:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO settings(key,value) VALUES(?,?)"
            " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


def fetch_collections() -> pd.DataFrame:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM collections ORDER BY name").fetchall()
    if not rows:
        return pd.DataFrame(columns=["id", "name", "emoji", "color", "created_at"])
    return pd.DataFrame([dict(r) for r in rows])


def insert_collection(name: str, emoji: str, color: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO collections(name,emoji,color,created_at) VALUES(?,?,?,?)",
            (name, emoji, color, datetime.now().isoformat(timespec="seconds")),
        )


def delete_collection(coll_id: int):
    with get_conn() as conn:
        # desvincula os jogos antes de apagar a pasta
        conn.execute("UPDATE games SET collection_id=NULL WHERE collection_id=?", (coll_id,))
        conn.execute("DELETE FROM collections WHERE id=?", (coll_id,))


def insert_game(data: dict):
    payload = {**data, "created_at": datetime.now().isoformat(timespec="seconds")}
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO games
               (name,platform,genre,status,rating,review,
                start_date,end_date,hours,cover_url,collection_id,created_at)
               VALUES
               (:name,:platform,:genre,:status,:rating,:review,
                :start_date,:end_date,:hours,:cover_url,:collection_id,:created_at)""",
            payload,
        )


def update_game(game_id: int, data: dict):
    with get_conn() as conn:
        conn.execute(
            """UPDATE games SET
               name=:name, platform=:platform, genre=:genre,
               status=:status, rating=:rating, review=:review,
               start_date=:start_date, end_date=:end_date,
               hours=:hours, cover_url=:cover_url, collection_id=:collection_id
               WHERE id=:id""",
            {**data, "id": game_id},
        )


def delete_game(game_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM games WHERE id=?", (game_id,))


def fetch_all(collection_id=None) -> pd.DataFrame:
    with get_conn() as conn:
        if collection_id is None:
            rows = conn.execute("SELECT * FROM games ORDER BY name").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM games WHERE collection_id=? ORDER BY name",
                (collection_id,),
            ).fetchall()
    if not rows:
        return pd.DataFrame(columns=[
            "id","name","platform","genre","status","rating","review",
            "start_date","end_date","hours","cover_url","collection_id","created_at",
        ])
    return pd.DataFrame([dict(r) for r in rows])


def fetch_game(game_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM games WHERE id=?", (game_id,)).fetchone()
    return dict(row) if row else {}


# busca na Steam - coloquei cache de 5min pra não bater na API toda hora
# sem o cache tava travando quando digitava rápido
@st.cache_data(ttl=300)
def search_steam(query: str) -> list:
    try:
        r = requests.get(
            "https://store.steampowered.com/api/storesearch/",
            params={"term": query, "l": "portuguese", "cc": "BR"},
            timeout=7,
        )
        r.raise_for_status()
        return [
            {
                "name":      item["name"],
                "appid":     item["id"],
                "cover_url": f"https://cdn.akamai.steamstatic.com/steam/apps/{item['id']}/header.jpg",
                "thumb_url": item.get("tiny_image", ""),
            }
            for item in r.json().get("items", [])[:8]
        ]
    except Exception:
        return []


# TODO: a RAWG às vezes devolve resultados duplicados — filtrar isso aqui um dia
# já tentei com set() mas perdia a ordem, vou pensar melhor nisso
@st.cache_data(ttl=300)
def search_rawg(query: str, platform_ids: str, api_key: str) -> list:
    if not api_key.strip():
        return []
    try:
        r = requests.get(
            "https://api.rawg.io/api/games",
            params={
                "key":       api_key,
                "search":    query,
                "platforms": platform_ids,
                "page_size": 8,
                "ordering":  "-added",
            },
            timeout=7,
        )
        r.raise_for_status()
        return [
            {
                "name":      item["name"],
                "cover_url": item.get("background_image") or "",
            }
            for item in r.json().get("results", [])[:8]
            if item.get("background_image")
        ]
    except Exception:
        return []


PLATFORMS = ["PC", "PlayStation", "Xbox", "Nintendo", "Mobile"]
GENRES    = ["Ação","Aventura","RPG","FPS","Estratégia","Simulação","Esporte","Luta","Puzzle","Terror","Outro"]
STATUSES  = ["Jogando","Zerado","Abandonado","Lista de Desejos"]

STATUS_COLORS = {
    "Jogando":          "#4CAF50",
    "Zerado":           "#2196F3",
    "Abandonado":       "#F44336",
    "Lista de Desejos": "#FF9800",
}

COLL_EMOJIS = ["📁","⭐","🎯","🏆","🔥","❤️","💎","🎮","🌙","🎲","⚔️","🛡️","🚀","🌟","👑","🎪"]
COLL_COLORS = [
    "#607D8B","#E91E63","#9C27B0","#3F51B5",
    "#2196F3","#009688","#4CAF50","#FF9800",
    "#FF5722","#795548","#F44336","#00BCD4",
]

# placeholder quando o jogo não tem capa cadastrada
NO_COVER = (
    "<div style='background:#1e1e2e;height:150px;border-radius:6px;"
    "display:flex;align-items:center;justify-content:center;"
    "border:1px solid #2a2a2a;margin-bottom:4px'>"
    "<span style='font-size:2.5em'>🎮</span></div>"
)

LIGHT_CSS = """<style>
    [data-testid="stSidebar"] { background: #1a1a2e !important; }
    [data-testid="stSidebar"] * { color: #e0e0e0 !important; }
    div[data-testid="metric-container"] {
        background:#f8f9fb; border:1px solid #e0e0e0;
        border-radius:10px; padding:16px;
    }
</style>"""

DARK_CSS = """<style>
    .stApp, [data-testid="stAppViewContainer"],
    .main .block-container { background-color:#0e1117 !important; }
    [data-testid="stHeader"] {
        background-color:#0e1117 !important;
        border-bottom:1px solid #262730 !important;
    }
    [data-testid="stSidebar"] { background-color:#111827 !important; }
    [data-testid="stSidebar"] * { color:#e0e0e0 !important; }
    .stMarkdown p, .stText, label,
    [data-testid="stMarkdownContainer"] p { color:#e0e0e0 !important; }
    h1,h2,h3,h4,h5,h6 { color:#ffffff !important; }
    .stTextInput input, .stTextArea textarea,
    .stNumberInput input {
        background-color:#262730 !important;
        color:#fafafa !important; border-color:#444 !important;
    }
    [data-baseweb="select"] > div {
        background-color:#262730 !important;
        border-color:#444 !important; color:#fafafa !important;
    }
    [data-baseweb="popover"] * {
        background-color:#1e2128 !important; color:#fafafa !important;
    }
    div[data-testid="metric-container"] {
        background:#1e2128 !important; border:1px solid #333 !important;
        border-radius:10px; padding:16px;
    }
    div[data-testid="metric-container"] * { color:#fafafa !important; }
    [data-testid="stExpander"] {
        border-color:#333 !important; background-color:#1e2128 !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color:#1e2128 !important; border-color:#333 !important;
    }
    hr { border-color:#333 !important; }
    .stCaption, [data-testid="stCaptionContainer"] { color:#888 !important; }
    .stButton button {
        background-color:#262730 !important;
        color:#e0e0e0 !important; border-color:#444 !important;
    }
    .stButton button:hover {
        background-color:#31333f !important; border-color:#666 !important;
    }
    [data-testid="stAlert"] { background-color:#1e2128 !important; }
</style>"""


def _dark() -> bool:
    return get_setting("dark_mode", "0") == "1"


def _rawg_key() -> str:
    # no cloud a chave vem do secrets, localmente vem do banco mesmo
    try:
        chave = st.secrets.get("RAWG_API_KEY", "")
        if chave:
            return chave
    except Exception:
        pass
    return get_setting("rawg_api_key", "")


def _plotly_tmpl() -> str:
    return "plotly_dark" if _dark() else "plotly_white"


def _date_or_none(val):
    if val and str(val).strip():
        try:
            return datetime.strptime(str(val), "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def _badge(status: str) -> str:
    cor = STATUS_COLORS.get(status, "#888")
    return (
        f"<span style='background:{cor};color:white;padding:3px 8px;"
        f"border-radius:12px;font-size:.75em;font-weight:bold'>{status}</span>"
    )


def _cover(url, **kwargs):
    if url and str(url).startswith("http"):
        st.image(url, **kwargs)
    else:
        st.markdown(NO_COVER, unsafe_allow_html=True)


def _coll_options(include_none=True):
    df = fetch_collections()
    labels = [f"{r['emoji']} {r['name']}" for _, r in df.iterrows()]
    ids    = [int(r["id"]) for _, r in df.iterrows()]
    if include_none:
        labels = ["— Nenhuma pasta —"] + labels
        ids    = [None] + ids
    return labels, ids


def _active_coll_label() -> str:
    cid = st.session_state.get("active_collection")
    if cid is None:
        return ""
    df = fetch_collections()
    linha = df[df["id"] == cid]
    if linha.empty:
        return ""
    r = linha.iloc[0]
    return f" · {r['emoji']} {r['name']}"


def game_form(prefill: dict | None = None, key_prefix: str = "f") -> dict | None:
    p = prefill or {}

    cover_url = st.text_input(
        "URL da Capa",
        value=p.get("cover_url") or "",
        key=f"{key_prefix}_cover_url",
        placeholder="Preenchido automaticamente pela busca Steam, ou cole uma URL",
    )
    if cover_url.strip():
        st.image(cover_url.strip(), width=320)

    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Nome do Jogo *", value=p.get("name",""), key=f"{key_prefix}_name")
        platform = st.selectbox(
            "Plataforma *", PLATFORMS,
            index=PLATFORMS.index(p["platform"]) if p.get("platform") in PLATFORMS else 0,
            key=f"{key_prefix}_platform",
        )
        genre = st.selectbox(
            "Gênero *", GENRES,
            index=GENRES.index(p["genre"]) if p.get("genre") in GENRES else 0,
            key=f"{key_prefix}_genre",
        )
        status = st.selectbox(
            "Status *", STATUSES,
            index=STATUSES.index(p["status"]) if p.get("status") in STATUSES else 0,
            key=f"{key_prefix}_status",
        )
        labels, ids = _coll_options(include_none=True)
        curr_cid = p.get("collection_id")
        coll_idx = ids.index(curr_cid) if curr_cid in ids else 0
        coll_sel = st.selectbox("Pasta", labels, index=coll_idx, key=f"{key_prefix}_coll")
        selected_cid = ids[labels.index(coll_sel)]

    with col2:
        rating = st.slider(
            "Nota (0–10)", 0.0, 10.0,
            value=float(p.get("rating") or 0.0),
            step=0.5, key=f"{key_prefix}_rating",
        )
        hours = st.number_input(
            "Horas Jogadas", min_value=0.0,
            value=float(p.get("hours") or 0.0),
            step=0.5, key=f"{key_prefix}_hours",
        )
        start_date = st.date_input(
            "Data de Início", value=_date_or_none(p.get("start_date")),
            key=f"{key_prefix}_start", format="DD/MM/YYYY",
        )
        end_date = st.date_input(
            "Data de Término", value=_date_or_none(p.get("end_date")),
            key=f"{key_prefix}_end", format="DD/MM/YYYY",
        )

    review = st.text_area(
        "Review / Observações", value=p.get("review") or "",
        height=100, key=f"{key_prefix}_review",
    )

    if st.button("💾 Salvar", key=f"{key_prefix}_save", use_container_width=True):
        if not name.strip():
            st.error("O nome do jogo é obrigatório.")
            return None
        return {
            "name":          name.strip(),
            "platform":      platform,
            "genre":         genre,
            "status":        status,
            "rating":        rating,
            "review":        review.strip() or None,
            "start_date":    str(start_date) if start_date else None,
            "end_date":      str(end_date)   if end_date   else None,
            "hours":         hours,
            "cover_url":     cover_url.strip() or None,
            "collection_id": selected_cid,
        }
    return None


def page_dashboard():
    cid = st.session_state.get("active_collection")
    st.title(f"🎮 Dashboard{_active_coll_label()}")
    df = fetch_all(cid)

    if df.empty:
        st.info("Nenhum jogo encontrado. Adicione seu primeiro jogo!")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🎯 Total de Jogos",  len(df))
    c2.metric("⏱️ Horas Jogadas",   f"{df['hours'].sum():.0f}h")
    c3.metric("✅ Jogos Zerados",   len(df[df["status"] == "Zerado"]))
    c4.metric("❤️ Gênero Favorito", df["genre"].value_counts().idxmax() if len(df) else "—")

    st.divider()

    por_status = df["status"].value_counts().reindex(STATUSES, fill_value=0).reset_index()
    por_status.columns = ["Status","Quantidade"]
    fig = px.bar(
        por_status, x="Status", y="Quantidade",
        color="Status", color_discrete_map=STATUS_COLORS,
        title="Jogos por Status", text="Quantidade",
        template=_plotly_tmpl(),
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Adicionados Recentemente")
    recentes = df.sort_values("created_at", ascending=False).head(6)
    cols = st.columns(3)
    for i, (_, row) in enumerate(recentes.iterrows()):
        with cols[i % 3]:
            _cover(row.get("cover_url"), use_container_width=True)
            st.markdown(f"**{row['name']}** {_badge(row['status'])}", unsafe_allow_html=True)
            st.caption(f"{row['platform']} · {row['genre']}")


def _search_panel(pkey: str, placeholder: str, search_fn, no_key_msg: str = ""):
    # essa função tava repetida 4 vezes antes, aí refatorei pra cá
    # muito melhor assim, devia ter feito isso antes
    if no_key_msg:
        st.info(f"{no_key_msg}  →  ⚙️ Configurações → API Keys")
        return

    campo_busca, btn_buscar = st.columns([5, 1])
    query = campo_busca.text_input(
        "", placeholder=placeholder,
        label_visibility="collapsed", key=f"{pkey}_q",
    )
    if btn_buscar.button("Buscar", key=f"{pkey}_btn", use_container_width=True) and query.strip():
        with st.spinner("Buscando…"):
            st.session_state[f"{pkey}_results"] = search_fn(query.strip())

    resultados: list = st.session_state.get(f"{pkey}_results", [])
    if not resultados:
        return

    st.caption(f"{len(resultados)} resultado(s)")
    cols = st.columns(4)
    for i, game in enumerate(resultados):
        with cols[i % 4]:
            if game.get("cover_url"):
                st.image(game["cover_url"], use_container_width=True)
            st.caption(game["name"])
            if st.button("✅ Usar", key=f"use_{pkey}_{i}", use_container_width=True):
                st.session_state["steam_pick"] = game
                st.session_state[f"{pkey}_results"] = []
                st.session_state["add_v"] = st.session_state.get("add_v", 0) + 1
                st.rerun()


def page_add_game():
    st.title("➕ Adicionar Jogo")

    with st.expander("🔍 Buscar em catálogos (opcional)", expanded=True):
        t_steam, t_nin, t_ps, t_xbox = st.tabs(
            ["🖥️ Steam", "🍄 Nintendo", "🎮 PlayStation", "❎ Xbox"]
        )
        rawg_key = _rawg_key()
        rawg_msg = "" if rawg_key else "Configure sua chave RAWG gratuita em rawg.io/apidocs"

        with t_steam:
            _search_panel(
                "steam", "Ex: Elden Ring, Cyberpunk, Hades…",
                search_steam,
            )
        with t_nin:
            _search_panel(
                "nin", "Ex: Zelda, Mario, Metroid, Kirby…",
                lambda q: search_rawg(q, "7,137", rawg_key),
                rawg_msg,
            )
        with t_ps:
            _search_panel(
                "ps", "Ex: God of War, Spider-Man, Horizon…",
                lambda q: search_rawg(q, "18,187", rawg_key),
                rawg_msg,
            )
        with t_xbox:
            _search_panel(
                "xbox", "Ex: Halo, Forza, Sea of Thieves…",
                lambda q: search_rawg(q, "1,186", rawg_key),
                rawg_msg,
            )

    if "steam_pick" in st.session_state:
        pick = st.session_state["steam_pick"]
        col_capa, col_info = st.columns([1, 3])
        with col_capa:
            if pick.get("cover_url"):
                st.image(pick["cover_url"], use_container_width=True)
        with col_info:
            st.success(f"**{pick['name']}** selecionado")
            if st.button("✖ Limpar seleção"):
                st.session_state.pop("steam_pick", None)
                st.session_state["add_v"] = st.session_state.get("add_v", 0) + 1
                st.rerun()

    st.divider()

    prefill = {**st.session_state.get("steam_pick", {})}
    if "collection_id" not in prefill:
        prefill["collection_id"] = st.session_state.get("active_collection")
    versao_form = st.session_state.get("add_v", 0)

    data = game_form(prefill=prefill, key_prefix=f"add{versao_form}")
    if data:
        insert_game(data)
        st.session_state.pop("steam_pick", None)
        st.success(f"✅ **{data['name']}** adicionado!")
        st.rerun()


def page_game_list():
    cid = st.session_state.get("active_collection")
    st.title(f"📋 Lista de Jogos{_active_coll_label()}")

    if cid is not None:
        sem_pasta = fetch_all(collection_id=None)
        sem_pasta = sem_pasta[sem_pasta["collection_id"].isna()]
        if not sem_pasta.empty:
            with st.expander("➕ Adicionar jogo existente a esta pasta", expanded=False):
                opcoes = {f"{row['name']} ({row['platform']})": int(row["id"])
                          for _, row in sem_pasta.iterrows()}
                selecionados = st.multiselect(
                    "Selecione os jogos sem pasta para adicionar aqui:",
                    options=list(opcoes.keys()),
                    key="mover_jogos",
                )
                if st.button("✅ Mover para esta pasta", disabled=not selecionados, use_container_width=True):
                    with get_conn() as conn:
                        for nome in selecionados:
                            conn.execute(
                                "UPDATE games SET collection_id=? WHERE id=?",
                                (cid, opcoes[nome]),
                            )
                    st.success(f"{len(selecionados)} jogo(s) adicionado(s) à pasta!")
                    st.rerun()

    df = fetch_all(cid)
    if df.empty:
        st.info("Nenhum jogo encontrado.")
        return

    with st.expander("🔍 Filtros", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        search   = c1.text_input("Buscar por nome", placeholder="Digite…")
        f_status = c2.selectbox("Status",     ["Todos"] + STATUSES)
        f_plat   = c3.selectbox("Plataforma", ["Todos"] + PLATFORMS)
        f_genre  = c4.selectbox("Gênero",     ["Todos"] + GENRES)

    filtro = pd.Series([True] * len(df))
    if search:
        filtro &= df["name"].str.contains(search, case=False, na=False)
    if f_status != "Todos":
        filtro &= df["status"] == f_status
    if f_plat != "Todos":
        filtro &= df["platform"] == f_plat
    if f_genre != "Todos":
        filtro &= df["genre"] == f_genre

    filtrados = df[filtro].copy()
    st.caption(f"{len(filtrados)} jogo(s)")
    if filtrados.empty:
        st.warning("Nenhum jogo encontrado.")
        return

    colunas_por_linha = 3
    for inicio in range(0, len(filtrados), colunas_por_linha):
        bloco = filtrados.iloc[inicio : inicio + colunas_por_linha]
        cols  = st.columns(colunas_por_linha)
        for col, (_, g) in zip(cols, bloco.iterrows()):
            with col:
                with st.container(border=True):
                    _cover(g.get("cover_url"), use_container_width=True)
                    st.markdown(
                        f"<b>{g['name']}</b><br>{_badge(g['status'])}",
                        unsafe_allow_html=True,
                    )
                    partes = [f"🖥 {g['platform']}", f"🎭 {g['genre']}"]
                    if g.get("rating"):
                        partes.append(f"⭐ {g['rating']:.1f}")
                    if g.get("hours"):
                        partes.append(f"⏱ {g['hours']:.0f}h")
                    st.caption(" · ".join(partes))

                    btn_edit, btn_del = st.columns(2)
                    if btn_edit.button("✏️", key=f"e_{g['id']}", use_container_width=True):
                        st.session_state["editing_id"] = int(g["id"])
                        st.session_state["page"] = "edit"
                        st.rerun()
                    if btn_del.button("🗑️", key=f"d_{g['id']}", use_container_width=True):
                        st.session_state["confirm_delete"] = int(g["id"])

                    if st.session_state.get("confirm_delete") == int(g["id"]):
                        st.warning("Confirmar?")
                        y, n = st.columns(2)
                        if y.button("✅", key=f"y_{g['id']}", use_container_width=True):
                            delete_game(int(g["id"]))
                            st.session_state.pop("confirm_delete", None)
                            st.rerun()
                        if n.button("❌", key=f"n_{g['id']}", use_container_width=True):
                            st.session_state.pop("confirm_delete", None)
                            st.rerun()


def page_edit_game():
    game_id = st.session_state.get("editing_id")
    if not game_id:
        st.warning("Nenhum jogo selecionado.")
        return
    game = fetch_game(game_id)
    if not game:
        st.error("Jogo não encontrado.")
        return

    st.title(f"✏️ Editar: {game['name']}")
    if st.button("← Voltar"):
        st.session_state.pop("editing_id", None)
        st.session_state["page"] = "list"
        st.rerun()

    data = game_form(prefill=game, key_prefix="edit")
    if data:
        update_game(game_id, data)
        st.success(f"✅ **{data['name']}** atualizado!")
        st.session_state.pop("editing_id", None)
        st.session_state["page"] = "list"
        st.rerun()


def page_statistics():
    cid = st.session_state.get("active_collection")
    st.title(f"📊 Estatísticas{_active_coll_label()}")
    df = fetch_all(cid)
    if df.empty:
        st.info("Nenhum dado disponível.")
        return

    tmpl = _plotly_tmpl()
    # plotly não pega o fundo do streamlit automaticamente, demorei pra descobrir isso
    # sem isso os gráficos ficavam com fundo branco no modo escuro, ficava horrível
    fundo_transparente = {"paper_bgcolor": "rgba(0,0,0,0)", "plot_bgcolor": "rgba(0,0,0,0)"}

    horas_por_genero = df.groupby("genre")["hours"].sum().reset_index()
    horas_por_genero = horas_por_genero[horas_por_genero["hours"] > 0]
    if not horas_por_genero.empty:
        fig = px.pie(horas_por_genero, values="hours", names="genre",
                     title="⏱️ Horas por Gênero", hole=0.4, template=tmpl)
        fig.update_traces(textinfo="label+percent")
        fig.update_layout(**fundo_transparente)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Registre horas jogadas para ver este gráfico.")

    st.divider()

    jogos_por_plat = df["platform"].value_counts().reindex(PLATFORMS, fill_value=0).reset_index()
    jogos_por_plat.columns = ["Plataforma", "Quantidade"]
    fig2 = px.bar(jogos_por_plat, x="Plataforma", y="Quantidade",
                  title="🖥️ Jogos por Plataforma",
                  color="Quantidade", color_continuous_scale="Blues",
                  text="Quantidade", template=tmpl)
    fig2.update_traces(textposition="outside")
    fig2.update_layout(coloraxis_showscale=False,
                       paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    zerados = df[(df["status"] == "Zerado") & df["end_date"].notna()].copy()
    zerados = zerados[zerados["end_date"] != ""]
    if not zerados.empty:
        zerados["end_date"] = pd.to_datetime(zerados["end_date"], errors="coerce")
        zerados = zerados.dropna(subset=["end_date"])
        zerados["month"] = zerados["end_date"].dt.to_period("M").astype(str)
        por_mes = zerados.groupby("month").size().reset_index(name="Zerados").sort_values("month")
        fig3 = px.line(por_mes, x="month", y="Zerados",
                       title="✅ Jogos Zerados por Mês", markers=True, template=tmpl)
        fig3.update_layout(xaxis_title="Mês",
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Registre a data de término dos jogos zerados para ver este gráfico.")

    st.divider()

    st.subheader("Resumo por Gênero")
    resumo = (
        df.groupby("genre")
        .agg(Jogos=("id","count"), Horas=("hours","sum"), Nota_Média=("rating","mean"))
        .reset_index().rename(columns={"genre":"Gênero"})
        .sort_values("Jogos", ascending=False)
    )
    resumo["Nota_Média"] = resumo["Nota_Média"].round(1)
    resumo["Horas"]      = resumo["Horas"].round(1)
    st.dataframe(resumo, use_container_width=True, hide_index=True)

    st.divider()

    # adicionei essas métricas depois, achei que ficou bem mais completo
    total = len(df)
    zerados_total = len(df[df["status"] == "Zerado"])
    taxa = (zerados_total / total * 100) if total else 0
    media_nota = df[df["rating"] > 0]["rating"].mean()
    media_horas = df[df["hours"] > 0]["hours"].mean()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🏁 Taxa de Conclusão",  f"{taxa:.0f}%")
    m2.metric("⭐ Nota Média Geral",   f"{media_nota:.1f}" if not pd.isna(media_nota) else "—")
    m3.metric("⏱️ Média de Horas/Jogo", f"{media_horas:.0f}h" if not pd.isna(media_horas) else "—")
    m4.metric("🗂️ Plataformas Usadas", df["platform"].nunique())

    st.divider()

    # top 5 jogos com mais horas
    top_horas = df[df["hours"] > 0].nlargest(5, "hours")[["name", "hours", "platform"]]
    if not top_horas.empty:
        fig4 = px.bar(
            top_horas, x="hours", y="name", orientation="h",
            title="🏆 Top 5 Jogos com Mais Horas",
            color="platform", text="hours", template=tmpl,
            labels={"hours": "Horas", "name": "Jogo", "platform": "Plataforma"},
        )
        fig4.update_traces(texttemplate="%{text:.0f}h", textposition="outside")
        fig4.update_layout(yaxis={"categoryorder": "total ascending"}, **fundo_transparente)
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("Registre horas jogadas para ver o ranking.")

    st.divider()

    # distribuição de notas
    notas = df[df["rating"] > 0]["rating"]
    if not notas.empty:
        fig5 = px.histogram(
            notas, x=notas, nbins=10,
            title="⭐ Distribuição de Notas",
            labels={"x": "Nota", "count": "Qtd. Jogos"},
            template=tmpl, color_discrete_sequence=["#a78bfa"],
        )
        fig5.update_layout(bargap=0.1,
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig5, use_container_width=True)
    else:
        st.info("Avalie seus jogos para ver a distribuição de notas.")

    st.divider()

    # nota média por plataforma
    nota_plat = (
        df[df["rating"] > 0]
        .groupby("platform")["rating"].mean()
        .reset_index()
        .rename(columns={"platform": "Plataforma", "rating": "Nota Média"})
        .sort_values("Nota Média", ascending=False)
    )
    if not nota_plat.empty:
        nota_plat["Nota Média"] = nota_plat["Nota Média"].round(1)
        fig6 = px.bar(
            nota_plat, x="Plataforma", y="Nota Média",
            title="🎯 Nota Média por Plataforma",
            color="Nota Média", color_continuous_scale="Purples",
            text="Nota Média", template=tmpl,
        )
        fig6.update_traces(textposition="outside")
        fig6.update_layout(coloraxis_showscale=False, yaxis_range=[0, 10.5], **fundo_transparente)
        st.plotly_chart(fig6, use_container_width=True)

    st.divider()

    # jogos adicionados por mês
    df_datas = df[df["created_at"].notna()].copy()
    df_datas["created_at"] = pd.to_datetime(df_datas["created_at"], errors="coerce")
    df_datas = df_datas.dropna(subset=["created_at"])
    if not df_datas.empty:
        df_datas["mes"] = df_datas["created_at"].dt.to_period("M").astype(str)
        por_mes_add = df_datas.groupby("mes").size().reset_index(name="Adicionados").sort_values("mes")
        fig7 = px.bar(
            por_mes_add, x="mes", y="Adicionados",
            title="📅 Jogos Adicionados por Mês",
            text="Adicionados", template=tmpl,
            color_discrete_sequence=["#7c3aed"],
        )
        fig7.update_traces(textposition="outside")
        fig7.update_layout(xaxis_title="Mês",
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig7, use_container_width=True)


def page_settings():
    st.title("⚙️ Configurações")

    st.subheader("🔑 API Keys")
    rawg_salva = get_setting("rawg_api_key", "") or _rawg_key()
    nova_rawg = st.text_input(
        "Chave RAWG  (Nintendo / PlayStation / Xbox)",
        value=rawg_salva,
        type="password",
        placeholder="Cole aqui sua chave gratuita",
        help="Obtenha grátis em rawg.io/apidocs — necessária para buscar jogos fora da Steam",
    )
    st.caption(
        "Acesse [rawg.io/apidocs](https://rawg.io/apidocs), clique em **GET API KEY**, "
        "crie uma conta gratuita e copie a chave gerada."
    )
    if st.button("💾 Salvar chave", key="save_rawg"):
        set_setting("rawg_api_key", nova_rawg.strip())
        st.success("Chave salva! Agora você pode buscar jogos de Nintendo, PlayStation e Xbox.")
        st.rerun()

    st.divider()

    st.subheader("🎨 Aparência")
    dark_agora = _dark()
    novo_dark = st.toggle("🌙 Modo Escuro", value=dark_agora, key="toggle_dark")
    if novo_dark != dark_agora:
        set_setting("dark_mode", "1" if novo_dark else "0")
        st.rerun()

    st.divider()

    st.subheader("🗂️ Gerenciar Pastas")
    colls = fetch_collections()

    if colls.empty:
        st.info("Nenhuma pasta criada ainda.")
    else:
        for _, coll in colls.iterrows():
            cid = int(coll["id"])
            qtd_jogos = len(fetch_all(cid))
            c1, c2, c3 = st.columns([1, 6, 1])
            with c1:
                st.markdown(
                    f"<div style='background:{coll['color']};width:36px;height:36px;"
                    f"border-radius:8px;display:flex;align-items:center;"
                    f"justify-content:center;font-size:1.3em'>{coll['emoji']}</div>",
                    unsafe_allow_html=True,
                )
            with c2:
                st.markdown(f"**{coll['name']}**")
                st.caption(f"{qtd_jogos} jogo(s)")
            with c3:
                if st.button("🗑️", key=f"delc_{cid}", help="Excluir pasta"):
                    st.session_state["confirm_del_coll"] = cid

            if st.session_state.get("confirm_del_coll") == cid:
                st.warning(f"Excluir **{coll['name']}**? Os jogos não serão excluídos.")
                y, n = st.columns(2)
                if y.button("✅ Confirmar", key=f"yc_{cid}"):
                    delete_collection(cid)
                    if st.session_state.get("active_collection") == cid:
                        st.session_state["active_collection"] = None
                    st.session_state.pop("confirm_del_coll", None)
                    st.rerun()
                if n.button("❌ Cancelar", key=f"nc_{cid}"):
                    st.session_state.pop("confirm_del_coll", None)
                    st.rerun()

    st.divider()
    st.subheader("➕ Nova Pasta")

    col_nome, col_icone, col_cor = st.columns([3, 2, 2])
    new_name  = col_nome.text_input("Nome", key="new_coll_name")
    new_emoji = col_icone.selectbox("Ícone", COLL_EMOJIS, key="new_coll_emoji")
    new_color = col_cor.selectbox("Cor",   COLL_COLORS,  key="new_coll_color")

    if new_color in COLL_COLORS:
        col_cor.markdown(
            f"<div style='background:{new_color};height:12px;border-radius:4px'></div>",
            unsafe_allow_html=True,
        )

    if st.button("Criar Pasta", use_container_width=True):
        if not new_name.strip():
            st.error("Digite um nome para a pasta.")
        else:
            insert_collection(new_name.strip(), new_emoji, new_color)
            st.success(f"Pasta **{new_name}** criada!")
            st.rerun()


import base64, pathlib  # esqueci de botar lá em cima junto dos outros


def main():
    st.set_page_config(
        page_title="Game Registration",
        page_icon="🎮",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_db()

    dark = _dark()
    st.markdown(DARK_CSS if dark else LIGHT_CSS, unsafe_allow_html=True)

    if "page" not in st.session_state:
        st.session_state["page"] = "dashboard"
    if "active_collection" not in st.session_state:
        st.session_state["active_collection"] = None

    colls = fetch_collections()

    with st.sidebar:
        st.markdown("## 🎮 Game Registration")
        st.divider()

        nav = {
            "dashboard":  "🏠 Dashboard",
            "add":        "➕ Adicionar Jogo",
            "list":       "📋 Lista de Jogos",
            "statistics": "📊 Estatísticas",
            "settings":   "⚙️ Configurações",
        }
        for key, label in nav.items():
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                st.session_state["page"] = key
                st.session_state.pop("editing_id", None)
                st.rerun()

        st.divider()
        st.markdown("**🗂️ Coleções**")

        is_all = st.session_state["active_collection"] is None
        label_todos = "📋 **Todos os Jogos**" if is_all else "📋 Todos os Jogos"
        if st.button(label_todos, key="nav_all_coll", use_container_width=True):
            st.session_state["active_collection"] = None
            st.rerun()

        for _, coll in colls.iterrows():
            cid    = int(coll["id"])
            active = st.session_state["active_collection"] == cid
            lbl    = f"{coll['emoji']} **{coll['name']}**" if active else f"{coll['emoji']} {coll['name']}"
            if st.button(lbl, key=f"coll_{cid}", use_container_width=True):
                st.session_state["active_collection"] = cid
                st.rerun()

        if st.button("➕ Nova Pasta", key="new_coll_btn", use_container_width=True):
            st.session_state["page"] = "settings"
            st.rerun()

        st.divider()
        df_all = fetch_all()
        st.caption(f"Total: **{len(df_all)}** jogos")
        st.caption(f"Horas: **{df_all['hours'].sum():.0f}h**")
        if dark:
            st.caption("🌙 Modo escuro ativo")
        st.divider()
        st.markdown(
            "<div style='text-align:center; color:#a78bfa; font-size:0.85em; font-weight:600; padding:4px 0'>"
            "Desenvolvido por<br><span style='font-size:1.1em'>Antonio Carvalho</span><br>"
            "<span style='letter-spacing:2px; font-size:0.85em'>ICMC/USP</span></div>",
            unsafe_allow_html=True,
        )

    dispatch = {
        "dashboard":  page_dashboard,
        "add":        page_add_game,
        "list":       page_game_list,
        "edit":       page_edit_game,
        "statistics": page_statistics,
        "settings":   page_settings,
    }

    # tenta carregar o logo como svg em base64, se não tiver usa o emoji mesmo
    try:
        svg_path    = pathlib.Path(__file__).parent / "logo.svg"
        logo_base64 = base64.b64encode(svg_path.read_bytes()).decode()
        logo_html   = f'<img src="data:image/svg+xml;base64,{logo_base64}" style="height:80px;filter:drop-shadow(0 0 10px #a78bfa)">'
    except Exception:
        logo_html = '<span style="font-size:3em">🎮</span>'

    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        padding: 20px 32px;
        border-radius: 14px;
        margin-bottom: 28px;
        border: 1px solid rgba(167,139,250,0.25);
        box-shadow: 0 8px 32px rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        gap: 24px;
    ">
        {logo_html}
        <div>
            <div style="
                color: #ffffff;
                font-size: 1.95em;
                font-weight: 800;
                letter-spacing: 3px;
                line-height: 1.1;
                text-transform: uppercase;
                text-shadow: 0 0 20px rgba(167,139,250,0.5);
            ">Game Registration</div>
            <div style="
                color: #a78bfa;
                font-size: 0.76em;
                letter-spacing: 5px;
                margin-top: 5px;
                text-transform: uppercase;
            ">✦ rastreador pessoal de jogos ✦</div>
        </div>
        <div style="margin-left:auto; text-align:center; flex-shrink:0;">
            <div style="
                background: linear-gradient(135deg, #003FA3 0%, #0055CC 45%, #CC0000 100%);
                padding: 9px 16px;
                border-radius: 10px;
                color: white;
                font-weight: 900;
                font-size: 0.82em;
                letter-spacing: 2px;
                text-shadow: 0 1px 4px rgba(0,0,0,0.6);
                border: 1px solid rgba(255,255,255,0.15);
                box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            ">🦁 VAI LEÃO!</div>
            <div style="
                color: rgba(200,210,255,0.55);
                font-size: 0.60em;
                margin-top: 5px;
                letter-spacing: 2.5px;
                text-transform: uppercase;
            ">Clube do Remo</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    dispatch.get(st.session_state["page"], page_dashboard)()
    st.markdown("""
        <style>
        .author-credit {
            position: fixed;
            top: 14px;
            right: 16px;
            z-index: 9999;
            background: rgba(15,12,41,0.88);
            border: 1px solid rgba(167,139,250,0.3);
            border-radius: 20px;
            padding: 5px 13px;
            font-size: 0.70em;
            color: #a78bfa;
            letter-spacing: 0.5px;
            backdrop-filter: blur(6px);
            pointer-events: none;
        }
        </style>
        <div class="author-credit">Desenvolvido por Antonio Carvalho - ICMC/USP</div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
