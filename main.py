"""
Pedra, Papel e Tesoura com Visao Computacional - Trabalho C2
Visao Computacional - FAESA - 2026/2

Equipe:
    Juliano Dantas
    Cauan Henrique Damacena

Como executar (na pasta do projeto):
    pip install -r requirements.txt
    python main.py                 # webcam padrao (indice 0)
    python main.py --camera 1      # outra webcam
    python main.py --video arquivo.mp4

Controles:
    Mao  : aponte o indicador para um botao e faca a PINCA (polegar + indicador)
    Jogo : apos "PEDRA... PAPEL... TESOURA...", mostre o gesto quando aparecer "JA!"
    Teclado: [Q]/[ESC] sair, [M] voltar ao menu, [1]/[2] escolher modo sem a mao

Organizacao:
    maos.py   -> captura e rastreamento da mao (MediaPipe Tasks)
    gestos.py -> regras de interacao (gesto, pinca, estabilidade)
    logica.py -> maquina de estados do jogo, placar e adversario
    visual.py -> desenho da tela
"""
import argparse
import time

import cv2

from gestos import DetectorPinca, EstabilizadorGesto, classificar
from logica import LEITURA, Jogo
from maos import RastreadorMao
from visual import desenhar

LARGURA, ALTURA = 960, 720


def main():
    ap = argparse.ArgumentParser(description="Pedra, Papel e Tesoura com MediaPipe")
    ap.add_argument("--camera", type=int, default=0, help="indice da webcam")
    ap.add_argument("--video", type=str, default=None, help="usar um arquivo de video")
    args = ap.parse_args()

    fonte = args.video if args.video else args.camera
    cap = cv2.VideoCapture(fonte)
    if not cap.isOpened():
        raise SystemExit(f"Nao foi possivel abrir a fonte de video: {fonte}")
    espelhar = args.video is None   # espelha a webcam para o movimento parecer natural

    rastreador = RastreadorMao()
    pinca = DetectorPinca()
    estabilizador = EstabilizadorGesto()
    jogo = Jogo(LARGURA, ALTURA)

    estado_anterior = None
    t_ant, fps = time.monotonic(), 0.0
    janela = "Pedra Papel Tesoura - C2"
    cv2.namedWindow(janela, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(janela, LARGURA, ALTURA)

    while True:
        ok, frame = cap.read()
        if not ok:
            if args.video:              # video terminou: recomeca do inicio
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            break
        if espelhar:
            frame = cv2.flip(frame, 1)
        frame = cv2.resize(frame, (LARGURA, ALTURA))
        agora = time.monotonic()

        # 1) visao: landmarks da mao (ou None)
        pts = rastreador.processar(frame)

        # 2) interpretacao: gesto instantaneo, pinca e estabilidade
        gesto = classificar(pts)
        evento_pinca = pinca.atualizar(pts)
        if jogo.estado == LEITURA:
            estabilizador.adicionar(gesto)
        gesto_estavel, confianca = estabilizador.estavel()
        cursor = tuple(pts[8][:2]) if pts is not None else None

        # 3) regras do jogo
        jogo.atualizar(agora, pts is not None, cursor, evento_pinca,
                       gesto_estavel if jogo.estado == LEITURA else "?")
        if jogo.estado != estado_anterior:
            estabilizador.limpar()      # cada fase comeca com o historico de gestos zerado
            estado_anterior = jogo.estado

        # 4) desenho
        dt = agora - t_ant
        t_ant = agora
        if dt > 0:
            fps = 0.9 * fps + 0.1 * (1.0 / dt)
        desenhar(frame, jogo, agora, pts, gesto, confianca, pinca.ativa, fps)
        cv2.imshow(janela, frame)

        tecla = cv2.waitKey(1) & 0xFF
        if tecla in (ord("q"), 27):
            break
        if tecla == ord("m"):
            jogo.ir_para_menu()
        if tecla in (ord("1"), ord("2")) and jogo.estado == "MENU":
            jogo.nova_partida("FACIL" if tecla == ord("1") else "ESPERTO", agora)
        if cv2.getWindowProperty(janela, cv2.WND_PROP_VISIBLE) < 1:
            break

    rastreador.fechar()
    cap.release()
    cv2.destroyAllWindows()



if __name__ == "__main__":
    main()
