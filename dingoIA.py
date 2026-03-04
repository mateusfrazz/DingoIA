#!/usr/bin/env python3
import subprocess
import sys
import os

# ─────────────────────────────────────────────────────────
# AUTO-INSTALL DE DEPENDÊNCIAS
# ─────────────────────────────────────────────────────────
def install_deps():
    deps = ["requests", "rich"]
    for dep in deps:
        try:
            __import__(dep)
        except ImportError:
            print(f"[Dingo IA] Instalando {dep}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep, "-q"])
            print(f"[Dingo IA] {dep} instalado com sucesso!")

install_deps()

# ─────────────────────────────────────────────────────────
# IMPORTS (após garantir instalação)
# ─────────────────────────────────────────────────────────
import asyncio
from time import sleep
import requests
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.progress import track
from rich.markup import escape
from rich import print as rprint
from rich.traceback import install
install(show_locals=False)

console = Console()

# ─────────────────────────────────────────────────────────
# CONFIGURAÇÕES
# ─────────────────────────────────────────────────────────
OLLAMA_MODEL    = "qwen2.5:7b"
OLLAMA_API_URL  = "http://localhost:11434"
NOTION_API_KEY  = os.environ.get("NOTION_API_KEY", "")
GMAIL_CREDS     = os.environ.get("GMAIL_CREDENTIALS", "credentials.json")

ollama_process  = None

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
# AUTO-START OLLAMA
# ─────────────────────────────────────────────────────────
async def ensure_ollama(model: str = OLLAMA_MODEL):
    global ollama_process
    tags_url = f"{OLLAMA_API_URL}/api/tags"

    # 1. Checa se já está rodando
    try:
        resp = requests.get(tags_url, timeout=2)
        if resp.status_code == 200:
            console.print(f"[green]✅ Ollama já está rodando![/]")
            modelos = [m["name"] for m in resp.json().get("models", [])]
            if not any(model in m for m in modelos):
                console.print(f"[yellow]📥 Baixando modelo {model}... (aguarde)[/]")
                subprocess.run(["ollama", "pull", model], check=True)
            return
    except:
        pass

    # 2. Inicia Ollama serve em background
    console.print("[bold blue]🚀 Iniciando Ollama serve em background...[/]")
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    ollama_process = subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags
    )

    # 3. Aguarda ficar pronto (até 30s)
    console.print("[bold yellow]⏳ Aguardando Ollama iniciar...[/]")
    for i in track(range(30), description="Conectando ao Ollama..."):
        try:
            resp = requests.get(tags_url, timeout=1)
            if resp.status_code == 200:
                console.print("[green]✅ Ollama pronto![/]")
                # 4. Baixa modelo se não tiver
                modelos = [m["name"] for m in resp.json().get("models", [])]
                if not any(model in m for m in modelos):
                    console.print(f"[yellow]📥 Baixando modelo {model}... (aguarde)[/]")
                    subprocess.run(["ollama", "pull", model], check=True)
                return
        except:
            pass
        sleep(1)

    console.print("[bold red]❌ Falha ao iniciar Ollama. Verifique a instalação.[/]")
    sys.exit(1)

# ─────────────────────────────────────────────────────────
# BOOT ANIMATION
# ─────────────────────────────────────────────────────────
async def boot_animation():
    os.system("title Dingo IA - Ollama MCP Agent" if os.name == "nt" else "")
    console.clear()

    await ensure_ollama()

    text = Text()
    for char in DINGO_ASCII:
        text.append(char, style="bold cyan")
        with Live(text, refresh_per_second=30, console=console) as live:
            live.update(text)
        await asyncio.sleep(0.01)

    rprint(Panel.fit(
        DINGO_ASCII,
        title="[bold green]🐕 Dingo IA Ativado![/]",
        subtitle="[dim]powered by Ollama + MCP[/]",
        border_style="bright_green"
    ))
    console.print("[bold magenta]Digite 'exit' para sair | /tools para ver MCPs disponíveis[/]\n")

