# 🎮 Game Registration

Aplicativo desktop para rastreamento pessoal de jogos, construído com Python e Streamlit.
Desenvolvido por **Antonio Carvalho — ICMC/USP**.

---

## 📸 Screenshots

| Dashboard | Lista de Jogos |
|-----------|---------------|
| ![Dashboard](docs/screenshots/dashboard.png) | ![Lista de Jogos](docs/screenshots/lista_jogos.png) |

| Adicionar Jogo | Estatísticas |
|----------------|-------------|
| ![Adicionar Jogo](docs/screenshots/adicionar_jogo.png) | ![Estatísticas](docs/screenshots/estatisticas.png) |

---

## 📥 Como instalar

### Passo 1 — Baixe o arquivo

Acesse o repositório no GitHub e clique em **Code → Download ZIP**:

```
https://github.com/antoniocaarvalh/game-registration
```

### Passo 2 — Extraia o ZIP

Clique com o botão direito no arquivo baixado e selecione **Extrair tudo**.
Escolha uma pasta de sua preferência (ex: Documentos ou Desktop).

### Passo 3 — Instale o Python (se ainda não tiver)

O app precisa do Python para funcionar. Baixe em:

```
https://www.python.org/downloads
```

> ⚠️ **Importante:** durante a instalação, marque a opção **"Add Python to PATH"** antes de clicar em Install Now.

### Passo 4 — Execute o setup (apenas na primeira vez)

Dentro da pasta extraída, dê duplo clique no arquivo **`setup.bat`**.

Ele instalará automaticamente todas as dependências. Aguarde a mensagem:
```
Instalação concluída com sucesso!
```

### Passo 5 — Abra o app

Dê duplo clique no **`INICIAR.bat`** para abrir o app.

> A partir de agora, use sempre o **`INICIAR.bat`** para abrir o Game Registration.

---

## ✨ Funcionalidades

- **Dashboard** — métricas gerais: total de jogos, horas jogadas, jogos zerados e gênero favorito
- **Adicionar Jogo** — cadastro com nome, plataforma, gênero, status, nota (0–10), review, datas e horas jogadas
- **Busca automática de capas** — integração com Steam, Nintendo, PlayStation e Xbox
- **Lista de Jogos** — filtros por nome, status, plataforma e gênero; edição e exclusão inline
- **Coleções/Pastas** — organize seus jogos em pastas personalizadas com ícone e cor
- **Estatísticas** — gráficos de horas por gênero, jogos por plataforma, ranking de horas, distribuição de notas e mais
- **Modo escuro/claro** — alternável nas configurações

---

## 🛠️ Tecnologias

| Tecnologia | Uso |
|------------|-----|
| Python 3.10+ | Linguagem principal |
| Streamlit | Interface web |
| SQLite | Banco de dados local |
| Pandas | Manipulação de dados |
| Plotly | Gráficos interativos |
| Requests | Integração com APIs (Steam, RAWG) |
| pywebview | Janela desktop nativa |

---

## 💡 Observação

Cada pessoa que instalar o app terá o seu próprio banco de dados local (`gametracker.db`).
Seus jogos ficam salvos apenas no seu computador.
