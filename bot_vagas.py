"""Bot que lê um canal de vagas no Telegram e reenvia só as que combinam com o perfil."""
import json
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from telethon import TelegramClient, events

from filtros import avaliar, chave, parse, separar_links

load_dotenv()  # lê o arquivo .env (que NÃO vai pro Git)

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
GRUPO = os.environ["GRUPO"]                       # canal/grupo de origem
DESTINO = os.getenv("DESTINO", "me")              # grupo de destino ("me" = Mensagens Salvas)
DIAS_INICIAIS = int(os.getenv("DIAS_INICIAIS", "2"))
ARQ_ESTADO = "ultimo_id.txt"                      # guarda até onde já processou

ARQ_ENVIADAS = "vagas_enviadas.json"              # memória das vagas já enviadas
DIAS_MEMORIA = 30                                 # esquece vagas enviadas há mais de X dias

client = TelegramClient("sessao", API_ID, API_HASH)
destino = "me"
processadas = set()                               # IDs de mensagens já vistas nesta execução
separador_enviado = False                         # já avisou o início desta execução?


def carregar_enviadas():
    try:
        with open(ARQ_ENVIADAS, encoding="utf-8") as f:
            dados = json.load(f)
    except Exception:
        return {}
    limite = (datetime.now(timezone.utc) - timedelta(days=DIAS_MEMORIA)).timestamp()
    return {k: t for k, t in dados.items() if t >= limite}


def salvar_enviadas():
    with open(ARQ_ENVIADAS, "w", encoding="utf-8") as f:
        json.dump(enviadas, f, ensure_ascii=False)


enviadas = carregar_enviadas()


async def achar_destino():
    if DESTINO == "me":
        return "me"
    async for d in client.iter_dialogs():
        if d.name == DESTINO:
            return d.entity
    raise SystemExit(f"Grupo '{DESTINO}' não encontrado. Confira o nome exato.")


def ler_ultimo_id():
    try:
        with open(ARQ_ESTADO) as f:
            return int(f.read().strip())
    except Exception:
        return None


def salvar_ultimo_id(i):
    with open(ARQ_ESTADO, "w") as f:
        f.write(str(i))


async def enviar_separador(extra=""):
    global separador_enviado
    separador_enviado = True
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    linhas = ["━━━━━━━━━━━━━━━━━━", f"🔄 Nova execução - {agora}"]
    if extra:
        linhas.append(extra)
    linhas.append("━━━━━━━━━━━━━━━━━━")
    await client.send_message(destino, "\n".join(linhas))


def urls_dos_botoes(msg):
    """Links que ficam em botões abaixo da mensagem (não aparecem no texto)."""
    urls = []
    for linha in (msg.buttons or []):
        for botao in linha:
            if getattr(botao, "url", None):
                urls.append(botao.url)
    return urls


async def link_da_mensagem(msg):
    """Link para o post original no canal (plano B quando a vaga vem sem link)."""
    try:
        chat = await msg.get_chat()
        if getattr(chat, "username", None):
            return f"https://t.me/{chat.username}/{msg.id}"
        return f"https://t.me/c/{chat.id}/{msg.id}"
    except Exception:
        return ""


async def processar(msg):
    if msg.id in processadas:        # evita processar a mesma mensagem 2x
        return
    processadas.add(msg.id)
    texto = msg.text or ""           # versão markdown (mantém links)
    if "tulo:" not in texto:
        return
    enviou = False
    vagas = parse(texto)
    botoes = urls_dos_botoes(msg) if len(vagas) == 1 else []
    for v in vagas:
        ok, avisos = avaliar(v)
        if not ok:
            continue
        k = chave(v)
        if k in enviadas:            # vaga repetida: ignora
            continue
        enviadas[k] = datetime.now(timezone.utc).timestamp()
        salvar_enviadas()
        enviou = True
        if not separador_enviado:    # separador antes da 1ª vaga desta execução
            await enviar_separador()
        linhas = [f"🎯 {v['titulo']}"]
        if v["empresa"]:  linhas.append(f"🏢 {v['empresa']}")
        if v["local"]:    linhas.append(f"🌍 {v['local']}")
        if v["atuacao"]:  linhas.append(f"👨‍💻 {v['atuacao']}")
        if v["nivel"]:    linhas.append(f"🎓 {v['nivel']}")
        if v["contrato"]: linhas.append(f"📄 {v['contrato']}")
        if avisos:        linhas.append("⚠️ " + ", ".join(avisos))
        links_vaga, links_recrutador = separar_links(list(dict.fromkeys(v["urls"] + botoes)))
        linhas += [f"🔗 {u}" for u in links_vaga]
        if links_recrutador:
            linhas.append(f"👤 Recrutador: {links_recrutador[0]}")
        if not links_vaga:           # vaga sem link: aponta para o post original
            original = await link_da_mensagem(msg)
            if original:
                linhas.append(f"📎 Post original: {original}")
        await client.send_message(destino, "\n".join(linhas))
    if enviou:   # encaminha o original: preserva botões e links escondidos
        await client.forward_messages(destino, msg)


@client.on(events.NewMessage(chats=GRUPO))
async def handler(event):
    await processar(event.message)
    salvar_ultimo_id(event.message.id)


async def principal():
    global destino
    await client.start()
    destino = await achar_destino()

    ultimo = ler_ultimo_id()
    if ultimo:
        filtro = dict(min_id=ultimo)
        print(f"Buscando vagas depois da mensagem {ultimo}...")
    else:
        inicio = datetime.now(timezone.utc) - timedelta(days=DIAS_INICIAIS)
        filtro = dict(offset_date=inicio)
        print(f"Primeira execução: buscando os últimos {DIAS_INICIAIS} dias...")

    maior = ultimo or 0
    async for msg in client.iter_messages(GRUPO, reverse=True, **filtro):
        await processar(msg)
        maior = max(maior, msg.id)

    if not separador_enviado:        # busca inicial não achou nada para enviar
        await enviar_separador("😴 Nenhuma vaga nova que combine com o seu perfil")

    if not maior:
        ultimas = await client.get_messages(GRUPO, limit=1)
        if ultimas:
            maior = ultimas[0].id
    if maior:
        salvar_ultimo_id(maior)

    print("Rodando... aguardando vagas novas")
    await client.run_until_disconnected()


if __name__ == "__main__":
    client.loop.run_until_complete(principal())
