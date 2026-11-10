"""
logica.py - Regras do jogo Pedra, Papel e Tesoura (maquina de estados).

Estados:
  MENU      -> o jogador aponta o indicador para um botao e faz a pinca para escolher
               o adversario (FACIL = aleatorio, ESPERTO = aprende com o historico).
  CONTAGEM  -> "PEDRA... PAPEL... TESOURA... JA!". Se a mao some, a contagem PAUSA
               e recomeca do inicio quando a mao volta (evita jogar "atrasado").
  LEITURA   -> janela curta para o gesto ficar estavel por varios quadros.
               O computador ja escolheu sua jogada ANTES desta fase (jogo justo).
  RESULTADO -> mostra quem venceu a rodada e atualiza placar, sequencia e pontos.
  FIM       -> partida encerrada (primeiro a VITORIAS_PARA_VENCER). Pinca volta ao menu.

Comportamento sem deteccao:
  * MENU/FIM: o cursor some e a tela pede para mostrar a mao.
  * CONTAGEM: pausa e reinicia quando a mao reaparece.
  * LEITURA: se o tempo acabar sem gesto valido a rodada e ANULADA (nao conta ponto);
    apos ANULADAS_MAX anulacoes seguidas a partida volta ao menu.
"""
import random
from collections import Counter, defaultdict

from gestos import INDEFINIDO, JOGADAS, PAPEL, PEDRA, TESOURA

VENCE = {PEDRA: TESOURA, PAPEL: PEDRA, TESOURA: PAPEL}      # chave vence valor
PERDE_PARA = {v: k for k, v in VENCE.items()}               # quem vence cada jogada

TEMPO_CONTAGEM = 3.0
TEMPO_LEITURA = 2.0
TEMPO_RESULTADO = 2.5
TEMPO_ANULADA = 1.8
TOLERANCIA_SEM_MAO = 0.4     # segundos sem mao antes de pausar a contagem
VITORIAS_PARA_VENCER = 3
ANULADAS_MAX = 3

MENU, CONTAGEM, LEITURA, RESULTADO, ANULADA, FIM = (
    "MENU", "CONTAGEM", "LEITURA", "RESULTADO", "ANULADA", "FIM")


class Botao:
    def __init__(self, rotulo, valor, x, y, w, h):
        self.rotulo, self.valor = rotulo, valor
        self.ret = (x, y, w, h)
        self.hover = False

    def contem(self, p):
        if p is None:
            return False
        x, y, w, h = self.ret
        return x <= p[0] <= x + w and y <= p[1] <= y + h


class Adversario:
    """FACIL: jogada aleatoria.
    ESPERTO: modelo de Markov de 1a ordem sobre as jogadas do usuario.
    Conta quantas vezes, depois de jogar X, o usuario jogou Y; preve o Y mais
    provavel e joga o que vence Y. Mantem 20% de aleatoriedade para nao ser obvio."""

    def __init__(self, modo):
        self.modo = modo
        self.transicoes = defaultdict(Counter)
        self.frequencia = Counter()
        self.ultima_do_jogador = None
        self.previsao = None

    def escolher(self):
        self.previsao = None
        if self.modo == "FACIL" or random.random() < 0.2:
            return random.choice(JOGADAS)
        candidatos = self.transicoes.get(self.ultima_do_jogador)
        if not candidatos:
            candidatos = self.frequencia
        if not candidatos:
            return random.choice(JOGADAS)
        self.previsao = candidatos.most_common(1)[0][0]
        return PERDE_PARA[self.previsao]

    def registrar(self, jogada_usuario):
        if self.ultima_do_jogador is not None:
            self.transicoes[self.ultima_do_jogador][jogada_usuario] += 1
        self.frequencia[jogada_usuario] += 1
        self.ultima_do_jogador = jogada_usuario