# ─────────────────────────────────────────────────────────
# OLLAMA CHAT
# ─────────────────────────────────────────────────────────
async def call_ollama(prompt: str, model: str = OLLAMA_MODEL) -> str:
    url = f"{OLLAMA_API_URL}/api/generate"
    data = {
        "model": model,
        "prompt": f"Você é Dingo IA, um assistente terminal inteligente. Responda sempre em português de forma clara e útil.\n\nUsuário: {prompt}",
        "stream": False,
        "options": {"temperature": 0.7}
    }
    try:
        with console.status(f"[bold green]Dingo pensando... 🧠[/]"):
            resp = requests.post(url, json=data, timeout=120)
            if resp.status_code == 404:
                return f"⚠️ Modelo '{model}' não encontrado. Rode: ollama pull {model}"
            resp.raise_for_status()
            return resp.json().get("response", "Sem resposta gerada.")
    except requests.exceptions.ConnectionError:
        return "❌ Ollama desconectado. Reinicie o Dingo IA."
    except requests.exceptions.Timeout:
        return "⏱️ Timeout: modelo demorou demais para responder."
    except Exception as e:
        return f"❌ Erro: {str(e)}"

# ─────────────────────────────────────────────────────────
# MCP TOOLS
# ─────────────────────────────────────────────────────────
async def run_mcp_tool(tool: str, args: str) -> str:
    env = os.environ.copy()
    env["NOTION_API_KEY"] = NOTION_API_KEY
    env["GMAIL_CREDENTIALS"] = GMAIL_CREDS

    cmds = {
        "notion":     ["npx", "-y", "@notionhq/notion-mcp-server", args],
        "filesystem": ["npx", "-y", "@modelcontextprotocol/server-filesystem", args],
        "gmail":      ["npx", "-y", "@gcp-mcp/gmail-mcp-server", args],
    }

    if tool not in cmds:
        return f"❌ MCP '{tool}' não configurado. Use: notion, filesystem, gmail."

    try:
        proc = subprocess.run(
            cmds[tool],
            capture_output=True,
            text=True,
            timeout=60,
            env=env
        )
        return proc.stdout or proc.stderr or "MCP retornou vazio."
    except FileNotFoundError:
        return "❌ npx não encontrado. Instale Node.js: https://nodejs.org"
    except subprocess.TimeoutExpired:
        return "⏱️ MCP timeout. Tente novamente."
    except Exception as e:
        return f"❌ Erro MCP: {str(e)}"

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

        # Sair
        if user_input.lower() in ["exit", "quit", "sair"]:
            console.print("[bold red]\n👋 Dingo IA desligado! Até mais![/]")
            if ollama_process:
                ollama_process.terminate()
            sys.exit(0)

        # Listar MCPs
        if user_input.startswith("/tools"):
            rprint(Panel(
                "[green]/notion[/] [white]<texto>[/]    → Cria/busca no Notion\n"
                "[green]/fs[/]     [white]<caminho>[/]   → Gerencia arquivos\n"
                "[green]/gmail[/]  [white]<texto>[/]    → Acessa Gmail\n"
                "[green]/model[/]  [white]<nome>[/]     → Troca modelo Ollama",
                title="[bold]🛠 MCPs Disponíveis[/]",
                border_style="cyan"
            ))
            continue

        # Trocar modelo
        if user_input.startswith("/model "):
            novo_modelo = user_input.split(" ", 1)[1]
            OLLAMA_MODEL_ATUAL = novo_modelo
            console.print(f"[green]✅ Modelo trocado para: {novo_modelo}[/]")
            continue

        # MCP Notion
        if user_input.startswith("/notion"):
            args = user_input.split(" ", 1)[1] if " " in user_input else ""
            result = await run_mcp_tool("notion", args)
            rprint(Panel(escape(result), title="[blue]📝 Notion MCP[/]", border_style="blue"))
            continue

        # MCP Filesystem
        if user_input.startswith("/fs"):
            args = user_input.split(" ", 1)[1] if " " in user_input else ""
            result = await run_mcp_tool("filesystem", args)
            rprint(Panel(escape(result), title="[blue]📁 Filesystem MCP[/]", border_style="blue"))
            continue

        # MCP Gmail
        if user_input.startswith("/gmail"):
            args = user_input.split(" ", 1)[1] if " " in user_input else ""
            result = await run_mcp_tool("gmail", args)
            rprint(Panel(escape(result), title="[blue]📧 Gmail MCP[/]", border_style="blue"))
            continue

        # Chat normal com Ollama
        response = await call_ollama(user_input)
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
