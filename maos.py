"""
maos.py - Captura e rastreamento da mao (camada de visao computacional).

Usa o Hand Landmarker da API Tasks do MediaPipe em modo VIDEO.
O modelo hand_landmarker.task e baixado automaticamente na primeira execucao
(fonte: https://storage.googleapis.com/mediapipe-models/, Google / MediaPipe).

Este modulo NAO conhece as regras do jogo: ele so entrega os 21 pontos da mao
(em pixels), suavizados ao longo do tempo, ou None quando nenhuma mao e vista.
"""
import os
import time
import urllib.request

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

MODELO_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/latest/hand_landmarker.task"
)
PASTA = os.path.dirname(os.path.abspath(__file__))
MODELO_CAMINHO = os.path.join(PASTA, "modelos", "hand_landmarker.task")

# Ligacoes entre os 21 pontos (para desenhar o esqueleto da mao)
CONEXOES = [
    (0, 1), (1, 2), (2, 3), (3, 4),          # polegar
    (0, 5), (5, 6), (6, 7), (7, 8),          # indicador
    (5, 9), (9, 10), (10, 11), (11, 12),     # medio
    (9, 13), (13, 14), (14, 15), (15, 16),   # anelar
    (13, 17), (17, 18), (18, 19), (19, 20),  # minimo
    (0, 17),
]


def garantir_modelo():
    """Baixa o modelo se ainda nao existir na pasta do projeto."""
    if os.path.exists(MODELO_CAMINHO):
        return MODELO_CAMINHO
    os.makedirs(os.path.dirname(MODELO_CAMINHO), exist_ok=True)
    print("Baixando hand_landmarker.task (somente na primeira execucao)...")
    urllib.request.urlretrieve(MODELO_URL, MODELO_CAMINHO)
    return MODELO_CAMINHO


class RastreadorMao:
    """Detecta uma mao por quadro e devolve seus landmarks em pixels."""

    def __init__(self, suavizacao=0.5, confianca=0.6):
        opcoes = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=garantir_modelo()),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=confianca,
            min_hand_presence_confidence=confianca,
            min_tracking_confidence=0.5,
        )
        self.detector = vision.HandLandmarker.create_from_options(opcoes)
        self.alpha = suavizacao      # 0 = sem suavizacao, perto de 1 = muito suave
        self.anterior = None         # landmarks suavizados do quadro anterior
        self.lateralidade = None     # "Left" / "Right" segundo o MediaPipe
        self.t0 = time.monotonic()
        self.ultimo_ts = -1

    def processar(self, frame_bgr):
        """Retorna np.array (21, 3) com (x_px, y_px, z) ou None se nao ha mao."""
        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        imagem = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        # O modo VIDEO exige timestamps estritamente crescentes (ms)
        ts = int((time.monotonic() - self.t0) * 1000)
        if ts <= self.ultimo_ts:
            ts = self.ultimo_ts + 1
        self.ultimo_ts = ts

        resultado = self.detector.detect_for_video(imagem, ts)
        if not resultado.hand_landmarks:
            self.anterior = None
            self.lateralidade = None
            return None

        pts = np.array(
            [(p.x * w, p.y * h, p.z * w) for p in resultado.hand_landmarks[0]],
            dtype=np.float32,
        )
        if resultado.handedness:
            self.lateralidade = resultado.handedness[0][0].category_name

        # Media movel exponencial: reduz tremidas sem atrasar muito
        if self.anterior is not None:
            pts = self.alpha * self.anterior + (1 - self.alpha) * pts
        self.anterior = pts
        return pts

    def fechar(self):
        self.detector.close()
