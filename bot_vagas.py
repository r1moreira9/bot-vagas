"""Bot que lê um canal de vagas no Telegram e reenvia só as que combinam com o perfil."""
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from telethon import TelegramClient, events

from filtros import avaliar, parse

load_dotenv()  # lê o arquivo .env (que NÃO vai pro Git)

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
GRUPO = os.environ["GRUPO"]                       # canal/grupo de origem
DESTINO = os.getenv("DESTINO", "me")              # grupo de destino ("me" = Mensagens Salvas)
DIAS_INICIAIS = int(os.getenv("DIAS_INICIAIS", "2"))
ARQ_ESTADO = "ultimo_id.txt"                      # guarda até onde já processou

client = TelegramClient("sessao", API_ID, API_HASH)
destino = "me"


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


async def processar(msg):
    texto = msg.text or ""           # versão markdown (mantém links)
    if "tulo:" not in texto:
        return
    enviou = False
    for v in parse(texto):
        ok, avisos = avaliar(v)
        if not ok:
            continue
        enviou = True
        linhas = [f"🎯 {v['titulo']}"]
        if v["empresa"]:  linhas.append(f"🏢 {v['empresa']}")
        if v["local"]:    linhas.append(f"🌍 {v['local']}")
        if v["atuacao"]:  linhas.append(f"👨‍💻 {v['atuacao']}")
        if v["nivel"]:    linhas.append(f"🎓 {v['nivel']}")
        if v["contrato"]: linhas.append(f"📄 {v['contrato']}")
        if avisos:        linhas.append("⚠️ " + ", ".join(avisos))
        linhas += [f"🔗 {u}" for u in v["urls"]]
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
