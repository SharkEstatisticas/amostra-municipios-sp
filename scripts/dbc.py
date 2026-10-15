"""Leitor de arquivos .dbc do DataSUS (DBF comprimido) só com a biblioteca padrão.

O .dbc é um .dbf cujo corpo foi comprimido com o formato "implode" do PKWARE DCL. A descompressão
abaixo segue o algoritmo público de `blast.c` (zlib/contrib/blast, Mark Adler, licença zlib).
Formato: o cabeçalho do DBF vem puro (o tamanho está nos bytes 8 e 9), depois 4 bytes de CRC e,
em seguida, o fluxo comprimido com os registros.
"""
import struct

_LITLEN = bytes([11, 124, 8, 7, 28, 7, 188, 13, 76, 4, 10, 8, 12, 10, 12, 10, 8, 23, 8, 9, 7, 6, 7, 8, 7, 6, 55, 8,
                 23, 24, 12, 11, 7, 9, 11, 12, 6, 7, 22, 5, 7, 24, 6, 11, 9, 6, 7, 22, 7, 11, 38, 7, 9, 8, 25, 11,
                 8, 11, 9, 12, 8, 12, 5, 38, 5, 38, 5, 11, 7, 5, 6, 21, 6, 10, 53, 8, 7, 24, 10, 27, 44, 253, 253,
                 253, 252, 252, 252, 13, 12, 45, 12, 45, 12, 61, 12, 45, 44, 173])
_LENLEN = bytes([2, 35, 36, 53, 38, 23])
_DISTLEN = bytes([2, 20, 53, 230, 247, 151, 248])
_BASE = [3, 2, 4, 5, 6, 7, 8, 9, 10, 12, 16, 24, 40, 72, 136, 264]
_EXTRA = [0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8]
_MAXBITS = 13


def _construir(rep: bytes):
    comprimentos = []
    for byte in rep:
        repete = (byte >> 4) + 1
        comprimentos.extend([byte & 15] * repete)
    contagem = [0] * (_MAXBITS + 1)
    for c in comprimentos:
        contagem[c] += 1
    offs = [0] * (_MAXBITS + 2)
    for c in range(1, _MAXBITS):
        offs[c + 1] = offs[c] + contagem[c]
    simbolos = [0] * len(comprimentos)
    for s, c in enumerate(comprimentos):
        if c:
            simbolos[offs[c]] = s
            offs[c] += 1
    return contagem, simbolos


_LIT = _construir(_LITLEN)
_LEN = _construir(_LENLEN)
_DIST = _construir(_DISTLEN)


class _Bits:
    def __init__(self, dados: bytes, pos: int):
        self.d, self.p, self.buf, self.n = dados, pos, 0, 0

    def bits(self, k: int) -> int:
        while self.n < k:
            self.buf |= self.d[self.p] << self.n
            self.p += 1
            self.n += 8
        v = self.buf & ((1 << k) - 1)
        self.buf >>= k
        self.n -= k
        return v

    def decodificar(self, tabela) -> int:
        contagem, simbolos = tabela
        code = first = index = 0
        for comp in range(1, _MAXBITS + 1):
            code |= self.bits(1) ^ 1
            c = contagem[comp]
            if code < first + c:
                return simbolos[index + (code - first)]
            index += c
            first = (first + c) << 1
            code <<= 1
        raise ValueError('código inválido no fluxo comprimido')


def descomprimir(corpo: bytes) -> bytes:
    b = _Bits(corpo, 0)
    lit = b.bits(8)
    dic = b.bits(8)
    if lit > 1 or not 4 <= dic <= 6:
        raise ValueError('cabeçalho do fluxo implode inválido')
    saida = bytearray()
    while True:
        if b.bits(1):
            s = b.decodificar(_LEN)
            comp = _BASE[s] + b.bits(_EXTRA[s])
            if comp == 519:
                break
            s = 2 if comp == 2 else dic
            dist = (b.decodificar(_DIST) << s) + b.bits(s) + 1
            for _ in range(comp):
                saida.append(saida[-dist])
        else:
            saida.append(b.decodificar(_LIT) if lit else b.bits(8))
    return bytes(saida)


def ler_dbc(caminho: str):
    """Devolve (campos, registros): campos = [(nome, tipo, tamanho)], registros = lista de dicts de str."""
    with open(caminho, 'rb') as f:
        dados = f.read()
    tam_cab = struct.unpack('<H', dados[8:10])[0]
    corpo = descomprimir(dados[tam_cab + 4:])
    dbf = dados[:tam_cab] + corpo
    n_reg = struct.unpack('<I', dbf[4:8])[0]
    tam_reg = struct.unpack('<H', dbf[10:12])[0]
    campos, p = [], 32
    while dbf[p] != 0x0D:
        nome = dbf[p:p + 11].split(b'\x00')[0].decode('latin-1')
        campos.append((nome, chr(dbf[p + 11]), dbf[p + 16]))
        p += 32
    return campos, dbf, tam_cab, tam_reg, n_reg
