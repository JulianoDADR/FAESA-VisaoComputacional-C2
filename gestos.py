"""
gestos.py - Regras de interacao definidas pela equipe a partir dos landmarks.

Aqui os 21 pontos viram informacao util para o jogo:
  * quais dedos estao esticados;
  * qual gesto (PEDRA, PAPEL, TESOURA ou INDEFINIDO) a mao esta fazendo;
  * se ha uma pinca (polegar + indicador), com histerese para nao "piscar";
  * se o gesto esta ESTAVEL por varios quadros seguidos.
Nada aqui depende do MediaPipe nem do desenho da tela.
"""
from collections import Counter, deque

import numpy as np

PEDRA, PAPEL, TESOURA, INDEFINIDO = "PEDRA", "PAPEL", "TESOURA", "?"
JOGADAS = (PEDRA, PAPEL, TESOURA)

# indices dos landmarks: (ponta, articulacao PIP) de cada dedo longo
DEDOS = {"indicador": (8, 6), "medio": (12, 10), "anelar": (16, 14), "minimo": (20, 18)}
PULSO, POLEGAR_PONTA, POLEGAR_IP, INDICADOR_MCP, MEDIO_MCP, MINIMO_MCP = 0, 4, 3, 5, 9, 17


def _dist(a, b):
    return float(np.linalg.norm(a[:2] - b[:2]))


def tamanho_mao(pts):
    """Escala de referencia: pulso ate a base do dedo medio.
    Usar distancias relativas deixa as regras independentes da distancia da camera."""
    return max(_dist(pts[PULSO], pts[MEDIO_MCP]), 1e-6)


def dedos_esticados(pts):
    """Um dedo esta esticado se a ponta esta bem mais longe do pulso do que a
    articulacao do meio (PIP). O polegar usa a distancia ate a base do minimo."""
    estado = {}
    for nome, (ponta, pip) in DEDOS.items():
        estado[nome] = _dist(pts[ponta], pts[PULSO]) > 1.15 * _dist(pts[pip], pts[PULSO])
    estado["polegar"] = (
        _dist(pts[POLEGAR_PONTA], pts[MINIMO_MCP]) > 1.1 * _dist(pts[POLEGAR_IP], pts[MINIMO_MCP])
        and _dist(pts[POLEGAR_PONTA], pts[INDICADOR_MCP]) > 0.55 * tamanho_mao(pts)
    )
    return estado


def classificar(pts):
    """Transforma o estado dos dedos em uma jogada."""
    if pts is None:
        return INDEFINIDO
    d = dedos_esticados(pts)
    longos = [d["indicador"], d["medio"], d["anelar"], d["minimo"]]
    n = sum(longos)
    if n == 0:
        return PEDRA
    if n == 4:
        return PAPEL
    if d["indicador"] and d["medio"] and not d["anelar"] and not d["minimo"]:
        return TESOURA
    return INDEFINIDO


class DetectorPinca:
    """Pinca = pontas do polegar e do indicador proximas.
    Histerese: fecha abaixo de 0.30 e so reabre acima de 0.45 (relativo a mao)."""

    def __init__(self, fechar=0.30, abrir=0.45):
        self.fechar, self.abrir = fechar, abrir
        self.ativa = False

    def atualizar(self, pts):
        """Retorna True apenas no quadro em que a pinca COMECA (borda de subida)."""
        if pts is None:
            self.ativa = False
            return False
        razao = _dist(pts[POLEGAR_PONTA], pts[8]) / tamanho_mao(pts)
        antes = self.ativa
        if self.ativa and razao > self.abrir:
            self.ativa = False
        elif not self.ativa and razao < self.fechar:
            self.ativa = True
        return self.ativa and not antes


class EstabilizadorGesto:
    """Guarda os ultimos N gestos e so confirma quando a maioria concorda.
    Evita que um quadro ruido seja tomado como a jogada do usuario."""

    def __init__(self, janela=8, minimo=6):
        self.historico = deque(maxlen=janela)
        self.minimo = minimo

    def adicionar(self, gesto):
        self.historico.append(gesto)

    def limpar(self):
        self.historico.clear()

    def estavel(self):
        """Retorna (gesto, confianca 0..1). gesto = INDEFINIDO se nao estabilizou."""
        if not self.historico:
            return INDEFINIDO, 0.0
        gesto, qtd = Counter(self.historico).most_common(1)[0]
        confianca = qtd / self.historico.maxlen
        if gesto != INDEFINIDO and qtd >= self.minimo:
            return gesto, confianca
        return INDEFINIDO, confianca if gesto != INDEFINIDO else 0.0
