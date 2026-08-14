"""Yuke's BPE (byte pair encoding) decompressor.  Python 3 port.

The original used numpy purely for a fixed uint8 scratch array; a bytearray
does the same job with no dependency.
"""
from io import BytesIO

STACK_SIZE = 4608


def read_int(content, offset, size):
    return int.from_bytes(content[offset:offset + size], "little")


def xgetc(stream):
    b = stream.read(1)
    if not b:
        return -1
    return b[0]


def yuke_bpe(input_buffer, unbpe_size, fillout_size):
    in_buf = BytesIO(input_buffer)
    out_buf = BytesIO()
    stack = bytearray(STACK_SIZE)
    count = 0
    out_buf_size = 0

    while True:
        i = 0
        while True:
            c = xgetc(in_buf)
            if c < 0:
                break
            if c > 127:
                c -= 127
                while c > 0 and i < 256:
                    stack[i * 2] = i
                    c -= 1
                    i += 1
            c += 1
            while c > 0 and i < 256:
                n = xgetc(in_buf)
                if n < 0:
                    break
                stack[i * 2] = n
                if i != n:
                    n = xgetc(in_buf)
                    if n < 0:
                        break
                    stack[i * 2 + 1] = n
                c -= 1
                i += 1
            if not i < 256:
                break

        n = xgetc(in_buf)
        if n < 0:
            break
        size = n
        n = xgetc(in_buf)
        if n < 0:
            break
        size |= n << 8

        while size | count != 0:
            if count != 0:
                count -= 1
                n = stack[count + 512]
            else:
                n = xgetc(in_buf)
                if n < 0:
                    break
                size -= 1
            c = stack[n * 2]
            if n == c:
                # literal byte
                if out_buf_size >= unbpe_size:
                    return out_buf.getvalue()
                out_buf.write(bytes([n]))
                out_buf_size += 1
                continue
            # pair: push right then left back onto the stack
            if count + 512 + 2 > STACK_SIZE:
                return out_buf.getvalue()
            stack[count + 512] = stack[n * 2 + 1]
            stack[count + 512 + 1] = c
            count += 2

    if fillout_size != 0:
        out_buf.write(b"\x00" * (unbpe_size - out_buf_size))
    return out_buf.getvalue()


def extract_bpe(input_buffer):
    unbpe_size = read_int(input_buffer, 12, 4)
    return yuke_bpe(input_buffer[16:], unbpe_size, 1)
