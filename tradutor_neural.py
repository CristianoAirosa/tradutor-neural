import threading, sys, time, json, os
import tkinter as tk
import tkinter.messagebox as messagebox
import requests
from collections import deque
from tkinter import font as tkfont
from PIL import Image, ImageTk   # pip install Pillow

import cv2
import mediapipe as mp
import numpy as np
import pyttsx3

if not hasattr(mp, "solutions"):
    raise RuntimeError(
        "mediapipe nao encontrado ou versao incorrecta.\n"
        "Execute:  pip uninstall mediapipe -y  &&  pip install mediapipe==0.10.11\n"
    )


CONFIG_FILE    = "neural_config.json"
_DEFAULT_TOKEN = "8627477750:AAE384nb4nMBR7lxc26HNHsi94COiEWNVmU"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                cfg = json.load(f)
            if not cfg.get("telegram_token"):
                cfg["telegram_token"] = _DEFAULT_TOKEN
            return cfg
        except Exception:
            pass
    return {
        "telegram_token":   _DEFAULT_TOKEN,
        "telegram_chat_id": "8474897915",
        "scan_speed":       1100,
        "ear_threshold":    0.21,
    }

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


C = {
    "bg":          "#12213a",   # fundo geral — navy medio
    "panel":       "#1b2f52",   # paineis / cabeçalho / rodape
    "panel2":      "#243a63",   # hover de paineis
    "key":         "#1e3a6e",   # tecla normal
    "key_hi":      "#2a4f90",   # tecla activa / hover
    "row_scan":    "#2a5a9a",   # linha em varrimento
    "col_scan":    "#00d4ff",   # coluna seleccionada  (ciano)
    "group_scan":  "#ffb300",   # grupo em varrimento  (ambar)
    "accent":      "#00d4ff",   # ciano brilhante
    "accent2":     "#009bcc",
    "green":       "#2ecc71",
    "yellow":      "#f4c542",
    "orange":      "#ff8c00",
    "red":         "#e74c3c",
    "red_dark":    "#3d1010",
    "purple":      "#c084ff",
    "purple_dark": "#231050",
    "text":        "#eaf2ff",   # texto principal
    "text_mid":    "#90b4d8",   # texto secundario
    "text_dim":    "#4a6a8a",   # texto terciario
    "border":      "#2a4070",
    # Necessidades
    "need_agua":   ("#163a70", "#5bc8f5"),
    "need_comida": ("#4a2208", "#ff9040"),
    "need_wc":     ("#0e3820", "#2ecc71"),
    "need_dor":    ("#4a1212", "#ff6b6b"),
    "need_sos":    ("#5a0808", "#ff2020"),
    "need_remedio":("#2a1050", "#c084ff"),
}


