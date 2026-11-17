"""Abertura segura de imagens raster decodificadas pelo Pillow no servidor.

O Pillow detecta o formato pelo conteúdo, não pelo tipo declarado: uma data
URL ``image/png`` pode carregar TIFF, GIF, BMP ou qualquer outro formato que o
Pillow saiba ler, e cada decodificador extra é superfície de ataque. Aqui só
PNG e JPEG são aceitos, e o conteúdo precisa começar pela assinatura real do
tipo declarado. O Pillow recebe ``formats=[...]`` com esse único formato, para
nunca tentar outro decodificador.
"""
import io

PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
JPEG_SIGNATURE = b'\xff\xd8\xff'

_FORMAT_BY_SUBTYPE = {'png': 'PNG', 'jpeg': 'JPEG', 'jpg': 'JPEG'}
_SIGNATURE_BY_FORMAT = {'PNG': PNG_SIGNATURE, 'JPEG': JPEG_SIGNATURE}


def pillow_format_for(subtype):
    """Formato Pillow ('PNG'/'JPEG') para o subtipo ``image/<subtype>``, ou None."""
    return _FORMAT_BY_SUBTYPE.get(str(subtype or '').strip().lower())


def has_signature(content, pillow_format):
    signature = _SIGNATURE_BY_FORMAT.get(pillow_format)
    return bool(signature) and isinstance(content, (bytes, bytearray)) and bytes(content).startswith(signature)


def open_verified(content, pillow_format, error_message):
    """Abre ``content`` só como ``pillow_format``; qualquer divergência vira ValueError.

    Devolve a imagem aberta (preguiçosa, como ``Image.open``); quem chama usa
    ``with`` e faz ``load()``. Erros de decodificação e de bomba de
    descompressão viram ``ValueError(error_message)``, sem refletir conteúdo.
    """
    if not has_signature(content, pillow_format):
        raise ValueError(error_message)
    from PIL import Image, UnidentifiedImageError

    try:
        image = Image.open(io.BytesIO(bytes(content)), formats=[pillow_format])
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError):
        raise ValueError(error_message) from None
    if image.format != pillow_format:
        image.close()
        raise ValueError(error_message)
    return image


__all__ = ['JPEG_SIGNATURE', 'PNG_SIGNATURE', 'has_signature', 'open_verified', 'pillow_format_for']
