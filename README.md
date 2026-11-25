# 🎯 Vagas QA Bot

![Testes](https://github.com/r1moreira9/bot-vagas.git/actions/workflows/tests.yml/badge.svg)

Bot em Python que lê um canal de vagas no Telegram e reenvia, para um grupo meu,
**apenas as vagas que combinam com o meu perfil**, sem precisar abrir uma por uma.

## O problema

O canal de vagas recebe dezenas de posts por dia, com várias senioridades, cidades e
modelos de trabalho. Filtrar na mão consome tempo e vaga boa passa batida.

## O que ele faz

- Interpreta dois formatos de mensagem do canal (vaga única e várias vagas num post)
- Filtra por **título**, **nível**, **local** e **modalidade**
- Envia um resumo da vaga + o post original (mantém botões e links)
- Lembra a última mensagem processada, então pega também o que chegou com o PC desligado
- Avisa (⚠️) quando a vaga não informa nível ou local

## Regras de filtro (exemplo do meu perfil)

| Nível | Atuação | Local | Resultado |
|---|---|---|---|
| Pleno | qualquer | São Paulo | ✅ |
| Pleno | remoto | qualquer | ✅ |
| Pleno | presencial/híbrido | outra cidade | ❌ |
| Júnior | remoto | qualquer | ✅ |
| Júnior | híbrido/presencial | qualquer | ❌ |
| Sênior, Tech Lead, estágio | - | - | ❌ |

As regras ficam em `filtros.py` e são facilmente ajustáveis.

## Testes

As regras são cobertas por testes automatizados (pytest) com vagas fictícias,
rodando no GitHub Actions a cada push. Um bug real que os testes ajudaram a achar:
o filtro inicial descartava todas as vagas de júnior, porque elas chegam com um
cabeçalho diferente ("VAGA PARA JÚNIOR!!!").

```
python -m pytest -v
```

## Como usar

1. Pegue `api_id` e `api_hash` em https://my.telegram.org (API development tools)
2. Instale: `pip install -r requirements.txt`
3. Copie `.env.example` para `.env` e preencha
4. Rode: `python bot_vagas.py` (o primeiro uso pede telefone e código do Telegram)

## Segurança

`.env`, `*.session` e `ultimo_id.txt` estão no `.gitignore`. Nunca suba esses arquivos:
a sessão dá acesso à conta do Telegram.

## Aviso

Projeto de uso pessoal: lê apenas canais dos quais já participo.