class TelegramSetupWindow:
    def __init__(self, parent, config, on_save):
        self.parent  = parent
        self.config  = config
        self.on_save = on_save

        self.win = tk.Toplevel(parent)
        self.win.title("Configuracao Telegram — @CO_ocularbot")
        self.win.configure(bg=C["bg"])
        self.win.geometry("620x400")
        self.win.resizable(False, False)
        self.win.grab_set()
        self.win.focus_set()

        self.win.update_idletasks()
        px = max(0, parent.winfo_x() + parent.winfo_width()  // 2 - 310)
        py = max(0, parent.winfo_y() + parent.winfo_height() // 2 - 200)
        self.win.geometry(f"620x400+{px}+{py}")
        self._build()

    def _build(self):
        mono = "Courier New"
        fT = tkfont.Font(family=mono, size=14, weight="bold")
        fS = tkfont.Font(family=mono, size=9)
        fL = tkfont.Font(family=mono, size=11)
        fE = tkfont.Font(family=mono, size=13)
        fB = tkfont.Font(family=mono, size=11, weight="bold")

        hdr = tk.Frame(self.win, bg=C["panel"], pady=16)
        hdr.pack(fill="x")
        tk.Label(hdr, text="NOTIFICACOES TELEGRAM", font=fT,
                 fg=C["accent"], bg=C["panel"]).pack()
        tk.Label(hdr, text="Bot activo: @CO_ocularbot  —  token pre-configurado",
                 font=fS, fg=C["green"], bg=C["panel"]).pack(pady=(2,0))
        tk.Frame(self.win, height=2, bg=C["accent"]).pack(fill="x")

        body = tk.Frame(self.win, bg=C["bg"], padx=48, pady=20)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="Para receber alertas, o cuidador precisa de fazer 3 passos:",
                 font=fS, fg=C["text_mid"], bg=C["bg"], anchor="w").pack(fill="x")
        for s in [
            "1.  Abrir o Telegram e pesquisar  @CO_ocularbot",
            "2.  Enviar qualquer mensagem ao bot  (ex: ola)",
            "3.  Clicar em DETECTAR abaixo — o ID e preenchido automaticamente",
        ]:
            tk.Label(body, text=s, font=fS, fg=C["text"],
                     bg=C["bg"], anchor="w").pack(fill="x", pady=2)

        tk.Frame(body, height=1, bg=C["border"]).pack(fill="x", pady=12)

        row = tk.Frame(body, bg=C["bg"])
        row.pack(fill="x")
        tk.Label(row, text="CHAT ID DO CUIDADOR", font=fL,
                 fg=C["text_mid"], bg=C["bg"]).pack(side="left")
        self.status = tk.Label(row, text="", font=fS, fg=C["green"], bg=C["bg"])
        self.status.pack(side="right")

        self.chatid_var = tk.StringVar(value=self.config.get("telegram_chat_id", ""))
        tk.Entry(body, textvariable=self.chatid_var, font=fE,
                 bg=C["panel"], fg=C["accent"], insertbackground=C["accent"],
                 relief="flat", bd=0, highlightthickness=1,
                 highlightbackground=C["border"],
                 highlightcolor=C["accent"]).pack(fill="x", ipady=9, pady=(6,10))

        tk.Button(body, text="DETECTAR CHAT ID AUTOMATICAMENTE",
                  font=fB, bg=C["panel"], fg=C["accent"],
                  activebackground=C["panel2"], relief="flat", bd=0,
                  cursor="hand2", command=self._detect).pack(fill="x", ipady=6)

        tk.Frame(self.win, height=1, bg=C["border"]).pack(fill="x")
        foot = tk.Frame(self.win, bg=C["panel"], pady=12)
        foot.pack(fill="x", padx=40)

        tk.Button(foot, text="TESTAR", font=fB, width=12,
                  bg="#2a2008", fg=C["yellow"], activebackground="#3a3010",
                  relief="flat", bd=0, cursor="hand2",
                  command=self._test).pack(side="left", ipady=6)
        tk.Button(foot, text="CANCELAR", font=fB, width=12,
                  bg=C["red_dark"], fg="#f87171", activebackground="#4a1818",
                  relief="flat", bd=0, cursor="hand2",
                  command=self.win.destroy).pack(side="right", padx=(8,0), ipady=6)
        tk.Button(foot, text="GUARDAR", font=fB, width=12,
                  bg=C["accent"], fg=C["bg"], activebackground=C["accent2"],
                  relief="flat", bd=0, cursor="hand2",
                  command=self._save).pack(side="right", ipady=6)

    def _detect(self):
        self.status.config(text="A detectar...", fg=C["yellow"])
        def go():
            try:
                r = requests.get(
                    f"https://api.telegram.org/bot{_DEFAULT_TOKEN}/getUpdates",
                    timeout=8)
                d = r.json()
                if d.get("ok") and d.get("result"):
                    cid = str(d["result"][-1]["message"]["from"]["id"])
                    self.chatid_var.set(cid)
                    self.win.after(0, lambda: self.status.config(
                        text=f"ID detectado: {cid}", fg=C["green"]))
                else:
                    self.win.after(0, lambda: self.status.config(
                        text="Sem mensagens — envie uma msg ao bot primeiro",
                        fg=C["red"]))
            except Exception as e:
                self.win.after(0, lambda: self.status.config(
                    text=f"Erro: {e}", fg=C["red"]))
        threading.Thread(target=go, daemon=True).start()

    def _test(self):
        cid = self.chatid_var.get().strip()
        if not cid:
            self.status.config(text="Detecte ou insira o Chat ID primeiro", fg=C["red"])
            return
        self.status.config(text="A enviar mensagem de teste...", fg=C["yellow"])
        def go():
            try:
                r = requests.post(
                    f"https://api.telegram.org/bot{_DEFAULT_TOKEN}/sendMessage",
                    data={"chat_id": cid,
                          "text": "Tradutor Neural — ligacao testada! (@CO_ocularbot)"},
                    timeout=8)
                ok = r.status_code == 200
                self.win.after(0, lambda: self.status.config(
                    text="Mensagem enviada!" if ok else f"Erro {r.status_code}",
                    fg=C["green"] if ok else C["red"]))
            except Exception as e:
                self.win.after(0, lambda: self.status.config(
                    text=f"Erro: {e}", fg=C["red"]))
        threading.Thread(target=go, daemon=True).start()

    def _save(self):
        self.config["telegram_chat_id"] = self.chatid_var.get().strip()
        self.config["telegram_token"]   = _DEFAULT_TOKEN
        save_config(self.config)
        self.on_save()
        self.win.destroy()



class BlinkKeyboard:

    def __init__(self):
        self.config = load_config()

        self.root = tk.Tk()
        self.root.title("TRADUTOR NEURAL — Comunicacao Ocular")
        self.root.configure(bg=C["bg"])
        self.root.attributes("-fullscreen", True)

        # Texto
        self.typed_text = ""

        # Varredura
        self.scan_speed    = self.config.get("scan_speed", 1100)
        self.scanning      = True
        self.running       = True
        self.scan_level    = "row"   # "row" | "group" | "col"
        self.current_row   = 0
        self.current_group = 0
        self.current_col   = 0

        # Piscadas
        self.ear_threshold       = self.config.get("ear_threshold", 0.21)
        self.eye_closed_start    = None
        self.long_blink_duration = 0.65
        self.last_blink_time     = 0
        self.blink_cooldown      = 0.45
        self.ear_history         = deque(maxlen=5)
        self.calibrating         = False
        self.calibration_values  = []

        # MediaPipe
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1, refine_landmarks=True,
            min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.LEFT_EYE  = [362, 385, 387, 263, 373, 380]
        self.RIGHT_EYE = [33,  160, 158, 133, 153, 144]

        # Camera
        self.cap       = None
        self.cam_photo = None

        # Dicionario
        self.dicionario = {
            "ABR":["ABRIR","ABRACO","ABRIGO","ABRIL"],
            "ACA":["ACAR","ACAI","ACO","ACAO"],
            "AGU":["AGUA","AGUARDAR","AGULHA","AGUDO"],
            "AJA":["AJUDAR","AJUSTE","AJUDA"],
            "ALC":["ALCANCAR","ALCOOL","ALCANCE"],
            "ALI":["ALIMENTO","ALINHAR","ALIADO","ALIVIO"],
            "ALT":["ALTO","ALTURA","ALTERAR","ALTERNATIVA"],
            "ALU":["ALUNO","ALUGAR","ALUNA"],
            "AMO":["AMOR","AMIGO","AMOSTRA","AMANHA"],
            "AND":["ANDAR","ANDAMENTO"],
            "ANI":["ANIMAL","ANIMACAO","ANIVERSARIO"],
            "ANO":["ANO","ANOTACAO"],
            "ANT":["ANTES","ANTIGO","ANTECIPAR"],
            "APR":["APRENDER","APRESENTAR","APROVAR","APROVEITAR"],
            "AQU":["AQUI","AQUECER","AQUARIO"],
            "ART":["ARTE","ARTIGO","ARTISTA"],
            "ARV":["ARVORE"],
            "ASS":["ASSUNTO","ASSISTIR","ASSIM"],
            "BAN":["BANCO","BANANA","BANDEIRA","BANHO"],
            "BAR":["BARATO","BARULHO"],
            "BAT":["BATER","BATATA","BATALHA"],
            "BEL":["BELO","BELEZA"],
            "BOM":["BOM","BOMBA","BOM DIA"],
            "BOR":["BORBOLETA","BORRACHA"],
            "BRA":["BRASIL","BRANCO","BRACO","BRASILEIRO"],
            "BRI":["BRILHO","BRINCAR","BRINQUEDO"],
            "BUS":["BUSCAR","BUSCA"],
            "CAB":["CABO","CABELO","CABECA"],
            "CAF":["CAFE","CAFETEIRA"],
            "CAL":["CALOR","CALCA","CALMA","CALCULAR"],
            "CAM":["CAMINHO","CAMA","CAMISA","CAMPANHA"],
            "CAN":["CANETA","CANSADO","CANTAR","CANCELAR"],
            "CAP":["CAPACIDADE","CAPITAO","CAPACETE"],
            "CAR":["CARRO","CARTAO","CARNE","CARTA","CARNAVAL"],
            "CAS":["CASA","CASAR","CASACO","CASAMENTO"],
            "CEL":["CELULAR","CELESTE"],
            "CEN":["CENOURA","CENTRO","CENARIO"],
            "CER":["CERTEZA","CERTO","CEREBRO"],
            "CHA":["CHA","CHAVE","CHAMAR","CHAPEU"],
            "CHE":["CHEGAR","CHEIO","CHEFE","CHEIRO"],
            "CHO":["CHOVER","CHOCOLATE","CHORAR"],
            "CID":["CIDADE","CIDADAO"],
            "CIN":["CINCO","CINEMA","CINZA"],
            "CLA":["CLARO","CLASSE"],
            "CLI":["CLIENTE","CLIMA","CLIQUE"],
            "COL":["COLEGA","COLORIDO","COLETIVO"],
            "COM":["COMER","COMPUTADOR","COMIDA","COMISSAO"],
            "CON":["CONTROLE","CONHECER","CONTA","CONSERTAR"],
            "COR":["CORAGEM","CORPO","CORRER","CORDA","CORACAO"],
            "DAN":["DANCAR","DANCA"],
            "DAT":["DATA"],
            "DEZ":["DEZ","DEZEMBRO"],
            "DIA":["DIA","DIARIO","DIAMANTE"],
            "DIN":["DINHEIRO","DINAMICO"],
            "DIR":["DIREITO","DIRETOR","DIRIGIR"],
            "DOR":["DOR","DORMIR"],
            "ECO":["ECONOMIA","ECOLOGICO"],
            "EDI":["EDUCACAO","EDIFICIO"],
            "ELE":["ELE","ELETRICIDADE","ELEFANTE"],
            "EMA":["EMAIL"],
            "EMO":["EMOCAO","EMOCIONAL"],
            "EMP":["EMPRESA","EMPREGO","EMPATIA"],
            "ENC":["ENCONTRAR","ENCHER"],
            "ENE":["ENERGIA"],
            "ENG":["ENGENHEIRO","ENGENHARIA"],
            "ENT":["ENTRAR","ENTENDER","ENTREGA"],
            "EQU":["EQUIPE","EQUILIBRIO"],
            "ERR":["ERRO","ERRADO"],
            "ESC":["ESCOLA","ESCREVER","ESCOLHA","ESCONDER"],
            "FAL":["FALAR","FALTA","FALSO"],
            "FAM":["FAMILIA","FAMOSO"],
            "FAR":["FAROL","FARMACIA"],
            "FAT":["FATIA","FATO"],
            "FAV":["FAVOR","FAVORITO"],
            "FAZ":["FAZER","FAZENDA"],
            "FEL":["FELIZ","FELICIDADE"],
            "FER":["FERRO","FERIAS","FERRAMENTA"],
            "FES":["FESTA","FESTIVAL"],
            "FIC":["FICAR"],
            "FIL":["FILHO","FILA","FILME"],
            "FIM":["FIM","FINAL","FIM DE SEMANA"],
            "GAL":["GALINHA","GALAXIA"],
            "GAN":["GANHAR"],
            "GAR":["GARFO","GAROTA","GARAGEM","GARANTIR"],
            "GAT":["GATO","GATINHO"],
            "GEL":["GELO","GELADEIRA"],
            "GER":["GERAL","GERENTE"],
            "GIR":["GIRAR","GIRAFA"],
            "GOL":["GOL","GOLFINHO"],
            "GRA":["GRANDE","GRACA","GRADUACAO"],
            "HAB":["HABITAR","HABITO","HABILIDADE"],
            "HIS":["HISTORIA"],
            "HOM":["HOMEM","HOMENAGEM"],
            "HOR":["HORA","HORARIO","HORIZONTE"],
            "HUM":["HUMANO","HUMILDE","HUMOR"],
            "IDE":["IDEIA","IDENTIDADE","IDEAL"],
            "IGR":["IGREJA","IGUAL"],
            "IMA":["IMAGEM","IMAGINACAO"],
            "IMP":["IMPORTANTE","IMPOSSIVEL"],
            "IND":["INDUSTRIA","INDIVIDUO"],
            "INF":["INFORMACAO","INFANCIA"],
            "INI":["INICIO","INIMIGO"],
            "INT":["INTERNET","INTELIGENTE"],
            "INV":["INVENTAR","INVESTIR","INVERNO"],
            "JAN":["JANELA","JANEIRO","JANTAR"],
            "JAR":["JARRA","JARDIM"],
            "JOG":["JOGAR","JOGO","JOGADOR"],
            "JOR":["JORNAL","JORNALISTA"],
            "JUL":["JULHO"],
            "JUN":["JUNHO","JUNTAR"],
            "LAM":["LAMPADA"],
            "LAN":["LANCHE","LANTERNA"],
            "LAR":["LAR","LARANJA","LARGO"],
            "LAZ":["LAZER"],
            "LEG":["LEGAL","LEGUME"],
            "LEI":["LEI","LEITURA","LEITE"],
            "LEM":["LEMBRAR"],
            "LIG":["LIGAR","LIGACAO"],
            "LIM":["LIMPAR","LIMITE","LIMPEZA"],
            "LIN":["LINDO","LINGUA","LINHA"],
            "LIS":["LISTA"],
            "MAC":["MACHADO","MACACO"],
            "MAE":["MAE"],
            "MAI":["MAIS","MAIOR","MAIORIA","MAIO"],
            "MAL":["MAL","MALUCO"],
            "MAN":["MAOS","MANHA","MANTER"],
            "MAP":["MAPA"],
            "MAR":["MAR","MARCO","MARROM","MARGEM"],
            "MAT":["MATEMATICA","MATERIAL"],
            "MEC":["MEDICO","MEDICINA","MEDIDA","MEDO"],
            "MEL":["MEL","MELHOR","MELANCIA"],
            "MEM":["MEMORIA","MEMBRO"],
            "MEN":["MENOS","MENTE","MENOR","MENINO"],
            "MER":["MERCADO"],
            "MES":["MES","MESA","MESMO"],
            "MET":["METADE","METODO"],
            "MEU":["MEU","MEUS"],
            "MIL":["MIL","MILHAO"],
            "MIN":["MINUTO","MINHA"],
            "MIS":["MISTERIO","MISTURAR"],
            "NAC":["NACAO","NACIONAL"],
            "NAD":["NADA","NADAR"],
            "NAS":["NASCER","NASCIMENTO"],
            "NAT":["NATAL","NATUREZA"],
            "NAV":["NAVIO","NAVEGAR"],
            "NEC":["NECESSARIO","NECESSIDADE"],
            "NEG":["NEGOCIO","NEGAR"],
            "NER":["NERVOSO"],
            "OBJ":["OBJETO","OBJETIVO"],
            "OBR":["OBRIGADO","OBRIGACAO"],
            "PAC":["PACIENTE","PACIENCIA"],
            "PAG":["PAGAR","PAGAMENTO"],
            "PAI":["PAI","PAISAGEM"],
            "PAL":["PALAVRA","PALCO"],
            "PAN":["PAO","PANELA"],
            "PAP":["PAPEL","PAPAI"],
            "PAR":["PARAR","PARTE","PARQUE","PARABENS"],
            "PAS":["PASSAR","PASTA","PASSAGEM"],
            "PAZ":["PAZ"],
            "PED":["PEDRA","PEDIR"],
            "PEI":["PEITO","PEIXE"],
            "PEN":["PENSAR","PENDURAR"],
            "PER":["PERGUNTA","PERDER","PERSONAGEM"],
            "PES":["PESSOA","PESO","PESCAR"],
            "PIN":["PINTAR"],
            "PIR":["PIRATA","PIRAMIDE"],
            "PIS":["PISCAR","PISCINA"],
            "PLA":["PLANO","PLACA","PLANETA"],
            "POD":["PODER","PODE","PODERIA"],
            "POL":["POLICIA","POLITICA"],
            "POR":["PORTUGAL","PORTA","PORQUE","POR FAVOR"],
            "POS":["POSITIVO","POSICAO","POSSIVEL"],
            "QUA":["QUAL","QUARTO","QUATRO","QUASE"],
            "QUE":["QUE","QUERER","QUESTAO","QUEIJO"],
            "QUI":["QUINTA","QUIMICA"],
            "RAP":["RAPAZ","RAPIDO"],
            "REA":["REAL","REALIDADE","REACAO"],
            "REC":["RECEITA","RECEBER"],
            "RED":["REDE","REDUZIR"],
            "REG":["REGRA","REGULAR"],
            "REI":["REI","REINO"],
            "REL":["RELACAO","RELOGIO"],
            "REM":["REMEDIO","REMOTO"],
            "RES":["RESPOSTA","RESPEITO","RESTAURANTE"],
            "REU":["REUNIAO","REUNIR"],
            "RIS":["RISCO","RISADA"],
            "ROD":["RODA","RODOVIA"],
            "ROM":["ROMANCE"],
            "ROU":["ROUPA","ROUBAR"],
            "SAB":["SABER","SABOR","SABADO"],
            "SAD":["SAUDADE"],
            "SAL":["SAL","SALADA","SALARIO"],
            "SAN":["SANGUE","SANTO"],
            "SAP":["SAPATO"],
            "SAU":["SAUDE","SAUDAVEL"],
            "SEG":["SEGURO","SEGUNDO","SEGREDO"],
            "SEM":["SEM","SEMANA","SEMELHANTE"],
            "SEN":["SENHOR","SENTIR","SENTIDO"],
            "SER":["SER","SERVICO","SERIO","SERRA"],
            "SIM":["SIM","SIMPLES"],
            "SIS":["SISTEMA"],
            "SIT":["SITUACAO","SITE"],
            "SOC":["SOCIAL","SOCIEDADE","SOCORRO"],
            "TAM":["TAMANHO","TAMBEM"],
            "TAN":["TANTO","TANQUE"],
            "TAR":["TARDE","TAREFA"],
            "TEC":["TECNOLOGIA","TECIDO","TECNICO"],
            "TEL":["TELEFONE","TELEVISAO","TELA"],
            "TEM":["TEMPO","TEMPERO","TEMPERATURA"],
            "TER":["TER","TERRA","TERMINAR","TERCA"],
            "TES":["TESOURA","TESTE"],
            "TEX":["TEXTO"],
            "TIG":["TIGRE"],
            "TIM":["TIME"],
            "TIN":["TINTA"],
            "TIP":["TIPO"],
            "ULT":["ULTIMO"],
            "UNI":["UNIVERSO","UNIVERSIDADE","UNIDO"],
            "USU":["USUARIO","USUAL"],
            "UTI":["UTILIZAR","UTIL"],
            "VAC":["VACA","VACINA"],
            "VAL":["VALOR","VALENTE"],
            "VAM":["VAMOS"],
            "VAZ":["VAZIO","VAZAR"],
            "VEL":["VELOCIDADE"],
            "VEN":["VENDER","VENTO","VENENO"],
            "VER":["VERDADE","VERDE","VERAO"],
            "VES":["VESTIR","VESTIDO"],
            "VIA":["VIAGEM","VIAJAR"],
            "VID":["VIDA","VIDRO","VIDEO"],
            "VIN":["VINHO"],
            "VIR":["VIRAR","VIRTUAL"],
            "VIS":["VISITA","VISAO"],
            "ZER":["ZERO","ZERAR"],
            "ZOO":["ZOOLOGICO"],
        }
        self.sugestoes_atuais = []

       
        self.keys = [
            # 0 — Sugestoes (varredura directa)
            ["", "", "", "", "FALAR"],
            # 1 — Necessidades (varredura directa)
            ["AGUA", "COMIDA", "WC", "DOR", "SOS", "REMEDIO"],
            # 2 — Q-P  (com grupos)
            ["Q","W","E","R","T","Y","U","I","O","P"],
            # 3 — A-L  (com grupos)
            ["A","S","D","F","G","H","J","K","L"],
            # 4 — Z-M  (com grupos)
            ["Z","X","C","V","B","N","M"],
            # 5 — Accoes (varredura directa)
            ["LIMPAR","ESPACO","APAGAR"],
            # 6 — Sim/Nao (varredura directa)
            ["SIM","NAO"],
        ]

        # Grupos por linha de letras
        self.line_groups = {
            2: [[0,1,2,3,4], [5,6,7,8,9]],    # Q W E R T  /  Y U I O P
            3: [[0,1,2,3,4], [5,6,7,8]],       # A S D F G  /  H J K L
            4: [[0,1,2,3],   [4,5,6]],          # Z X C V    /  B N M
        }

        self.all_buttons      = []
        self.button_grid      = []
        self.row_frames       = []
        self.sugestao_buttons = []

        self._setup_ui()
        self._start_camera()
        self._start_scanning()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

   
    def _setup_ui(self):
        mono = "Courier New"
        sans = "Helvetica"
        F = lambda sz, w="normal", fam=mono: tkfont.Font(family=fam, size=sz, weight=w)

        fDisplay = F(26, "bold")
        fStatus  = F(9)
        fKey     = F(18, "bold", sans)
        fAction  = F(12, "bold")
        fSuggest = F(11, "bold")
        fNeed    = F(12, "bold")
        fCtrl    = F(9)
        fCamLbl  = F(8)

        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=0)
        self.root.grid_columnconfigure(0, weight=1)


        top = tk.Frame(self.root, bg=C["panel"])
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(0, weight=1)
        top.grid_columnconfigure(1, weight=0)

        left = tk.Frame(top, bg=C["panel"])
        left.grid(row=0, column=0, sticky="nsew", padx=28, pady=12)

        tk.Label(left, text="MENSAGEM COMPOSTA",
                 font=F(7), fg=C["text_dim"], bg=C["panel"], anchor="w").pack(fill="x")
        self.text_display = tk.Label(
            left, text="_", font=fDisplay,
            fg=C["accent"], bg=C["panel"], anchor="w", wraplength=860)
        self.text_display.pack(fill="x", pady=(2,0))
        self.status_label = tk.Label(
            left, text="A INICIAR CAMERA...",
            font=fStatus, fg=C["yellow"], bg=C["panel"], anchor="w")
        self.status_label.pack(fill="x", pady=(5,0))

        # Camera
        right = tk.Frame(top, bg=C["panel"], padx=14, pady=8)
        right.grid(row=0, column=1, sticky="ns")

        cam_wrap = tk.Frame(right, bg=C["accent"], bd=0)
        cam_wrap.pack()
        self.camera_label = tk.Label(
            cam_wrap, bg="#0a1525", width=26, height=7,
            text="CAMERA A INICIAR", fg=C["text_dim"], font=fCamLbl)
        self.camera_label.pack(padx=2, pady=2)

        ind_row = tk.Frame(right, bg=C["panel"])
        ind_row.pack(fill="x", pady=(5,0))
        tk.Label(ind_row, text="ABERTURA OCULAR:",
                 font=fCamLbl, fg=C["text_dim"], bg=C["panel"]).pack(side="left")
        self.ear_label = tk.Label(ind_row, text="---",
                                  font=F(9,"bold"), fg=C["accent"], bg=C["panel"])
        self.ear_label.pack(side="left", padx=4)

        self.blink_indicator = tk.Label(
            right, text="  ", font=F(8,"bold"),
            fg=C["bg"], bg=C["bg"], width=20, relief="flat")
        self.blink_indicator.pack(pady=(3,0))

        tk.Frame(self.root, height=2, bg=C["accent"]).grid(
            row=0, column=0, sticky="sew")

       
        kb_outer = tk.Frame(self.root, bg=C["bg"])
        kb_outer.grid(row=1, column=0, sticky="nsew")
        kb_outer.grid_rowconfigure(0, weight=1)
        kb_outer.grid_columnconfigure(0, weight=1)

        kb = tk.Frame(kb_outer, bg=C["bg"])
        kb.grid(row=0, column=0)  # centrado

        NEED_MAP = {
            "AGUA":    ("AGUA",          C["need_agua"]),
            "COMIDA":  ("COMIDA",        C["need_comida"]),
            "WC":      ("WC",            C["need_wc"]),
            "DOR":     ("DOR",           C["need_dor"]),
            "SOS":     ("SOS  URGENTE",  C["need_sos"]),
            "REMEDIO": ("REMEDIO",       C["need_remedio"]),
        }

        for ri, row in enumerate(self.keys):
            rf = tk.Frame(kb, bg=C["bg"])
            rf.pack(pady=4)
            self.row_frames.append(rf)
            row_btns = []

            for key in row:
                if ri == 0:  # Sugestoes
                    if key == "FALAR":
                        btn = tk.Button(rf, text="FALAR", font=fAction,
                                        width=9, height=2,
                                        bg=C["purple_dark"], fg=C["purple"],
                                        activebackground="#301a60",
                                        relief="flat", bd=0, cursor="hand2")
                    else:
                        btn = tk.Button(rf, text=key, font=fSuggest,
                                        width=14, height=2,
                                        bg=C["panel"], fg=C["accent"],
                                        activebackground=C["panel2"],
                                        relief="flat", bd=0, cursor="hand2")
                        self.sugestao_buttons.append(btn)

                elif ri == 1:  # Necessidades
                    label, (bg, fg) = NEED_MAP[key]
                    btn = tk.Button(rf, text=label, font=fNeed,
                                    width=13, height=2,
                                    bg=bg, fg=fg, activebackground=bg,
                                    relief="flat", bd=0, cursor="hand2")

                elif key in ["LIMPAR","ESPACO","APAGAR"]:
                    btn = tk.Button(rf, text=key, font=fAction,
                                    width=12, height=2,
                                    bg=C["panel"], fg=C["text_mid"],
                                    activebackground=C["panel2"],
                                    relief="flat", bd=0, cursor="hand2")

                elif key in ["SIM","NAO"]:
                    bg = "#0e3820" if key=="SIM" else C["red_dark"]
                    fg = C["green"] if key=="SIM" else "#ff6b6b"
                    btn = tk.Button(rf, text=key, font=fAction,
                                    width=20, height=2,
                                    bg=bg, fg=fg, activebackground=bg,
                                    relief="flat", bd=0, cursor="hand2")

                else:  # Letras
                    btn = tk.Button(rf, text=key, font=fKey,
                                    width=5, height=2,
                                    bg=C["key"], fg=C["text"],
                                    activebackground=C["key_hi"],
                                    relief="flat", bd=0, cursor="hand2")

                btn.pack(side="left", padx=3)
                self.all_buttons.append(btn)
                row_btns.append(btn)
            self.button_grid.append(row_btns)

        # ── RODAPE ────────────────────────────────────────────
        tk.Frame(self.root, height=2, bg=C["border"]).grid(
            row=2, column=0, sticky="nwe")
        footer = tk.Frame(self.root, bg=C["panel"], height=78)
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_propagate(False)

        ctrl = tk.Frame(footer, bg=C["panel"])
        ctrl.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(ctrl, text="VELOCIDADE", font=fCtrl,
                 fg=C["text_dim"], bg=C["panel"]).grid(row=0, column=0, padx=(0,6))
        self.speed_scale = tk.Scale(
            ctrl, from_=300, to=2500, orient="horizontal", length=210,
            bg=C["panel"], fg=C["text"], highlightthickness=0,
            troughcolor=C["border"], activebackground=C["accent"],
            sliderrelief="flat", showvalue=False,
            command=self._update_speed)
        self.speed_scale.set(self.scan_speed)
        self.speed_scale.grid(row=0, column=1, padx=4)
        self.speed_val_lbl = tk.Label(
            ctrl, text=f"{self.scan_speed} ms",
            font=fCtrl, fg=C["accent"], bg=C["panel"], width=7, anchor="w")
        self.speed_val_lbl.grid(row=0, column=2, padx=(0,20))

        def _btn(col, text, bg, fg, abg, cmd, w=12):
            b = tk.Button(ctrl, text=text, font=F(10,"bold"),
                          width=w, bg=bg, fg=fg,
                          activebackground=abg, relief="flat", bd=0,
                          cursor="hand2", command=cmd)
            b.grid(row=0, column=col, padx=6, ipady=6)
            return b

        self.calib_btn = _btn(3, "CALIBRAR",
                              "#1a3010", "#86efac", "#253d18",
                              self._calibrate)
        _btn(4, "TELEGRAM", C["panel"], C["accent"], C["panel2"], self._open_telegram)
        _btn(5, "SAIR", C["red_dark"], "#ff6b6b", "#4a1818", self._confirm_exit, w=8)

        tk.Label(ctrl,
                 text="PISCADA RAPIDA: seleccionar / entrar no grupo   |   PISCADA LONGA: voltar / inserir espaco",
                 font=fCtrl, fg=C["text_dim"], bg=C["panel"]
                 ).grid(row=1, column=0, columnspan=6, pady=(5,0))

    
    def _start_camera(self):
        def cam_thread():
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self.root.after(0, lambda: self._set_status(
                    "ERRO: CAMERA NAO ENCONTRADA", C["red"]))
                return
            self.root.after(0, lambda: self._set_status(
                "CAMERA ACTIVA — DETECCAO OCULAR EM CURSO", C["green"]))

            while self.running:
                ret, frame = self.cap.read()
                if not ret:
                    time.sleep(0.04)
                    continue

                frame  = cv2.flip(frame, 1)
                ih, iw = frame.shape[:2]
                rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Preview
                try:
                    thumb = cv2.resize(frame, (210, 118))
                    img   = Image.fromarray(cv2.cvtColor(thumb, cv2.COLOR_BGR2RGB))
                    photo = ImageTk.PhotoImage(image=img)
                    self.cam_photo = photo
                    self.root.after(0, lambda p=photo: self._update_cam(p))
                except Exception:
                    pass

                results = self.face_mesh.process(rgb)
                if results.multi_face_landmarks:
                    lms   = results.multi_face_landmarks[0].landmark
                    l_ear = self._calc_ear(lms, self.LEFT_EYE,  iw, ih)
                    r_ear = self._calc_ear(lms, self.RIGHT_EYE, iw, ih)
                    ear   = (l_ear + r_ear) / 2.0
                    self.ear_history.append(ear)
                    s_ear = float(np.mean(self.ear_history))

                    self.root.after(0, lambda e=s_ear:
                        self.ear_label.config(text=f"{e:.3f}"))

                    if self.calibrating:
                        self.calibration_values.append(s_ear)

                    now = time.time()
                    if s_ear < self.ear_threshold:
                        if self.eye_closed_start is None:
                            self.eye_closed_start = now
                        self.root.after(0, lambda: self.blink_indicator.config(
                            text=" OLHO FECHADO ", bg=C["yellow"], fg=C["bg"]))
                    else:
                        self.root.after(0, lambda: self.blink_indicator.config(
                            text="  ", bg=C["bg"], fg=C["bg"]))
                        if self.eye_closed_start is not None:
                            dur = now - self.eye_closed_start
                            if now - self.last_blink_time > self.blink_cooldown:
                                if dur >= self.long_blink_duration:
                                    self.root.after(0, self._handle_long_blink)
                                elif dur > 0.08:
                                    self.root.after(0, self._handle_short_blink)
                                self.last_blink_time = now
                        self.eye_closed_start = None

                time.sleep(0.025)

            if self.cap:
                self.cap.release()

        threading.Thread(target=cam_thread, daemon=True).start()

    def _update_cam(self, photo):
        self.camera_label.config(image=photo, text="", width=210, height=118)

    def _calc_ear(self, landmarks, indices, iw, ih):
        pts = np.array([[landmarks[i].x * iw, landmarks[i].y * ih]
                        for i in indices])
        v1 = np.linalg.norm(pts[1] - pts[5])
        v2 = np.linalg.norm(pts[2] - pts[4])
        h  = np.linalg.norm(pts[0] - pts[3])
        return (v1 + v2) / (2.0 * h)

    
    def _base_colors(self, ri, ci):
        """Devolve (bg, fg) base para um botao identificado por (linha, coluna)."""
        if ri == 1:
            nc_list = [C["need_agua"], C["need_comida"], C["need_wc"],
                       C["need_dor"],  C["need_sos"],    C["need_remedio"]]
            if 0 <= ci < len(nc_list):
                return nc_list[ci][0], nc_list[ci][1]
        if ri == 0:
            if ci == 4: return C["purple_dark"], C["purple"]
            return C["panel"], C["accent"]
        if ri == 5: return C["panel"], C["text_mid"]
        if ri == 6:
            return ("#0e3820", C["green"]) if ci == 0 else (C["red_dark"], "#ff6b6b")
        return C["key"], C["text"]

    def _reset_colors(self):
        for ri, row_btns in enumerate(self.button_grid):
            for ci, btn in enumerate(row_btns):
                try:
                    bg, fg = self._base_colors(ri, ci)
                    btn.configure(bg=bg, fg=fg)
                except Exception:
                    pass

    def _start_scanning(self):
        def scan():
            if not self.scanning or not self.running:
                return
            try:
                self._reset_colors()
                ri = self.current_row

                if self.scan_level == "row":
                    for btn in self.button_grid[ri]:
                        btn.configure(bg=C["row_scan"])
                    self.current_row = (ri + 1) % len(self.keys)

                elif self.scan_level == "group":
                    groups = self.line_groups.get(ri)
                    if not groups:
                        self.scan_level  = "col"
                        self.current_col = 0
                    else:
                        for btn in self.button_grid[ri]:
                            btn.configure(bg=C["row_scan"])
                        gi = self.current_group % len(groups)
                        for idx in groups[gi]:
                            self.button_grid[ri][idx].configure(
                                bg=C["group_scan"], fg=C["bg"])
                        self.current_group = (gi + 1) % len(groups)

                elif self.scan_level == "col":
                    groups = self.line_groups.get(ri)
                    for btn in self.button_grid[ri]:
                        btn.configure(bg=C["row_scan"])
                    if groups:
                        gi   = self.current_group % len(groups)
                        idxs = groups[gi]
                        pos  = self.current_col % len(idxs)
                        ci   = idxs[pos]
                        self.current_col = (pos + 1) % len(idxs)
                    else:
                        row_len          = len(self.button_grid[ri])
                        ci               = self.current_col % row_len
                        self.current_col = (ci + 1) % row_len
                    self.button_grid[ri][ci].configure(
                        bg=C["col_scan"], fg=C["bg"])

            except Exception as e:
                print(f"[scan erro] {e}")

            # SEMPRE reagenda — mesmo se houve erro
            self.root.after(self.scan_speed, scan)

        self.root.after(200, scan)

    
    def _handle_short_blink(self):
        self._flash("SELECCIONADO", C["accent"])
        ri = self.current_row

        if self.scan_level == "row":
            self.current_row = (ri - 1) % len(self.keys)
            ri = self.current_row
            if self.line_groups.get(ri) is not None:
                self.scan_level    = "group"
                self.current_group = 0
            else:
                self.scan_level  = "col"
                self.current_col = 0

        elif self.scan_level == "group":
            self.current_group = (self.current_group - 1) % len(
                self.line_groups[ri])
            self.scan_level  = "col"
            self.current_col = 0

        elif self.scan_level == "col":
            groups = self.line_groups.get(ri)
            if groups:
                gi   = self.current_group
                idxs = groups[gi]
                ci   = idxs[(self.current_col - 1) % len(idxs)]
            else:
                ci = (self.current_col - 1) % len(self.button_grid[ri])

            key = self.button_grid[ri][ci].cget("text")
            if key:
                self._key_pressed(key)
            self.scan_level  = "row"
            self.current_col = 0

    def _handle_long_blink(self):
        self._flash("VOLTAR", C["yellow"])
        if self.scan_level == "col":
            if self.line_groups.get(self.current_row) is not None:
                self.scan_level    = "group"
                self.current_group = 0
            else:
                self.scan_level  = "row"
                self.current_col = 0
        elif self.scan_level == "group":
            self.scan_level = "row"
        else:
            self._key_pressed("ESPACO")

    def _flash(self, text, color):
        self.blink_indicator.config(text=f" {text} ", bg=color, fg=C["bg"])
        self.root.after(400, lambda: self.blink_indicator.config(
            text="  ", bg=C["bg"], fg=C["bg"]))


    def _key_pressed(self, key):
        base = key.strip().split()[0]
        if base in ["ÁGUA","COMIDA","WC","DOR","SOS","REMÉDIO"]:
            self._enviar_necessidade(base)
            return

        if   key == "FALAR":   self._falar_texto()
        elif key == "LIMPAR":  self.typed_text = ""
        elif key == "ESPACO":  self.typed_text += " "
        elif key == "APAGAR":  self.typed_text = self.typed_text[:-1]
        elif key == "SIM":     self.typed_text += " [SIM] "
        elif key == "NAO":     self.typed_text += " [NAO] "
        elif key in self.sugestoes_atuais:
            if len(self.typed_text) >= 3:
                self.typed_text = self.typed_text[:-3].rstrip() + " " + key + " "
            else:
                self.typed_text += key + " "
        else:
            self.typed_text += key

        disp = self.typed_text + "_" if self.typed_text else "_"
        self.text_display.config(text=disp)
        self._atualizar_sugestoes()

    
    def _atualizar_sugestoes(self):
        self.sugestoes_atuais = []
        limpo = self.typed_text.replace(" ","").replace("[","").replace("]","")
        if len(limpo) >= 3:
            pref = limpo[-3:].upper()
            if pref in self.dicionario:
                self.sugestoes_atuais = self.dicionario[pref][:4]
            else:
                found = []
                for k, vs in self.dicionario.items():
                    if k.startswith(pref) or pref.startswith(k):
                        for v in vs:
                            if v.startswith(pref) and v not in found:
                                found.append(v)
                                if len(found) >= 4:
                                    break
                    if len(found) >= 4:
                        break
                self.sugestoes_atuais = found

        for i, btn in enumerate(self.sugestao_buttons):
            if i < len(self.sugestoes_atuais):
                btn.config(text=self.sugestoes_atuais[i])
                self.keys[0][i] = self.sugestoes_atuais[i]
            else:
                btn.config(text="")
                self.keys[0][i] = ""

    
    def _falar_texto(self):
        if not self.typed_text.strip():
            return
        def speak():
            try:
                engine = pyttsx3.init()
                engine.setProperty('rate', 150)
                engine.setProperty('volume', 0.9)
                engine.say(self.typed_text)
                engine.runAndWait()
                engine.stop()
            except Exception as e:
                print(f"Fala erro: {e}")
        threading.Thread(target=speak, daemon=True).start()
        self._set_status("A REPRODUZIR VOZ...", C["green"])

    
    def _enviar_necessidade(self, chave):
        msgs = {
            "AGUA":    "Preciso de agua. Estou com sede.",
            "COMIDA":  "Tenho fome. Pode trazer comida?",
            "WC":      "Preciso ir ao WC.",
            "DOR":     "Estou com dores. Por favor venha.",
            "SOS":     "URGENTE: preciso de ajuda imediata!",
            "REMEDIO": "Esta na hora da minha medicacao.",
        }
        msg  = msgs.get(chave, chave)
        tipo = "sos" if chave == "SOS" else "necessidade"
        self._enviar_telegram(msg, tipo)
        self._set_status(f"ENVIADO: {msg}", C["green"])

    def _enviar_telegram(self, mensagem, tipo="necessidade"):
        token   = self.config.get("telegram_token", _DEFAULT_TOKEN)
        chat_id = self.config.get("telegram_chat_id", "")
        if not token or not chat_id:
            self._set_status("SEM CONFIGURACAO TELEGRAM — clique em TELEGRAM", C["red"])
            return
        pref  = "URGENTE — PEDIDO DE SOCORRO\n\n" if tipo=="sos" else "MENSAGEM DO PACIENTE\n\n"
        texto = (f"{pref}Mensagem: {mensagem}\n"
                 f"Texto actual: {self.typed_text}\n"
                 f"Hora: {time.strftime('%d/%m/%Y %H:%M:%S')}")

        def send():
            try:
                r = requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    data={"chat_id": chat_id, "text": texto}, timeout=10)
                ok = r.status_code == 200
                self.root.after(0, lambda: self._set_status(
                    "MENSAGEM ENVIADA AO CUIDADOR" if ok else f"ERRO [{r.status_code}]",
                    C["green"] if ok else C["red"]))
            except Exception as e:
                self.root.after(0, lambda: self._set_status(
                    f"ERRO DE LIGACAO: {e}", C["red"]))
        threading.Thread(target=send, daemon=True).start()

   
    def _calibrate(self):
        self.calib_btn.config(text="CALIBRANDO...", fg=C["yellow"], bg="#2a2808")
        self._set_status(
            "CALIBRACAO: olhe para a camera e pisque 5 vezes nos proximos 5 segundos",
            C["yellow"])
        self.calibrating        = True
        self.calibration_values = []

        def finish():
            self.calibrating = False
            if self.calibration_values:
                avg = float(np.mean(self.calibration_values))
                self.ear_threshold = avg * 0.75
                self.config["ear_threshold"] = self.ear_threshold
                save_config(self.config)
                self._set_status(
                    "CALIBRACAO CONCLUIDA — sensibilidade ajustada ao utilizador",
                    C["green"])
            else:
                self._set_status("CALIBRACAO FALHOU — tente novamente", C["red"])
            self.calib_btn.config(text="CALIBRAR", fg="#86efac", bg="#1a3010")

        self.root.after(5000, finish)

    
    def _update_speed(self, val):
        self.scan_speed = int(val)
        self.speed_val_lbl.config(text=f"{self.scan_speed} ms")
        self.config["scan_speed"] = self.scan_speed
        save_config(self.config)

   
    def _set_status(self, msg, color=None):
        self.status_label.config(text=msg, fg=color or C["text_mid"])
        self.root.after(5000, lambda: self.status_label.config(
            text="CAMERA ACTIVA — DETECCAO OCULAR EM CURSO", fg=C["green"]))

    
    
    def _open_telegram(self):
        TelegramSetupWindow(self.root, self.config,
                            on_save=lambda: self._set_status(
                                "CONFIGURACAO GUARDADA", C["green"]))

    def _confirm_exit(self):
        if messagebox.askyesno(
                "Sair", "Confirma que pretende fechar o Tradutor Neural?",
                parent=self.root):
            self.on_closing()

    def on_closing(self):
        self.running  = False
        self.scanning = False
        if self.cap:
            self.cap.release()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = BlinkKeyboard()
    app.run()