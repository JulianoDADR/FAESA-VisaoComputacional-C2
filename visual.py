"""
visual.py - Desenho da tela (resposta visual ao usuario).

Mostra o que a aplicacao entendeu: esqueleto da mao, gesto lido em tempo real
com barra de confianca, contagem, jogada do computador, placar e avisos quando
a mao nao e detectada. Nao contem regras do jogo, apenas le o estado de Jogo.
Os icones de pedra/papel/tesoura sao desenhados com primitivas do OpenCV
(nenhuma imagem de terceiros e usada).
"""
import cv2
import numpy as np

from gestos import INDEFINIDO, PAPEL, PEDRA, TESOURA
from logica import ANULADA, CONTAGEM, FIM, LEITURA, MENU, RESULTADO
from maos import CONEXOES

FONTE = cv2.FONT_HERSHEY_DUPLEX
BRANCO, PRETO = (255, 255, 255), (0, 0, 0)
VERDE, VERMELHO, AMARELO = (90, 220, 90), (70, 70, 235), (40, 210, 250)
AZUL, CINZA, LARANJA = (235, 170, 60), (150, 150, 150), (40, 140, 255)
COR_RESULTADO = {"VITORIA": VERDE, "DERROTA": VERMELHO, "EMPATE": AMARELO}


# ---------------------------------------------------------------- utilitarios
def texto(img, s, org, escala=1.0, cor=BRANCO, esp=2, centro=False):
    (tw, th), _ = cv2.getTextSize(s, FONTE, escala, esp)
    x, y = org
    if centro:
        x -= tw // 2
    if esp >= 2:   # contorno preto so no texto grosso (no fino ele "borra" as letras)
        cv2.putText(img, s, (int(x), int(y)), FONTE, escala, PRETO, esp + 2, cv2.LINE_AA)
    cv2.putText(img, s, (int(x), int(y)), FONTE, escala, cor, esp, cv2.LINE_AA)
    return tw, th


def painel(img, x, y, w, h, alpha=0.55, cor=(20, 20, 20)):
    """Retangulo semitransparente."""
    x, y = max(int(x), 0), max(int(y), 0)
    sub = img[y:y + int(h), x:x + int(w)]
    fundo = np.full_like(sub, cor)
    cv2.addWeighted(fundo, alpha, sub, 1 - alpha, 0, sub)


def barra(img, x, y, w, h, frac, cor):
    cv2.rectangle(img, (x, y), (x + w, y + h), (60, 60, 60), -1)
    cv2.rectangle(img, (x, y), (x + int(w * max(0, min(frac, 1))), y + h), cor, -1)
    cv2.rectangle(img, (x, y), (x + w, y + h), BRANCO, 1)


