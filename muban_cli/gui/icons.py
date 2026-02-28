"""
Custom icon utilities for palette-aware icons.

These icons automatically adapt to dark/light themes by using
the current palette's text color.
"""

from PyQt6.QtCore import Qt,QPoint
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QPolygon
from PyQt6.QtWidgets import QApplication


def get_text_color() -> QColor:
    """Get the current palette's text color."""
    app = QApplication.instance()
    if app and isinstance(app, QApplication):
        palette = app.palette()
        return palette.color(palette.ColorRole.WindowText)
    return QColor(0, 0, 0)  # Fallback to black


def create_play_icon(size: int = 16) -> QIcon:
    """Create a play triangle icon using palette text color."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    color = get_text_color()
    painter.setBrush(QBrush(color))
    painter.setPen(Qt.PenStyle.NoPen)
    
    # Draw play triangle
    margin = size // 4
    points = [
        QPoint(margin, margin),
        QPoint(size - margin, size // 2),
        QPoint(margin, size - margin),
    ]
    painter.drawPolygon(QPolygon(points))
    painter.end()
    
    return QIcon(pixmap)


def create_arrow_up_icon(size: int = 16) -> QIcon:
    """Create an up arrow icon using palette text color."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    color = get_text_color()
    painter.setBrush(QBrush(color))
    painter.setPen(Qt.PenStyle.NoPen)
    
    # Draw up arrow
    margin = size // 4
    points = [
        QPoint(size // 2, margin),
        QPoint(size - margin, size - margin),
        QPoint(margin, size - margin),
    ]
    painter.drawPolygon(QPolygon(points))
    painter.end()
    
    return QIcon(pixmap)


def create_arrow_down_icon(size: int = 16) -> QIcon:
    """Create a down arrow icon using palette text color."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    color = get_text_color()
    painter.setBrush(QBrush(color))
    painter.setPen(Qt.PenStyle.NoPen)
    
    # Draw down arrow
    margin = size // 4
    points = [
        QPoint(margin, margin),
        QPoint(size - margin, margin),
        QPoint(size // 2, size - margin),
    ]
    painter.drawPolygon(QPolygon(points))
    painter.end()
    
    return QIcon(pixmap)


def create_arrow_left_icon(size: int = 16) -> QIcon:
    """Create a left arrow icon using palette text color."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    color = get_text_color()
    painter.setBrush(QBrush(color))
    painter.setPen(Qt.PenStyle.NoPen)
    
    # Draw left arrow
    margin = size // 4
    points = [
        QPoint(margin, size // 2),
        QPoint(size - margin, margin),
        QPoint(size - margin, size - margin),
    ]
    painter.drawPolygon(QPolygon(points))
    painter.end()
    
    return QIcon(pixmap)


def create_arrow_right_icon(size: int = 16) -> QIcon:
    """Create a right arrow icon using palette text color."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    color = get_text_color()
    painter.setBrush(QBrush(color))
    painter.setPen(Qt.PenStyle.NoPen)
    
    # Draw right arrow
    margin = size // 4
    points = [
        QPoint(margin, margin),
        QPoint(size - margin, size // 2),
        QPoint(margin, size - margin),
    ]
    painter.drawPolygon(QPolygon(points))
    painter.end()
    
    return QIcon(pixmap)


def create_logout_icon(size: int = 16) -> QIcon:
    """Create a logout/exit icon using palette text color."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    color = get_text_color()
    pen = QPen(color)
    pen.setWidth(2)
    painter.setPen(pen)
    
    margin = size // 4
    # Draw door frame (right part open)
    painter.drawLine(margin, margin, margin, size - margin)
    painter.drawLine(margin, margin, size // 2, margin)
    painter.drawLine(margin, size - margin, size // 2, size - margin)
    
    # Draw arrow pointing out
    arrow_y = size // 2
    painter.drawLine(size // 3, arrow_y, size - margin, arrow_y)
    painter.drawLine(size - margin - 3, arrow_y - 3, size - margin, arrow_y)
    painter.drawLine(size - margin - 3, arrow_y + 3, size - margin, arrow_y)
    
    painter.end()
    
    return QIcon(pixmap)


def create_login_icon(size: int = 16) -> QIcon:
    """Create a login/lock icon using palette text color."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    color = get_text_color()
    pen = QPen(color)
    pen.setWidth(2)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    
    margin = size // 5
    # Draw lock body (rectangle)
    body_top = size // 2
    painter.drawRect(margin, body_top, size - 2 * margin, size - body_top - margin)
    
    # Draw lock shackle (arc)
    shackle_width = size - 4 * margin
    shackle_left = 2 * margin
    painter.drawArc(shackle_left, margin, shackle_width, size // 2, 0, 180 * 16)
    
    painter.end()
    
    return QIcon(pixmap)


def create_copy_icon(size: int = 16) -> QIcon:
    """Create a copy/clipboard icon using palette text color."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    color = get_text_color()
    pen = QPen(color)
    pen.setWidth(1)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    
    # Draw two overlapping rectangles (back and front)
    margin = 2
    offset = 3
    rect_w = size - margin * 2 - offset
    rect_h = size - margin * 2 - offset
    
    # Back rectangle (offset to top-left)
    painter.drawRect(margin, margin, rect_w, rect_h)
    
    # Front rectangle (offset to bottom-right)
    painter.drawRect(margin + offset, margin + offset, rect_w, rect_h)
    
    painter.end()
    
    return QIcon(pixmap)
