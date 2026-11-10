# Pedra, Papel e Tesoura com Visão Computacional — C2

**Equipe:** Juliano Dantas e Cauan Henrique Damacena

Jogo contra o computador controlado só pela mão, usando o **Hand Landmarker** do MediaPipe (API Tasks).

## Vídeo de demonstração
[video/demonstracao.mp4](video/demonstracao.mp4)

## Como executar
```
pip install -r requirements.txt
python main.py                 # webcam
python main.py --video x.mp4   # arquivo de vídeo
```
O modelo `hand_landmarker.task` é baixado automaticamente para `modelos/` na primeira execução.

## Como jogar
1. No menu, aponte o indicador para **FACIL** ou **ESPERTO** e faça a **pinça** (polegar + indicador).
2. Durante "PEDRA... PAPEL... TESOURA..." mantenha a mão visível.
3. Em **"JA!"**, mostre o gesto. Ele precisa ficar estável por alguns quadros.
4. Vence a partida quem chegar primeiro a 3 vitórias. A pinça volta ao menu.

Teclado: `Q`/`ESC` sai, `M` volta ao menu, `1`/`2` escolhem o modo.

## O que foi implementado (requisitos da C2)
| Requisito | Implementação |
|---|---|
| Regra de interação | Classificação do gesto pela razão das distâncias ponta→pulso / PIP→pulso de cada dedo (`gestos.py`); pinça com histerese; menu acionado por apontar + pinça |
| Estado ao longo do tempo | Máquina de estados MENU → CONTAGEM → LEITURA → RESULTADO/ANULADA → FIM; placar, pontos com bônus por sequência, recorde da sessão, histórico de jogadas |
| Resposta visual | Esqueleto da mão colorido pelo gesto, cursor que se preenche na pinça, "lendo: X" com barra de confiança, ícones das jogadas, barras de tempo |
| Sem detecção | Menu pede a mão; a contagem **pausa** e recomeça do zero; na leitura, a rodada é **anulada**; 3 anulações seguidas encerram a partida |

**Adversário ESPERTO:** usa uma cadeia de Markov de 1ª ordem sobre as jogadas do usuário (o que ele costuma jogar depois de cada jogada), prevê a próxima e joga o que a vence, com 20% de aleatoriedade.

## Organização
- `maos.py`: captura e rastreamento (MediaPipe), suavização dos pontos
- `gestos.py`: regras de interpretação dos landmarks
- `logica.py`: regras do jogo e adversário
- `visual.py`: desenho da tela
- `main.py`: laço principal

Créditos: modelo Hand Landmarker © Google / MediaPipe (Apache 2.0). Ícones desenhados com OpenCV, sem imagens de terceiros.
