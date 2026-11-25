"""Testes das regras de filtro. Rode com:  pytest -v

Os exemplos de vaga abaixo são fictícios/anonimizados, no mesmo formato do canal.
"""
import pytest

import filtros
from filtros import avaliar, chave, parse


def vaga(titulo, nivel=None, local=None, atuacao=None, contrato=None):
    """Monta o texto de uma vaga no formato do canal e devolve já interpretada."""
    linhas = ["🚨Nova vaga encontrada🚨", "", f"📜Título: {titulo}", "🏢Empresa: Empresa X"]
    if local:    linhas.append(f"🌍Local: {local}")
    if atuacao:  linhas.append(f"👨‍💻Atuação: {atuacao}")
    if contrato: linhas.append(f"📄Contrato: {contrato}")
    if nivel:    linhas.append(f"🎓Nível: #{nivel}")
    return parse("\n".join(linhas))[0]


# ---------- Regras de nível / local / modalidade ----------

@pytest.mark.parametrize("descricao, v, esperado", [
    ("pleno em SP, híbrido",
     vaga("Analista de QA", "Pleno", "São Paulo, SP", "híbrido"), True),
    ("pleno em SP, presencial",
     vaga("QA Engineer", "Pleno", "São Paulo", "presencial"), True),
    ("pleno 'São Paulo e Região', sem atuação",
     vaga("Analista de Qualidade Pleno", "Pleno", "São Paulo e Região"), True),
    ("pleno remoto em qualquer cidade",
     vaga("QA Pleno", "Pleno", "Curitiba, PR", "remoto"), True),
    ("pleno presencial em outra cidade",
     vaga("QA Pleno", "Pleno", "Curitiba, PR", "presencial"), False),
    ("pleno híbrido em outra cidade",
     vaga("QA Pleno", "Pleno", "Recife, PE", "híbrido"), False),
    ("júnior remoto",
     vaga("Mobile App Tester", "Junior", "Brasil", "remoto"), True),
    ("júnior híbrido em SP (só aceito júnior remoto)",
     vaga("Analista de QA Júnior", "Junior", "São Paulo", "híbrido"), False),
    ("júnior sem atuação em SP",
     vaga("Analista de QA Júnior", "Junior", "São Paulo, SP"), False),
    ("sênior remoto",
     vaga("Quality Assurance Engineer", "Senior", "Brasil", "remoto"), False),
    ("tech lead em SP",
     vaga("Quality Assurance Lead", "Techlead", "São Paulo, SP"), False),
])
def test_nivel_local_modalidade(descricao, v, esperado):
    ok, _ = avaliar(v)
    assert ok is esperado, descricao


def test_pleno_brasil_sem_atuacao_passa_com_aviso():
    ok, avisos = avaliar(vaga("QA Pleno", "Pleno", "Brasil"))
    assert ok
    assert any("Brasil" in a for a in avisos)


def test_junior_brasil_sem_atuacao_nao_passa():
    ok, _ = avaliar(vaga("QA Júnior", "Junior", "Brasil"))
    assert not ok


# ---------- Filtro de título ----------

@pytest.mark.parametrize("titulo", [
    "Analista de QA", "Quality Assurance Engineer", "Engenheiro de Qualidade (QA)",
    "Analista de Testes/Qualidade", "Software Engineer", "SDET", "Mobile App Tester",
    "Analista de Qualidade de Software", "Test Automation Engineer",
])
def test_titulos_que_interessam(titulo):
    ok, _ = avaliar(vaga(titulo, "Pleno", "São Paulo"))
    assert ok


@pytest.mark.parametrize("titulo", [
    "Controle de Qualidade Jr",                 # indústria, não é software
    "Manager, Production Quality",
    "Desenvolvedor Backend",
    "Estagiário de QA",
    "Quality Assurance Rater",
    "Assistente da Qualidade",
    "Analista de QA - Exclusiva PCD",
    "Analista de Qualidade - Recife/PE",        # UF no título
])
def test_titulos_que_nao_interessam(titulo):
    ok, _ = avaliar(vaga(titulo, "Pleno", "São Paulo", "remoto"))
    assert not ok


def test_qa_no_final_do_titulo_nao_e_confundido_com_estado():
    ok, _ = avaliar(vaga("Engenheiro de Testes - QA", "Pleno", "São Paulo"))
    assert ok


# ---------- Parser ----------

def test_formato_junior_cabecalho_diferente():
    texto = "🚨VAGA PARA JÚNIOR!!!🚨\n\n📜Título: QA Jr\n🌍Local: São Paulo\n🎓Nível: #Junior"
    assert len(parse(texto)) == 1


def test_mensagem_com_varias_vagas():
    texto = (
        "😀Segue algumas vagas\n\n"
        "📝Título: Analista de Qualidade\n🏢Empresa: A\n"
        "🔗Link [Acesse aqui](https://exemplo.com/vaga/1)\n\n"
        "📝Título: QA Engineer\n🏢Empresa: B\n"
        "🔗Link [Acesse aqui](https://exemplo.com/vaga/2)"
    )
    vagas = parse(texto)
    assert [v["titulo"] for v in vagas] == ["Analista de Qualidade", "QA Engineer"]
    assert vagas[0]["urls"] == ["https://exemplo.com/vaga/1"]
    assert vagas[1]["urls"] == ["https://exemplo.com/vaga/2"]


def test_vaga_sem_nivel_e_local_passa_com_avisos():
    texto = "📝Título: Analista de Qualidade\n🏢Empresa: A\n🔗Link (https://exemplo.com/1)"
    ok, avisos = avaliar(parse(texto)[0])
    assert ok
    assert len(avisos) == 2


def test_mensagem_que_nao_e_vaga():
    assert parse("Bom dia, galera! Lembrem das regras do canal.") == []


def test_campos_extraidos():
    v = vaga("QA Pleno", "Pleno", "São Paulo, SP", "híbrido", "CLT")
    assert v["titulo"] == "QA Pleno"
    assert v["local"] == "São Paulo, SP"
    assert v["atuacao"] == "híbrido"
    assert v["nivel"] == "Pleno"          # sem o '#'
    assert v["contrato"] == "CLT"


# ---------- Opções de configuração ----------

def test_excluir_pj(monkeypatch):
    v = vaga("QA Pleno", "Pleno", "São Paulo", contrato="PJ")
    assert avaliar(v)[0] is True
    monkeypatch.setattr(filtros, "EXCLUIR_PJ", True)
    assert avaliar(v)[0] is False


def test_aceitar_estado_sp(monkeypatch):
    v = vaga("QA Pleno", "Pleno", "Campinas, SP", "presencial")
    assert avaliar(v)[0] is False
    monkeypatch.setattr(filtros, "ACEITAR_ESTADO_SP", True)
    assert avaliar(v)[0] is True


def test_mesma_vaga_gera_mesma_chave():
    a = vaga("Analista de QA Pleno", "Pleno", "São Paulo, SP", "híbrido")
    b = vaga("ANALISTA DE QA  PLENO!", "Pleno", "Sao Paulo SP", "remoto")
    assert chave(a) == chave(b)


def test_codigo_no_inicio_do_titulo_e_ignorado():
    a = vaga("8475 - Analista de QA", "Pleno", "São Paulo")
    b = vaga("8472 - Analista de QA", "Pleno", "São Paulo")
    assert chave(a) == chave(b)


def test_vagas_diferentes_geram_chaves_diferentes():
    a = vaga("Analista de QA", "Pleno", "São Paulo")
    b = vaga("Analista de QA", "Pleno", "Campinas")
    assert chave(a) != chave(b)