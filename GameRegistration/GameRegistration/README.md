# 🎮 Game Tracker

Aplicativo web para rastreamento pessoal de jogos, construído com Python, Streamlit e SQLite.

## Funcionalidades

- **Dashboard** — métricas gerais (total de jogos, horas jogadas, jogos zerados, gênero favorito) e gráfico de jogos por status
- **Adicionar Jogo** — cadastro com nome, plataforma, gênero, status, nota (0–10), review, datas de início/término e horas jogadas
- **Lista de Jogos** — busca por nome e filtros por status, plataforma e gênero; edição e exclusão inline
- **Estatísticas** — gráfico de pizza (horas por gênero), barras (jogos por plataforma) e linha (jogos zerados por mês)

## Tecnologias

| Tecnologia | Uso |
|------------|-----|
| Python 3.10+ | Linguagem principal |
| Streamlit | Interface web |
| SQLite / sqlite3 | Banco de dados local |
| Pandas | Manipulação de dados |
| Plotly | Gráficos interativos |

## Como rodar

### 1. Instale as dependências

```bash
pip install streamlit pandas plotly
```

### 2. Execute o aplicativo

```bash
streamlit run app.py
```

O banco de dados `gametracker.db` é criado automaticamente na primeira execução.

### 3. Acesse no navegador

```
http://localhost:8501
```

## Estrutura

```
app/
├── app.py           # Código completo do aplicativo
├── gametracker.db   # Banco de dados SQLite (gerado automaticamente)
└── README.md
```

## Schema do Banco de Dados

```sql
CREATE TABLE games (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    platform    TEXT    NOT NULL,
    genre       TEXT    NOT NULL,
    status      TEXT    NOT NULL,
    rating      REAL,
    review      TEXT,
    start_date  TEXT,
    end_date    TEXT,
    hours       REAL    DEFAULT 0,
    created_at  TEXT    DEFAULT (datetime('now'))
);
```
