"""Lógica de filtro das vagas (sem Telegram, fácil de testar)."""
import re
import unicodedata

# ===== SEU PERFIL =====
CARGOS = [
    "qa", "quality assurance", "quality engineer", "quality engineering",
    "engenheiro de qualidade", "engenheira de qualidade", "analista de qualidade",
    "analista de teste", "analista de testes", "teste de software", "testes de software",
    "tester", "teste", "testes", "test", "sdet", "test automation",
    "automacao de testes", "automatizacao de testes",
    "software engineer", "engenheiro de software", "engenheira de software",
]
BLOQUEAR_TITULO = [
    "estagio", "estagiario", "trainee", "rater", "assistente",
    "pcd", "pessoa com deficiencia",
]
ACEITAR_ESTADO_SP = False          # True = aceita "Campinas, SP"
ACEITAR_BRASIL_SEM_MODELO = True   # pleno com "Local: Brasil" e sem atuação
EXCLUIR_PJ = False                 # True = descarta vagas com "Contrato: PJ"
# ======================

UFS = {"AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA",
       "PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SE","TO"}  # sem SP

def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")

def palavra(termo, texto):
    return re.search(rf"\b{re.escape(norm(termo))}\b", texto) is not None

def limpar(s):
    return s.replace("*", "").replace("_", "").replace("#", "").strip()

def parse(texto):
    """Quebra a mensagem em vagas (uma mensagem pode ter várias)."""
    vagas, atual = [], None
    for linha in texto.splitlines():
        m = re.search(r"T[íi]tulo:[ \t]*(.+)", linha, re.I)
        if m:
            atual = {"titulo": limpar(m.group(1)), "linhas": []}
            vagas.append(atual)
        elif atual is not None:
            atual["linhas"].append(linha)
    for v in vagas:
        bloco = "\n".join(v["linhas"])
        def campo(nome):
            m = re.search(rf"{nome}:[ \t]*(.+)", bloco, re.I)
            return limpar(m.group(1)) if m else ""
        v["empresa"] = campo("Empresa")
        v["local"] = campo("Local")
        v["atuacao"] = campo(r"Atua[çc][ãa]o")
        v["nivel"] = campo(r"N[íi]vel")
        v["contrato"] = campo("Contrato")
        v["urls"] = list(dict.fromkeys(re.findall(r"https?://[^\s)\]]+", bloco)))
    return vagas

def avaliar(v):
    """Retorna (aprovada, avisos)."""
    titulo = norm(v["titulo"])
    local, atuacao, nivel = norm(v["local"]), norm(v["atuacao"]), norm(v["nivel"])
    avisos = []

    if any(palavra(b, titulo) for b in BLOQUEAR_TITULO):
        return False, []
    if not any(palavra(c, titulo) for c in CARGOS):
        return False, []
    uf = re.search(r"[/,\-]\s*([A-Z]{2})\b", v["titulo"])
    if uf and uf.group(1) in UFS:          # ex: "... - Recife/PE" no título
        return False, []
    if EXCLUIR_PJ and "pj" in norm(v["contrato"]):
        return False, []

    eh_remoto = any(t in atuacao or t in local
                    for t in ["remoto", "remote", "home office", "homeoffice"])
    eh_pleno, eh_junior = "pleno" in nivel, "junior" in nivel

    if nivel:
        if eh_junior and not eh_remoto:
            return False, []
        if not (eh_pleno or eh_junior):
            return False, []
    else:
        avisos.append("nível não informado")

    if eh_remoto:
        return True, avisos
    if not local:
        avisos.append("local não informado")
        return True, avisos
    if palavra("sao paulo", local):
        return True, avisos
    if ACEITAR_ESTADO_SP and palavra("sp", local):
        return True, avisos
    if eh_pleno and ACEITAR_BRASIL_SEM_MODELO and not atuacao and palavra("brasil", local):
        avisos.append("sem modelo de atuação (Brasil)")
        return True, avisos
    return False, []
