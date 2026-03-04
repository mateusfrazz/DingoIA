#!/usr/bin/env python3
import subprocess
import sys
import os
import json
import webbrowser

# ─────────────────────────────────────────────────────────
# AUTO-INSTALL DE DEPENDÊNCIAS
# ─────────────────────────────────────────────────────────
def install_deps():
    deps = ["requests", "rich", "google-generativeai"]
    for dep in deps:
        pkg = dep.replace("-", "_").split("[")[0]
        try:
            __import__(pkg)
        except ImportError:
            print(f"[Dingo IA] Instalando {dep}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep, "-q"])
            print(f"[Dingo IA] {dep} instalado!")

install_deps()

# ─────────────────────────────────────────────────────────
# IMPORTS
# ─────────────────────────────────────────────────────────
import asyncio
from time import sleep
import requests
import google.generativeai as genai
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.progress import track
from rich.markup import escape
from rich.table import Table
from rich import print as rprint
from rich.traceback import install
install(show_locals=False)

console = Console()

# ─────────────────────────────────────────────────────────
# CONFIG.JSON
# ─────────────────────────────────────────────────────────
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

DEFAULT_CONFIG = {
    "gemini_api_key": "",
    "model": "gemini-2.0-flash",
    "mcps": {
        "notion": {
            "enabled": False,
            "api_key": "",
            "npx_package": "@notionhq/notion-mcp-server",
            "description": "Criar páginas, tarefas e databases"
        },
        "gmail": {
            "enabled": False,
            "credentials_file": "credentials.json",
            "npx_package": "@gcp-mcp/gmail-mcp-server",
            "description": "Ler, organizar e responder emails"
        },
        "google_calendar": {
            "enabled": False,
            "credentials_file": "credentials.json",
            "npx_package": "@googleapis/calendar-mcp-server",
            "description": "Criar e gerenciar eventos no calendário"
        },
        "filesystem": {
            "enabled": True,
            "allowed_paths": [os.path.expanduser("~")],
            "npx_package": "@modelcontextprotocol/server-filesystem",
            "description": "Organizar pastas e arquivos locais"
        },
        "github": {
            "enabled": False,
            "token": "",
            "npx_package": "@modelcontextprotocol/server-github",
            "description": "Gerenciar repositórios, issues e PRs"
        },
        "spotify": {
            "enabled": False,
            "client_id": "",
            "client_secret": "",
            "npx_package": "@modelcontextprotocol/server-spotify",
            "description": "Controlar música e playlists"
        }
    }
}

def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    # Merge com defaults para novos MCPs adicionados
    for mcp, vals in DEFAULT_CONFIG["mcps"].items():
        if mcp not in cfg["mcps"]:
            cfg["mcps"][mcp] = vals
    return cfg

def save_config(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

config = load_config()

# ─────────────────────────────────────────────────────────
# GEMINI SETUP
# ─────────────────────────────────────────────────────────
def setup_gemini():
    key = config.get("gemini_api_key", "")
    if not key:
        return None
    genai.configure(api_key=key)
    return genai.GenerativeModel(
        model_name=config.get("model", "gemini-2.0-flash"),
        system_instruction=(
            "Você é Dingo IA, um assistente terminal inteligente. "
            "Responda sempre em português, de forma clara, útil e concisa. "
            "Quando usar MCPs, explique os resultados de forma amigável."
        )
    )

gemini_model = setup_gemini()
chat_history = []

# ─────────────────────────────────────────────────────────
# ASCII ART
# ─────────────────────────────────────────────────────────
DINGO_ASCII = """
██████╗ ██╗███╗   ██╗ ██████╗  ██████╗     ██╗ █████╗ 
██╔══██╗██║████╗  ██║██╔════╝ ██╔═══██╗    ██║██╔══██╗
██║  ██║██║██╔██╗ ██║██║  ███╗██║   ██║    ██║███████║
██║  ██║██║██║╚██╗██║██║   ██║██║   ██║    ██║██╔══██║
██████╔╝██║██║ ╚████║╚██████╔╝╚██████╔╝    ██║██║  ██║
╚═════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝    ╚═╝╚═╝  ╚═╝
"""

# ─────────────────────────────────────────────────────────
# SETUP WIZARD
# ─────────────────────────────────────────────────────────
async def setup_wizard(force: bool = False):
    console.clear()
    rprint(Panel(
        "[bold cyan]🐕 Bem-vindo ao Dingo IA![/]\n\n"
        "Vou te guiar para conectar suas contas.\n"
        "[dim]Pressione Enter para pular qualquer etapa.[/]",
        border_style="cyan",
        title="⚙️  Setup"
    ))

    # ── GEMINI ──────────────────────────────────────────────
    console.print("\n[bold yellow]── PASSO 1: Gemini API Key (gratuita) ──[/]")
    console.print("[dim]Necessária para o chat funcionar.[/]")
    abrir = Prompt.ask("Abrir Google AI Studio no browser?", choices=["s", "n"], default="s")
    if abrir == "s":
        webbrowser.open("https://aistudio.google.com/apikey")
        sleep(2)

    key = Prompt.ask(
        "[yellow]Cole sua Gemini API Key[/]",
        default=config.get("gemini_api_key", "")
    )
    if key:
        config["gemini_api_key"] = key
        console.print("[green]✅ Gemini configurado![/]")
    else:
        console.print("[red]⚠️  Sem API Key o chat não funcionará.[/]")

    # ── SELECIONAR MCPs ─────────────────────────────────────
    console.print("\n[bold yellow]── PASSO 2: Conectar Plataformas ──[/]")

    table = Table(border_style="dim", show_header=True)
    table.add_column("Nº", style="bold cyan", width=4)
    table.add_column("Plataforma", width=20)
    table.add_column("O que faz")
    table.add_row("1", "📝 Notion",           "Criar páginas, tarefas, databases")
    table.add_row("2", "📧 Gmail",            "Ler, organizar e responder emails")
    table.add_row("3", "📅 Google Calendar",  "Criar e gerenciar eventos")
    table.add_row("4", "📁 Filesystem",       "Organizar pastas e arquivos locais")
    table.add_row("5", "🐙 GitHub",           "Gerenciar repos, issues e PRs")
    table.add_row("6", "🎵 Spotify",          "Controlar música e playlists")
    table.add_row("7", "✅ Todos",            "Ativar tudo")
    table.add_row("0", "⏭  Pular",           "Configurar depois com /config")
    console.print(table)

    escolha = Prompt.ask(
        "\n[yellow]Quais MCPs ativar?[/] [dim](ex: 1,3,4 ou 7)[/]",
        default="0"
    )

    selecionados = []
    if "7" in escolha:
        selecionados = ["notion", "gmail", "google_calendar", "filesystem", "github", "spotify"]
    else:
        if "1" in escolha: selecionados.append("notion")
        if "2" in escolha: selecionados.append("gmail")
        if "3" in escolha: selecionados.append("google_calendar")
        if "4" in escolha: selecionados.append("filesystem")
        if "5" in escolha: selecionados.append("github")
        if "6" in escolha: selecionados.append("spotify")

    # ── NOTION ──────────────────────────────────────────────
    if "notion" in selecionados:
        console.print("\n[bold cyan]── 📝 Configurando Notion ──[/]")
        console.print("  1. Acesse [link]notion.so/my-integrations[/link]")
        console.print("  2. Clique em [bold]'New Integration'[/]")
        console.print("  3. Dê um nome (ex: Dingo IA) e salve")
        console.print("  4. Copie o [bold]'Internal Integration Secret'[/] (secret_...)\n")
        abrir = Prompt.ask("Abrir Notion Integrations no browser?", choices=["s", "n"], default="s")
        if abrir == "s":
            webbrowser.open("https://www.notion.so/my-integrations")
            sleep(2)
        notion_key = Prompt.ask(
            "[yellow]Cole sua Notion API Key[/] [dim](secret_...)[/]",
            default=config["mcps"]["notion"].get("api_key", ""),
            password=True
        )
        if notion_key:
            config["mcps"]["notion"]["enabled"] = True
            config["mcps"]["notion"]["api_key"] = notion_key
            console.print("[green]✅ Notion configurado![/]")
            console.print("[dim]⚠️  Lembre: abra páginas no Notion > ··· > Connections > Dingo IA[/]")
        else:
            console.print("[yellow]⏭  Notion pulado.[/]")

    # ── GMAIL ───────────────────────────────────────────────
    if "gmail" in selecionados:
        console.print("\n[bold cyan]── 📧 Configurando Gmail ──[/]")
        console.print("  1. Acesse [link]console.cloud.google.com[/link]")
        console.print("  2. Crie um projeto > [bold]Enable Gmail API[/]")
        console.print("  3. Credentials > OAuth 2.0 > [bold]Desktop App[/]")
        console.print(f"  4. Baixe o JSON > renomeie para [bold]credentials.json[/]")
        console.print(f"  5. Mova para: [bold]{os.path.dirname(__file__)}[/]\n")
        abrir = Prompt.ask("Abrir Google Cloud Console no browser?", choices=["s", "n"], default="s")
        if abrir == "s":
            webbrowser.open("https://console.cloud.google.com/apis/library/gmail.googleapis.com")
            sleep(2)
        creds = Prompt.ask(
            "[yellow]Caminho do credentials.json[/]",
            default=os.path.join(os.path.dirname(__file__), "credentials.json")
        )
        if os.path.exists(creds):
            config["mcps"]["gmail"]["enabled"] = True
            config["mcps"]["gmail"]["credentials_file"] = creds
            console.print("[green]✅ Gmail configurado![/]")
        else:
            console.print(f"[red]⚠️  Arquivo não encontrado: {creds}[/]")
            console.print("[dim]Configure depois com /config quando tiver o arquivo.[/]")

    # ── GOOGLE CALENDAR ─────────────────────────────────────
    if "google_calendar" in selecionados:
        console.print("\n[bold cyan]── 📅 Configurando Google Calendar ──[/]")
        console.print("  Usa o mesmo credentials.json do Gmail (Google OAuth).")
        console.print("  1. Acesse [link]console.cloud.google.com[/link]")
        console.print("  2. [bold]Enable Google Calendar API[/] no mesmo projeto")
        console.print("  3. Mesmo credentials.json já serve!\n")
        abrir = Prompt.ask("Abrir Google Calendar API no browser?", choices=["s", "n"], default="s")
        if abrir == "s":
            webbrowser.open("https://console.cloud.google.com/apis/library/calendar-json.googleapis.com")
            sleep(2)
        creds = Prompt.ask(
            "[yellow]Caminho do credentials.json[/]",
            default=config["mcps"]["gmail"].get(
                "credentials_file",
                os.path.join(os.path.dirname(__file__), "credentials.json")
            )
        )
        if os.path.exists(creds):
            config["mcps"]["google_calendar"]["enabled"] = True
            config["mcps"]["google_calendar"]["credentials_file"] = creds
            console.print("[green]✅ Google Calendar configurado![/]")
        else:
            console.print(f"[red]⚠️  Arquivo não encontrado: {creds}[/]")
            console.print("[dim]Configure depois com /config.[/]")

    # ── FILESYSTEM ──────────────────────────────────────────
    if "filesystem" in selecionados:
        console.print("\n[bold cyan]── 📁 Configurando Filesystem ──[/]")
        console.print("  Defina quais pastas o Dingo IA pode acessar e organizar.\n")
        paths_input = Prompt.ask(
            "[yellow]Pastas permitidas[/] [dim](separe por vírgula)[/]",
            default=", ".join(config["mcps"]["filesystem"].get("allowed_paths", [os.path.expanduser("~")]))
        )
        paths = [p.strip() for p in paths_input.split(",") if p.strip()]
        config["mcps"]["filesystem"]["enabled"] = True
        config["mcps"]["filesystem"]["allowed_paths"] = paths
        console.print(f"[green]✅ Filesystem configurado! Pastas: {', '.join(paths)}[/]")

    # ── GITHUB ──────────────────────────────────────────────
    if "github" in selecionados:
        console.print("\n[bold cyan]── 🐙 Configurando GitHub ──[/]")
        console.print("  1. Acesse [link]github.com/settings/tokens[/link]")
        console.print("  2. [bold]Generate new token (classic)[/]")
        console.print("  3. Marque: repo, issues, pull_requests\n")
        abrir = Prompt.ask("Abrir GitHub Tokens no browser?", choices=["s", "n"], default="s")
        if abrir == "s":
            webbrowser.open("https://github.com/settings/tokens/new")
            sleep(2)
        token = Prompt.ask(
            "[yellow]Cole seu GitHub Token[/] [dim](ghp_...)[/]",
            default=config["mcps"]["github"].get("token", ""),
            password=True
        )
        if token:
            config["mcps"]["github"]["enabled"] = True
            config["mcps"]["github"]["token"] = token
            console.print("[green]✅ GitHub configurado![/]")
        else:
            console.print("[yellow]⏭  GitHub pulado.[/]")

    # ── SPOTIFY ─────────────────────────────────────────────
    if "spotify" in selecionados:
        console.print("\n[bold cyan]── 🎵 Configurando Spotify ──[/]")
        console.print("  1. Acesse [link]developer.spotify.com/dashboard[/link]")
        console.print("  2. [bold]Create App[/] > copie Client ID e Client Secret\n")
        abrir = Prompt.ask("Abrir Spotify Developer no browser?", choices=["s", "n"], default="s")
        if abrir == "s":
            webbrowser.open("https://developer.spotify.com/dashboard/create")
            sleep(2)
        client_id = Prompt.ask(
            "[yellow]Cole seu Spotify Client ID[/]",
            default=config["mcps"]["spotify"].get("client_id", "")
        )
        client_secret = Prompt.ask(
            "[yellow]Cole seu Spotify Client Secret[/]",
            default=config["mcps"]["spotify"].get("client_secret", ""),
            password=True
        )
        if client_id and client_secret:
            config["mcps"]["spotify"]["enabled"] = True
            config["mcps"]["spotify"]["client_id"] = client_id
            config["mcps"]["spotify"]["client_secret"] = client_secret
            console.print("[green]✅ Spotify configurado![/]")
        else:
            console.print("[yellow]⏭  Spotify pulado.[/]")

    # ── SALVAR ──────────────────────────────────────────────
    save_config(config)
    ativos = [k for k, v in config["mcps"].items() if v.get("enabled")]
    console.print(f"\n[bold green]✅ Configuração salva em config.json![/]")
    if ativos:
        console.print(f"[green]MCPs ativos: {', '.join(ativos)}[/]")

    global gemini_model
    gemini_model = setup_gemini()
    Prompt.ask("\n[dim]Pressione Enter para iniciar o Dingo IA[/]")

# ─────────────────────────────────────────────────────────
# BOOT ANIMATION
# ─────────────────────────────────────────────────────────
async def boot_animation():
    if os.name == "nt":
        os.system("title Dingo IA - Gemini + MCP Agent")
    console.clear()

    if not config.get("gemini_api_key"):
        await setup_wizard()

    text = Text()
    for char in DINGO_ASCII:
        text.append(char, style="bold cyan")
        with Live(text, refresh_per_second=30, console=console) as live:
            live.update(text)
        await asyncio.sleep(0.01)

    ativos = [k for k, v in config["mcps"].items() if v.get("enabled")]
    subtitle = f"MCPs: {', '.join(ativos)}" if ativos else "Nenhum MCP ativo — use /config"

    rprint(Panel.fit(
        DINGO_ASCII,
        title="[bold green]🐕 Dingo IA Ativado![/]",
        subtitle=f"[dim]{subtitle}[/]",
        border_style="bright_green"
    ))
    console.print("[bold magenta]Digite 'exit' para sair | /tools para comandos | /config para configurar MCPs[/]\n")

# ─────────────────────────────────────────────────────────
# GEMINI CHAT
# ─────────────────────────────────────────────────────────
async def call_gemini(prompt: str) -> str:
    if not gemini_model:
        return "❌ Gemini não configurado. Digite /config."
    try:
        with console.status("[bold green]Dingo pensando... 🧠[/]"):
            chat = gemini_model.start_chat(history=chat_history)
            response = chat.send_message(prompt)
            chat_history.append({"role": "user",  "parts": [prompt]})
            chat_history.append({"role": "model", "parts": [response.text]})
            if len(chat_history) > 20:
                chat_history.pop(0)
                chat_history.pop(0)
            return response.text
    except Exception as e:
        err = str(e)
        if "API_KEY" in err or "403" in err: return "❌ API Key inválida. Use /config."
        if "429" in err or "quota" in err.lower(): return "⏱️ Limite atingido. Aguarde 1 minuto."
        return f"❌ Erro Gemini: {err}"

# ─────────────────────────────────────────────────────────
# MCP TOOLS
# ─────────────────────────────────────────────────────────
async def run_mcp_tool(tool: str, args: str) -> str:
    mcp_cfg = config["mcps"].get(tool)
    if not mcp_cfg:
        return f"❌ MCP '{tool}' não existe."
    if not mcp_cfg.get("enabled"):
        ativar = Prompt.ask(f"[yellow]MCP '{tool}' desativado. Configurar agora?[/]", choices=["s", "n"], default="s")
        if ativar == "s":
            await setup_wizard()
        return ""

    env = os.environ.copy()
    if tool == "notion":
        env["NOTION_API_KEY"] = mcp_cfg.get("api_key", "")
    elif tool in ["gmail", "google_calendar"]:
        env["GOOGLE_CREDENTIALS"] = mcp_cfg.get("credentials_file", "credentials.json")
    elif tool == "github":
        env["GITHUB_TOKEN"] = mcp_cfg.get("token", "")
    elif tool == "spotify":
        env["SPOTIFY_CLIENT_ID"]     = mcp_cfg.get("client_id", "")
        env["SPOTIFY_CLIENT_SECRET"] = mcp_cfg.get("client_secret", "")
    elif tool == "filesystem":
        args = args or mcp_cfg["allowed_paths"][0]

    pkg = mcp_cfg.get("npx_package", "")
    cmd = f"npx -y {pkg} {args}"

    try:
        with console.status(f"[bold blue]Executando {tool} MCP...[/]"):
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env, shell=True)
        return proc.stdout or proc.stderr or "MCP retornou vazio."
    except subprocess.TimeoutExpired:
        return "⏱️ MCP timeout."
    except Exception as e:
        return f"❌ Erro MCP: {str(e)}"

# ─────────────────────────────────────────────────────────
# AUTO DETECT MCP POR PALAVRAS-CHAVE
# ─────────────────────────────────────────────────────────
async def call_gemini_with_mcp(prompt: str) -> str:
    p = prompt.lower()

    keywords = {
        "notion":          ["notion", "página", "tarefa", "database", "bloco"],
        "gmail":           ["gmail", "email", "e-mail", "caixa de entrada", "mensagem"],
        "google_calendar": ["calendário", "calendar", "evento", "reunião", "agendar", "agenda"],
        "filesystem":      ["pasta", "arquivo", "organiz", "downloads", "desktop", "mover"],
        "github":          ["github", "repositório", "repo", "issue", "pull request", "commit"],
        "spotify":         ["spotify", "música", "playlist", "tocar", "pausar"],
    }

    for tool, keys in keywords.items():
        if any(k in p for k in keys) and config["mcps"].get(tool, {}).get("enabled"):
            path_arg = next((w for w in prompt.split() if "\\" in w or "/" in w or ":" in w), "")
            result = await run_mcp_tool(tool, path_arg if tool == "filesystem" else prompt)
            if result and "❌" not in result and "vazio" not in result:
                return await call_gemini(f"MCP {tool} retornou:\n{result}\n\nExplique ao usuário: {prompt}")

    return await call_gemini(prompt)

# ─────────────────────────────────────────────────────────
# STATUS DOS MCPs
# ─────────────────────────────────────────────────────────
def show_mcp_status():
    table = Table(title="🛠 Status dos MCPs", border_style="cyan")
    table.add_column("MCP",         style="bold", width=20)
    table.add_column("Status",      width=12)
    table.add_column("Descrição")

    icons = {
        "notion": "📝", "gmail": "📧", "google_calendar": "📅",
        "filesystem": "📁", "github": "🐙", "spotify": "🎵"
    }
    for name, cfg in config["mcps"].items():
        status  = "[green]✅ Ativo[/]" if cfg.get("enabled") else "[red]❌ Inativo[/]"
        icon    = icons.get(name, "🔧")
        desc    = cfg.get("description", "")
        table.add_row(f"{icon} {name}", status, desc)
    console.print(table)

# ─────────────────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────────────────
async def main():
    await boot_animation()

    while True:
        try:
            user_input = Prompt.ask("\n[bold yellow]🐕 Dingo IA[/]", console=console)
        except (KeyboardInterrupt, EOFError):
            user_input = "exit"

        user_input = user_input.strip()
        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit", "sair"]:
            console.print("[bold red]\n👋 Dingo IA desligado! Até mais![/]")
            sys.exit(0)

        if user_input.lower() in ["clear", "limpar"]:
            console.clear()
            continue

        if user_input.lower() in ["/reset", "/clear"]:
            chat_history.clear()
            console.print("[green]✅ Histórico limpo![/]")
            continue

        if user_input.lower() == "/config":
            await setup_wizard()
            continue

        if user_input.lower() == "/status":
            show_mcp_status()
            continue

        if user_input.lower() in ["/tools", "/help"]:
            rprint(Panel(
                "[green]/config[/]            → Configurar MCPs e API Keys\n"
                "[green]/status[/]            → Ver MCPs ativos/inativos\n"
                "[green]/notion[/]   [white]<texto>[/]  → Notion MCP direto\n"
                "[green]/gmail[/]    [white]<texto>[/]  → Gmail MCP direto\n"
                "[green]/calendar[/] [white]<texto>[/]  → Google Calendar MCP direto\n"
                "[green]/fs[/]       [white]<path>[/]   → Filesystem MCP direto\n"
                "[green]/github[/]   [white]<texto>[/]  → GitHub MCP direto\n"
                "[green]/spotify[/]  [white]<texto>[/]  → Spotify MCP direto\n"
                "[green]/reset[/]            → Limpar histórico da conversa\n"
                "[green]clear[/]             → Limpar tela\n"
                "[green]exit[/]             → Sair",
                title="[bold]🐕 Dingo IA — Comandos[/]",
                border_style="cyan"
            ))
            continue

        # Comandos MCP diretos
        mcp_commands = {
            "/notion":   "notion",
            "/gmail":    "gmail",
            "/calendar": "google_calendar",
            "/fs":       "filesystem",
            "/github":   "github",
            "/spotify":  "spotify",
        }
        matched = False
        for cmd, tool in mcp_commands.items():
            if user_input.startswith(cmd):
                args = user_input.split(" ", 1)[1] if " " in user_input else ""
                result = await run_mcp_tool(tool, args)
                if result:
                    icons = {"notion":"📝","gmail":"📧","google_calendar":"📅",
                             "filesystem":"📁","github":"🐙","spotify":"🎵"}
                    rprint(Panel(escape(result),
                                 title=f"[blue]{icons.get(tool,'')} {tool} MCP[/]",
                                 border_style="blue"))
                matched = True
                break

        if matched:
            continue

        # Chat com auto-detecção de MCP
        response = await call_gemini_with_mcp(user_input)
        rprint(Panel(
            escape(response),
            title="[bold green]🐕 Dingo IA[/]",
            border_style="green"
        ))

# ─────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    asyncio.run(main())
