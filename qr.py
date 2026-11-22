"""Minimal QR Code generator (ISO/IEC 18004), pure Python, no dependencies.

Byte mode, error correction level M, versions 1-40, automatic mask selection.
Public API:
    matrix(text)  -> list of rows of booleans (True = dark module)
    svg(text, ...) -> inline SVG string
"""

# ---- tables (index = version; index 0 unused) for error correction level M ----
_ECC_PER_BLOCK_M = (-1, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26,
                    26, 26, 26, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28,
                    28, 28, 28)
_NUM_BLOCKS_M = (-1, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16, 17, 17,
                 18, 20, 21, 23, 25, 26, 28, 29, 31, 33, 35, 37, 38, 40, 43, 45, 47, 49)
_FORMAT_BITS_M = 0           # error correction level M


def _raw_modules(ver: int) -> int:
    n = (16 * ver + 128) * ver + 64
    if ver >= 2:
        a = ver // 7 + 2
        n -= (25 * a - 10) * a - 55
        if ver >= 7:
            n -= 36
    return n


def _data_codewords(ver: int) -> int:
    return _raw_modules(ver) // 8 - _ECC_PER_BLOCK_M[ver] * _NUM_BLOCKS_M[ver]


# ---- Reed-Solomon over GF(256), polynomial 0x11D ----
def _gf_mul(x: int, y: int) -> int:
    z = 0
    for i in range(7, -1, -1):
        z = (z << 1) ^ ((z >> 7) * 0x11D)
        z ^= ((y >> i) & 1) * x
    return z


def _rs_divisor(degree: int):
    result = [0] * (degree - 1) + [1]
    root = 1
    for _ in range(degree):
        for j in range(degree):
            result[j] = _gf_mul(result[j], root)
            if j + 1 < degree:
                result[j] ^= result[j + 1]
        root = _gf_mul(root, 2)
    return result


def _rs_remainder(data, divisor):
    result = [0] * len(divisor)
    for b in data:
        factor = b ^ result.pop(0)
        result.append(0)
        for i, coef in enumerate(divisor):
            result[i] ^= _gf_mul(coef, factor)
    return result


def _interleave(data, ver):
    n_blocks, ecc_len = _NUM_BLOCKS_M[ver], _ECC_PER_BLOCK_M[ver]
    raw = _raw_modules(ver) // 8
    n_short = n_blocks - raw % n_blocks
    short_len = raw // n_blocks
    div = _rs_divisor(ecc_len)
    blocks, k = [], 0
    for i in range(n_blocks):
        dat = list(data[k:k + short_len - ecc_len + (0 if i < n_short else 1)])
        k += len(dat)
        ecc = _rs_remainder(dat, div)
        if i < n_short:
            dat.append(0)
        blocks.append(dat + ecc)
    out = []
    for i in range(len(blocks[0])):
        for j, blk in enumerate(blocks):
            if i != short_len - ecc_len or j >= n_short:
                out.append(blk[i])
    return out


def _align_positions(ver: int, size: int):
    if ver == 1:
        return []
    n = ver // 7 + 2
    step = 26 if ver == 32 else (ver * 4 + n * 2 + 1) // (n * 2 - 2) * 2
    pos = [6] + [0] * (n - 1)
    p = size - 7
    for i in range(n - 1, 0, -1):
        pos[i] = p
        p -= step
    return pos


