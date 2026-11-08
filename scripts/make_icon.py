from pathlib import Path
import struct
from PyQt6.QtCore import QByteArray, QBuffer, QIODevice
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtSvg import QSvgRenderer
root = Path(__file__).resolve().parents[1] / "assets"
renderer = QSvgRenderer(str(root / "icon.svg"))
images = []
for size in (16, 24, 32, 48, 64, 128, 256):
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    images.append((size, bytes(data)))
    if size == 256:
        image.save(str(root / "icon.png"))
offset = 6 + 16 * len(images)
entries = []
for size, data in images:
    entries.append(struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset))
    offset += len(data)
(root / "icon.ico").write_bytes(struct.pack("<HHH", 0, 1, len(images)) + b"".join(entries) + b"".join(data for _, data in images))