def icone(img, jogada, centro, r, cor=BRANCO):
    """Desenha um icone simples da jogada."""
    cx, cy = int(centro[0]), int(centro[1])
    if jogada == PEDRA:
        cv2.circle(img, (cx, cy), r, (110, 110, 120), -1, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), r, cor, 3, cv2.LINE_AA)
        cv2.circle(img, (cx - r // 3, cy - r // 3), r // 5, (160, 160, 170), -1, cv2.LINE_AA)
    elif jogada == PAPEL:
        w, h = int(r * 1.5), int(r * 1.9)
        cv2.rectangle(img, (cx - w // 2, cy - h // 2), (cx + w // 2, cy + h // 2), (245, 245, 245), -1)
        cv2.rectangle(img, (cx - w // 2, cy - h // 2), (cx + w // 2, cy + h // 2), cor, 3)
        for i in range(1, 5):
            yy = cy - h // 2 + i * h // 5
            cv2.line(img, (cx - w // 3, yy), (cx + w // 3, yy), (180, 180, 180), 2)
    elif jogada == TESOURA:
        cv2.line(img, (cx - r, cy - r), (cx + r // 3, cy + r // 3), (200, 200, 210), 6, cv2.LINE_AA)
        cv2.line(img, (cx + r, cy - r), (cx - r // 3, cy + r // 3), (200, 200, 210), 6, cv2.LINE_AA)
        cv2.circle(img, (cx - r // 2, cy + r // 2 + 4), r // 3, cor, 4, cv2.LINE_AA)
        cv2.circle(img, (cx + r // 2, cy + r // 2 + 4), r // 3, cor, 4, cv2.LINE_AA)
    else:
        texto(img, "?", (cx, cy + r // 2), r / 25, cor, 3, centro=True)


# ---------------------------------------------------------------- mao
def desenhar_mao(img, pts, gesto, pinca_ativa):
    if pts is None:
        return
    cor = {PEDRA: CINZA, PAPEL: BRANCO, TESOURA: AZUL}.get(gesto, (120, 120, 255))
    for a, b in CONEXOES:
        cv2.line(img, tuple(pts[a][:2].astype(int)), tuple(pts[b][:2].astype(int)), cor, 2, cv2.LINE_AA)
    for p in pts:
        cv2.circle(img, tuple(p[:2].astype(int)), 4, VERDE, -1, cv2.LINE_AA)
    # cursor na ponta do indicador; fica cheio durante a pinca
    ponta = tuple(pts[8][:2].astype(int))
    cv2.circle(img, ponta, 14, AMARELO, -1 if pinca_ativa else 3, cv2.LINE_AA)


# ---------------------------------------------------------------- telas
def desenhar(img, jogo, agora, pts, gesto_inst, conf, pinca_ativa, fps):
    h, w = img.shape[:2]
    if jogo.estado == MENU:
        _tela_menu(img, jogo, agora)
    else:
        _hud(img, jogo)
        if jogo.estado == CONTAGEM:
            _tela_contagem(img, jogo, agora)
        elif jogo.estado == LEITURA:
            _tela_leitura(img, jogo, agora, gesto_inst, conf)
        elif jogo.estado == RESULTADO:
            _tela_resultado(img, jogo)
        elif jogo.estado == ANULADA:
            painel(img, 0, h // 2 - 50, w, 90, 0.6, (0, 0, 90))
            texto(img, jogo.mensagem, (w // 2, h // 2 + 8), 0.9, BRANCO, 2, centro=True)
        elif jogo.estado == FIM:
            _tela_fim(img, jogo)

    # a mao e desenhada por ultimo para ficar sempre visivel sobre os paineis
    desenhar_mao(img, pts, gesto_inst, pinca_ativa)

    # rodape: o que o sistema esta lendo agora
    painel(img, 0, h - 34, w, 34, 0.6)
    status = "MAO: " + ("detectada" if pts is not None else "NAO DETECTADA")
    texto(img, status, (12, h - 11), 0.55, VERDE if pts is not None else VERMELHO, 1)
    texto(img, f"gesto: {gesto_inst}", (240, h - 11), 0.55, BRANCO, 1)
    texto(img, "PINCA" if pinca_ativa else "", (420, h - 11), 0.55, AMARELO, 1)
    texto(img, f"{fps:4.0f} fps   [Q] sair  [M] menu", (w - 300, h - 11), 0.55, CINZA, 1)


def _tela_menu(img, jogo, agora):
    h, w = img.shape[:2]
    painel(img, 0, 0, w, h, 0.35)
    texto(img, "PEDRA, PAPEL e TESOURA", (w // 2, int(h * 0.15)), 1.4, AMARELO, 3, centro=True)
    texto(img, "Escolha o adversario", (w // 2, int(h * 0.25)), 0.85, BRANCO, 2, centro=True)
    descr = {"FACIL": "joga ao acaso", "ESPERTO": "aprende seus habitos"}
    for b in jogo.botoes:
        x, y, bw, bh = b.ret
        painel(img, x, y, bw, bh, 0.75, (60, 90, 40) if b.hover else (40, 40, 40))
        cv2.rectangle(img, (x, y), (x + bw, y + bh), AMARELO if b.hover else BRANCO, 3 if b.hover else 1)
        texto(img, b.rotulo, (x + bw // 2, y + bh // 2 + 5), 1.0, BRANCO, 2, centro=True)
        texto(img, descr[b.valor], (x + bw // 2, y + bh - 12), 0.5, CINZA, 1, centro=True)
    cor = BRANCO if jogo.tem_mao else VERMELHO
    texto(img, jogo.mensagem, (w // 2, int(h * 0.78)), 0.8, cor, 2, centro=True)
    texto(img, f"Primeiro a 3 vitorias  |  recorde: {jogo.recorde_pontos} pts",
          (w // 2, int(h * 0.85)), 0.6, CINZA, 1, centro=True)
    if jogo.aviso and agora < jogo.aviso_ate:
        painel(img, 0, int(h * 0.33), w, 40, 0.6, (0, 0, 90))
        texto(img, jogo.aviso, (w // 2, int(h * 0.33) + 28), 0.7, BRANCO, 2, centro=True)


def _hud(img, jogo):
    h, w = img.shape[:2]
    painel(img, 0, 0, w, 64, 0.6)
    p = jogo.placar
    texto(img, f"VOCE {p['jogador']}  x  {p['computador']} PC", (14, 42), 1.0, BRANCO, 2)
    texto(img, f"empates {p['empates']}", (330, 42), 0.6, CINZA, 1)
    texto(img, f"{jogo.pontos} pts", (w - 170, 30), 0.8, AMARELO, 2)
    texto(img, f"modo {jogo.modo}", (w - 170, 54), 0.5, CINZA, 1)
    if jogo.sequencia >= 2:
        texto(img, f"SEQUENCIA x{jogo.sequencia}!", (w // 2 + 40, 42), 0.75, LARANJA, 2)
    # ultimas jogadas (historico)
    for i, (ju, jp, res) in enumerate(jogo.historico[-6:]):
        x = 20 + i * 52
        cv2.circle(img, (x, 84), 9, COR_RESULTADO[res], -1, cv2.LINE_AA)
        abrev = {PEDRA: "PD", PAPEL: "PP", TESOURA: "TS"}[ju]
        texto(img, abrev, (x, 108), 0.45, BRANCO, 1, centro=True)


def _tela_contagem(img, jogo, agora):
    h, w = img.shape[:2]
    if jogo.pausado:
        painel(img, 0, h // 2 - 60, w, 110, 0.65, (0, 0, 100))
        texto(img, "PAUSADO", (w // 2, h // 2 - 5), 1.4, BRANCO, 3, centro=True)
        texto(img, "mostre a mao para recomecar a contagem", (w // 2, h // 2 + 35), 0.7, BRANCO, 1, centro=True)
        return
    frac = jogo.progresso_contagem(agora)
    palavras = ["PEDRA...", "PAPEL...", "TESOURA..."]
    i = min(int(frac * 3), 2)
    texto(img, palavras[i], (w // 2, h // 2), 2.0, AMARELO, 4, centro=True)
    texto(img, f"Rodada {jogo.rodada + 1}", (w // 2, h // 2 - 80), 0.8, BRANCO, 2, centro=True)
    barra(img, w // 4, h // 2 + 30, w // 2, 14, frac, AMARELO)


def _tela_leitura(img, jogo, agora, gesto_inst, conf):
    h, w = img.shape[:2]
    texto(img, "JA!", (w // 2, int(h * 0.35)), 2.6, VERDE, 5, centro=True)
    # o que o sistema esta vendo + confianca do estabilizador
    painel(img, w // 2 - 170, int(h * 0.45), 340, 90, 0.6)
    texto(img, f"lendo: {gesto_inst}", (w // 2, int(h * 0.45) + 35), 0.85, BRANCO, 2, centro=True)
    barra(img, w // 2 - 140, int(h * 0.45) + 52, 280, 14, conf, VERDE)
    # tempo restante
    barra(img, w // 4, h - 60, w // 2, 8, 1 - jogo.progresso_leitura(agora), VERMELHO)
    if not jogo.tem_mao:
        texto(img, "Mao nao detectada!", (w // 2, int(h * 0.72)), 0.9, VERMELHO, 2, centro=True)


def _tela_resultado(img, jogo):
    h, w = img.shape[:2]
    cor = COR_RESULTADO[jogo.resultado]
    painel(img, 0, int(h * 0.22), w, int(h * 0.55), 0.6)
    texto(img, "VOCE", (w // 4, int(h * 0.30)), 0.8, BRANCO, 2, centro=True)
    texto(img, "COMPUTADOR", (3 * w // 4, int(h * 0.30)), 0.8, BRANCO, 2, centro=True)
    icone(img, jogo.jogada_usuario, (w // 4, int(h * 0.47)), 55)
    icone(img, jogo.jogada_pc, (3 * w // 4, int(h * 0.47)), 55)
    texto(img, jogo.jogada_usuario, (w // 4, int(h * 0.64)), 0.8, BRANCO, 2, centro=True)
    texto(img, jogo.jogada_pc, (3 * w // 4, int(h * 0.64)), 0.8, BRANCO, 2, centro=True)
    texto(img, jogo.resultado, (w // 2, int(h * 0.73)), 1.5, cor, 3, centro=True)
    if jogo.adversario.previsao:
        texto(img, f"(o PC previu que voce jogaria {jogo.adversario.previsao})",
              (w // 2, int(h * 0.80)), 0.55, CINZA, 1, centro=True)


def _tela_fim(img, jogo):
    h, w = img.shape[:2]
    painel(img, 0, 0, w, h, 0.65)
    venceu = jogo.placar["jogador"] > jogo.placar["computador"]
    texto(img, jogo.vencedor_partida(), (w // 2, int(h * 0.30)), 1.5, VERDE if venceu else VERMELHO, 3, centro=True)
    p = jogo.placar
    linhas = [
        f"Placar final: {p['jogador']} x {p['computador']}  ({p['empates']} empates)",
        f"Pontos: {jogo.pontos}    Melhor sequencia: {jogo.melhor_sequencia}",
        f"Recorde da sessao: {jogo.recorde_pontos} pts",
    ]
    for i, s in enumerate(linhas):
        texto(img, s, (w // 2, int(h * 0.45) + i * 40), 0.75, BRANCO, 2, centro=True)
    texto(img, "Faca a PINCA para voltar ao menu", (w // 2, int(h * 0.78)), 0.8, AMARELO, 2, centro=True)