class _Builder:
    def __init__(self, ver: int, codewords):
        self.ver, self.size = ver, ver * 4 + 17
        self.m = [[False] * self.size for _ in range(self.size)]
        self.fn = [[False] * self.size for _ in range(self.size)]
        self._function_patterns()
        self._place(codewords)

    def _set(self, x, y, dark):
        self.m[y][x] = dark
        self.fn[y][x] = True

    def _function_patterns(self):
        s = self.size
        for i in range(s):
            self._set(6, i, i % 2 == 0)
            self._set(i, 6, i % 2 == 0)
        for cx, cy in ((3, 3), (s - 4, 3), (3, s - 4)):
            for dy in range(-4, 5):
                for dx in range(-4, 5):
                    x, y = cx + dx, cy + dy
                    if 0 <= x < s and 0 <= y < s:
                        self._set(x, y, max(abs(dx), abs(dy)) not in (2, 4))
        pos = _align_positions(self.ver, s)
        n = len(pos)
        for i in range(n):
            for j in range(n):
                if (i == 0 and j == 0) or (i == 0 and j == n - 1) or (i == n - 1 and j == 0):
                    continue
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        self._set(pos[i] + dx, pos[j] + dy, max(abs(dx), abs(dy)) != 1)
        self._format(0)
        self._version()

    def _format(self, mask):
        data = (_FORMAT_BITS_M << 3) | mask
        rem = data
        for _ in range(10):
            rem = (rem << 1) ^ ((rem >> 9) * 0x537)
        bits = ((data << 10) | rem) ^ 0x5412
        b = lambda i: (bits >> i) & 1 == 1
        s = self.size
        for i in range(6):
            self._set(8, i, b(i))
        self._set(8, 7, b(6))
        self._set(8, 8, b(7))
        self._set(7, 8, b(8))
        for i in range(9, 15):
            self._set(14 - i, 8, b(i))
        for i in range(8):
            self._set(s - 1 - i, 8, b(i))
        for i in range(8, 15):
            self._set(8, s - 15 + i, b(i))
        self._set(8, s - 8, True)

    def _version(self):
        if self.ver < 7:
            return
        rem = self.ver
        for _ in range(12):
            rem = (rem << 1) ^ ((rem >> 11) * 0x1F25)
        bits = (self.ver << 12) | rem
        for i in range(18):
            bit = (bits >> i) & 1 == 1
            a, b = self.size - 11 + i % 3, i // 3
            self._set(a, b, bit)
            self._set(b, a, bit)

    def _place(self, data):
        s, i = self.size, 0
        right = s - 1
        while right >= 1:
            if right == 6:
                right = 5
            for vert in range(s):
                for j in range(2):
                    x = right - j
                    upward = ((right + 1) & 2) == 0
                    y = s - 1 - vert if upward else vert
                    if not self.fn[y][x] and i < len(data) * 8:
                        self.m[y][x] = ((data[i >> 3] >> (7 - (i & 7))) & 1) == 1
                        i += 1
            right -= 2

    def _mask(self, mask):
        for y in range(self.size):
            for x in range(self.size):
                if self.fn[y][x]:
                    continue
                inv = [(x + y) % 2 == 0, y % 2 == 0, x % 3 == 0, (x + y) % 3 == 0,
                       (x // 3 + y // 2) % 2 == 0, x * y % 2 + x * y % 3 == 0,
                       (x * y % 2 + x * y % 3) % 2 == 0, ((x + y) % 2 + x * y % 3) % 2 == 0][mask]
                if inv:
                    self.m[y][x] = not self.m[y][x]

    def _penalty(self):
        s, m, score = self.size, self.m, 0
        rows = ["".join("1" if c else "0" for c in r) for r in m]
        cols = ["".join("1" if m[y][x] else "0" for y in range(s)) for x in range(s)]
        for line in rows + cols:
            run, prev = 0, ""
            for ch in line:
                if ch == prev:
                    run += 1
                    score += 3 if run == 5 else (1 if run > 5 else 0)
                else:
                    prev, run = ch, 1
            for pat in ("00001011101", "10111010000"):
                k = line.find(pat)
                while k != -1:
                    score += 40
                    k = line.find(pat, k + 1)
        for y in range(s - 1):
            for x in range(s - 1):
                if m[y][x] == m[y][x + 1] == m[y + 1][x] == m[y + 1][x + 1]:
                    score += 3
        dark = sum(sum(r) for r in m)
        total = s * s
        score += ((abs(dark * 20 - total * 10) + total - 1) // total - 1) * 10
        return score

    def finish(self):
        best, best_score = 0, None
        for mask in range(8):
            self._mask(mask)
            self._format(mask)
            sc = self._penalty()
            if best_score is None or sc < best_score:
                best, best_score = mask, sc
            self._mask(mask)            # undo
        self._mask(best)
        self._format(best)
        return self.m


def matrix(text: str):
    data = text.encode("utf-8")
    for ver in range(1, 41):
        cap_bits = _data_codewords(ver) * 8
        count_bits = 8 if ver < 10 else 16
        if 4 + count_bits + len(data) * 8 <= cap_bits:
            break
    else:
        raise ValueError("text too long for a QR code")
    bits = []

    def put(val, n):
        bits.extend((val >> i) & 1 for i in range(n - 1, -1, -1))

    put(0b0100, 4)
    put(len(data), count_bits)
    for b in data:
        put(b, 8)
    put(0, min(4, cap_bits - len(bits)))
    put(0, -len(bits) % 8)
    pad = 0xEC
    while len(bits) < cap_bits:
        put(pad, 8)
        pad ^= 0xEC ^ 0x11
    words = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
    return _Builder(ver, _interleave(words, ver)).finish()


def svg(text: str, border: int = 3, dark: str = "#1C1C1C") -> str:
    """Inline SVG (transparent background, one path, crisp edges)."""
    m = matrix(text)
    n = len(m)
    d = []
    for y, row in enumerate(m):
        x = 0
        while x < n:
            if row[x]:
                start = x
                while x < n and row[x]:
                    x += 1
                d.append(f"M{start + border},{y + border}h{x - start}v1h-{x - start}z")
            else:
                x += 1
    size = n + 2 * border
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
            f'shape-rendering="crispEdges"><path d="{"".join(d)}" fill="{dark}"/></svg>')