class Jogo:
    def __init__(self, largura, altura):
        self.largura, self.altura = largura, altura
        bw, bh = int(largura * 0.3), int(altura * 0.16)
        y = int(altura * 0.45)
        self.botoes = [
            Botao("FACIL", "FACIL", int(largura * 0.14), y, bw, bh),
            Botao("ESPERTO", "ESPERTO", int(largura * 0.56), y, bw, bh),
        ]
        self.recorde_pontos = 0
        self.ir_para_menu()

    # ------------------------------------------------------------------ estados
    def ir_para_menu(self, aviso="", agora=0.0):
        self.estado = MENU
        self.mensagem = "Aponte para um modo e faca a PINCA"
        self.adversario = None
        self.cursor = None
        self.aviso = aviso                 # mensagem temporaria (ex.: partida interrompida)
        self.aviso_ate = agora + 4.0

    def nova_partida(self, modo, agora):
        self.modo = modo
        self.adversario = Adversario(modo)
        self.placar = {"jogador": 0, "computador": 0, "empates": 0}
        self.rodada = 0
        self.sequencia = 0
        self.melhor_sequencia = 0
        self.pontos = 0
        self.anuladas_seguidas = 0
        self.historico = []          # lista de (jogador, computador, resultado)
        self.iniciar_contagem(agora)

    def iniciar_contagem(self, agora):
        self.estado = CONTAGEM
        self.rodada_inicio = agora
        self.pausado = False
        self.sem_mao_desde = None
        self.jogada_usuario = None
        self.jogada_pc = None
        self.resultado = None
        self.mensagem = ""

    def _entrar(self, estado, agora):
        self.estado = estado
        self.t_estado = agora

    # ------------------------------------------------------------------ passo
    def atualizar(self, agora, tem_mao, cursor, pinca, gesto_estavel):
        """Avanca a maquina de estados. Chamado uma vez por quadro.
        tem_mao: bool | cursor: (x,y) da ponta do indicador ou None
        pinca: True no quadro em que a pinca comecou | gesto_estavel: jogada confirmada"""
        self.cursor = cursor
        self.tem_mao = tem_mao

        if self.estado == MENU:
            for b in self.botoes:
                b.hover = b.contem(cursor)
                if b.hover and pinca:
                    self.nova_partida(b.valor, agora)
                    return "inicio"
            self.mensagem = ("Aponte para um modo e faca a PINCA" if tem_mao
                             else "Mostre a mao para a camera")

        elif self.estado == CONTAGEM:
            self._passo_contagem(agora, tem_mao)

        elif self.estado == LEITURA:
            if gesto_estavel != INDEFINIDO:
                self._decidir(gesto_estavel, agora)
                return "resultado"
            if agora - self.t_estado > TEMPO_LEITURA:
                self.anuladas_seguidas += 1
                self.mensagem = ("Mao nao detectada - rodada anulada" if not tem_mao
                                 else "Gesto nao reconhecido - rodada anulada")
                self._entrar(ANULADA, agora)
                return "anulada"

        elif self.estado == ANULADA:
            if agora - self.t_estado > TEMPO_ANULADA:
                if self.anuladas_seguidas >= ANULADAS_MAX:
                    self.ir_para_menu("Partida interrompida: muitas rodadas sem gesto", agora)
                else:
                    self.iniciar_contagem(agora)

        elif self.estado == RESULTADO:
            if agora - self.t_estado > TEMPO_RESULTADO:
                p = self.placar
                if max(p["jogador"], p["computador"]) >= VITORIAS_PARA_VENCER:
                    self.recorde_pontos = max(self.recorde_pontos, self.pontos)
                    self._entrar(FIM, agora)
                    return "fim"
                self.iniciar_contagem(agora)

        elif self.estado == FIM:
            if pinca:
                self.ir_para_menu()
        return None

    def _passo_contagem(self, agora, tem_mao):
        if not tem_mao:
            if self.sem_mao_desde is None:
                self.sem_mao_desde = agora
            if agora - self.sem_mao_desde > TOLERANCIA_SEM_MAO:
                self.pausado = True
                self.mensagem = "PAUSADO - mostre a mao para continuar"
            return
        self.sem_mao_desde = None
        if self.pausado:
            # a mao voltou: recomeca a contagem inteira
            self.pausado = False
            self.mensagem = ""
            self.rodada_inicio = agora
            return
        if agora - self.rodada_inicio >= TEMPO_CONTAGEM:
            self.jogada_pc = self.adversario.escolher()   # escolhe antes de ver o usuario
            self._entrar(LEITURA, agora)

    def _decidir(self, jogada, agora):
        self.rodada += 1
        self.anuladas_seguidas = 0
        self.jogada_usuario = jogada
        pc = self.jogada_pc
        if jogada == pc:
            self.resultado = "EMPATE"
            self.placar["empates"] += 1
            self.sequencia = 0
        elif VENCE[jogada] == pc:
            self.resultado = "VITORIA"
            self.placar["jogador"] += 1
            self.sequencia += 1
            self.melhor_sequencia = max(self.melhor_sequencia, self.sequencia)
            # bonus por sequencia de vitorias e por vencer o adversario esperto
            base = 150 if self.modo == "ESPERTO" else 100
            self.pontos += base * self.sequencia
        else:
            self.resultado = "DERROTA"
            self.placar["computador"] += 1
            self.sequencia = 0
        self.adversario.registrar(jogada)
        self.historico.append((jogada, pc, self.resultado))
        self._entrar(RESULTADO, agora)

    # ------------------------------------------------------------------ consultas
    def progresso_contagem(self, agora):
        """0..1 da contagem atual (para a barra e o texto PEDRA/PAPEL/TESOURA)."""
        if self.estado != CONTAGEM or self.pausado:
            return 0.0
        return min((agora - self.rodada_inicio) / TEMPO_CONTAGEM, 1.0)

    def progresso_leitura(self, agora):
        if self.estado != LEITURA:
            return 0.0
        return min((agora - self.t_estado) / TEMPO_LEITURA, 1.0)

    def vencedor_partida(self):
        p = self.placar
        return "VOCE VENCEU!" if p["jogador"] > p["computador"] else "O COMPUTADOR VENCEU"
